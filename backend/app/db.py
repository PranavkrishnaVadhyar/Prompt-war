from contextlib import contextmanager
import json
import psycopg
from psycopg.rows import dict_row
from .config import settings


@contextmanager
def database():
    # A transaction per operation; no schema creation or migrations during startup.
    with psycopg.connect(settings().postgres_url, row_factory=dict_row, connect_timeout=10) as conn:
        conn.execute("SET LOCAL search_path TO prompt_war")
        conn.execute("SET LOCAL statement_timeout TO '15s'")
        yield conn


def audit(conn, actor, action, details=None):
    conn.execute(
        "INSERT INTO audit_log(actor_id, action, details) VALUES (%s,%s,%s::jsonb)",
        (actor, action, json.dumps(details or {}, default=str)),
    )


def synchronize(conn):
    # The deadline remains authoritative even with no scheduler or browser connected.
    conn.execute("UPDATE rounds SET status='submission' WHERE status='running' AND challenge_ends_at <= now()")
    conn.execute("UPDATE rounds SET status='evaluation' WHERE status='submission' AND upload_ends_at <= now()")

