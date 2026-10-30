from fastapi import HTTPException
from .db import audit, synchronize
from . import questions


def get_round(conn, round_id, lock=False):
    row = conn.execute("SELECT *, now() AS server_now FROM rounds WHERE id=%s" + (" FOR UPDATE" if lock else ""), (round_id,)).fetchone()
    if not row:
        raise HTTPException(404,"Round not found.")
    return row


def public_round(row):
    return {key:row[key] for key in (
        "id","stage","title","kind","status","duration_seconds","upload_seconds","max_attempts",
        "qualifier_count","llm_instructions","started_at","challenge_ends_at","upload_ends_at","paused_at","paused_from","published_at",
    )}


def latest(conn, round_id):
    return conn.execute("""SELECT s.*, e.checks,e.ai_suggestion,e.scores,e.total,e.comments,e.tie_break_score,e.approved_at,e.ai_run_id,e.manual_override
        FROM (SELECT DISTINCT ON(team_id) * FROM submissions WHERE round_id=%s AND confirmed_at IS NOT NULL
            ORDER BY team_id,confirmed_at DESC,id DESC) s
        LEFT JOIN evaluations e ON e.submission_id=s.id
        JOIN entries n ON n.round_id=s.round_id AND n.team_id=s.team_id
        WHERE n.outcome<>'disqualified' ORDER BY s.confirmed_at,s.id""", (round_id,)).fetchall()


def change_state(conn, round_id, action, actor):
    conn.execute("SELECT pg_advisory_xact_lock(803126)")
    synchronize(conn)
    round_ = get_round(conn,round_id,True)
    state = round_["status"]
    if action == "brief":
        if state != "waiting":
            raise HTTPException(409,"Only a waiting round can enter briefing.")
        previous = conn.execute("SELECT status FROM rounds WHERE stage=%s", (round_["stage"]-1,)).fetchone()
        if previous and previous["status"] not in ("results","closed"):
            raise HTTPException(409,"Publish the previous round's results before briefing this round.")
        other = conn.execute("SELECT id FROM rounds WHERE id<>%s AND status IN ('briefing','running','submission','evaluation','paused')", (round_id,)).fetchone()
        if other:
            raise HTTPException(409,"Finish the current round before opening another.")
        count = conn.execute("SELECT count(*) AS n FROM entries WHERE round_id=%s AND outcome='eligible'", (round_id,)).fetchone()["n"]
        if not count:
            raise HTTPException(409,"There are no eligible teams for this round.")
        if not questions.bank_count(conn,round_["kind"]):
            raise HTTPException(409,"Import this challenge's question bank before releasing briefing.")
        conn.execute("UPDATE rounds SET status='briefing' WHERE id=%s", (round_id,))
    elif action == "start":
        if state != "briefing":
            raise HTTPException(409,"Brief the round before starting it.")
        # Assignment and the shared clock start commit together, or both roll back.
        questions.assign(conn,round_,actor)
        conn.execute("""WITH clock AS MATERIALIZED (SELECT clock_timestamp() AS started)
            UPDATE rounds SET status='running',started_at=clock.started,
            challenge_ends_at=clock.started+make_interval(secs=>duration_seconds),
            upload_ends_at=clock.started+make_interval(secs=>duration_seconds+upload_seconds)
            FROM clock WHERE id=%s""", (round_id,))
    elif action == "pause":
        if state not in ("running","submission"):
            raise HTTPException(409,"Only an active challenge or upload window can be paused.")
        conn.execute("UPDATE rounds SET paused_from=status,status='paused',paused_at=now() WHERE id=%s", (round_id,))
    elif action == "resume":
        if state != "paused":
            raise HTTPException(409,"This round is not paused.")
        delta = round_["server_now"]-round_["paused_at"]
        conn.execute("""UPDATE rounds SET status=paused_from,challenge_ends_at=challenge_ends_at+%s,
            upload_ends_at=upload_ends_at+%s,paused_at=NULL,paused_from=NULL WHERE id=%s""", (delta,delta,round_id))
        conn.execute("UPDATE entries SET extension_until=extension_until+%s WHERE round_id=%s AND extension_until>%s", (delta,round_id,round_["paused_at"]))
    elif action == "end_challenge":
        if state != "running":
            raise HTTPException(409,"The challenge is not running.")
        conn.execute("UPDATE rounds SET status='submission',challenge_ends_at=now(),upload_ends_at=now()+make_interval(secs=>upload_seconds) WHERE id=%s", (round_id,))
    elif action == "close_uploads":
        if state not in ("submission","evaluation"):
            raise HTTPException(409,"There is no submission window to close.")
        conn.execute("UPDATE rounds SET status='evaluation',upload_ends_at=now() WHERE id=%s", (round_id,))
        conn.execute("UPDATE entries SET extension_until=now() WHERE round_id=%s AND extension_until>now()", (round_id,))
    elif action == "close":
        if state != "results":
            raise HTTPException(409,"Publish results before closing the round.")
        conn.execute("UPDATE rounds SET status='closed' WHERE id=%s", (round_id,))
    audit(conn,actor,"round_"+action,{"round_id":round_id,"previous_status":state})


