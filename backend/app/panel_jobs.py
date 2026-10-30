"""Database-backed evaluation jobs; no provider requests occur when jobs are queued."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from fastapi import HTTPException
from . import competition, evaluation, model_panel, questions
from .config import settings
from .db import audit, database


def panel_for_round(conn, round_id, actor):
    panel=conn.execute("SELECT * FROM ai_panels WHERE round_id=%s",(round_id,)).fetchone()
    if panel:
        if not settings().groq_api_key or not settings().openai_api_key:
            raise HTTPException(503,"Both provider API keys must be configured. No jobs were queued.")
        return panel["roster"]
    roster=model_panel.configured_roster()
    conn.execute("INSERT INTO ai_panels(round_id,roster,created_by) VALUES (%s,%s::jsonb,%s)",(round_id,json.dumps(roster),actor))
    audit(conn,actor,"lock_evaluation_roster",{"round_id":round_id,"roster":roster})
    return roster


def queue_one(conn, round_, submission, actor, retry=False):
    # Caller holds the round lock. All teams in that stage use the same frozen roster.
    context=questions.for_submission(conn,round_,submission)
    previous=conn.execute("SELECT * FROM ai_runs WHERE submission_id=%s AND status<>'superseded' ORDER BY created_at DESC,id DESC LIMIT 1",(submission["id"],)).fetchone()
    if submission["approved_at"] and not (previous and previous["status"]=='complete'):
        raise HTTPException(409,"This submission already has an approved human score. A new panel cannot be started afterward.")
    if previous and (previous["status"] in ("queued","running","complete") or not retry):
        return previous
    count=conn.execute("SELECT count(*) AS n FROM ai_runs WHERE submission_id=%s",(submission["id"],)).fetchone()["n"]
    if count>=4:
        raise HTTPException(409,"This submission has reached four panel runs. Use documented manual judging rather than repeatedly resampling scores.")
    roster=panel_for_round(conn,round_["id"],actor)
    automatic=evaluation.checks(context,submission)
    snapshot={"version":model_panel.VERSION,"roster":roster,"kind":round_["kind"],"task":context["task"],
              "flawed_output":context["flawed_output"],"expected_output":context["expected_output"],
              "participant_rules":context['participant_rules'],
              "question":{key:str(context[key]) for key in ('assignment_id','question_id','question_key','question_title','question_hash')},
              "rubric":evaluation.RUBRICS[round_["kind"]],"checks":automatic,
              "selected_attempt":submission["selected_attempt"],"attempts":submission["attempts"]}
    retained={}
    if previous:
        # An explicit retry changes neither the input nor the model mix; successes are not rerun.
        snapshot=previous["snapshot"]
        retained={key:row for key,row in previous["model_results"].items() if row.get("status")=="success"}
    run=conn.execute("""INSERT INTO ai_runs(submission_id,round_id,snapshot,model_results,requested_by,retry_of)
        VALUES (%s,%s,%s::jsonb,%s::jsonb,%s,%s) RETURNING *""",
        (submission["id"],round_["id"],json.dumps(snapshot),json.dumps(retained),actor,previous["id"] if previous else None)).fetchone()
    audit(conn,actor,"queue_evaluation_panel",{"run_id":run["id"],"submission_id":submission["id"],"retry_of":run["retry_of"]})
    return run


def visible_run(run, history=False):
    if not run:
        return None
    data={key:run[key] for key in ("id","status","model_results","aggregate","error","created_at","started_at","finished_at","retry_of")} | {
        "roster":run["snapshot"]["roster"],"selected_attempt":run["snapshot"]["selected_attempt"],"version":run["snapshot"]["version"]}
    if data["aggregate"]:
        data["aggregate"]={key:value for key,value in data["aggregate"].items() if key!="models"}
    if history:
        data["model_results"]={slot:{key:value for key,value in row.items() if key in ("slot","provider","model","status","total","error")}
                               for slot,row in data["model_results"].items()}
    return data


def active_context(conn, run):
    round_=competition.get_round(conn,run["round_id"],True)
    if round_["status"]!="evaluation":
        return False
    current=next((row for row in competition.latest(conn,round_["id"]) if row["id"]==run["submission_id"]),None)
    if not current:
        return False
    if str(current.get('assignment_id'))!=run['snapshot'].get('question',{}).get('assignment_id'):
        return False
    entry=conn.execute("SELECT outcome,extension_until,now() AS now FROM entries WHERE round_id=%s AND team_id=%s",(round_["id"],current["team_id"])).fetchone()
    return entry["outcome"]=="eligible" and not (entry["extension_until"] and entry["extension_until"]>entry["now"])


def expire_abandoned():
    with database() as conn:
        conn.execute("""UPDATE ai_runs SET status='incomplete',finished_at=now(),lease_until=NULL,
            error='The evaluation worker was interrupted. Successful model results were preserved; explicitly retry the missing evaluators.'
            WHERE status='running' AND lease_until<now()""")


def claim():
    with database() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(803127)")
        candidate=conn.execute("SELECT * FROM ai_runs WHERE status='queued' ORDER BY created_at,id LIMIT 1").fetchone()
        if not candidate:
            return None
        # Maintain round → run lock order, shared with exceptions and publication.
        if not active_context(conn,candidate):
            conn.execute("UPDATE ai_runs SET status='superseded',finished_at=now(),error='The submission or round is no longer eligible for evaluation.' WHERE id=%s",(candidate["id"],))
            return None
        return conn.execute("""UPDATE ai_runs SET status='running',started_at=now(),lease_until=now()+interval '5 minutes'
            WHERE id=%s AND status='queued' RETURNING *""",(candidate["id"],)).fetchone()


def store_result(run, result):
    with database() as conn:
        if not active_context(conn,run):
            conn.execute("UPDATE ai_runs SET status='superseded',finished_at=now(),lease_until=NULL WHERE id=%s AND status='running'",(run["id"],))
            return False
        row=conn.execute("SELECT status FROM ai_runs WHERE id=%s FOR UPDATE",(run["id"],)).fetchone()
        if not row or row["status"]!="running":
            return False
        conn.execute("UPDATE ai_runs SET model_results=model_results || %s::jsonb,lease_until=now()+interval '5 minutes' WHERE id=%s",
                     (json.dumps({result["slot"]:result}),run["id"]))
    return True


def finish(run):
    with database() as conn:
        if not active_context(conn,run):
            conn.execute("UPDATE ai_runs SET status='superseded',finished_at=now(),lease_until=NULL WHERE id=%s AND status='running'",(run["id"],))
            return
        row=conn.execute("SELECT * FROM ai_runs WHERE id=%s FOR UPDATE",(run["id"],)).fetchone()
        if not row or row["status"]!="running":
            return
        combined=model_panel.aggregate(row["snapshot"],row["model_results"],row["id"])
        conn.execute("UPDATE ai_runs SET status=%s,aggregate=%s::jsonb,error=%s,finished_at=now(),lease_until=NULL WHERE id=%s",
                     ("complete" if combined else "incomplete",json.dumps(combined),None if combined else "At least one evaluator failed. There is no combined score until all four succeed.",row["id"]))
        if combined:
            conn.execute("""INSERT INTO evaluations(submission_id,checks,ai_suggestion) VALUES (%s,%s::jsonb,%s::jsonb)
                ON CONFLICT(submission_id) DO UPDATE SET checks=excluded.checks,ai_suggestion=excluded.ai_suggestion""",
                         (row["submission_id"],json.dumps(row["snapshot"]["checks"]),json.dumps(combined)))
        audit(conn,row["requested_by"],"complete_evaluation_panel" if combined else "incomplete_evaluation_panel",{"run_id":row["id"],"submission_id":row["submission_id"],"suggested_total":combined["total"] if combined else None})


def process(run):
    if run["snapshot"]["version"]!=model_panel.VERSION:
        with database() as conn:
            conn.execute("UPDATE ai_runs SET status='failed',error='The evaluator version changed. Operator review is required.',finished_at=now(),lease_until=NULL WHERE id=%s AND status='running'",(run["id"],))
        return
    pending=[slot for slot in run["snapshot"]["roster"] if run["model_results"].get(slot["slot"],{}).get("status")!="success"]
    # Exactly four independent assessments per submission, with no model seeing another's score.
    with ThreadPoolExecutor(max_workers=4,thread_name_prefix="prompt-war-model") as pool:
        futures={pool.submit(model_panel.evaluate_one,slot,run["snapshot"]):slot for slot in pending}
        for future in as_completed(futures):
            try:
                result=future.result()
            except Exception:
                result={**futures[future],"status":"error","error_code":"worker_error","error":"This evaluator failed unexpectedly. Retry after operator review."}
            if not store_result(run,result):
                return
    finish(run)

