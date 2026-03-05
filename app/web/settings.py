import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class WebSettings:
    database_url: str
    session_secret: str
    bootstrap_admin_login: str
    bootstrap_admin_password: str


@lru_cache(maxsize=1)
def get_web_settings() -> WebSettings:
    return WebSettings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/web.db"),
        session_secret=os.getenv("SESSION_SECRET", "change-me-session-secret"),
        bootstrap_admin_login=os.getenv("BOOTSTRAP_ADMIN_LOGIN", "admin"),
        bootstrap_admin_password=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "admin"),
    )
