from datetime import datetime, timedelta
from typing import Optional
from .storage import Storage

class Timer:
    def __init__(self, storage: Storage):
        self.storage = storage
        self.current_session_id: Optional[int] = None
        self.start_time: Optional[datetime] = None
        self.mode: str = 'countup'
        self.target_duration: Optional[timedelta] = None
        
        # Check for active session on startup
        self._recover_session()

    def _recover_session(self):
        active = self.storage.get_active_session()
        if active:
            self.current_session_id = active['id']
            self.start_time = datetime.fromisoformat(active['start_ts'])
            self.mode = active['mode']
            if active['target_sec']:
                self.target_duration = timedelta(seconds=active['target_sec'])

    def start(self, mode: str = 'countup', target_duration: Optional[timedelta] = None, comment: str = "", project_id: Optional[int] = None):
        if self.current_session_id is not None:
            raise RuntimeError("Session already running")

        now = datetime.now()
        self.start_time = now
        self.mode = mode
        self.target_duration = target_duration
        
        target_sec = int(target_duration.total_seconds()) if target_duration else None
        
        self.current_session_id = self.storage.create_session(
            start_ts=now.isoformat(),
            date=now.strftime("%Y-%m-%d"),
            mode=mode,
            target_sec=target_sec,
            comment=comment,
            project_id=project_id
        )

    def stop(self, comment: Optional[str] = None):
        if self.current_session_id is None:
            return

        now = datetime.now()
        start = self.start_time
        duration = now - start
        duration_sec = int(duration.total_seconds())

        # For countdown, check if completed
        completed = None
        if self.mode == 'countdown' and self.target_duration:
            if duration >= self.target_duration:
                completed = 1
            else:
                completed = 0

        self.storage.update_session(
            session_id=self.current_session_id,
            end_ts=now.isoformat(),
            duration_sec=duration_sec,
            completed=completed,
            comment=comment
        )
        
        self.current_session_id = None
        self.start_time = None
        self.target_duration = None

    def get_elapsed(self) -> timedelta:
        if self.start_time is None:
            return timedelta(0)
        return datetime.now() - self.start_time

    def get_remaining(self) -> Optional[timedelta]:
        if self.mode != 'countdown' or not self.target_duration:
            return None
        
        elapsed = self.get_elapsed()
        remaining = self.target_duration - elapsed
        return remaining

    def is_running(self) -> bool:
        return self.current_session_id is not None
