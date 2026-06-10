import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from backend.services.email_service import send_welcome_email
from backend.app.database import (
    _get_user, _verify_password, _hash_password,
    _create_user, _list_users, _delete_user,
    _create_user_with_email, _clear_temp_password,
)

router = APIRouter()

JWT_SECRET    = os.getenv("JWT_SECRET", "changeme-set-in-env")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_H  = 8

ROLE_LABELS = {
    "super_admin": "Super Admin",
    "admin":       "Admin",
    "user":        "User (View Only)",
}


def _create_token(username: str, role: str, must_change: bool = False) -> str:
    payload = {
        "sub":         username,
        "role":        role,
        "must_change": must_change,
        "exp":         datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_H),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def _require_auth(authorization: str = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    try:
        return _decode_token(authorization.split(" ", 1)[1])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired — please log in again")
    except Exception:
        raise HTTPException(401, "Invalid token")


def _require_super_admin(session: dict = Depends(_require_auth)) -> dict:
    if session.get("role") != "super_admin":
        raise HTTPException(403, "Director access required")
    return session


class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    full_name: str
    email:     str
    role:      str = "user"

class ResetPasswordRequest(BaseModel):
    new_password: str


@router.post("/auth/login")
async def login(req: LoginRequest):
    user = _get_user(req.username.strip().lower())
    if not user or not _verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    # Check temp password expiry
    temp_exp = user.get("temp_expires_at")
    if temp_exp:
        if isinstance(temp_exp, str):
            temp_exp = datetime.fromisoformat(temp_exp)
        now = datetime.now(timezone.utc) if temp_exp.tzinfo else datetime.now()
        if now > temp_exp and user.get("must_change_password"):
            raise HTTPException(401, "Temporary password has expired. Contact your administrator to resend access.")

    must_change = user.get("must_change_password", False)
    token = _create_token(user["username"], user["role"], must_change=must_change)
    return {
        "token":                token,
        "username":             user["username"],
        "full_name":            user.get("full_name"),
        "role":                 user["role"],
        "label":                ROLE_LABELS.get(user["role"], user["role"]),
        "must_change_password": must_change,
    }


@router.post("/auth/logout")
async def logout():
    return {"status": "ok"}


@router.get("/auth/me")
async def me(session: dict = Depends(_require_auth)):
    return {
        "username":             session["sub"],
        "role":                 session["role"],
        "label":                ROLE_LABELS.get(session["role"], session["role"]),
        "must_change_password": session.get("must_change", False),
    }


@router.get("/auth/users")
async def list_users(session: dict = Depends(_require_super_admin)):
    users = _list_users()
    return {"users": [
        {**u, "label": ROLE_LABELS.get(u["role"], u["role"])}
        for u in users
    ]}


@router.post("/auth/users")
async def create_user(req: CreateUserRequest, session: dict = Depends(_require_super_admin)):
    email     = req.email.strip().lower()
    full_name = req.full_name.strip()
    if not full_name:
        raise HTTPException(400, "Name is required")
    if not email.endswith("@nickelfox.com"):
        raise HTTPException(400, "Email must be a @nickelfox.com address")
    if req.role not in ("super_admin", "admin", "user"):
        raise HTTPException(400, "Role must be super_admin, admin, or user")
    temp_pass = _create_user_with_email(email, full_name, req.role)
    if not temp_pass:
        raise HTTPException(400, "This email already has an account")
    try:
        send_welcome_email(to_email=email, full_name=full_name, temp_password=temp_pass, role=req.role)
    except Exception as e:
        print(f"[Email] Skipped — {e}")
    return {"status": "created", "email": email}


@router.delete("/auth/users/{username}")
async def delete_user(username: str, session: dict = Depends(_require_super_admin)):
    if username == session["sub"]:
        raise HTTPException(400, "Cannot remove your own account")
    _delete_user(username)
    return {"status": "deleted"}


@router.put("/auth/users/{username}/password")
async def reset_password(username: str, req: ResetPasswordRequest, session: dict = Depends(_require_super_admin)):
    if not req.new_password.strip():
        raise HTTPException(400, "Password cannot be empty")
    from backend.app.database import _db_engine
    from sqlalchemy import text as _text
    if not _db_engine:
        raise HTTPException(503, "Database unavailable")
    try:
        with _db_engine.connect() as conn:
            conn.execute(_text(
                "UPDATE users SET password_hash = :ph, must_change_password = TRUE WHERE username = :u"
            ), {"ph": _hash_password(req.new_password), "u": username})
            conn.commit()
    except Exception as e:
        raise HTTPException(500, f"Failed to reset password: {e}")
    return {"status": "updated"}


@router.put("/auth/change-password")
async def change_my_password(req: ResetPasswordRequest, session: dict = Depends(_require_auth)):
    if not req.new_password.strip():
        raise HTTPException(400, "Password cannot be empty")
    from backend.app.database import _db_engine
    from sqlalchemy import text as _text
    if not _db_engine:
        raise HTTPException(503, "Database unavailable")
    try:
        with _db_engine.connect() as conn:
            conn.execute(_text("""
                UPDATE users SET
                    password_hash        = :ph,
                    must_change_password = FALSE,
                    temp_expires_at      = NULL
                WHERE username = :u
            """), {"ph": _hash_password(req.new_password), "u": session["sub"]})
            conn.commit()
    except Exception as e:
        raise HTTPException(500, f"Failed to update password: {e}")
    new_token = _create_token(session["sub"], session["role"], must_change=False)
    return {"token": new_token, "status": "updated"}
