from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select

from app.web.auth import hash_password
from app.web.db import SessionLocal, engine
from app.web.models import User
from app.web.settings import get_web_settings


def _run_migrations() -> None:
    project_root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    settings = get_web_settings()
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    has_app_tables = "users" in table_names or "conversion_jobs" in table_names
    has_alembic_table = "alembic_version" in table_names

    if has_app_tables and not has_alembic_table:
        command.stamp(alembic_cfg, "head")
        return

    command.upgrade(alembic_cfg, "head")


def initialize_database() -> None:
    _run_migrations()

    settings = get_web_settings()
    with SessionLocal() as db:
        admin_exists = db.scalar(select(User.id).where(User.is_admin.is_(True)))
        if admin_exists is not None:
            return

        user = User(
            username=settings.bootstrap_admin_login,
            password_hash=hash_password(settings.bootstrap_admin_password),
            is_admin=True,
            is_active=True,
        )
        db.add(user)
        db.commit()
