"""
Versioned, additive-only SQLite migration runner.

Rules that keep existing data safe:
  * Every migration may only ADD columns/tables/indexes - never DROP or
    RENAME an existing column/table, never change a column's type.
  * The current schema version is tracked with SQLite's built-in
    ``PRAGMA user_version`` (no extra table needed).
  * Before applying any pending migration, the raw ``.db`` file is copied
    into a rotating backups folder so a bad migration can never destroy
    user data.
"""
import os
import shutil
import sqlite3
from datetime import datetime
from typing import Callable, List, Optional

MAX_ROTATING_BACKUPS = 15


def backups_dir_for(db_path: str) -> str:
    base = os.path.dirname(os.path.abspath(db_path))
    path = os.path.join(base, "backups")
    os.makedirs(path, exist_ok=True)
    return path


def backup_db(db_path: str, tag: str = "auto") -> Optional[str]:
    """Copies the db file into backups/ with a timestamped name. Returns the new path (or None if source missing)."""
    if not os.path.exists(db_path):
        return None

    dest_dir = backups_dir_for(db_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(dest_dir, f"worktrack.{tag}_{ts}.db")
    shutil.copy2(db_path, dest)
    _rotate_backups(dest_dir)
    return dest


def _rotate_backups(dest_dir: str, keep: int = MAX_ROTATING_BACKUPS):
    try:
        files = [
            os.path.join(dest_dir, f)
            for f in os.listdir(dest_dir)
            if f.startswith("worktrack.") and f.endswith(".db")
        ]
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for stale in files[keep:]:
            try:
                os.remove(stale)
            except OSError:
                pass
    except OSError:
        pass


# --- Migration steps -------------------------------------------------------
# Each entry: target_version -> function(cursor) that mutates schema only.
# Never remove an entry once released; append new ones with increasing versions.

def _migration_v1(cursor: sqlite3.Cursor):
    """Ensure sessions.project_id exists (older DBs may pre-date this column)."""
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [info[1] for info in cursor.fetchall()]
    if "project_id" not in columns:
        cursor.execute("ALTER TABLE sessions ADD COLUMN project_id INTEGER REFERENCES projects(id)")


def _migration_v2(cursor: sqlite3.Cursor):
    """Add goals table (daily/weekly targets, overall or per-project)."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT NOT NULL CHECK(scope IN ('overall', 'project')),
            project_id INTEGER REFERENCES projects(id),
            period TEXT NOT NULL CHECK(period IN ('daily', 'weekly')),
            target_sec INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _migration_v3(cursor: sqlite3.Cursor):
    """Helpful indexes for the new dashboard/heatmap/analytics queries."""
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id)")


def _migration_v4(cursor: sqlite3.Cursor):
    """Milestones log — prevents duplicate milestone notifications."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS milestones_seen (
            key TEXT PRIMARY KEY,
            seen_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


MIGRATIONS: List[Callable[[sqlite3.Cursor], None]] = [
    _migration_v1,
    _migration_v2,
    _migration_v3,
    _migration_v4,
]


def run_migrations(conn: sqlite3.Connection, db_path: str):
    """Applies any pending migrations, backing up the db first if there are any."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    current_version = cursor.fetchone()[0]
    target_version = len(MIGRATIONS)

    if current_version >= target_version:
        return

    backup_db(db_path, tag="pre_migration")

    for version in range(current_version, target_version):
        migration_fn = MIGRATIONS[version]
        migration_fn(cursor)
        cursor.execute(f"PRAGMA user_version = {version + 1}")

    conn.commit()
