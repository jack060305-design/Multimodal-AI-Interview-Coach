from __future__ import annotations

import secrets
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from auth.deps import get_current_user
from auth.facebook_oauth import exchange_code_for_token, facebook_login_url, fetch_facebook_profile
from auth.jwt_tokens import create_access_token
from auth.passwords import verify_password
from auth.repository import UserRepository
from config import get_settings
from db.database import db_session
from db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

# Short-lived CSRF state for Facebook redirect (single-instance; ok for student deploy)
_oauth_states: set[str] = set()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str | None
    name: str
    avatar_url: str | None
    has_facebook: bool

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            has_facebook=bool(user.facebook_id),
        )


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def _require_db(db: Session | None) -> Session:
    if db is None:
        raise HTTPException(503, "Database not available — set DB_ENABLED=true and DATABASE_URL")
    return db


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserResponse.from_user(user),
    )


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: Session | None = Depends(db_session)):
    db = _require_db(db)
    repo = UserRepository(db)
    if repo.get_by_email(body.email):
        raise HTTPException(409, "Email already registered")
    user = repo.create_email_user(email=body.email, password=body.password, name=body.name)
    return _auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session | None = Depends(db_session)):
    db = _require_db(db)
    repo = UserRepository(db)
    user = repo.get_by_email(body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    return _auth_response(user)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.from_user(user)


@router.get("/facebook/login")
def facebook_login():
    settings = get_settings()
    if not settings.facebook_app_id or not settings.facebook_app_secret:
        raise HTTPException(503, "Facebook login not configured")
    state = secrets.token_urlsafe(24)
    _oauth_states.add(state)
    if len(_oauth_states) > 500:
        _oauth_states.clear()
    return RedirectResponse(facebook_login_url(state=state))


@router.get("/facebook/callback")
def facebook_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session | None = Depends(db_session),
):
    settings = get_settings()
    frontend = settings.frontend_url.rstrip("/")

    if error:
        return RedirectResponse(f"{frontend}/login?error={urllib.parse.quote(error)}")
    if not code or not state or state not in _oauth_states:
        return RedirectResponse(f"{frontend}/login?error=invalid_oauth_state")
    _oauth_states.discard(state)

    db = _require_db(db)
    repo = UserRepository(db)

    try:
        token = exchange_code_for_token(code)
        profile = fetch_facebook_profile(token)
    except Exception as exc:
        return RedirectResponse(f"{frontend}/login?error={urllib.parse.quote(str(exc)[:120])}")

    fb_id = str(profile.get("id", ""))
    if not fb_id:
        return RedirectResponse(f"{frontend}/login?error=facebook_profile_missing")

    user = repo.get_by_facebook_id(fb_id)
    if not user:
        email = profile.get("email")
        if email:
            user = repo.get_by_email(email)
        if user:
            picture = (profile.get("picture") or {}).get("data", {}).get("url")
            user = repo.link_facebook(user, facebook_id=fb_id, avatar_url=picture)
        else:
            picture = (profile.get("picture") or {}).get("data", {}).get("url")
            user = repo.create_facebook_user(
                facebook_id=fb_id,
                email=email,
                name=profile.get("name", "Facebook User"),
                avatar_url=picture,
            )

    jwt = create_access_token(user.id)
    return RedirectResponse(f"{frontend}/auth/callback?token={urllib.parse.quote(jwt)}")
