"""SQLite storage layer for mission dashboard."""

from __future__ import annotations

import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .constants import APP_NAME, DEFAULT_SORT_DIR, DEFAULT_SORT_FIELD, FILTER_FIELDS, PERSON_FIELDS, SCHEMA_VERSION
from .models import DatasetState, PersonRecord


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_default_db_path(app_name: str = APP_NAME) -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".local" / "share"
    data_dir = base / app_name.replace(" ", "")
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "dashboard.sqlite3"


class StorageRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.recovery_notice: str | None = None
        self._initialize()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _initialize(self) -> None:
        try:
            with self._connect() as conn:
                self._create_schema(conn)
                conn.commit()
                conn.execute("PRAGMA quick_check")
        except sqlite3.DatabaseError:
            backup = self.db_path.with_suffix(self.db_path.suffix + ".corrupt")
            try:
                shutil.move(self.db_path, backup)
            except OSError:
                pass
            self.recovery_notice = f"Corrupt local database was moved to {backup.name}."
            with self._connect() as conn:
                self._create_schema(conn)
                conn.commit()

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS people (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                current_companion TEXT,
                new_companion TEXT,
                current_zone TEXT,
                current_area TEXT,
                new_zone TEXT,
                new_area TEXT,
                staying INTEGER,
                pre_travel TEXT,
                departure_terminal TEXT,
                departure_time TEXT,
                arrival_terminal TEXT,
                arrival_time TEXT,
                second_leg INTEGER,
                second_departure_terminal TEXT,
                second_departure_time TEXT,
                second_arrival_terminal TEXT,
                second_arrival_time TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_file_name TEXT,
                source_row_number INTEGER,
                dataset_version INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dataset_meta (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                source_file_name TEXT,
                created_at TEXT NOT NULL,
                records_processed INTEGER NOT NULL,
                records_inserted INTEGER NOT NULL,
                records_updated INTEGER NOT NULL,
                records_skipped INTEGER NOT NULL,
                success INTEGER NOT NULL,
                notes TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_people_current_zone ON people(current_zone);
            CREATE INDEX IF NOT EXISTS idx_people_current_area ON people(current_area);
            CREATE INDEX IF NOT EXISTS idx_people_new_zone ON people(new_zone);
            CREATE INDEX IF NOT EXISTS idx_people_new_area ON people(new_area);
            CREATE INDEX IF NOT EXISTS idx_people_first_name ON people(first_name);
            CREATE INDEX IF NOT EXISTS idx_people_last_name ON people(last_name);
            CREATE INDEX IF NOT EXISTS idx_people_departure_time ON people(departure_time);
            CREATE INDEX IF NOT EXISTS idx_people_arrival_time ON people(arrival_time);
            CREATE INDEX IF NOT EXISTS idx_people_second_leg ON people(second_leg);
            CREATE INDEX IF NOT EXISTS idx_people_second_departure_time ON people(second_departure_time);
            CREATE INDEX IF NOT EXISTS idx_people_second_arrival_time ON people(second_arrival_time);
            """
        )
        for key, value in {
            "schema_version": str(SCHEMA_VERSION),
            "last_imported_at": "",
            "record_count": "0",
            "source_file_name": "",
        }.items():
            conn.execute("INSERT OR IGNORE INTO dataset_meta(key, value) VALUES(?, ?)", (key, value))

    def dataset_state(self) -> DatasetState:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM dataset_meta").fetchall()
            meta = {r["key"]: r["value"] for r in rows}
        return DatasetState(
            record_count=int(meta.get("record_count", "0") or 0),
            schema_version=int(meta.get("schema_version", str(SCHEMA_VERSION)) or SCHEMA_VERSION),
            last_imported_at=meta.get("last_imported_at") or None,
            source_file_name=meta.get("source_file_name") or None,
            recovery_notice=self.recovery_notice,
        )

    def _set_meta(self, conn: sqlite3.Connection, **meta: str) -> None:
        for key, value in meta.items():
            conn.execute(
                "INSERT INTO dataset_meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def _record_history(self, conn: sqlite3.Connection, operation: str, source_file_name: str, processed: int, inserted: int, updated: int, skipped: int, success: bool, notes: str = "") -> None:
        conn.execute(
            "INSERT INTO import_history(operation, source_file_name, created_at, records_processed, records_inserted, records_updated, records_skipped, success, notes) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (operation, source_file_name, utc_now(), processed, inserted, updated, skipped, 1 if success else 0, notes),
        )

    def _insert_person(self, conn: sqlite3.Connection, rec: dict[str, Any]) -> None:
        now = utc_now()
        row = {field: rec.get(field) for field in PERSON_FIELDS}
        row.update(
            {
                "id": rec.get("id") or str(uuid4()),
                "created_at": now,
                "updated_at": now,
                "source_file_name": rec.get("source_file_name"),
                "source_row_number": rec.get("source_row_number"),
                "dataset_version": SCHEMA_VERSION,
            }
        )
        conn.execute(
            """
            INSERT INTO people(
                id, first_name, last_name, current_companion, new_companion, current_zone,
                current_area, new_zone, new_area, staying, pre_travel, departure_terminal,
                departure_time, arrival_terminal, arrival_time, second_leg,
                second_departure_terminal, second_departure_time, second_arrival_terminal,
                second_arrival_time, created_at, updated_at, source_file_name, source_row_number, dataset_version
            ) VALUES(
                :id, :first_name, :last_name, :current_companion, :new_companion, :current_zone,
                :current_area, :new_zone, :new_area, :staying, :pre_travel, :departure_terminal,
                :departure_time, :arrival_terminal, :arrival_time, :second_leg,
                :second_departure_terminal, :second_departure_time, :second_arrival_terminal,
                :second_arrival_time, :created_at, :updated_at, :source_file_name, :source_row_number, :dataset_version
            )
            """,
            row,
        )

    def _update_person_row(self, conn: sqlite3.Connection, person_id: str, rec: dict[str, Any]) -> None:
        values = {field: rec.get(field) for field in PERSON_FIELDS}
        values["id"] = person_id
        values["updated_at"] = utc_now()
        conn.execute(
            """
            UPDATE people SET
                first_name=:first_name, last_name=:last_name,
                current_companion=:current_companion, new_companion=:new_companion,
                current_zone=:current_zone, current_area=:current_area,
                new_zone=:new_zone, new_area=:new_area,
                staying=:staying, pre_travel=:pre_travel,
                departure_terminal=:departure_terminal, departure_time=:departure_time,
                arrival_terminal=:arrival_terminal, arrival_time=:arrival_time,
                second_leg=:second_leg, second_departure_terminal=:second_departure_terminal,
                second_departure_time=:second_departure_time, second_arrival_terminal=:second_arrival_terminal,
                second_arrival_time=:second_arrival_time, updated_at=:updated_at
            WHERE id=:id
            """,
            values,
        )

    def replace_people(self, records: list[dict[str, Any]], source_file_name: str, processed: int, skipped: int) -> tuple[int, int]:
        inserted = 0
        with self._connect() as conn:
            conn.execute("BEGIN")
            conn.execute("DELETE FROM people")
            for rec in records:
                self._insert_person(conn, rec)
                inserted += 1
            self._set_meta(conn, last_imported_at=utc_now(), record_count=str(inserted), source_file_name=source_file_name, schema_version=str(SCHEMA_VERSION))
            self._record_history(conn, "replace", source_file_name, processed, inserted, 0, skipped, True)
            conn.commit()
        return inserted, 0

    def append_people(self, records: list[dict[str, Any]], source_file_name: str, processed: int, skipped: int) -> tuple[int, int]:
        inserted = 0
        updated = 0
        with self._connect() as conn:
            conn.execute("BEGIN")
            for rec in records:
                existing = conn.execute(
                    "SELECT id FROM people WHERE lower(first_name)=? AND lower(last_name)=? AND lower(COALESCE(current_area,''))=?",
                    ((rec.get("first_name") or "").lower(), (rec.get("last_name") or "").lower(), (rec.get("current_area") or "").lower()),
                ).fetchone()
                if existing:
                    self._update_person_row(conn, existing["id"], rec)
                    updated += 1
                else:
                    self._insert_person(conn, rec)
                    inserted += 1
            count = conn.execute("SELECT COUNT(*) as c FROM people").fetchone()["c"]
            self._set_meta(conn, last_imported_at=utc_now(), record_count=str(count), source_file_name=source_file_name, schema_version=str(SCHEMA_VERSION))
            self._record_history(conn, "append", source_file_name, processed, inserted, updated, skipped, True)
            conn.commit()
        return inserted, updated

    def _row_to_person(self, row: sqlite3.Row) -> PersonRecord:
        data = dict(row)
        for key in ("staying", "second_leg"):
            if data.get(key) is not None:
                data[key] = bool(data[key])
        return PersonRecord(**data)

    def list_people(self, filters: dict[str, Any] | None = None, sort_field: str = DEFAULT_SORT_FIELD, sort_dir: str = DEFAULT_SORT_DIR, search_field: str | None = None, search_query: str | None = None) -> list[PersonRecord]:
        filters = filters or {}
        where = []
        params: list[Any] = []
        for field in FILTER_FIELDS:
            value = filters.get(field)
            if value in (None, "", "All"):
                continue
            if field == "second_leg":
                where.append("second_leg = ?")
                params.append(1 if str(value).lower() in {"yes", "true", "1"} else 0)
            else:
                where.append(f"COALESCE({field}, '') = ?")
                params.append(value)

        if search_query:
            q = f"%{search_query.strip().lower()}%"
            boolean_expr = (
                "lower(CASE WHEN {field}=1 THEN 'yes' "
                "WHEN {field}=0 THEN 'no' ELSE '' END) LIKE ?"
            )

            def field_search_clause(field: str) -> str:
                if field in {"staying", "second_leg"}:
                    return boolean_expr.format(field=field)
                return f"lower(COALESCE(CAST({field} AS TEXT), '')) LIKE ?"

            if search_field and search_field in PERSON_FIELDS:
                where.append(field_search_clause(search_field))
                params.append(q)
            else:
                where.append(
                    "("
                    + " OR ".join([field_search_clause(field) for field in PERSON_FIELDS])
                    + ")"
                )
                params.extend([q] * len(PERSON_FIELDS))

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        allowed_sort = set(PERSON_FIELDS)
        sort_field = sort_field if sort_field in allowed_sort else DEFAULT_SORT_FIELD
        dir_sql = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
        query = f"SELECT * FROM people {where_sql} ORDER BY COALESCE({sort_field}, '') {dir_sql}, last_name ASC, first_name ASC, id ASC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_person(r) for r in rows]

    def get_person(self, person_id: str) -> PersonRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
        return self._row_to_person(row) if row else None

    def update_person(self, person_id: str, patch: dict[str, Any]) -> PersonRecord | None:
        existing = self.get_person(person_id)
        if not existing:
            return None
        updates = {k: v for k, v in patch.items() if k in set(PERSON_FIELDS)}
        if not updates:
            return existing
        updates["id"] = person_id
        updates["updated_at"] = utc_now()
        assigns = ", ".join([f"{k}=:{k}" for k in updates if k != "id"])
        with self._connect() as conn:
            conn.execute(f"UPDATE people SET {assigns} WHERE id=:id", updates)
            conn.commit()
        return self.get_person(person_id)

    def clear_dataset(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM people")
            self._set_meta(conn, last_imported_at="", record_count="0", source_file_name="", schema_version=str(SCHEMA_VERSION))
            self._record_history(conn, "clear", "", 0, 0, 0, 0, True)
            conn.commit()
