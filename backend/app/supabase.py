import secrets
import httpx
from fastapi import HTTPException
from .config import settings


def call(method, path, payload=None, token=None, *, admin=False):
    config = settings()
    key = config.supabase_service_role_key if admin else config.auth_key
    headers = {"apikey": key}
    if token or admin:
        headers["Authorization"] = "Bearer " + (token or config.supabase_service_role_key)
    try:
        response = httpx.request(method, config.supabase_url.rstrip("/") + path,
                                headers=headers, json=payload, timeout=20)
    except httpx.RequestError:
        raise HTTPException(503, "The authentication service is unavailable. Please try again.")
    if response.is_error:
        if response.status_code == 429:
            raise HTTPException(429, "Too many attempts. Wait before trying again.")
        raise HTTPException(401 if response.status_code in (400, 401, 403, 422) else 502,
                            "Authentication could not be completed. Check your credentials or contact the organiser.")
    return response.json() if response.content else {}


def ensure_user(email):
    # Never resets a password or changes roles of an existing shared Supabase user.
    for page in range(1, 101):
        rows = call("GET", f"/auth/v1/admin/users?page={page}&per_page=200", admin=True).get("users", [])
        match = next((u for u in rows if u.get("email", "").lower() == email.lower()), None)
        if match:
            return match["id"]
        if len(rows) < 200:
            break
    else:
        raise HTTPException(409, "User directory is too large for automatic lookup; contact the operator.")
    return call("POST", "/auth/v1/admin/users", {
        "email": email, "password": secrets.token_urlsafe(36), "email_confirm": True,
    }, admin=True)["id"]
