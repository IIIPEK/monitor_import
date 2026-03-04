from __future__ import annotations

from pathlib import Path
from typing import Any

import sqlanydb

from app.config import Settings


class SQLAnyQueryError(RuntimeError):
    pass


class SQLAnyDBClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._conn = sqlanydb.connect(
            uid=settings.sqlany_uid,
            pwd=settings.sqlany_pwd,
            servername=settings.sqlany_servername,
            dbn=settings.sqlany_dbn,
            astart=settings.sqlany_astart,
            host=settings.sqlany_host,
        )
        self._cursor = self._conn.cursor()

    def query_select(self, query: str, params: tuple[Any, ...] | None = None):
        try:
            self._cursor.execute(query, params or ())
            return self._cursor.description, self._cursor.fetchall()
        except Exception as exc:  # pragma: no cover
            raise SQLAnyQueryError(f"SQLAny query failed: {exc}") from exc

    def read_query(self, query_file: str | Path | None = None) -> str:
        path = Path(query_file) if query_file else self._settings.query_file
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise SQLAnyQueryError(f"Cannot read SQL file '{path}': {exc}") from exc

    def query_select_from_file(
        self,
        query_file: str | Path | None = None,
        params: tuple[Any, ...] | None = None,
    ):
        return self.query_select(self.read_query(query_file), params=params)

    def close(self):
        self._cursor.close()
        self._conn.close()

    def __enter__(self) -> SQLAnyDBClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
