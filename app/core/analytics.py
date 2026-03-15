from datetime import datetime, timedelta
from typing import Dict, List, Any
from app.core.storage import Storage

class Analytics:
    def __init__(self, storage: Storage):
        self.storage = storage

    def get_kpis(self) -> Dict[str, str]:
        """Returns string formatted KPIs."""
        conn = self.storage._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        # Today
        cursor.execute("SELECT SUM(duration_sec) FROM sessions WHERE date = ?", (today_str,))
        today_sec = cursor.fetchone()[0] or 0
        
        # This Week (Start from Monday)
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week_str = start_of_week.strftime("%Y-%m-%d")
        cursor.execute("SELECT SUM(duration_sec) FROM sessions WHERE date >= ?", (start_of_week_str,))
        week_sec = cursor.fetchone()[0] or 0
        
        # This Month
        start_of_month_str = now.strftime("%Y-%m-01")
        cursor.execute("SELECT SUM(duration_sec) FROM sessions WHERE date >= ?", (start_of_month_str,))
        month_sec = cursor.fetchone()[0] or 0
        
        # All Time
        cursor.execute("SELECT SUM(duration_sec) FROM sessions")
        all_time_sec = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "today": self._format_hours(today_sec),
            "week": self._format_hours(week_sec),
            "month": self._format_hours(month_sec),
            "all_time": self._format_hours(all_time_sec)
        }

    def get_daily_hours(self, days: int = 14) -> Dict[str, List[Any]]:
        """Returns data for bar chart: dates and hours."""
        conn = self.storage._get_connection()
        cursor = conn.cursor()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days-1)
        start_str = start_date.strftime("%Y-%m-%d")
        
        cursor.execute('''
            SELECT date, SUM(duration_sec) 
            FROM sessions 
            WHERE date >= ? 
            GROUP BY date 
            ORDER BY date
        ''', (start_str,))
        
        rows = dict(cursor.fetchall())
        conn.close()
        
        # Fill gaps
        dates = []
        hours = []
        
        current = start_date
        while current <= end_date:
            d_str = current.strftime("%Y-%m-%d")
            dates.append(current.strftime("%m-%d")) # Short format for axis
            
            sec = rows.get(d_str, 0)
            hours.append(round(sec / 3600, 2))
            
            current += timedelta(days=1)
            
        return {"dates": dates, "hours": hours}

    def get_project_hours(self, days: int = 30) -> Dict[str, List[Any]]:
        """Returns data for project breakdown: names, hours, and colors."""
        conn = self.storage._get_connection()
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days)
        start_str = start_date.strftime("%Y-%m-%d")
        
        cursor.execute('''
            SELECT p.name, p.color, SUM(s.duration_sec) 
            FROM sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE s.date >= ? 
            GROUP BY s.project_id 
            ORDER BY SUM(s.duration_sec) DESC
        ''', (start_str,))
        
        rows = cursor.fetchall()
        conn.close()
        
        names = []
        hours = []
        colors = []
        
        for row in rows:
            name = row[0] or "No Project"
            color = row[1] or "#bdc3c7"
            sec = row[2] or 0
            
            names.append(name)
            colors.append(color)
            hours.append(round(sec / 3600, 2))
            
        return {"names": names, "hours": hours, "colors": colors}

    def _format_hours(self, seconds: int) -> str:
        hours = round(seconds / 3600, 1)
        return f"{hours} h"
