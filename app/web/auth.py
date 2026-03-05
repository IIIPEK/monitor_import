from fastapi import Cookie, Depends, HTTPException
from itsdangerous import BadSignature, URLSafeSerializer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.web.db import get_db
from app.web.models import User
from app.web.settings import get_web_settings


SESSION_COOKIE_NAME = "mi_session"
_pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain_password, password_hash)


def _session_serializer() -> URLSafeSerializer:
    settings = get_web_settings()
    return URLSafeSerializer(settings.session_secret, salt="monitor-import-session")


def create_session_token(user_id: int) -> str:
    return _session_serializer().dumps({"user_id": user_id})


def parse_session_token(token: str) -> int | None:
    try:
        payload = _session_serializer().loads(token)
    except BadSignature:
        return None

    user_id = payload.get("user_id")
    return user_id if isinstance(user_id, int) else None


def get_optional_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> User | None:
    if not session_token:
        return None

    user_id = parse_session_token(session_token)
    if user_id is None:
        return None

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    return user


def get_current_user(current_user: User | None = Depends(get_optional_current_user)) -> User:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
