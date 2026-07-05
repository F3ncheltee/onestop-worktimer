import sqlite3
import sys
import json
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, List, Any

from app.core import migrations

DB_NAME = "worktrack.db"

DEFAULT_QUICK_COMMENTS = ["Deep work", "Meeting", "Admin", "Research", "Coffee Break ☕"]


def resolve_db_path() -> str:
    """
    Resolves the worktrack.db location the same way the app has always found it:
    a file named `worktrack.db` sitting right next to the running app.

    - When packaged with PyInstaller (frozen), that's the folder containing the .exe.
    - When running from source, that's the project root (parent of the `app` package),
      regardless of the shell's current working directory.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        # this file lives at <project_root>/app/core/storage.py
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, DB_NAME)


class Storage:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or resolve_db_path()
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the database schema, then run any pending additive migrations."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Base tables (safe no-ops if they already exist - never altered destructively).
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_ts TEXT NOT NULL,
                end_ts TEXT,
                duration_sec INTEGER,
                date TEXT NOT NULL,
                mode TEXT CHECK(mode IN ('countup', 'countdown')) NOT NULL DEFAULT 'countup',
                target_sec INTEGER,
                completed INTEGER,
                comment TEXT,
                project_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        conn.commit()

        # Versioned, additive-only migrations (goals table, indexes, milestones, etc.)
        migrations.run_migrations(conn, self.db_path)

        conn.close()

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def create_session(self, start_ts: str, date: str, mode: str = 'countup', target_sec: Optional[int] = None, comment: str = "", project_id: Optional[int] = None) -> int:
        """Creates a new session and returns its ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sessions (start_ts, date, mode, target_sec, comment, project_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (start_ts, date, mode, target_sec, comment, project_id))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def add_past_session(self, start_ts: str, end_ts: str, date: str, duration_sec: int, comment: str = "", project_id: Optional[int] = None) -> int:
        """Manually adds a completed session."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sessions (start_ts, end_ts, duration_sec, date, mode, comment, project_id, completed)
            VALUES (?, ?, ?, ?, 'countup', ?, ?, 1)
        ''', (start_ts, end_ts, duration_sec, date, comment, project_id))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id

    def update_session(self, session_id: int, end_ts: str, duration_sec: int, completed: Optional[int] = None, comment: Optional[str] = None):
        """Updates an existing session (usually on stop)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        updates = [
            ("end_ts", end_ts),
            ("duration_sec", duration_sec),
            ("updated_at", datetime.now().isoformat())
        ]
        params = [end_ts, duration_sec, datetime.now().isoformat()]

        if completed is not None:
            updates.append(("completed", completed))
            params.append(completed)
        
        if comment is not None:
            updates.append(("comment", comment))
            params.append(comment)
            
        params.append(session_id)

        set_clause = ", ".join([f"{col} = ?" for col, _ in updates])
        
        cursor.execute(f'''
            UPDATE sessions
            SET {set_clause}
            WHERE id = ?
        ''', tuple(params))
        
        conn.commit()
        conn.close()

    def update_session_details(self, session_id: int, start_ts: str, end_ts: str, duration_sec: int, date: str, comment: str, project_id: Optional[int]):
        """Fully updates session details (for edit dialog)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sessions
            SET start_ts = ?, end_ts = ?, duration_sec = ?, date = ?, comment = ?, project_id = ?, updated_at = ?
            WHERE id = ?
        ''', (start_ts, end_ts, duration_sec, date, comment, project_id, datetime.now().isoformat(), session_id))
        
        conn.commit()
        conn.close()

    def delete_session(self, session_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()

    def get_active_session(self) -> Optional[Dict[str, Any]]:
        """Checks if there is a running session (end_ts is NULL) and returns it."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.*, p.name as project_name, p.color as project_color
            FROM sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE s.end_ts IS NULL 
            ORDER BY s.id DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        return None

    def get_sessions(self, limit: int = 100, date_from: str = None, date_to: str = None, search: str = None) -> List[Dict[str, Any]]:
        """Returns list of sessions with optional filters."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT s.*, p.name as project_name, p.color as project_color
            FROM sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE 1=1
        '''
        params = []
        
        if date_from:
            query += " AND s.date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND s.date <= ?"
            params.append(date_to)
        if search:
            query += " AND (s.comment LIKE ? OR p.name LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
            
        query += " ORDER BY s.start_ts DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, tuple(params))
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))
            
        conn.close()
        return results

    def get_daily_duration_totals(self, date_from: str, date_to: str) -> Dict[str, int]:
        """Sum duration_sec per calendar date for sessions that have a recorded duration."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT date, COALESCE(SUM(duration_sec), 0)
            FROM sessions
            WHERE date >= ? AND date <= ?
              AND duration_sec IS NOT NULL AND duration_sec > 0
            GROUP BY date
            """,
            (date_from, date_to),
        )
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: int(row[1]) for row in rows}

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def get_projects(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY name")
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        conn.close()
        return [dict(zip(columns, row)) for row in rows]

    def add_project(self, name: str, color: str = None) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO projects (name, color) VALUES (?, ?)", (name, color))
            pid = cursor.lastrowid
            conn.commit()
            return pid
        except sqlite3.IntegrityError:
            conn.close()
            raise ValueError("Project already exists")
        finally:
             if conn: conn.close()

    def update_project(self, project_id: int, name: str, color: str = None):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE projects SET name = ?, color = ? WHERE id = ?", (name, color, project_id))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            raise ValueError("Project name already exists")
        finally:
             if conn: conn.close()

    def delete_project(self, project_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # First, set project_id to NULL in sessions table to prevent breaking history
            cursor.execute("UPDATE sessions SET project_id = NULL WHERE project_id = ?", (project_id,))
            # Then delete the project
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
        finally:
            if conn: conn.close()

    # ------------------------------------------------------------------
    # Settings (generic JSON-encoded key/value store)
    # ------------------------------------------------------------------

    def save_setting(self, key: str, value: Any):
        """Saves a setting value (JSON encoded)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        json_val = json.dumps(value)
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        ''', (key, json_val))
        
        conn.commit()
        conn.close()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieves a setting value."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return row[0]
        return default

    def get_quick_comments(self) -> List[str]:
        return self.get_setting("quick_comments", DEFAULT_QUICK_COMMENTS)

    def save_quick_comments(self, comments: List[str]):
        cleaned = [c.strip() for c in comments if c and c.strip()]
        self.save_setting("quick_comments", cleaned)

    # ------------------------------------------------------------------
    # Goals (daily/weekly targets, overall or per-project)
    # ------------------------------------------------------------------

    def get_goals(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT g.*, p.name as project_name, p.color as project_color
            FROM goals g
            LEFT JOIN projects p ON g.project_id = p.id
            ORDER BY g.scope, g.period
        ''')
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        conn.close()
        return [dict(zip(columns, row)) for row in rows]

    def upsert_goal(self, scope: str, period: str, target_sec: int, project_id: Optional[int] = None) -> int:
        """Creates or updates the goal matching (scope, project_id, period)."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if scope == "project" and project_id is not None:
            cursor.execute(
                "SELECT id FROM goals WHERE scope = ? AND project_id = ? AND period = ?",
                (scope, project_id, period),
            )
        else:
            cursor.execute(
                "SELECT id FROM goals WHERE scope = ? AND project_id IS NULL AND period = ?",
                (scope, period),
            )
        existing = cursor.fetchone()

        now = datetime.now().isoformat()
        if existing:
            goal_id = existing[0]
            cursor.execute(
                "UPDATE goals SET target_sec = ?, updated_at = ? WHERE id = ?",
                (target_sec, now, goal_id),
            )
        else:
            cursor.execute(
                "INSERT INTO goals (scope, project_id, period, target_sec) VALUES (?, ?, ?, ?)",
                (scope, project_id if scope == "project" else None, period, target_sec),
            )
            goal_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return goal_id

    def delete_goal(self, goal_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Milestones
    # ------------------------------------------------------------------

    def has_milestone_seen(self, key: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM milestones_seen WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row is not None

    def mark_milestone_seen(self, key: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO milestones_seen (key) VALUES (?)", (key,))
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Backup / restore / export (Settings > Data panel)
    # ------------------------------------------------------------------

    def backup_now(self) -> str:
        path = migrations.backup_db(self.db_path, tag="manual")
        if not path:
            raise IOError("Database file not found, nothing to back up.")
        return path

    def list_backups(self) -> List[Dict[str, Any]]:
        backups_dir = migrations.backups_dir_for(self.db_path)
        items = []
        for name in os.listdir(backups_dir):
            if name.endswith(".db"):
                full = os.path.join(backups_dir, name)
                items.append({
                    "name": name,
                    "path": full,
                    "size_bytes": os.path.getsize(full),
                    "modified": datetime.fromtimestamp(os.path.getmtime(full)).isoformat(),
                })
        items.sort(key=lambda i: i["modified"], reverse=True)
        return items

    def restore_from_backup(self, backup_path: str):
        if not os.path.exists(backup_path):
            raise IOError("Backup file not found.")
        migrations.backup_db(self.db_path, tag="pre_restore")
        shutil.copy2(backup_path, self.db_path)

    def export_bundle(self) -> Dict[str, Any]:
        """Full JSON export of all app data (sessions, projects, goals, settings)."""
        conn = self._get_connection()
        cursor = conn.cursor()

        def _all(table):
            cursor.execute(f"SELECT * FROM {table}")
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

        bundle = {
            "exported_at": datetime.now().isoformat(),
            "db_path": self.db_path,
            "sessions": _all("sessions"),
            "projects": _all("projects"),
            "goals": _all("goals"),
            "settings": _all("settings"),
        }
        conn.close()
        return bundle
