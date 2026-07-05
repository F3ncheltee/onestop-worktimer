"""
JS-facing API bridge.

Every public method on `Api` becomes callable from the front end as
`window.pywebview.api.<method_name>(...)` and returns a JSON-serializable
value (pywebview handles the (de)serialization automatically).
"""
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import webview

from app.core.storage import Storage
from app.core.timer import Timer
from app.core.analytics import Analytics
from app.core.export import Exporter
from app.core.idle import IdleDetector

DEFAULT_SETTINGS = {
    "idle_enabled": False,
    "idle_threshold_min": 5,
    "idle_warning_sec": 30,
    "idle_auto_resume": True,
    "smart_enabled": True,
    "smart_interval_min": 50,
    "theme": "dark",
    "hotkey_enabled": True,
}


class Api:
    """Public methods are exposed to JS via pywebview. Use underscore-prefixed attrs for internals."""

    def __init__(self, storage: Storage, timer: Timer, analytics: Analytics):
        self._storage = storage
        self._timer = timer
        self._analytics = analytics
        self._idle_detector = IdleDetector()

        self._window: Optional["webview.Window"] = None
        self._auto_paused = False
        self._idle_warning_active = False
        self._stop_background = threading.Event()

    # ------------------------------------------------------------------
    # Wiring (called from main.py, not exposed to JS)
    # ------------------------------------------------------------------

    def bind_window(self, window):
        self._window = window

    def _push(self, js: str):
        """Safely runs JS in the front end from a background thread."""
        if self._window is None:
            return
        try:
            self._window.evaluate_js(js)
        except Exception:
            pass

    def start_background_loops(self):
        threading.Thread(target=self._idle_loop, daemon=True).start()

    def shutdown(self):
        self._stop_background.set()

    def _idle_loop(self):
        while not self._stop_background.is_set():
            time.sleep(2)
            try:
                self._check_idle_once()
            except Exception:
                pass

    def _check_idle_once(self):
        settings = self.get_settings()
        if not settings.get("idle_enabled"):
            return

        threshold_sec = float(settings.get("idle_threshold_min", 5)) * 60
        idle_sec = self._idle_detector.get_idle_seconds()

        if self._timer.is_running() and self._timer.mode == "countup":
            if idle_sec > threshold_sec and not self._idle_warning_active:
                self._idle_warning_active = True
                warning_sec = int(settings.get("idle_warning_sec", 30))
                self._push(f"window.__onIdleWarning && window.__onIdleWarning({warning_sec})")

        if self._auto_paused and settings.get("idle_auto_resume", True):
            if idle_sec < 2.0:
                self._auto_paused = False
                self._push("window.__onAutoResumeAvailable && window.__onAutoResumeAvailable()")

    # Called by the front end once the user dismisses/times-out the idle overlay.
    def idle_warning_resolved(self, timed_out: bool):
        self._idle_warning_active = False
        if timed_out:
            state = self.stop_timer(None)
            self._auto_paused = True
            return {"auto_paused": True, "state": state}
        return {"auto_paused": False}

    def clear_auto_pause(self):
        self._auto_paused = False

    # ------------------------------------------------------------------
    # Bootstrap
    # ------------------------------------------------------------------

    def get_bootstrap(self) -> Dict[str, Any]:
        projects = self.get_projects()
        return {
            "timer_state": self.get_timer_state(),
            "projects": projects,
            "quick_comments": self._storage.get_quick_comments(),
            "settings": self.get_settings(),
            "kpis": self._analytics.get_kpis(),
            "streak": self._analytics.get_streak(),
            "goal_progress": self._analytics.get_goal_progress(),
            "week_glance": self._analytics.get_week_glance(),
            "milestones": self.check_milestones(),
            "db_info": self.get_db_info(),
        }

    # ------------------------------------------------------------------
    # Timer
    # ------------------------------------------------------------------

    def get_timer_state(self) -> Dict[str, Any]:
        running = self._timer.is_running()
        state: Dict[str, Any] = {
            "running": running,
            "mode": self._timer.mode,
            "start_ts": self._timer.start_time.isoformat() if self._timer.start_time else None,
            "target_sec": int(self._timer.target_duration.total_seconds()) if self._timer.target_duration else None,
            "comment": "",
            "project_id": None,
            "auto_paused": self._auto_paused,
        }
        if running and self._timer.current_session_id:
            conn = self._storage._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT comment, project_id FROM sessions WHERE id = ?",
                (self._timer.current_session_id,),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                state["comment"] = row[0] or ""
                state["project_id"] = row[1]
        return state

    def start_timer(self, mode: str, target_sec: Optional[int], comment: str, project_id: Optional[int]) -> Dict[str, Any]:
        target_duration = timedelta(seconds=target_sec) if target_sec else None
        self._timer.start(mode=mode, target_duration=target_duration, comment=comment or "", project_id=project_id)
        self._auto_paused = False
        return self.get_timer_state()

    def stop_timer(self, comment: Optional[str]) -> Dict[str, Any]:
        self._timer.stop(comment=comment)
        return self.get_timer_state()

    def toggle_timer_from_hotkey(self):
        """Invoked by the global hotkey listener; tells the front end to toggle."""
        self._push("window.__onHotkeyToggle && window.__onHotkeyToggle()")

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def get_projects(self) -> List[Dict[str, Any]]:
        return self._storage.get_projects()

    def add_project(self, name: str, color: str) -> Dict[str, Any]:
        try:
            pid = self._storage.add_project(name.strip(), color)
            return {"success": True, "id": pid}
        except ValueError as e:
            return {"success": False, "error": str(e)}

    def update_project(self, project_id: int, name: str, color: str) -> Dict[str, Any]:
        try:
            self._storage.update_project(project_id, name.strip(), color)
            return {"success": True}
        except ValueError as e:
            return {"success": False, "error": str(e)}

    def delete_project(self, project_id: int) -> Dict[str, Any]:
        self._storage.delete_project(project_id)
        return {"success": True}

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def get_sessions(self, date_from: Optional[str] = None, date_to: Optional[str] = None,
                      search: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return self._storage.get_sessions(limit=limit, date_from=date_from, date_to=date_to, search=search)

    def add_session(self, start_iso: str, end_iso: str, comment: str, project_id: Optional[int]) -> Dict[str, Any]:
        start_dt = datetime.fromisoformat(start_iso)
        end_dt = datetime.fromisoformat(end_iso)
        if end_dt <= start_dt:
            return {"success": False, "error": "End time must be after start time."}
        duration = int((end_dt - start_dt).total_seconds())
        sid = self._storage.add_past_session(
            start_dt.isoformat(), end_dt.isoformat(), start_dt.strftime("%Y-%m-%d"),
            duration, comment or "", project_id,
        )
        return {"success": True, "id": sid}

    def update_session(self, session_id: int, start_iso: str, end_iso: str, comment: str,
                        project_id: Optional[int]) -> Dict[str, Any]:
        start_dt = datetime.fromisoformat(start_iso)
        end_dt = datetime.fromisoformat(end_iso)
        if end_dt <= start_dt:
            return {"success": False, "error": "End time must be after start time."}
        duration = int((end_dt - start_dt).total_seconds())
        self._storage.update_session_details(
            session_id, start_dt.isoformat(), end_dt.isoformat(), duration,
            start_dt.strftime("%Y-%m-%d"), comment or "", project_id,
        )
        return {"success": True}

    def delete_session(self, session_id: int) -> Dict[str, Any]:
        self._storage.delete_session(session_id)
        return {"success": True}

    def export_sessions(self, fmt: str, date_from: Optional[str], date_to: Optional[str],
                         search: Optional[str]) -> Dict[str, Any]:
        sessions = self._storage.get_sessions(limit=None, date_from=date_from, date_to=date_to, search=search)
        if not sessions:
            return {"success": False, "error": "No sessions to export for the current filters."}

        default_name = "sessions.xlsx" if fmt == "excel" else "sessions.csv"
        file_types = ("Excel Files (*.xlsx)",) if fmt == "excel" else ("CSV Files (*.csv)",)

        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=default_name, file_types=file_types
        )
        if not result:
            return {"success": False, "error": None}

        path = result[0] if isinstance(result, (list, tuple)) else result
        try:
            if fmt == "excel":
                Exporter.export_excel(path, sessions)
            else:
                Exporter.export_csv(path, sessions)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Calendar
    # ------------------------------------------------------------------

    def get_month_data(self, date_from: str, date_to: str) -> Dict[str, Any]:
        totals = self._storage.get_daily_duration_totals(date_from, date_to)
        sessions = self._storage.get_sessions(limit=None, date_from=date_from, date_to=date_to)
        return {"daily_totals": totals, "sessions": sessions}

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_kpis(self) -> Dict[str, str]:
        return self._analytics.get_kpis()

    def get_daily_hours(self, days: Optional[int]) -> Dict[str, List[Any]]:
        return self._analytics.get_daily_hours(days=days)

    def get_weekly_hours(self, days: Optional[int]) -> Dict[str, List[Any]]:
        return self._analytics.get_weekly_hours(days=days)

    def get_project_hours(self, days: Optional[int], limit: Optional[int] = None) -> Dict[str, List[Any]]:
        return self._analytics.get_project_hours(days=days, limit=limit)

    def get_range_stats(self, days: Optional[int]) -> Dict[str, Any]:
        if days is None:
            return self._analytics.get_range_stats_all_time()
        return self._analytics.get_range_stats(days=days)

    def get_streak(self) -> Dict[str, int]:
        return self._analytics.get_streak()

    def get_heatmap(self, days: int = 365) -> List[Dict[str, Any]]:
        return self._analytics.get_heatmap_data(days=days)

    def get_week_glance(self) -> List[Dict[str, Any]]:
        return self._analytics.get_week_glance()

    def get_hours_by_time_of_day(self, days: Optional[int]) -> Dict[str, List[Any]]:
        return self._analytics.get_hours_by_time_of_day(days=days)

    def get_hours_by_weekday(self, days: Optional[int]) -> Dict[str, List[Any]]:
        return self._analytics.get_hours_by_weekday(days=days)

    def check_milestones(self) -> List[Dict[str, Any]]:
        return self._analytics.get_milestone_events()

    # ------------------------------------------------------------------
    # Goals
    # ------------------------------------------------------------------

    def get_goals(self) -> List[Dict[str, Any]]:
        return self._storage.get_goals()

    def upsert_goal(self, scope: str, period: str, target_hours: float, project_id: Optional[int]) -> Dict[str, Any]:
        target_sec = int(round(target_hours * 3600))
        goal_id = self._storage.upsert_goal(scope=scope, period=period, target_sec=target_sec, project_id=project_id)
        return {"success": True, "id": goal_id}

    def delete_goal(self, goal_id: int) -> Dict[str, Any]:
        self._storage.delete_goal(goal_id)
        return {"success": True}

    def get_goal_progress(self) -> List[Dict[str, Any]]:
        return self._analytics.get_goal_progress()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_settings(self) -> Dict[str, Any]:
        merged = dict(DEFAULT_SETTINGS)
        stored = self._storage.get_setting("app_settings", {})
        if isinstance(stored, dict):
            merged.update(stored)
        return merged

    def save_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_settings()
        current.update(settings or {})
        self._storage.save_setting("app_settings", current)
        return {"success": True, "settings": current}

    def get_quick_comments(self) -> List[str]:
        return self._storage.get_quick_comments()

    def save_quick_comments(self, comments: List[str]) -> Dict[str, Any]:
        self._storage.save_quick_comments(comments)
        return {"success": True}

    # ------------------------------------------------------------------
    # Data / backup / restore
    # ------------------------------------------------------------------

    def get_db_info(self) -> Dict[str, Any]:
        path = self._storage.db_path
        size = os.path.getsize(path) if os.path.exists(path) else 0
        sessions = self._storage.get_sessions(limit=None)
        projects = self._storage.get_projects()
        return {
            "path": path,
            "size_bytes": size,
            "session_count": len(sessions),
            "project_count": len(projects),
        }

    def backup_now(self) -> Dict[str, Any]:
        try:
            path = self._storage.backup_now()
            return {"success": True, "path": path}
        except IOError as e:
            return {"success": False, "error": str(e)}

    def list_backups(self) -> List[Dict[str, Any]]:
        return self._storage.list_backups()

    def restore_from_backup_picker(self) -> Dict[str, Any]:
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG, file_types=("SQLite Database (*.db)",)
        )
        if not result:
            return {"success": False, "error": None}
        path = result[0] if isinstance(result, (list, tuple)) else result
        try:
            self._storage.restore_from_backup(path)
            return {"success": True}
        except IOError as e:
            return {"success": False, "error": str(e)}

    def export_full_backup(self) -> Dict[str, Any]:
        """Exports a full JSON snapshot of all data via a save dialog."""
        import json

        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename="worktrack_export.json", file_types=("JSON Files (*.json)",)
        )
        if not result:
            return {"success": False, "error": None}
        path = result[0] if isinstance(result, (list, tuple)) else result
        try:
            bundle = self._storage.export_bundle()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(bundle, f, indent=2, default=str)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_data_folder(self) -> Dict[str, Any]:
        folder = os.path.dirname(os.path.abspath(self._storage.db_path))
        try:
            os.startfile(folder)  # noqa: S606 (Windows-only helper app)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Window controls
    # ------------------------------------------------------------------

    def minimize_to_tray(self):
        if self._window:
            self._window.hide()

    def restore_window(self):
        if self._window:
            self._window.show()
            self._window.restore()

    def set_compact_mode(self, enabled: bool):
        if not self._window:
            return
        if enabled:
            self._window.on_top = True
            self._window.resize(300, 150)
        else:
            self._window.on_top = False
            self._window.resize(1080, 760)

    def quit_app(self):
        if self._window:
            self._window.destroy()
