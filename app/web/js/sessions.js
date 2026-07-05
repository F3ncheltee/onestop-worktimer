(function () {
  let currentSessions = [];

  function el(id) { return document.getElementById(id); }
  function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function fmtDuration(sec) {
    if (sec == null) return "-";
    const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  function fmtTime(iso) {
    if (!iso) return "-";
    try { return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); } catch { return iso; }
  }
  function fmtDateLabel(dateStr) {
    const d = new Date(dateStr + "T00:00:00");
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const diffDays = Math.round((today - d) / 86400000);
    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    return d.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
  }

  function defaultFilters() {
    const to = new Date();
    const from = new Date(); from.setDate(from.getDate() - 30);
    return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) };
  }

  async function loadData() {
    const dateFrom = el("filter-date-from").value || null;
    const dateTo = el("filter-date-to").value || null;
    const search = el("filter-search").value || null;
    currentSessions = await WT.api.get_sessions(dateFrom, dateTo, search, null);
    render();
  }

  function render() {
    const list = el("sessions-list");
    if (!currentSessions.length) {
      list.innerHTML = `<div class="empty-state">${WT.icons.iconHTML("list")}<div>No sessions match these filters.</div></div>`;
      return;
    }
    const groups = {};
    currentSessions.forEach((s) => { (groups[s.date] = groups[s.date] || []).push(s); });
    const dates = Object.keys(groups).sort((a, b) => (a < b ? 1 : -1));

    list.innerHTML = dates.map((date) => {
      const daySessions = groups[date];
      const dayTotal = daySessions.reduce((sum, s) => sum + (s.duration_sec || 0), 0);
      return `
        <div class="session-day-group">
          <div class="session-day-heading">
            <span>${fmtDateLabel(date)}</span>
            <span class="session-day-total">${fmtDuration(dayTotal)}</span>
          </div>
          ${daySessions.map((s) => sessionRowHtml(s)).join("")}
        </div>`;
    }).join("");

    list.querySelectorAll("[data-edit-id]").forEach((btn) => btn.addEventListener("click", () => openEditor(parseInt(btn.dataset.editId, 10))));
    list.querySelectorAll("[data-del-id]").forEach((btn) => btn.addEventListener("click", () => confirmDelete(parseInt(btn.dataset.delId, 10))));
  }

  function sessionRowHtml(s) {
    const color = s.project_color || "#6b7280";
    const running = !s.end_ts;
    return `
      <div class="session-row" style="--proj-color:${color}">
        <div class="session-row-color"></div>
        <div class="session-row-main">
          <div class="session-row-top">
            <span class="session-project">${escapeHtml(s.project_name || "No project")}</span>
            ${running ? '<span class="badge-running">RUNNING</span>' : ""}
          </div>
          ${s.comment ? `<div class="session-comment">${escapeHtml(s.comment)}</div>` : ""}
          <div class="session-row-meta">${fmtTime(s.start_ts)} - ${running ? "now" : fmtTime(s.end_ts)}</div>
        </div>
        <div class="session-row-duration">${fmtDuration(s.duration_sec)}</div>
        <div class="session-row-actions">
          <button class="btn-icon" data-edit-id="${s.id}">${WT.icons.iconHTML("edit-2")}</button>
          <button class="btn-icon danger" data-del-id="${s.id}">${WT.icons.iconHTML("trash-2")}</button>
        </div>
      </div>`;
  }

  function confirmDelete(id) {
    WT.modal.open(`
      <div class="modal-header"><h2>Delete session?</h2></div>
      <div class="modal-body"><p>This can't be undone.</p></div>
      <div class="modal-footer">
        <button class="btn-secondary" id="cancel-del">Cancel</button>
        <button class="btn-primary danger" id="confirm-del">Delete</button>
      </div>`, {
      onMount: (box) => {
        box.querySelector("#cancel-del").addEventListener("click", WT.modal.close);
        box.querySelector("#confirm-del").addEventListener("click", async () => {
          await WT.api.delete_session(id);
          WT.modal.close();
          await loadData();
          WT.toast("Session deleted.", { kind: "success" });
        });
      },
    });
  }

  function toLocalInput(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function openEditor(sessionId, prefillDate) {
    const session = sessionId ? currentSessions.find((s) => s.id === sessionId) : null;
    const projects = WT.state.projects || [];
    const now = new Date();
    const defaultStart = prefillDate ? new Date(prefillDate + "T09:00:00") : new Date(now.getTime() - 3600000);
    const defaultEnd = prefillDate ? new Date(prefillDate + "T10:00:00") : now;

    const projOptions = `<option value="">No project</option>` + projects.map((p) =>
      `<option value="${p.id}" ${session && session.project_id === p.id ? "selected" : ""}>${escapeHtml(p.name)}</option>`).join("");

    WT.modal.open(`
      <div class="modal-header"><h2>${session ? "Edit session" : "Add past session"}</h2><button class="btn-icon modal-close">${WT.icons.iconHTML("x")}</button></div>
      <div class="modal-body">
        <div class="form-row">
          <label>Start</label>
          <input type="datetime-local" id="f-start" value="${session ? toLocalInput(session.start_ts) : toLocalInput(defaultStart.toISOString())}" />
        </div>
        <div class="form-row">
          <label>End</label>
          <input type="datetime-local" id="f-end" value="${session ? toLocalInput(session.end_ts) : toLocalInput(defaultEnd.toISOString())}" />
        </div>
        <div class="form-row"><label>Project</label><select id="f-project">${projOptions}</select></div>
        <div class="form-row"><label>Notes</label><input type="text" id="f-comment" value="${session ? escapeHtml(session.comment || "") : ""}" placeholder="Optional" /></div>
        <div class="form-hint" id="f-duration-preview"></div>
      </div>
      <div class="modal-footer">
        ${session ? '<button class="btn-secondary danger" id="btn-modal-delete" style="margin-right:auto;">Delete</button>' : ""}
        <button class="btn-secondary modal-close">Cancel</button>
        <button class="btn-primary" id="btn-save-session">Save</button>
      </div>`, {
      onMount: (box) => {
        box.querySelectorAll(".modal-close").forEach((b) => b.addEventListener("click", WT.modal.close));
        const preview = () => {
          const s = new Date(box.querySelector("#f-start").value);
          const e = new Date(box.querySelector("#f-end").value);
          const diff = (e - s) / 1000;
          box.querySelector("#f-duration-preview").textContent = diff > 0 ? `Duration: ${fmtDuration(diff)}` : "End must be after start.";
        };
        box.querySelector("#f-start").addEventListener("input", preview);
        box.querySelector("#f-end").addEventListener("input", preview);
        preview();

        if (session) {
          box.querySelector("#btn-modal-delete").addEventListener("click", () => { WT.modal.close(); confirmDelete(session.id); });
        }

        box.querySelector("#btn-save-session").addEventListener("click", async () => {
          const startIso = new Date(box.querySelector("#f-start").value).toISOString();
          const endIso = new Date(box.querySelector("#f-end").value).toISOString();
          const comment = box.querySelector("#f-comment").value;
          const pidRaw = box.querySelector("#f-project").value;
          const projectId = pidRaw ? parseInt(pidRaw, 10) : null;

          const result = session
            ? await WT.api.update_session(session.id, startIso, endIso, comment, projectId)
            : await WT.api.add_session(startIso, endIso, comment, projectId);

          if (!result.success) { WT.toast(result.error || "Could not save session.", { kind: "error" }); return; }
          WT.modal.close();
          await loadData();
          if (WT.viewCalendar) WT.viewCalendar.refresh();
          WT.toast(session ? "Session updated." : "Session added.", { kind: "success" });
        });
      },
    });
  }

  async function exportData(fmt) {
    const dateFrom = el("filter-date-from").value || null;
    const dateTo = el("filter-date-to").value || null;
    const search = el("filter-search").value || null;
    const result = await WT.api.export_sessions(fmt, dateFrom, dateTo, search);
    if (result.success) WT.toast(`Exported to ${result.path}`, { kind: "success" });
    else if (result.error) WT.toast(result.error, { kind: "error" });
  }

  function init() {
    const defaults = defaultFilters();
    el("filter-date-from").value = defaults.from;
    el("filter-date-to").value = defaults.to;
    el("filter-date-from").addEventListener("change", loadData);
    el("filter-date-to").addEventListener("change", loadData);
    let searchTimer;
    el("filter-search").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(loadData, 250); });
    el("btn-add-session").addEventListener("click", () => openEditor(null));
    el("btn-export-csv").addEventListener("click", () => exportData("csv"));
    el("btn-export-excel").addEventListener("click", () => exportData("excel"));
    loadData();
  }

  window.WT = window.WT || {};
  window.WT.viewSessions = { init, refresh: loadData, openEditor };
})();
