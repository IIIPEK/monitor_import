import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    sqlany_uid: str
    sqlany_pwd: str
    sqlany_servername: str
    sqlany_dbn: str
    sqlany_astart: str
    sqlany_host: str
    query_file: Path


def _required(name: str, default: str = "") -> str:
    value = os.getenv(name, default).strip()
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_env_file(env_file: str) -> Path | None:
    env_path = Path(env_file)
    candidates: list[Path] = []

    if env_path.is_absolute():
        candidates.append(env_path)
    else:
        candidates.append(Path.cwd() / env_path)
        candidates.append(_project_root() / env_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _resolve_query_file(raw_path: str) -> Path:
    path = Path(raw_path.strip())
    if path.is_absolute():
        return path
    return (_project_root() / path).resolve()


def _load_conf_params() -> dict[str, str]:
    try:
        from app.conf import params
    except ImportError:
        return {}
    return params


def load_settings(env_file: str = ".env") -> Settings:
    resolved_env = _resolve_env_file(env_file)
    if resolved_env:
        load_dotenv(resolved_env)
    params = _load_conf_params()

    return Settings(
        sqlany_uid=_required("SQLANY_UID", params.get("SQLANY_UID", "")),
        sqlany_pwd=_required("SQLANY_PWD", params.get("SQLANY_PWD", "")),
        sqlany_servername=_required("SQLANY_SERVERNAME", params.get("SQLANY_SERVERNAME", "")),
        sqlany_dbn=_required("SQLANY_DBN", params.get("SQLANY_DBN", "")),
        sqlany_astart=os.getenv("SQLANY_ASTART", params.get("SQLANY_ASTART", "No")).strip() or "No",
        sqlany_host=_required("SQLANY_HOST", params.get("SQLANY_HOST", "")),
        query_file=_resolve_query_file(os.getenv("QUERY_FILE", "sql/query.sql")),
    )
