from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Tuple, Optional, Literal
import statistics
from app.core.storage import Storage

STREAK_MILESTONES = [3, 7, 14, 30, 60, 100, 200, 365]
TOTAL_HOURS_MILESTONES = [10, 25, 50, 100, 250, 500, 1000, 2000]
SESSION_COUNT_MILESTONES = [10, 25, 50, 100, 250, 500, 1000]
WEEKLY_HOURS_MILESTONES = [5, 10, 20, 30, 40, 50]


class Analytics:
    def __init__(self, storage: Storage):
        self.storage = storage

    def _range_start_end(self, days: int) -> Tuple[str, str]:
        """
        Returns (date_from, date_to) inclusive strings for the given number of days.
        Example: days=14 => includes today + previous 13 days.
        """
        if days <= 0:
            days = 1
        end_d: date = datetime.now().date()
        start_d: date = end_d - timedelta(days=days - 1)
        return start_d.strftime("%Y-%m-%d"), end_d.strftime("%Y-%m-%d")

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

    def _get_all_time_bounds(self) -> Tuple[Optional[str], Optional[str]]:
        """Returns (min_date, max_date) from sessions with recorded duration."""
        conn = self.storage._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT MIN(date), MAX(date)
            FROM sessions
            WHERE duration_sec IS NOT NULL AND duration_sec > 0
            """
        )
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0] or not row[1]:
            return None, None
        return str(row[0]), str(row[1])

    def _fetch_daily_totals(
        self, date_from: str, date_to: str
    ) -> Dict[str, float]:
        """Returns dict date_str -> total_hours (float)."""
        conn = self.storage._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT date, SUM(duration_sec)
            FROM sessions
            WHERE date >= ? AND date <= ?
              AND duration_sec IS NOT NULL AND duration_sec > 0
            GROUP BY date
            ORDER BY date
            """,
            (date_from, date_to),
        )
        rows = cursor.fetchall()
        conn.close()
        return {r[0]: (r[1] or 0) / 3600.0 for r in rows}

    def get_daily_hours(self, days: Optional[int] = 14, fill_gaps: bool = True) -> Dict[str, List[Any]]:
        """Returns data for bar chart: dates and hours.

        If `days` is None, returns daily totals between first and last logged day (no gap filling by default).
        """
        conn = self.storage._get_connection()
        cursor = conn.cursor()  # kept for compatibility, but we don't use it below
        conn.close()

        if days is None:
            date_from, date_to = self._get_all_time_bounds()
            if not date_from or not date_to:
                return {"dates": [], "hours": []}
        else:
            date_from, date_to = self._range_start_end(days)

        start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        end_date = datetime.strptime(date_to, "%Y-%m-%d").date()

        totals = self._fetch_daily_totals(date_from, date_to)

        dates = []
        hours = []

        if fill_gaps:
            current = start_date
            while current <= end_date:
                d_str = current.strftime("%Y-%m-%d")
                dates.append(current.strftime("%m-%d"))  # short format
                hours.append(round(totals.get(d_str, 0.0), 2))
                current += timedelta(days=1)
        else:
            # Only plot days that actually have data (readable for large ranges)
            current_dates = sorted(totals.keys())
            for d_str in current_dates:
                d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                dates.append(d_obj.strftime("%m-%d"))
                hours.append(round(totals[d_str], 2))

        return {"dates": dates, "hours": hours}

    def _aggregate_daily_to_weekly(
        self, date_from: str, date_to: str, daily_hours: Dict[str, float]
    ) -> Dict[str, List[Any]]:
        """Aggregates daily hours into week buckets (week starts on Monday)."""
        start_d = datetime.strptime(date_from, "%Y-%m-%d").date()
        end_d = datetime.strptime(date_to, "%Y-%m-%d").date()

        # Build week buckets
        # Align start to the Monday of its week
        week_start = start_d - timedelta(days=start_d.weekday())
        week_starts: List[date] = []
        current = week_start
        while current <= end_d:
            week_starts.append(current)
            current += timedelta(days=7)

        buckets: Dict[str, float] = {}
        for ws in week_starts:
            we = ws + timedelta(days=6)
            total = 0.0
            current_day = ws
            while current_day <= we:
                if start_d <= current_day <= end_d:
                    ds = current_day.strftime("%Y-%m-%d")
                    total += daily_hours.get(ds, 0.0)
                current_day += timedelta(days=1)
            key = ws.strftime("%m-%d")
            buckets[key] = total

        # Order by actual week start, not by dict insertion order
        ordered_keys = [ws.strftime("%m-%d") for ws in week_starts]
        return {
            "dates": ordered_keys,
            "hours": [round(buckets[k], 2) for k in ordered_keys],
        }

    def get_weekly_hours(self, days: Optional[int] = 14) -> Dict[str, List[Any]]:
        """Returns weekly hours grouped by Monday-based weeks."""
        if days is None:
            date_from, date_to = self._get_all_time_bounds()
            if not date_from or not date_to:
                return {"dates": [], "hours": []}
        else:
            date_from, date_to = self._range_start_end(days)

        totals = self._fetch_daily_totals(date_from, date_to)
        return self._aggregate_daily_to_weekly(date_from, date_to, totals)

    def get_project_hours(self, days: Optional[int] = 30, limit: Optional[int] = None) -> Dict[str, List[Any]]:
        """Returns data for project breakdown: names, hours, and colors."""
        conn = self.storage._get_connection()
        cursor = conn.cursor()

        if days is None:
            date_from, date_to = self._get_all_time_bounds()
            if not date_from or not date_to:
                conn.close()
                return {"names": [], "hours": [], "colors": []}
        else:
            date_from, date_to = self._range_start_end(days)
        
        cursor.execute('''
            SELECT p.name, p.color, SUM(s.duration_sec) 
            FROM sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE s.date >= ? AND s.date <= ?
              AND s.duration_sec IS NOT NULL AND s.duration_sec > 0
            GROUP BY s.project_id
            ORDER BY SUM(s.duration_sec) DESC
        ''', (date_from, date_to))
        
        rows = cursor.fetchall()
        if limit is not None:
            rows = rows[:limit]
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

    def get_range_stats(self, days: int) -> Dict[str, Any]:
        """
        Returns a simple summary for the selected time range:
        total hours, session count, avg/median session length, and mean daily hours.
        """
        date_from, date_to = self._range_start_end(days)

        conn = self.storage._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT
              COALESCE(SUM(duration_sec), 0),
              COUNT(*)
            FROM sessions
            WHERE date >= ? AND date <= ?
              AND duration_sec IS NOT NULL AND duration_sec > 0
            ''',
            (date_from, date_to),
        )
        total_sec, session_count = cursor.fetchone()

        # Daily totals include gaps => good for mean/median daily
        daily = self.get_daily_hours(days=days)
        conn.close()

        total_hours = total_sec / 3600.0 if total_sec else 0.0
        avg_session_hours = (total_hours / session_count) if session_count else 0.0

        # Per-day: already normalized by the selected number of days (includes zero days).
        mean_daily_hours = (total_hours / days) if days else 0.0

        # Per-week: normalized to 7-day weeks (so "mean per week" is comparable across ranges).
        mean_weekly_hours = (total_hours / (days / 7.0)) if days else 0.0

        # Per-month: normalized to calendar months spanned by the range (partial months count as 1).
        start_d = datetime.strptime(date_from, "%Y-%m-%d").date()
        end_d = datetime.strptime(date_to, "%Y-%m-%d").date()
        months_count = (end_d.year - start_d.year) * 12 + (end_d.month - start_d.month) + 1
        mean_monthly_hours = (total_hours / months_count) if months_count else 0.0

        # Median daily hours is computed over the (filled) per-day series.
        median_daily_hours = statistics.median(daily["hours"]) if daily["hours"] else 0.0

        return {
            "total_hours": round(total_hours, 2),
            "session_count": int(session_count or 0),
            "avg_session_hours": round(avg_session_hours, 2),
            "mean_daily_hours": round(mean_daily_hours, 2),
            "mean_weekly_hours": round(mean_weekly_hours, 2),
            "mean_monthly_hours": round(mean_monthly_hours, 2),
            "median_daily_hours": round(median_daily_hours, 2),
        }

    def get_range_stats_all_time(self) -> Dict[str, Any]:
        """Range summary for all time (uses first/last logged day bounds)."""
        date_from, date_to = self._get_all_time_bounds()
        if not date_from or not date_to:
            return {
                "total_hours": 0.0,
                "session_count": 0,
                "avg_session_hours": 0.0,
                "mean_daily_hours": 0.0,
                "mean_weekly_hours": 0.0,
                "mean_monthly_hours": 0.0,
                "median_daily_hours": 0.0,
            }

        start_d = datetime.strptime(date_from, "%Y-%m-%d").date()
        end_d = datetime.strptime(date_to, "%Y-%m-%d").date()
        days = (end_d - start_d).days + 1

        # Compute totals + count
        conn = self.storage._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
              COALESCE(SUM(duration_sec), 0),
              COUNT(*)
            FROM sessions
            WHERE date >= ? AND date <= ?
              AND duration_sec IS NOT NULL AND duration_sec > 0
            """,
            (date_from, date_to),
        )
        total_sec, session_count = cursor.fetchone()

        # For median, use the daily series without gap filling (readable + fast for big ranges).
        daily = self.get_daily_hours(days=None, fill_gaps=False)
        conn.close()

        total_hours = total_sec / 3600.0 if total_sec else 0.0
        avg_session_hours = (total_hours / session_count) if session_count else 0.0
        mean_daily_hours = (total_hours / days) if days else 0.0
        mean_weekly_hours = (total_hours / (days / 7.0)) if days else 0.0

        months_count = (end_d.year - start_d.year) * 12 + (end_d.month - start_d.month) + 1
        mean_monthly_hours = (total_hours / months_count) if months_count else 0.0

        median_daily_hours = statistics.median(daily["hours"]) if daily["hours"] else 0.0

        return {
            "total_hours": round(total_hours, 2),
            "session_count": int(session_count or 0),
            "avg_session_hours": round(avg_session_hours, 2),
            "mean_daily_hours": round(mean_daily_hours, 2),
            "mean_weekly_hours": round(mean_weekly_hours, 2),
            "mean_monthly_hours": round(mean_monthly_hours, 2),
            "median_daily_hours": round(median_daily_hours, 2),
        }

    def _format_hours(self, seconds: int) -> str:
        hours = round(seconds / 3600, 1)
        return f"{hours} h"

    # ------------------------------------------------------------------
    # Streaks, heatmap, goals
    # ------------------------------------------------------------------

    def get_streak(self) -> Dict[str, int]:
        """
        Returns the current consecutive-days-worked streak and the longest
        streak ever recorded. A day "counts" if it has any logged duration.
        """
        conn = self.storage._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT date FROM sessions
            WHERE duration_sec IS NOT NULL AND duration_sec > 0
            ORDER BY date DESC
            """
        )
        worked_dates = {row[0] for row in cursor.fetchall()}
        conn.close()

        if not worked_dates:
            return {"current_streak": 0, "longest_streak": 0}

        today = datetime.now().date()

        # Current streak: walk backwards from today (or yesterday, so an
        # unfinished "today" doesn't reset the streak before the day ends).
        current_streak = 0
        cursor_date = today
        if today.strftime("%Y-%m-%d") not in worked_dates:
            cursor_date = today - timedelta(days=1)
        while cursor_date.strftime("%Y-%m-%d") in worked_dates:
            current_streak += 1
            cursor_date -= timedelta(days=1)

        # Longest streak ever, computed from the sorted set of worked dates.
        sorted_dates = sorted(datetime.strptime(d, "%Y-%m-%d").date() for d in worked_dates)
        longest_streak = 1
        run = 1
        for prev, cur in zip(sorted_dates, sorted_dates[1:]):
            if (cur - prev).days == 1:
                run += 1
            else:
                run = 1
            longest_streak = max(longest_streak, run)

        return {"current_streak": current_streak, "longest_streak": longest_streak}

    def get_heatmap_data(self, days: int = 365) -> List[Dict[str, Any]]:
        """Returns {date, hours} rows for the activity heatmap."""
        date_from, date_to = self._range_start_end(days)
        totals = self._fetch_daily_totals(date_from, date_to)

        start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        end_date = datetime.strptime(date_to, "%Y-%m-%d").date()

        result = []
        current = start_date
        while current <= end_date:
            d_str = current.strftime("%Y-%m-%d")
            result.append({"date": d_str, "hours": round(totals.get(d_str, 0.0), 2)})
            current += timedelta(days=1)
        return result

    def get_week_glance(self) -> List[Dict[str, Any]]:
        """
        Mon–Sun of the current calendar week with per-project hours for each day.
        Used by the dashboard week-at-a-glance strip.
        """
        now = datetime.now()
        week_start = now.date() - timedelta(days=now.weekday())
        today_str = now.strftime("%Y-%m-%d")

        conn = self.storage._get_connection()
        cursor = conn.cursor()
        date_from = week_start.strftime("%Y-%m-%d")
        date_to = (week_start + timedelta(days=6)).strftime("%Y-%m-%d")
        cursor.execute(
            """
            SELECT s.date, s.duration_sec, p.name, p.color, s.project_id
            FROM sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE s.date >= ? AND s.date <= ?
              AND s.duration_sec IS NOT NULL AND s.duration_sec > 0
            ORDER BY s.date
            """,
            (date_from, date_to),
        )
        rows = cursor.fetchall()
        conn.close()

        by_date: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            d_str, sec, name, color, pid = row
            if d_str not in by_date:
                by_date[d_str] = {"total_sec": 0, "projects": {}}
            by_date[d_str]["total_sec"] += sec or 0
            key = str(pid) if pid is not None else "none"
            proj = by_date[d_str]["projects"].get(key) or {
                "name": name or "No project",
                "color": color or "#6b7280",
                "sec": 0,
            }
            proj["sec"] += sec or 0
            by_date[d_str]["projects"][key] = proj

        weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        result = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            d_str = d.strftime("%Y-%m-%d")
            day = by_date.get(d_str, {"total_sec": 0, "projects": {}})
            projects = sorted(day["projects"].values(), key=lambda p: p["sec"], reverse=True)
            result.append({
                "date": d_str,
                "label": weekday_labels[i],
                "is_today": d_str == today_str,
                "total_sec": int(day["total_sec"]),
                "projects": [
                    {"name": p["name"], "color": p["color"], "sec": int(p["sec"])}
                    for p in projects
                ],
            })
        return result

    def get_hours_by_time_of_day(self, days: Optional[int] = 30) -> Dict[str, List[Any]]:
        """
        Hours logged bucketed by session start hour (0–23).
        Simple and intuitive: 'when do I usually start working?'
        """
        if days is None:
            date_from, date_to = self._get_all_time_bounds()
            if not date_from or not date_to:
                return {"labels": [], "hours": []}
        else:
            date_from, date_to = self._range_start_end(days)

        conn = self.storage._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT start_ts, duration_sec
            FROM sessions
            WHERE date >= ? AND date <= ?
              AND duration_sec IS NOT NULL AND duration_sec > 0
              AND start_ts IS NOT NULL
            """,
            (date_from, date_to),
        )
        rows = cursor.fetchall()
        conn.close()

        buckets = [0.0] * 24
        for start_ts, duration_sec in rows:
            try:
                hour = datetime.fromisoformat(str(start_ts)).hour
            except (ValueError, TypeError):
                continue
            buckets[hour] += (duration_sec or 0) / 3600.0

        labels = []
        for h in range(24):
            if h == 0:
                labels.append("12a")
            elif h < 12:
                labels.append(f"{h}a")
            elif h == 12:
                labels.append("12p")
            else:
                labels.append(f"{h - 12}p")

        return {"labels": labels, "hours": [round(v, 2) for v in buckets]}

    def get_hours_by_weekday(self, days: Optional[int] = 30) -> Dict[str, List[Any]]:
        """Total hours logged per weekday (Mon–Sun) in the selected range."""
        if days is None:
            date_from, date_to = self._get_all_time_bounds()
            if not date_from or not date_to:
                return {"labels": [], "hours": []}
        else:
            date_from, date_to = self._range_start_end(days)

        conn = self.storage._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT date, duration_sec
            FROM sessions
            WHERE date >= ? AND date <= ?
              AND duration_sec IS NOT NULL AND duration_sec > 0
            """,
            (date_from, date_to),
        )
        rows = cursor.fetchall()
        conn.close()

        buckets = [0.0] * 7
        weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for d_str, duration_sec in rows:
            try:
                wd = datetime.strptime(d_str, "%Y-%m-%d").weekday()
            except ValueError:
                continue
            buckets[wd] += (duration_sec or 0) / 3600.0

        return {"labels": weekday_labels, "hours": [round(v, 2) for v in buckets]}

    def get_goal_progress(self) -> List[Dict[str, Any]]:
        """Combines stored goals with actual hours logged for the current day/week."""
        goals = self.storage.get_goals()
        if not goals:
            return []

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        start_of_week_str = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")

        conn = self.storage._get_connection()
        cursor = conn.cursor()

        progress = []
        for goal in goals:
            period = goal["period"]
            date_from = today_str if period == "daily" else start_of_week_str

            if goal["scope"] == "project" and goal.get("project_id"):
                cursor.execute(
                    "SELECT COALESCE(SUM(duration_sec), 0) FROM sessions WHERE date >= ? AND project_id = ?",
                    (date_from, goal["project_id"]),
                )
            else:
                cursor.execute(
                    "SELECT COALESCE(SUM(duration_sec), 0) FROM sessions WHERE date >= ?",
                    (date_from,),
                )
            actual_sec = cursor.fetchone()[0] or 0

            target_sec = goal["target_sec"] or 1
            progress.append({
                **goal,
                "actual_sec": int(actual_sec),
                "pct": min(100, round((actual_sec / target_sec) * 100)),
            })

        conn.close()
        return progress

    def get_milestone_events(self) -> List[Dict[str, Any]]:
        """
        Checks a handful of achievement thresholds (streaks, all-time hours,
        session count, weekly hours). Any threshold reached for the first time
        Any threshold reached for the first time is marked as seen and returned once.
        """
        events: List[Dict[str, Any]] = []

        streak = self.get_streak()
        for m in STREAK_MILESTONES:
            if streak["current_streak"] >= m:
                key = f"streak_{m}"
                if not self.storage.has_milestone_seen(key):
                    self.storage.mark_milestone_seen(key)
                    events.append({
                        "type": "streak",
                        "value": m,
                        "title": f"{m}-day streak!",
                        "message": f"{m} consecutive days with logged work.",
                    })

        conn = self.storage._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(duration_sec), 0), COUNT(*) FROM sessions "
            "WHERE duration_sec IS NOT NULL AND duration_sec > 0"
        )
        total_sec, session_count = cursor.fetchone()
        conn.close()

        total_hours = (total_sec or 0) / 3600.0
        for m in TOTAL_HOURS_MILESTONES:
            if total_hours >= m:
                key = f"total_hours_{m}"
                if not self.storage.has_milestone_seen(key):
                    self.storage.mark_milestone_seen(key)
                    events.append({
                        "type": "total_hours",
                        "value": m,
                        "title": f"{m}h logged all-time!",
                        "message": f"{m} hours logged in total.",
                    })

        for m in SESSION_COUNT_MILESTONES:
            if (session_count or 0) >= m:
                key = f"session_count_{m}"
                if not self.storage.has_milestone_seen(key):
                    self.storage.mark_milestone_seen(key)
                    events.append({
                        "type": "session_count",
                        "value": m,
                        "title": f"{m} sessions logged!",
                        "message": f"{m} sessions logged in total.",
                    })

        now = datetime.now()
        start_of_week_str = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        this_week_key = f"week_{start_of_week_str}"
        conn = self.storage._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(duration_sec), 0) FROM sessions WHERE date >= ?",
            (start_of_week_str,),
        )
        week_sec = cursor.fetchone()[0] or 0
        conn.close()
        week_hours = week_sec / 3600.0
        for m in WEEKLY_HOURS_MILESTONES:
            if week_hours >= m:
                key = f"{this_week_key}_hours_{m}"
                if not self.storage.has_milestone_seen(key):
                    self.storage.mark_milestone_seen(key)
                    events.append({
                        "type": "weekly_hours",
                        "value": m,
                        "title": f"{m}h this week!",
                        "message": f"{m} hours logged this week.",
                    })

        return events
