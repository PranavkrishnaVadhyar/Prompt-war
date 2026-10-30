import csv
import io
import json
from uuid import UUID
import psycopg
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from . import participant_import
from . import auth, competition, evaluation, schemas, submissions, supabase, panel_jobs, model_panel, questions
from .config import PROJECT, settings
from .db import audit, database, synchronize

app = FastAPI(title="Prompt War — VYUHAM ’26", version="1.0.0")


class RequestSizeLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST","PUT","PATCH"):
            return await self.app(scope,receive,send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body",b""))
            if size > settings().max_submission_bytes + 65536:
                return await JSONResponse(status_code=413,content={"detail":"The combined submission text is too large. Reduce it within the published limits."})(scope,receive,send)
            messages.append(message)
            if not message.get("more_body",False):
                break
        iterator = iter(messages)
        async def replay():
            try:
                return next(iterator)
            except StopIteration:
                return await receive()
        await self.app(scope,replay,send)


app.add_middleware(RequestSizeLimit)
app.add_middleware(CORSMiddleware, allow_origins=settings().origins, allow_credentials=True,
                   allow_methods=["GET","POST","PUT"], allow_headers=["Content-Type","X-CSRF-Token"])
api = APIRouter(prefix="/api", dependencies=[Depends(auth.csrf_guard)])
organiser = auth.roles("organiser")
judge = auth.roles("judge","organiser")
staff = auth.roles("volunteer","organiser")


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.update({
        "X-Content-Type-Options":"nosniff", "X-Frame-Options":"DENY",
        "Referrer-Policy":"same-origin", "Permissions-Policy":"camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
        "Cache-Control":"no-store",
    })
    if settings().cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


@app.exception_handler(psycopg.IntegrityError)
async def integrity_error(request, error):
    return JSONResponse(status_code=409,content={"detail":"This record conflicts with an existing team, account, or competition rule. Refresh and check the submitted details."})


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # Never echo request bodies, CSV password columns or credentials in errors.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": e["loc"], "msg": e["msg"], "type": e["type"]}
        for e in error.errors()
    ]})


@app.exception_handler(psycopg.Error)
async def database_error(request, error):
    return JSONResponse(status_code=503,content={"detail":"The competition database is unavailable. Ask an organiser to check database setup or connectivity."})


@api.get("/health")
def health():
    return {"status":"ok","service":"prompt-war"}


@api.get("/auth/session")
def session(request: Request, response: Response):
    return {"csrf_token":auth.csrf_token(request,response)}


def require_approved(conn, email):
    return conn.execute("SELECT user_id FROM members WHERE email=%s AND active", (str(email).lower(),)).fetchone()


def finish_login(response, session_data):
    with database() as conn:
        member = conn.execute("SELECT user_id FROM members WHERE user_id=%s AND active", (session_data["user"]["id"],)).fetchone()
    if not member:
        raise HTTPException(403,"This account is not approved for Prompt War.")
    auth.write_session(response,session_data)
    return {"message":"Signed in."}


@api.post("/auth/login")
def login(body: schemas.PasswordLogin, request: Request, response: Response):
    auth.throttle(request,str(body.email))
    with database() as conn:
        approved = require_approved(conn,body.email)
    if not approved:
        raise HTTPException(401,"Unable to sign in with these details. Contact an organiser if your account is not approved.")
    data = supabase.call("POST","/auth/v1/token?grant_type=password",{"email":str(body.email).lower(),"password":body.password})
    return finish_login(response,data)


@api.post("/auth/refresh")
def refresh(request: Request, response: Response):
    token = request.cookies.get(auth.REFRESH)
    if not token:
        raise HTTPException(401,"Sign in again to continue.")
    data = supabase.call("POST","/auth/v1/token?grant_type=refresh_token",{"refresh_token":token})
    return finish_login(response,data)


