from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.web.settings import get_web_settings


class Base(DeclarativeBase):
    pass


def _create_engine():
    settings = get_web_settings()
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    if settings.database_url.startswith("sqlite:///./"):
        db_path = Path(settings.database_url.replace("sqlite:///./", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(settings.database_url, future=True, connect_args=connect_args)


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
