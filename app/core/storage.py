import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Any

DB_NAME = "worktrack.db"

class Storage:
    def __init__(self, db_path: str = DB_NAME):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Sessions table
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
        
        # Check if project_id exists in sessions (for migration)
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [info[1] for info in cursor.fetchall()]
        if "project_id" not in columns:
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN project_id INTEGER REFERENCES projects(id)")
            except sqlite3.Error:
                pass # Ignore if already exists or other error

        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        conn.commit()
        conn.close()

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