@api.post("/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(auth.ACCESS)
    if token:
        try:
            supabase.call("POST","/auth/v1/logout?scope=local",token=token)
        except HTTPException:
            pass
    auth.clear_session(response)
    return {"message":"Signed out. Also sign out of your personal LLM account before leaving this computer."}


@api.get("/auth/me")
def me(user=Depends(auth.current_user)):
    return user


@api.get("/dashboard")
def dashboard(user=Depends(auth.current_user)):
    with database() as conn:
        synchronize(conn)
        rounds = conn.execute("SELECT * FROM rounds ORDER BY stage").fetchall()
        team = conn.execute("SELECT * FROM teams WHERE id=%s", (user["team_id"],)).fetchone() if user["team_id"] else None
        entries = conn.execute("""SELECT e.round_id,e.outcome,e.extension_until,
            CASE WHEN r.published_at IS NOT NULL THEN e.placement END AS placement,
            CASE WHEN r.published_at IS NOT NULL THEN e.final_score END AS final_score
            FROM entries e JOIN rounds r ON r.id=e.round_id WHERE e.team_id=%s""", (user["team_id"],)).fetchall() if team else []
        now = conn.execute("SELECT now() AS now").fetchone()["now"]
    return {"user":user,"team":team,"rounds":[competition.public_round(r) for r in rounds],"entries":entries,"server_now":now}


@api.get("/rounds/{round_id}/workspace")
def workspace(round_id: UUID, user=Depends(auth.current_user)):
    with database() as conn:
        synchronize(conn)
        row = competition.get_round(conn,round_id)
        entry = conn.execute("SELECT * FROM entries WHERE round_id=%s AND team_id=%s", (round_id,user["team_id"])).fetchone() if user["team_id"] else None
        if user["role"] == "participant" and not entry:
            raise HTTPException(403,"Your team is not qualified for this round.")
        result = competition.public_round(row)
        released = row["status"] not in ("waiting","briefing")
        if user['role']=='participant' and released and entry['outcome']!='disqualified':
            result.update(questions.display_context(questions.for_team(conn,row,user['team_id'])))
        elif user['role'] in ('organiser','judge'):
            # Staff configuration is shared instructions, not any candidate's random target.
            result.update({key:row[key] for key in ('task','flawed_output','expected_output','banned_words')})
        if user['role']=='organiser':
            result['bank']={'active_questions':questions.bank_count(conn,row['kind']),
                            'assigned_teams':conn.execute('SELECT count(*) AS n FROM question_assignments WHERE round_id=%s',(round_id,)).fetchone()['n']}
        result["rubric"] = evaluation.RUBRICS[row["kind"]]
        if entry:
            result["entry"] = {"outcome":entry["outcome"],"extension_until":entry["extension_until"]}
            result["submissions"] = conn.execute("""SELECT id,source_type,assignment_id,attempts,selected_attempt,created_at,confirmed_at,sha256,byte_size
                FROM submissions WHERE round_id=%s AND team_id=%s ORDER BY created_at DESC""", (round_id,user["team_id"])).fetchall()
        return result


@api.post("/practice/preview")
def practice_preview(body: schemas.SubmissionCreate, user=Depends(auth.roles("participant"))):
    return {**submissions.validate_entry(body,5),"message":"Practice only. These prompts and answers were not stored or entered into competition results."}


@api.post("/rounds/{round_id}/submissions")
def submit_text(round_id: UUID, body: schemas.SubmissionCreate, user=Depends(auth.roles("participant"))):
    with database() as conn:
        synchronize(conn)
        return submissions.create(conn,round_id,user,body)


@api.post("/submissions/{submission_id}/confirm")
def confirm(submission_id: UUID, body: schemas.Confirm, user=Depends(auth.roles("participant"))):
    with database() as conn:
        synchronize(conn)
        row = conn.execute("SELECT * FROM submissions WHERE id=%s AND team_id=%s", (submission_id,user["team_id"])).fetchone()
        if not row:
            raise HTTPException(404,"Submission not found.")
        if row["confirmed_at"]:
            return {"id":row["id"],"confirmed_at":row["confirmed_at"],"sha256":row["sha256"],"message":"This version is already confirmed."}
        submissions.entry_for_submission(conn,row["round_id"],user["team_id"])
        # Another member may have confirmed while this request waited on the round lock.
        row = conn.execute("SELECT * FROM submissions WHERE id=%s FOR UPDATE", (submission_id,)).fetchone()
        if row["confirmed_at"]:
            return {"id":row["id"],"confirmed_at":row["confirmed_at"],"sha256":row["sha256"],"message":"This version is already confirmed."}
        # A newer confirmed version may not be replaced by an old draft.
        if conn.execute("SELECT 1 FROM submissions WHERE team_id=%s AND round_id=%s AND confirmed_at IS NOT NULL AND created_at>%s", (user["team_id"],row["round_id"],row["created_at"])).fetchone():
            raise HTTPException(409,"A newer submission version is already confirmed. Save a new version to replace it.")
        if body.selected_attempt > len(row["attempts"]):
            raise HTTPException(400,"The selected attempt does not exist.")
        digest,size=(submissions.content_digest(row["attempts"],body.selected_attempt) if row["source_type"]=='direct' else (row["sha256"],row["byte_size"]))
        result = conn.execute("UPDATE submissions SET selected_attempt=%s,sha256=%s,byte_size=%s,confirmed_at=now() WHERE id=%s RETURNING id,confirmed_at,sha256", (body.selected_attempt,digest,size,submission_id)).fetchone()
        audit(conn,user["user_id"],"confirm_submission",{"submission_id":submission_id,"selected_attempt":body.selected_attempt})
        return {**result,"message":"Final submission confirmed. This receipt uses server time."}


@api.get("/submissions/{submission_id}")
def submission_detail(submission_id: UUID, user=Depends(auth.current_user)):
    with database() as conn:
        row = conn.execute("SELECT s.*,r.status FROM submissions s JOIN rounds r ON r.id=s.round_id WHERE s.id=%s", (submission_id,)).fetchone()
        if not row:
            raise HTTPException(404,"Submission not found.")
        own = user["role"] == "participant" and row["team_id"] == user["team_id"]
        judging = user["role"] in ("organiser","judge") and row["status"] in ("evaluation","results","closed") and row["confirmed_at"]
        if not (own or judging):
            raise HTTPException(403,"You cannot access this submission.")
    return {key:row[key] for key in ("id","source_type","assignment_id","attempts","selected_attempt","created_at","confirmed_at","sha256","byte_size")}


@api.get('/admin/questions')
def question_bank(kind: str | None=None, user=Depends(organiser)):
    if kind is not None and kind not in ('fix','recreate','word_ban'):
        raise HTTPException(400,'Unknown question-bank kind.')
    with database() as conn:
        return conn.execute('SELECT * FROM question_bank WHERE (%s::text IS NULL OR kind=%s) ORDER BY kind,source_number',(kind,kind)).fetchall()


@api.get('/admin/rounds/{round_id}/assignments')
def assigned_questions(round_id: UUID, user=Depends(organiser)):
    with database() as conn:
        competition.get_round(conn,round_id)
        return conn.execute('''SELECT a.id,a.team_id,a.question_id,a.assigned_at,a.snapshot,t.name AS team_name,t.workstation
            FROM question_assignments a JOIN teams t ON t.id=a.team_id WHERE a.round_id=%s ORDER BY t.name''',(round_id,)).fetchall()


@api.get("/rounds/{round_id}/results")
def results(round_id: UUID, user=Depends(auth.current_user)):
    with database() as conn:
        row = competition.get_round(conn,round_id)
        if not row["published_at"]:
            raise HTTPException(409,"Results have not been published.")
        return conn.execute("""SELECT t.name,e.outcome,e.placement,e.final_score FROM entries e JOIN teams t ON t.id=e.team_id
            WHERE e.round_id=%s ORDER BY e.placement NULLS LAST,t.name""", (round_id,)).fetchall()


@api.get("/admin/overview")
def overview(user=Depends(staff)):
    with database() as conn:
        synchronize(conn)
        teams = conn.execute("SELECT t.*,array_agg(m.email ORDER BY m.email) AS emails FROM teams t LEFT JOIN members m ON m.team_id=t.id GROUP BY t.id ORDER BY t.name").fetchall()
        entries = conn.execute("""SELECT n.round_id,n.team_id,n.outcome,n.extension_until,
            (SELECT count(*) FROM submissions s WHERE s.team_id=n.team_id AND s.round_id=n.round_id) AS uploads,
            (SELECT max(confirmed_at) FROM submissions s WHERE s.team_id=n.team_id AND s.round_id=n.round_id) AS confirmed_at
            FROM entries n""").fetchall()
        incidents = conn.execute("SELECT i.*,t.name AS team_name FROM incidents i JOIN teams t ON t.id=i.team_id ORDER BY i.created_at DESC LIMIT 100").fetchall()
        members = conn.execute("SELECT email,role,active FROM members WHERE role<>'participant' ORDER BY role,email").fetchall() if user["role"] == "organiser" else []
    return {"teams":teams,"entries":entries,"incidents":incidents,"staff":members}


@api.post("/admin/teams")
def add_team(body: schemas.TeamCreate, user=Depends(organiser)):
    emails = [str(e).lower() for e in body.emails]
    if len(set(emails)) != len(emails):
        raise HTTPException(400,"Use distinct member emails.")
    with database() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(803126)")
        first = conn.execute("SELECT id,status FROM rounds WHERE stage=1 FOR UPDATE").fetchone()
        if not first or first["status"] != "waiting":
            raise HTTPException(409,"Team enrolment closes when the first briefing opens.")
        if conn.execute("SELECT count(*) AS n FROM teams").fetchone()["n"] >= 22:
            raise HTTPException(409,"The 22-team roster is full.")
        if conn.execute("SELECT 1 FROM members WHERE email=ANY(%s)", (emails,)).fetchone():
            raise HTTPException(409,"A supplied email already belongs to a Prompt War account.")
        ids = [supabase.ensure_user(email) for email in emails]
        team = conn.execute("INSERT INTO teams(name,workstation) VALUES (%s,%s) RETURNING *", (body.name,body.workstation)).fetchone()
        for email,user_id in zip(emails,ids):
            conn.execute("INSERT INTO members(user_id,email,role,team_id) VALUES (%s,%s,'participant',%s)", (user_id,email,team["id"]))
        conn.execute("INSERT INTO entries(round_id,team_id) VALUES (%s,%s)", (first["id"],team["id"]))
        audit(conn,user["user_id"],"create_team",{"team_id":team["id"],"emails":emails})
        return team


@api.post("/admin/participants/import")
def import_participants(body: schemas.ParticipantImport, user=Depends(organiser)):
    return participant_import.run(body.csv_text.get_secret_value(), body.password.get_secret_value(),
                                  body.preview, user['user_id'], body.email_column, body.team_column)


@api.post("/admin/staff")
def add_staff(body: schemas.StaffCreate, user=Depends(organiser)):
    email = str(body.email).lower()
    with database() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(803126)")
        if conn.execute("SELECT 1 FROM members WHERE email=%s", (email,)).fetchone():
            raise HTTPException(409,"That email already has a Prompt War role.")
        user_id = supabase.ensure_user(email)
        conn.execute("INSERT INTO members(user_id,email,role) VALUES (%s,%s,%s)", (user_id,email,body.role))
        audit(conn,user["user_id"],"create_staff",{"email":email,"role":body.role})
    return {"message":"Staff account approved. They can request an email code."}


# Computer allocation disabled at the organiser's request.
# @api.put("/admin/teams/{team_id}/allocation")
# def allocate(team_id: UUID, body: schemas.Allocation, user=Depends(organiser)):
#     with database() as conn:
#         result = conn.execute("UPDATE teams SET workstation=%s WHERE id=%s RETURNING id", (body.workstation,team_id)).fetchone()
#         if not result:
#             raise HTTPException(404,"Team not found.")
#         audit(conn,user["user_id"],"reassign_computer",{"team_id":team_id,**body.model_dump()})
#     return {"message":"Computer allocation updated."}


@api.put("/admin/rounds/{round_id}")
def update_round(round_id: UUID, body: schemas.RoundUpdate, user=Depends(organiser)):
    words = list(dict.fromkeys(word.strip().casefold() for word in body.banned_words if word.strip()))
    if any(len(word)>80 for word in words):
        raise HTTPException(400,"Banned words or phrases must be at most 80 characters.")
    with database() as conn:
        row = competition.get_round(conn,round_id,True)
        if row["status"] != "waiting":
            raise HTTPException(409,"Challenge configuration locks when briefing opens.")
        if row["stage"] == 3 and body.qualifier_count != 2:
            raise HTTPException(400,"The final awards two prize places: winner and runner-up.")
        conn.execute("""UPDATE rounds SET title=%s,task=%s,flawed_output=%s,expected_output=%s,banned_words=%s::jsonb,
            duration_seconds=%s,upload_seconds=%s,qualifier_count=%s,llm_instructions=%s WHERE id=%s""",
            (body.title,body.task,body.flawed_output,body.expected_output,json.dumps(words),body.duration_seconds,body.upload_seconds,body.qualifier_count,body.llm_instructions,round_id))
        audit(conn,user["user_id"],"configure_round",{"round_id":round_id})
    return {"message":"Round configuration saved."}


@api.post("/admin/rounds/{round_id}/action")
def round_action(round_id: UUID, body: schemas.Action, user=Depends(organiser)):
    with database() as conn:
        competition.change_state(conn,round_id,body.action,user["user_id"])
    return {"message":"Round updated."}


@api.post("/admin/rounds/{round_id}/publish")
def publish(round_id: UUID, user=Depends(organiser)):
    with database() as conn:
        competition.publish(conn,round_id,user["user_id"])
    return {"message":"Results published and qualifying teams enrolled into the next stage."}


@api.post("/admin/rounds/{round_id}/extensions")
def extend(round_id: UUID, body: schemas.Extension, user=Depends(organiser)):
    with database() as conn:
        synchronize(conn)
        row = competition.get_round(conn,round_id,True)
        if row["status"] not in ("submission","evaluation"):
            raise HTTPException(409,"Extensions are available only during submission or evaluation, before publication.")
        entry = conn.execute("SELECT * FROM entries WHERE round_id=%s AND team_id=%s AND outcome='eligible' FOR UPDATE", (round_id,body.team_id)).fetchone()
        if not entry:
            raise HTTPException(404,"Eligible team entry not found.")
        # A reopened submission may replace a judged file, so discard that team's provisional approvals.
        conn.execute("DELETE FROM evaluations WHERE submission_id IN (SELECT id FROM submissions WHERE round_id=%s AND team_id=%s)", (round_id,body.team_id))
        conn.execute("UPDATE ai_runs SET status='superseded',finished_at=now(),lease_until=NULL,error='The team received a new submission window; this assessment is no longer current.' WHERE submission_id IN (SELECT id FROM submissions WHERE round_id=%s AND team_id=%s)",(round_id,body.team_id))
        conn.execute("UPDATE entries SET extension_until=greatest(now(),coalesce(extension_until,upload_end.deadline))+make_interval(mins=>%s) FROM (SELECT upload_ends_at AS deadline FROM rounds WHERE id=%s) upload_end WHERE round_id=%s AND team_id=%s", (body.minutes,round_id,round_id,body.team_id))
        audit(conn,user["user_id"],"grant_extension",body.model_dump())
    return {"message":"Team upload window extended. That team's submission must be judged again."}


@api.post("/admin/rounds/{round_id}/disqualify")
def disqualify(round_id: UUID, body: schemas.Disqualify, user=Depends(organiser)):
    with database() as conn:
        row = competition.get_round(conn,round_id,True)
        if row["status"] in ("results","closed"):
            raise HTTPException(409,"Published results are locked.")
        result = conn.execute("UPDATE entries SET outcome='disqualified',reason=%s WHERE round_id=%s AND team_id=%s RETURNING team_id", (body.reason,round_id,body.team_id)).fetchone()
        if not result:
            raise HTTPException(404,"Team entry not found.")
        conn.execute("UPDATE ai_runs SET status='superseded',finished_at=now(),lease_until=NULL,error='The team was disqualified for this stage.' WHERE submission_id IN (SELECT id FROM submissions WHERE round_id=%s AND team_id=%s)",(round_id,body.team_id))
        audit(conn,user["user_id"],"disqualify",{"round_id":round_id,**body.model_dump()})
    return {"message":"Disqualification recorded with its reason."}


@api.post("/incidents")
def incident(body: schemas.Incident, user=Depends(auth.current_user)):
    if user["role"] == "participant" and body.team_id != user["team_id"]:
        raise HTTPException(403,"You can report problems only for your own team.")
    with database() as conn:
        result = conn.execute("INSERT INTO incidents(team_id,round_id,reporter_id,description) VALUES (%s,%s,%s,%s) RETURNING id,created_at", (body.team_id,body.round_id,user["user_id"],body.description)).fetchone()
        audit(conn,user["user_id"],"report_incident",{"incident_id":result["id"]})
    return result


def judging_context(conn, submission_id):
    # Lock round first, matching all publication/confirmation operations.
    basic = conn.execute("SELECT round_id FROM submissions WHERE id=%s", (submission_id,)).fetchone()
    if not basic:
        raise HTTPException(404,"Submission not found.")
    synchronize(conn)
    round_ = competition.get_round(conn,basic["round_id"],True)
    if round_["status"] != "evaluation":
        raise HTTPException(409,"Scores can change only during evaluation.")
    row = next((s for s in competition.latest(conn,round_["id"]) if s["id"]==submission_id),None)
    if not row:
        raise HTTPException(409,"This is not the team's current confirmed final submission.")
    if conn.execute("SELECT 1 FROM entries WHERE round_id=%s AND team_id=%s AND extension_until>now()", (round_["id"],row["team_id"])).fetchone():
        raise HTTPException(409,"This team still has an open upload extension.")
    return round_,row


@api.get("/judge/rounds/{round_id}/queue")
def queue(round_id: UUID, user=Depends(judge)):
    with database() as conn:
        synchronize(conn)
        round_ = competition.get_round(conn,round_id)
        if round_["status"] not in ("evaluation","results","closed"):
            raise HTTPException(409,"Judging opens after the submission window ends.")
        output=[]
        for row in competition.latest(conn,round_id):
            assigned=questions.for_submission(conn,round_,row)
            runs=conn.execute("SELECT * FROM ai_runs WHERE submission_id=%s ORDER BY created_at DESC,id DESC",(row["id"],)).fetchall()
            current=next((run for run in runs if run["status"]!='superseded'),None)
            candidate=None
            if user["role"]=="organiser":
                candidate=conn.execute("SELECT t.name,t.workstation,array_agg(m.email ORDER BY m.email) AS emails FROM teams t LEFT JOIN members m ON m.team_id=t.id WHERE t.id=%s GROUP BY t.id",(row["team_id"],)).fetchone()
            output.append({"id":row["id"],"label":"Submission "+str(row["id"])[:8],"candidate":candidate,
                           "attempts":row["attempts"],"selected_attempt":row["selected_attempt"],"confirmed_at":row["confirmed_at"],
                           "challenge":questions.display_context(assigned,private=True),
                           "checks":evaluation.checks(assigned,row),"rubric":evaluation.RUBRICS[round_["kind"]],"ai_suggestion":row["ai_suggestion"],
                           "panel_run":panel_jobs.visible_run(current),"panel_history":[panel_jobs.visible_run(run,history=True) for run in runs],
                           "scores":row["scores"],"total":row["total"],"comments":row["comments"],"approved_at":row["approved_at"],
                           "tie_break_score":row["tie_break_score"],"ai_run_id":row["ai_run_id"],"manual_override":row["manual_override"]})
        return output


@api.get("/judge/rounds/{round_id}/panel")
def panel_configuration(round_id: UUID, user=Depends(judge)):
    with database() as conn:
        competition.get_round(conn,round_id)
        locked=conn.execute("SELECT roster FROM ai_panels WHERE round_id=%s",(round_id,)).fetchone()
    message="Four independent evaluators. Equal-weight criterion averages; human approval required."
    try:
        configured=model_panel.configured_roster()
        ready=True
    except HTTPException as error:
        configured=[]
        ready=False
        message=error.detail
    if locked:
        configured=locked["roster"]
        ready=bool(settings().groq_api_key and settings().openai_api_key)
        message="This round uses the frozen four-model roster shown above." if ready else "Configure both provider API keys to process this round's frozen panel."
    return {"configured":ready,"locked":bool(locked),"roster":configured,"message":message,"required_models":4}


@api.post("/judge/rounds/{round_id}/evaluate")
def evaluate_round(round_id: UUID, user=Depends(judge)):
    with database() as conn:
        synchronize(conn)
        round_=competition.get_round(conn,round_id,True)
        if round_["status"]!='evaluation':
            raise HTTPException(409,"Panel evaluation opens after submissions close.")
        queued=[]
        skipped=0
        for row in competition.latest(conn,round_id):
            extension=conn.execute("SELECT 1 FROM entries WHERE round_id=%s AND team_id=%s AND extension_until>now()",(round_id,row["team_id"])).fetchone()
            if row["approved_at"] or extension:
                skipped+=1
                continue
            queued.append(panel_jobs.visible_run(panel_jobs.queue_one(conn,round_,row,user["user_id"])))
        return {"message":"Final submissions queued or already evaluated. The evaluation worker processes the jobs; failed panels require an explicit retry.","runs":queued,"skipped":skipped}


@api.post("/judge/submissions/{submission_id}/suggest")
def ai_suggestion(submission_id: UUID, user=Depends(judge)):
    with database() as conn:
        round_,row = judging_context(conn,submission_id)
        return panel_jobs.visible_run(panel_jobs.queue_one(conn,round_,row,user["user_id"]))


@api.post("/judge/submissions/{submission_id}/retry-panel")
def retry_panel(submission_id: UUID, user=Depends(judge)):
    with database() as conn:
        round_,row=judging_context(conn,submission_id)
        return panel_jobs.visible_run(panel_jobs.queue_one(conn,round_,row,user["user_id"],retry=True))


@api.post("/judge/submissions/{submission_id}/cancel-panel")
def cancel_panel(submission_id: UUID, body: schemas.Reason, user=Depends(judge)):
    with database() as conn:
        judging_context(conn,submission_id)
        result=conn.execute("UPDATE ai_runs SET status='failed',finished_at=now(),lease_until=NULL,error='Cancelled by a judge or organiser.' WHERE submission_id=%s AND status IN ('queued','running') RETURNING id",(submission_id,)).fetchone()
        if not result:
            raise HTTPException(409,"No active panel exists for this submission.")
        audit(conn,user["user_id"],"cancel_evaluation_panel",{"run_id":result["id"],"reason":body.reason})
    return {"message":"Panel cancelled. In-flight provider requests may finish and incur charges, but their results cannot change this panel."}


@api.put("/judge/submissions/{submission_id}/score")
def approve_score(submission_id: UUID, body: schemas.Score, user=Depends(judge)):
    with database() as conn:
        round_,row = judging_context(conn,submission_id)
        run=conn.execute("SELECT * FROM ai_runs WHERE submission_id=%s AND status<>'superseded' ORDER BY created_at DESC,id DESC LIMIT 1",(submission_id,)).fetchone()
        if run and run["status"] in ('queued','running'):
            raise HTTPException(409,"Wait for all evaluators or explicitly cancel the panel before approving a score.")
        complete=bool(run and run["status"]=='complete' and run["aggregate"])
        if not complete and not body.manual_override:
            raise HTTPException(409,"Four completed model assessments are required. For a provider outage, explicitly select manual override and document your reasoning.")
        automatic = evaluation.checks(questions.for_submission(conn,round_,row),row)
        scores,total = evaluation.validate_scores(round_["kind"],body.scores,automatic)
        conn.execute("""INSERT INTO evaluations(submission_id,checks,scores,total,judge_id,comments,tie_break_score,approved_at,ai_run_id,manual_override)
            VALUES (%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,now(),%s,%s) ON CONFLICT(submission_id) DO UPDATE SET
            checks=excluded.checks,scores=excluded.scores,total=excluded.total,judge_id=excluded.judge_id,
            comments=excluded.comments,tie_break_score=excluded.tie_break_score,approved_at=excluded.approved_at,
            ai_run_id=excluded.ai_run_id,manual_override=excluded.manual_override""",
            (submission_id,json.dumps(automatic),json.dumps(scores),total,user["user_id"],body.comments,body.tie_break_score,
             run["id"] if complete else None,body.manual_override))
        audit(conn,user["user_id"],"approve_score",{"submission_id":submission_id,"scores":scores,"total":total,"comments":body.comments,"tie_break_score":body.tie_break_score,"ai_run_id":run["id"] if complete else None,"manual_override":body.manual_override})
    return {"message":"Judge-approved score saved.","total":total}


@api.get("/admin/audit")
def audit_history(user=Depends(organiser)):
    with database() as conn:
        return conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 200").fetchall()


@api.get("/admin/export")
def export(user=Depends(organiser)):
    with database() as conn:
        rows = conn.execute("""SELECT r.stage,r.title,t.name AS team,n.outcome,n.placement,n.final_score,
            s.id AS submission_id,s.confirmed_at,s.selected_attempt,s.attempts,e.scores,e.comments,e.tie_break_score,e.ai_suggestion,e.ai_run_id,e.manual_override,
            a.id AS assignment_id,a.snapshot->>'key' AS question_key,a.snapshot->>'title' AS question_title
            FROM entries n JOIN rounds r ON r.id=n.round_id JOIN teams t ON t.id=n.team_id
            LEFT JOIN LATERAL (SELECT * FROM submissions WHERE team_id=n.team_id AND round_id=n.round_id AND confirmed_at IS NOT NULL ORDER BY confirmed_at DESC,id DESC LIMIT 1) s ON true
            LEFT JOIN evaluations e ON e.submission_id=s.id
            LEFT JOIN question_assignments a ON a.round_id=n.round_id AND a.team_id=n.team_id
            ORDER BY r.stage,n.placement NULLS LAST,t.name""").fetchall()
        audit(conn,user["user_id"],"export_results",{"rows":len(rows)})
    output = io.StringIO()
    columns = ["stage","title","team","outcome","placement","final_score","submission_id","confirmed_at","selected_attempt","attempts","scores","comments","tie_break_score","ai_suggestion","ai_run_id","manual_override","assignment_id","question_key","question_title"]
    writer = csv.DictWriter(output,fieldnames=columns)
    writer.writeheader()
    for row in rows:
        clean = {}
        for key,value in row.items():
            text = json.dumps(value,ensure_ascii=False,default=str) if isinstance(value,(list,dict)) else "" if value is None else str(value)
            clean[key] = "'"+text if text.lstrip().startswith(("=","+","-","@")) else text
        writer.writerow(clean)
    return StreamingResponse(iter([output.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=prompt-war-results.csv"})


app.include_router(api)
app.mount("/",StaticFiles(directory=PROJECT / "frontend", html=True),name="frontend")

