"""Direct text submissions stored in PostgreSQL, without file uploads or Storage."""
import hashlib
import json
from uuid import uuid4
from fastapi import HTTPException
from .config import settings
from .db import audit
from . import questions


def content_digest(attempts, selected_attempt):
    try:
        raw=json.dumps({"attempts":attempts,"selected_attempt":selected_attempt},ensure_ascii=False,
                       sort_keys=True,separators=(",", ":")).encode("utf-8")
    except UnicodeEncodeError:
        raise HTTPException(400,"The pasted text contains invalid Unicode characters. Paste it again as plain text.")
    if len(raw)>settings().max_submission_bytes:
        raise HTTPException(400,f"The combined prompts and answers exceed {settings().max_submission_bytes} UTF-8 bytes.")
    return hashlib.sha256(raw).hexdigest(),len(raw)


def validate_entry(body, max_attempts):
    data=body.model_dump()
    if len(data["attempts"])>max_attempts:
        raise HTTPException(400,f"This round allows at most {max_attempts} attempt(s).")
    # Schemas validate all fields without stripping whitespace from the evidence.
    content_digest(data["attempts"],data["selected_attempt"])
    return data


def entry_for_submission(conn, round_id, team_id):
    # Consistent lock order: round, then entry. This serializes close/pause/confirm races.
    round_=conn.execute("SELECT *, now() AS server_now FROM rounds WHERE id=%s FOR UPDATE",(round_id,)).fetchone()
    if not round_:
        raise HTTPException(404,"Round not found.")
    entry=conn.execute("SELECT * FROM entries WHERE round_id=%s AND team_id=%s FOR UPDATE",(round_id,team_id)).fetchone()
    if not entry or entry["outcome"]!="eligible":
        raise HTTPException(403,"Your team cannot submit for this round.")
    deadline=entry["extension_until"] or round_["upload_ends_at"]
    if round_["status"] not in ("submission","evaluation") or not deadline or round_["server_now"]>=deadline:
        raise HTTPException(409,"The submission window is closed. Contact a volunteer if you had a technical problem.")
    return round_,entry


def create(conn, round_id, user, body):
    round_,_=entry_for_submission(conn,round_id,user["team_id"])
    assigned=questions.for_team(conn,round_,user["team_id"])
    count=conn.execute("SELECT count(*) AS count FROM submissions WHERE team_id=%s AND round_id=%s",(user["team_id"],round_id)).fetchone()["count"]
    if count>=10:
        raise HTTPException(409,"Ten submission versions have already been saved. Contact an organiser.")
    data=validate_entry(body,round_["max_attempts"])
    digest,size=content_digest(data["attempts"],data["selected_attempt"])
    row=conn.execute("""INSERT INTO submissions(id,team_id,round_id,submitted_by,source_type,sha256,byte_size,attempts,selected_attempt,assignment_id)
        VALUES (%s,%s,%s,%s,'direct',%s,%s,%s::jsonb,%s,%s)
        RETURNING id,source_type,attempts,selected_attempt,created_at,confirmed_at,sha256,byte_size""",
        (uuid4(),user["team_id"],round_id,user["user_id"],digest,size,
         json.dumps(data["attempts"],ensure_ascii=False),data["selected_attempt"],assigned['assignment_id'])).fetchone()
    audit(conn,user["user_id"],"save_submission_draft",{"submission_id":row["id"],"round_id":round_id,"attempt_count":len(data["attempts"])})
    return row
