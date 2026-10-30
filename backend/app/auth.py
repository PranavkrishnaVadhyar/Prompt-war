import hashlib
import secrets
from fastapi import Depends, HTTPException, Request, Response
from . import supabase
from .config import settings
from .db import database

ACCESS = "pw_access"
REFRESH = "pw_refresh"
CSRF = "pw_csrf"


def write_session(response: Response, session):
    options = dict(httponly=True, secure=settings().cookie_secure, samesite="lax", path="/")
    response.set_cookie(ACCESS, session["access_token"], max_age=int(session.get("expires_in", 3600)), **options)
    response.set_cookie(REFRESH, session["refresh_token"], max_age=86400, **options)


def clear_session(response):
    for name in (ACCESS, REFRESH, CSRF):
        response.delete_cookie(name, path="/", secure=settings().cookie_secure, httponly=True, samesite="lax")


def csrf_token(request, response):
    token = request.cookies.get(CSRF) or secrets.token_urlsafe(32)
    response.set_cookie(CSRF, token, httponly=True, secure=settings().cookie_secure, samesite="lax", path="/")
    return token


def csrf_guard(request: Request):
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    origin = request.headers.get("origin", "").rstrip("/")
    if origin not in settings().origins:
        raise HTTPException(403, "Request origin is not allowed.")
    cookie = request.cookies.get(CSRF, "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or not header or not secrets.compare_digest(cookie, header):
        raise HTTPException(403, "Your security token expired. Reload the page and try again.")


def current_user(request: Request):
    token = request.cookies.get(ACCESS)
    if not token:
        raise HTTPException(401, "Sign in to continue.")
    auth_user = supabase.call("GET", "/auth/v1/user", token=token)
    with database() as conn:
        member = conn.execute("SELECT user_id, email, role, team_id, active FROM members WHERE user_id=%s", (auth_user["id"],)).fetchone()
    if not member or not member["active"]:
        raise HTTPException(403, "This account is not approved for Prompt War. Contact an organiser.")
    return member


def roles(*allowed):
    def dependency(user=Depends(current_user)):
        if user["role"] not in allowed:
            raise HTTPException(403, "Your account cannot perform this action.")
        return user
    return dependency


def throttle(request, email):
    # Stored centrally, so restarting the server does not reset login throttles.
    ip = request.client.host if request.client else "unknown"
    with database() as conn:
        for scope, value, limit in (("ip", ip, settings().auth_ip_limit), ("email", email.lower(), settings().auth_email_limit)):
            key = hashlib.sha256((scope + ":" + value).encode()).hexdigest()
            row = conn.execute("""INSERT INTO auth_limits(key, hits, window_start) VALUES (%s,1,now())
                ON CONFLICT(key) DO UPDATE SET
                hits=CASE WHEN auth_limits.window_start < now()-interval '15 minutes' THEN 1 ELSE auth_limits.hits+1 END,
                window_start=CASE WHEN auth_limits.window_start < now()-interval '15 minutes' THEN now() ELSE auth_limits.window_start END
                RETURNING hits""", (key,)).fetchone()
            if row["hits"] > limit:
                # Commit counters even when rejecting the request.
                conn.commit()
                raise HTTPException(429, "Too many sign-in attempts. Wait 15 minutes and try again.")

