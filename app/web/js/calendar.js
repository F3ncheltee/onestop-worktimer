(function () {
  const NO_PROJECT_COLOR = "#6b7280";
  let viewYear, viewMonth; // viewMonth is 0-indexed
  let selectedDate = null;
  let monthData = { daily_totals: {}, sessions: [] };

  function el(id) { return document.getElementById(id); }
  function pad(n) { return String(n).padStart(2, "0"); }
  function dateStr(y, m, d) { return `${y}-${pad(m + 1)}-${pad(d)}`; }
  function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function fmtHours(sec) {
    if (!sec) return "";
    const h = sec / 3600;
    return h >= 1 ? `${h.toFixed(1)}h` : `${Math.round(sec / 60)}m`;
  }

  /** Group sessions on a date by project, sorted by hours (desc). */
  function aggregateDayProjects(dateStr) {
    const sessions = (monthData.sessions || []).filter((s) => s.date === dateStr && (s.duration_sec || 0) > 0);
    const map = new Map();
    for (const s of sessions) {
      const key = s.project_id != null ? String(s.project_id) : "none";
      const color = s.project_color || NO_PROJECT_COLOR;
      const name = s.project_name || "No project";
      const prev = map.get(key) || { sec: 0, color, name };
      prev.sec += s.duration_sec || 0;
      map.set(key, prev);
    }
    return [...map.values()].sort((a, b) => b.sec - a.sec);
  }

  function isHeavyDay(totalSec) {
    return totalSec / 3600 >= 4;
  }

  function buildBandsHtml(projects) {
    const total = projects.reduce((sum, p) => sum + p.sec, 0);
    if (!total) return "";
    return `<div class="cal-cell-bands">${projects.map((p) =>
      `<span style="flex:${p.sec};background:${p.color}" title="${escapeHtml(p.name)}: ${fmtHours(p.sec)}"></span>`
    ).join("")}</div>`;
  }

  function buildTooltip(projects, totalSec) {
    if (!projects.length) return "";
    return projects.map((p) => `${p.name}: ${fmtHours(p.sec)}`).join(" · ") + ` (${fmtHours(totalSec)} total)`;
  }

  function renderMonthLegend() {
    const legend = el("cal-legend");
    const monthSessions = monthData.sessions || [];
    const byProject = new Map();
    for (const s of monthSessions) {
      if (!s.duration_sec) continue;
      const key = s.project_id != null ? String(s.project_id) : "none";
      const color = s.project_color || NO_PROJECT_COLOR;
      const name = s.project_name || "No project";
      const prev = byProject.get(key) || { sec: 0, color, name };
      prev.sec += s.duration_sec;
      byProject.set(key, prev);
    }
    const items = [...byProject.values()].sort((a, b) => b.sec - a.sec);
    if (!items.length) {
      legend.innerHTML = `<span class="empty-hint" style="margin:0">No logged time this month.</span>`;
      return;
    }
    legend.innerHTML = items.map((p) => `
      <span class="cal-legend-item">
        <span class="cal-legend-swatch" style="background:${p.color}"></span>
        ${escapeHtml(p.name)} <span class="text-muted">${fmtHours(p.sec)}</span>
      </span>`).join("");
  }

  async function loadMonth() {
    const first = new Date(viewYear, viewMonth, 1);
    const last = new Date(viewYear, viewMonth + 1, 0);
    const from = dateStr(first.getFullYear(), first.getMonth(), first.getDate());
    const to = dateStr(last.getFullYear(), last.getMonth(), last.getDate());
    monthData = await WT.api.get_month_data(from, to);
    render();
  }

  function render() {
    el("cal-month-label").textContent = new Date(viewYear, viewMonth, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });

    const first = new Date(viewYear, viewMonth, 1);
    const startOffset = (first.getDay() + 6) % 7; // Monday-first
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const todayStr = dateStr(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());

    let html = "";
    for (let i = 0; i < startOffset; i++) html += `<div class="cal-cell empty"></div>`;
    for (let d = 1; d <= daysInMonth; d++) {
      const ds = dateStr(viewYear, viewMonth, d);
      const sec = monthData.daily_totals[ds] || 0;
      const projects = aggregateDayProjects(ds);
      const isToday = ds === todayStr;
      const isSelected = ds === selectedDate;
      const hasWork = sec > 0 && projects.length > 0;
      const tint = hasWork ? projects[0].color : "";
      const classes = [
        "cal-cell",
        hasWork ? "has-work" : "",
        hasWork && isHeavyDay(sec) ? "cal-heavy" : "",
        isToday ? "today" : "",
        isSelected ? "selected" : "",
      ].filter(Boolean).join(" ");
      const style = tint ? ` style="--cal-tint:${tint}"` : "";
      const title = hasWork ? ` title="${escapeHtml(buildTooltip(projects, sec))}"` : "";
      html += `
        <button class="${classes}" data-date="${ds}"${style}${title}>
          ${hasWork ? buildBandsHtml(projects) : ""}
          <span class="cal-cell-day">${d}</span>
          ${sec ? `<span class="cal-cell-hours">${fmtHours(sec)}</span>` : ""}
        </button>`;
    }
    el("calendar-grid").innerHTML = html;
    el("calendar-grid").querySelectorAll(".cal-cell[data-date]").forEach((c) => {
      c.addEventListener("click", () => selectDate(c.dataset.date));
    });
    renderMonthLegend();

    if (!selectedDate) selectDate(todayStr >= dateStr(viewYear, viewMonth, 1) && todayStr <= dateStr(viewYear, viewMonth, daysInMonth) ? todayStr : dateStr(viewYear, viewMonth, 1));
    else renderDayPanel();
  }

  function selectDate(ds) {
    selectedDate = ds;
    document.querySelectorAll(".cal-cell").forEach((c) => c.classList.toggle("selected", c.dataset.date === ds));
    renderDayPanel();
  }

  function renderDayPanel() {
    const d = new Date(selectedDate + "T00:00:00");
    const totalSec = monthData.daily_totals[selectedDate] || 0;
    const projects = aggregateDayProjects(selectedDate);
    const titleBase = d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
    el("day-panel-title").innerHTML = totalSec
      ? `${titleBase} <span class="day-panel-total">${fmtHours(totalSec)}</span>`
      : titleBase;

    const sessions = (monthData.sessions || []).filter((s) => s.date === selectedDate);
    const container = el("day-sessions");
    if (!sessions.length) {
      container.innerHTML = `<div class="empty-hint">No entries for this date.</div>`;
      return;
    }

    const breakdown = projects.length
      ? `<div class="day-project-breakdown">${projects.map((p) =>
          `<span class="chip chip-ghost chip-proj" style="--proj-color:${p.color}"><span class="proj-dot" style="background:${p.color}"></span>${escapeHtml(p.name)} ${fmtHours(p.sec)}</span>`
        ).join("")}</div>`
      : "";

    container.innerHTML = breakdown + sessions.map((s) => `
      <div class="day-session-row" style="--proj-color:${s.project_color || NO_PROJECT_COLOR}">
        <div class="session-row-color"></div>
        <div class="session-row-main">
          <div class="session-row-top"><span class="session-project">${escapeHtml(s.project_name || "No project")}</span></div>
          ${s.comment ? `<div class="session-comment">${escapeHtml(s.comment)}</div>` : ""}
        </div>
        <div class="session-row-duration">${s.duration_sec ? Math.round(s.duration_sec / 60) + "m" : "-"}</div>
        <div class="session-row-actions">
          <button class="btn-icon" data-edit-id="${s.id}">${WT.icons.iconHTML("edit-2")}</button>
        </div>
      </div>`).join("");
    container.querySelectorAll("[data-edit-id]").forEach((btn) => btn.addEventListener("click", async () => {
      await WT.viewSessions.refresh();
      WT.viewSessions.openEditor(parseInt(btn.dataset.editId, 10));
    }));
  }

  function shiftMonth(delta) {
    viewMonth += delta;
    if (viewMonth < 0) { viewMonth = 11; viewYear--; }
    if (viewMonth > 11) { viewMonth = 0; viewYear++; }
    loadMonth();
  }

  function goToToday() {
    const now = new Date();
    viewYear = now.getFullYear();
    viewMonth = now.getMonth();
    selectedDate = dateStr(now.getFullYear(), now.getMonth(), now.getDate());
    loadMonth();
  }

  function goToDate(ds) {
    const d = new Date(ds + "T00:00:00");
    viewYear = d.getFullYear();
    viewMonth = d.getMonth();
    selectedDate = ds;
    loadMonth();
  }

  function init() {
    const now = new Date();
    viewYear = now.getFullYear();
    viewMonth = now.getMonth();
    el("btn-cal-prev").addEventListener("click", () => shiftMonth(-1));
    el("btn-cal-next").addEventListener("click", () => shiftMonth(1));
    el("btn-cal-today").addEventListener("click", goToToday);
    el("btn-day-add").addEventListener("click", async () => {
      await WT.viewSessions.refresh();
      WT.viewSessions.openEditor(null, selectedDate);
    });
    loadMonth();
  }

  window.WT = window.WT || {};
  window.WT.viewCalendar = { init, refresh: loadMonth, goToDate };
})();