def publish(conn, round_id, actor):
    conn.execute("SELECT pg_advisory_xact_lock(803126)")
    synchronize(conn)
    round_ = get_round(conn,round_id,True)
    if round_["status"] != "evaluation":
        raise HTTPException(409,"Only a round under evaluation can publish results.")
    if conn.execute("SELECT 1 FROM ai_runs WHERE round_id=%s AND status IN ('queued','running')",(round_id,)).fetchone():
        raise HTTPException(409,"An evaluation panel is still queued or running. Wait for completion or explicitly cancel it before publishing.")
    if conn.execute("SELECT 1 FROM entries WHERE round_id=%s AND extension_until>now() AND outcome='eligible'", (round_id,)).fetchone():
        raise HTTPException(409,"A team still has an open upload extension.")
    rows = latest(conn,round_id)
    if not rows:
        raise HTTPException(409,"There are no confirmed submissions to rank.")
    if any(not r["approved_at"] for r in rows):
        raise HTTPException(409,"Every confirmed final submission must have judge-approved scores.")
    key = lambda r: (r["total"],r["tie_break_score"] if r["tie_break_score"] is not None else -1)
    rows.sort(key=key,reverse=True)
    cutoff = min(round_["qualifier_count"],len(rows))
    # Ties at the qualification boundary, and at final prize places, need a surprise tie-break.
    boundaries = range(1,min(2,len(rows)-1)+1) if round_["stage"] == 3 else ([cutoff] if cutoff<len(rows) else [])
    for boundary in boundaries:
        if boundary < len(rows) and key(rows[boundary-1]) == key(rows[boundary]):
            raise HTTPException(409,"A tie affects qualification or a prize place. Complete and record the judges' surprise tie-break first.")
    conn.execute("UPDATE entries SET outcome='eliminated',final_score=NULL,placement=NULL WHERE round_id=%s AND outcome<>'disqualified'", (round_id,))
    next_round = conn.execute("SELECT id FROM rounds WHERE stage=%s", (round_["stage"]+1,)).fetchone()
    for position,row in enumerate(rows,1):
        if round_["stage"] == 3:
            outcome = "winner" if position==1 else "runner_up" if position==2 else "finalist"
        else:
            outcome = "qualified" if position<=cutoff else "eliminated"
        conn.execute("UPDATE entries SET outcome=%s,placement=%s,final_score=%s WHERE round_id=%s AND team_id=%s",
                     (outcome,position,row["total"],round_id,row["team_id"]))
        if outcome == "qualified" and next_round:
            conn.execute("INSERT INTO entries(round_id,team_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (next_round["id"],row["team_id"]))
    conn.execute("UPDATE rounds SET status='results',published_at=now() WHERE id=%s", (round_id,))
    audit(conn,actor,"publish_results",{"round_id":round_id,"ranked":len(rows),"qualifiers":cutoff})

