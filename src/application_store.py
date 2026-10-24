"""Local SQLite storage for applications and their Google Calendar events."""

import sqlite3
import os
from pathlib import Path
from datetime import datetime


class ApplicationStore:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_url = os.environ.get("DATABASE_URL")
        if not self.database_url:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        if self.database_url:
            import psycopg
            from psycopg.rows import dict_row
            return psycopg.connect(self.database_url, row_factory=dict_row)
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self):
        if self.database_url:
            with self._connect() as connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS applications (
                        id BIGSERIAL PRIMARY KEY, label TEXT NOT NULL,
                        active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS application_events (
                        id BIGSERIAL PRIMARY KEY,
                        application_id BIGINT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                        title TEXT NOT NULL, event_date TEXT NOT NULL,
                        google_event_id TEXT, status TEXT NOT NULL DEFAULT 'pending'
                    )
                """)
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS app_secrets (
                        name TEXT PRIMARY KEY, value TEXT NOT NULL
                    )
                """)
            return
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS application_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    google_event_id TEXT,
                    status TEXT NOT NULL DEFAULT 'pending'
                );
                CREATE TABLE IF NOT EXISTS app_secrets (
                    name TEXT PRIMARY KEY, value TEXT NOT NULL
                );
            """)

    def _sql(self, sql):
        return sql.replace("?", "%s") if self.database_url else sql

    def create_application(self, label, timeline):
        with self._connect() as connection:
            if self.database_url:
                row = connection.execute("INSERT INTO applications(label, active) VALUES (%s, FALSE) RETURNING id", (label,)).fetchone()
                application_id = row["id"]
            else:
                cursor = connection.execute("INSERT INTO applications(label, active) VALUES (?, 0)", (label,))
                application_id = cursor.lastrowid
            connection.executemany(
                self._sql("INSERT INTO application_events(application_id, title, event_date) VALUES (?, ?, ?)"),
                [(application_id, item["Event"], datetime.strptime(item["Date"], "%d-%m-%Y").strftime("%Y-%m-%d")) for item in timeline],
            )
        return application_id

    def save_created_events(self, application_id, created_events):
        with self._connect() as connection:
            for item in created_events:
                event_date = datetime.strptime(item["date"], "%d-%m-%Y").strftime("%Y-%m-%d")
                row = connection.execute(self._sql(
                    """SELECT id FROM application_events WHERE application_id = ? AND title = ?
                       AND event_date = ? AND status = 'pending' ORDER BY id LIMIT 1""",
                ), (application_id, item["title"], event_date)).fetchone()
                if row:
                    connection.execute(self._sql("UPDATE application_events SET google_event_id = ?, status = 'active' WHERE id = ?"),
                                        (item["id"], row["id"]))

    def remove_application(self, application_id):
        with self._connect() as connection:
            connection.execute(self._sql("DELETE FROM applications WHERE id = ?"), (application_id,))

    def list_applications(self):
        with self._connect() as connection:
            rows = connection.execute("""
                SELECT a.id, a.label, a.active, a.created_at,
                       e.id AS event_id, e.title, e.event_date, e.google_event_id, e.status
                FROM applications a
                LEFT JOIN application_events e ON e.application_id = a.id
                ORDER BY a.created_at DESC, a.id DESC, e.event_date, e.id
            """).fetchall()
        applications = []
        for row in rows:
            if not applications or applications[-1]["id"] != row["id"]:
                applications.append({"id": row["id"], "label": row["label"], "active": bool(row["active"]),
                                     "created_at": row["created_at"], "events": []})
            if row["event_id"] is not None:
                applications[-1]["events"].append({"id": row["event_id"], "title": row["title"],
                    "date": row["event_date"], "date_display": datetime.strptime(row["event_date"], "%Y-%m-%d").strftime("%d %b %Y"),
                    "google_event_id": row["google_event_id"], "status": row["status"]})
        return applications

    def get_application(self, application_id):
        applications = self.list_applications()
        return next((item for item in applications if item["id"] == application_id), None)

    def get_pending_events(self, application_id):
        with self._connect() as connection:
            rows = connection.execute(self._sql(
                "SELECT id, title, event_date FROM application_events WHERE application_id = ? AND status = 'pending' ORDER BY event_date, id"),
                (application_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_event_status(self, event_id, status):
        with self._connect() as connection:
            connection.execute(self._sql("UPDATE application_events SET status = ? WHERE id = ?"), (status, event_id))

    def set_event_calendar(self, event_id, google_event_id, status):
        with self._connect() as connection:
            connection.execute(self._sql("UPDATE application_events SET google_event_id = ?, status = ? WHERE id = ?"),
                               (google_event_id, status, event_id))

    def set_application_active(self, application_id, active):
        with self._connect() as connection:
            connection.execute(self._sql("UPDATE applications SET active = ? WHERE id = ?"), (bool(active) if self.database_url else int(active), application_id))

    def get_event_by_id(self, event_id):
        with self._connect() as connection:
            row = connection.execute(self._sql("SELECT * FROM application_events WHERE id = ?"), (event_id,)).fetchone()
        return dict(row) if row else None

    def get_secret(self, name):
        with self._connect() as connection:
            row = connection.execute(self._sql("SELECT value FROM app_secrets WHERE name = ?"), (name,)).fetchone()
        return row["value"] if row else None

    def set_secret(self, name, value):
        with self._connect() as connection:
            connection.execute(self._sql("""INSERT INTO app_secrets(name, value) VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET value = excluded.value"""), (name, value))
