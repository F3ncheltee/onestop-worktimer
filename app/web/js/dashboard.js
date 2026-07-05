(function () {
  let selectedProjectId = null;
  let selectedMode = "countup";
  let selectedCountdownMin = 25;
  let nextReminderSec = 0;
  let smartReminderShowing = false;

  function el(id) { return document.getElementById(id); }

  function greeting() {
    const h = new Date().getHours();
    if (h < 5) return "Burning the midnight oil";
    if (h < 12) return "Good morning";
    if (h < 18) return "Good afternoon";
    return "Good evening";
  }

  function renderHeader() {
    el("dashboard-greeting").textContent = `${greeting()}${WT.state.timerState.running ? " - you're on the clock" : ""}`;
    el("dashboard-date").textContent = new Date().toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
  }

  function renderStreak() {
    el("streak-count").textContent = WT.state.streak.current_streak || 0;
    const badge = el("streak-badge");
    badge.classList.toggle("active", (WT.state.streak.current_streak || 0) > 0);
  }

  function renderProjectPicker() {
    const wrap = el("project-picker");
    const projects = WT.state.projects || [];
    wrap.innerHTML = `<button class="chip proj-chip ${selectedProjectId === null ? "active" : ""}" data-pid="">No project</button>` +
      projects.map((p) => `
        <button class="chip proj-chip ${selectedProjectId === p.id ? "active" : ""}" data-pid="${p.id}" style="--proj-color:${p.color || "#3b82f6"}">
          <span class="proj-dot" style="background:${p.color || "#3b82f6"}"></span>${escapeHtml(p.name)}
        </button>`).join("") +
      `<button class="chip proj-chip proj-chip-add" id="chip-add-project">${WT.icons.iconHTML("plus")}</button>`;

    wrap.querySelectorAll(".proj-chip[data-pid]").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedProjectId = btn.dataset.pid ? parseInt(btn.dataset.pid, 10) : null;
        renderProjectPicker();
      });
    });
    const addBtn = document.getElementById("chip-add-project");
    if (addBtn) addBtn.addEventListener("click", () => WT.viewProjects.openEditor(null, refreshProjectDependents));
  }

  function renderQuickstart() {
    const grid = el("quickstart-grid");
    const projects = WT.state.projects || [];
    if (!projects.length) {
      grid.innerHTML = `<div class="empty-hint">Add a project to unlock one-tap starts.</div>`;
      return;
    }
    grid.innerHTML = projects.slice(0, 6).map((p) => `
      <button class="quickstart-btn" data-pid="${p.id}" style="--proj-color:${p.color || "#3b82f6"}">
        ${WT.icons.iconHTML("play")} ${escapeHtml(p.name)}
      </button>`).join("");
    grid.querySelectorAll(".quickstart-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (WT.state.timerState.running) { WT.toast("Stop the current timer first.", { kind: "error" }); return; }
        selectedProjectId = parseInt(btn.dataset.pid, 10);
        renderProjectPicker();
        await startTimer();
      });
    });
  }

  function renderQuickComments() {
    const wrap = el("quick-comments");
    const presets = WT.state.quickComments || [];
    wrap.innerHTML = presets.map((c) => `<button class="chip chip-ghost">${escapeHtml(c)}</button>`).join("");
    wrap.querySelectorAll(".chip-ghost").forEach((btn) => {
      btn.addEventListener("click", () => { el("comment-input").value = btn.textContent; });
    });
  }

  function renderKpis() {
    const kpis = WT.state.kpis || {};
    document.querySelectorAll("#kpi-grid .kpi-card").forEach((card) => {
      const key = card.dataset.kpi;
      card.querySelector(".kpi-value").textContent = kpis[key] || "0 h";
    });
  }

  function renderGoals() {
    const list = el("goals-list");
    const progress = WT.state.goalProgress || [];
    if (!progress.length) {
      list.innerHTML = `<div class="empty-hint">No goals yet - set one to track progress.</div>`;
      return;
    }
    list.innerHTML = progress.map((g) => {
      const label = g.scope === "project" ? (g.project_name || "Project") : "Overall";
      const periodLabel = g.period === "daily" ? "today" : "this week";
      return `
        <div class="goal-row">
          <div class="goal-row-top">
            <span class="goal-name">${escapeHtml(label)} <span class="goal-period">/ ${periodLabel}</span></span>
            <span class="goal-pct">${g.pct}%</span>
          </div>
          <div class="goal-bar"><div class="goal-bar-fill" style="width:${g.pct}%"></div></div>
        </div>`;
    }).join("");
  }

  function fmtHoursShort(sec) {
    if (!sec) return "—";
    const h = sec / 3600;
    return h >= 1 ? `${h.toFixed(1)}h` : `${Math.round(sec / 60)}m`;
  }

  function renderWeekGlance() {
    const strip = el("week-glance-strip");
    const days = WT.state.weekGlance || [];
    if (!days.length) {
      strip.innerHTML = `<div class="empty-hint">No data yet this week.</div>`;
      return;
    }
    strip.innerHTML = days.map((d) => {
      const hasWork = d.total_sec > 0 && d.projects && d.projects.length;
      const tint = hasWork ? d.projects[0].color : "";
      const bands = hasWork
        ? `<div class="week-glance-bands">${d.projects.map((p) =>
            `<span style="flex:${p.sec};background:${p.color}" title="${escapeHtml(p.name)}"></span>`
          ).join("")}</div>`
        : "";
      const tip = hasWork
        ? `${d.label}: ${d.projects.map((p) => `${p.name} ${fmtHoursShort(p.sec)}`).join(", ")}`
        : d.label;
      return `
        <button type="button" class="week-glance-day ${d.is_today ? "today" : ""} ${hasWork ? "has-work" : ""}"
          data-date="${d.date}" title="${escapeHtml(tip)}"${tint ? ` style="--cal-tint:${tint}"` : ""}>
          ${bands}
          <span class="week-glance-label">${d.label}</span>
          <span class="week-glance-hours">${fmtHoursShort(d.total_sec)}</span>
        </button>`;
    }).join("");
    strip.querySelectorAll(".week-glance-day").forEach((btn) => {
      btn.addEventListener("click", () => {
        WT.navigateTo("calendar");
        if (WT.viewCalendar && WT.viewCalendar.goToDate) {
          WT.viewCalendar.goToDate(btn.dataset.date);
        }
      });
    });
  }

  function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function setMode(mode) {
    selectedMode = mode;
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
    const thumb = document.querySelector(".mode-thumb");
    thumb.style.transform = mode === "countup" ? "translateX(0)" : "translateX(100%)";
    el("countdown-picker").classList.toggle("hidden", mode !== "countdown");
    if (!WT.state.timerState.running) {
      el("ring-time").textContent = mode === "countdown" ? WT.timerRing.formatDuration(selectedCountdownMin * 60) : "00:00:00";
    }
  }

  function bindModeSwitch() {
    document.querySelectorAll(".mode-btn").forEach((btn) => {
      btn.addEventListener("click", () => setMode(btn.dataset.mode));
    });
    document.querySelectorAll("#countdown-picker .chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedCountdownMin = parseInt(btn.dataset.min, 10);
        el("countdown-custom").value = "";
        document.querySelectorAll("#countdown-picker .chip").forEach((c) => c.classList.toggle("active", c === btn));
        if (!WT.state.timerState.running) el("ring-time").textContent = WT.timerRing.formatDuration(selectedCountdownMin * 60);
      });
    });
    el("countdown-custom").addEventListener("input", (e) => {
      const v = parseInt(e.target.value, 10);
      if (v > 0) {
        selectedCountdownMin = v;
        document.querySelectorAll("#countdown-picker .chip").forEach((c) => c.classList.remove("active"));
        if (!WT.state.timerState.running) el("ring-time").textContent = WT.timerRing.formatDuration(selectedCountdownMin * 60);
      }
    });
  }

  function setSessionControlsEnabled(enabled) {
    el("comment-input").disabled = !enabled;
    document.querySelectorAll(".mode-btn").forEach((b) => (b.disabled = !enabled));
    document.querySelectorAll("#project-picker .proj-chip").forEach((b) => (b.disabled = !enabled));
    document.querySelectorAll("#countdown-picker .chip, #countdown-custom").forEach((b) => (b.disabled = !enabled));
  }

  async function startTimer() {
    const targetSec = selectedMode === "countdown" ? selectedCountdownMin * 60 : null;
    if (selectedMode === "countdown" && (!targetSec || targetSec <= 0)) {
      WT.toast("Set a countdown duration first.", { kind: "error" });
      return;
    }
    const comment = el("comment-input").value;
    const state = await WT.api.start_timer(selectedMode, targetSec, comment, selectedProjectId);
    WT.state.timerState = state;
    nextReminderSec = 0;
    const settings = WT.state.settings || {};
    if (settings.smart_enabled) nextReminderSec = (settings.smart_interval_min || 50) * 60;
    applyRunningUi();
  }

  async function stopTimer() {
    const comment = el("comment-input").value;
    const state = await WT.api.stop_timer(comment);
    WT.state.timerState = state;
    applyStoppedUi();
    await WT.refreshDashboardStats();
    const milestones = await WT.api.check_milestones();
    (milestones || []).forEach((m) => WT.toast(m.message, { kind: "milestone", title: m.title }));
  }

  function applyRunningUi() {
    setSessionControlsEnabled(false);
    el("btn-timer-toggle").classList.add("running");
    el("btn-timer-toggle-label").textContent = "Stop";
    el("btn-timer-toggle").querySelector(".icon use").setAttribute("href", "#ic-square");
  }

  function applyStoppedUi() {
    setSessionControlsEnabled(true);
    el("btn-timer-toggle").classList.remove("running");
    el("btn-timer-toggle-label").textContent = "Start";
    const use = el("btn-timer-toggle").querySelector(".icon use");
    if (use) use.setAttribute("href", "#ic-play");
    el("ring-status").textContent = "READY";
    el("ring-status").className = "ring-status";
    document.getElementById("ring-progress").className = "ring-progress";
    WT.timerRing.setProgress(el("ring-progress"), selectedMode === "countdown" ? 1 : 0);
    el("ring-time").textContent = selectedMode === "countdown" ? WT.timerRing.formatDuration(selectedCountdownMin * 60) : "00:00:00";
  }

  function bindToggleButton() {
    el("btn-timer-toggle").addEventListener("click", async () => {
      if (WT.state.timerState.running) await stopTimer();
      else await startTimer();
    });
  }

  function tick() {
    const ts = WT.state.timerState;
    if (!ts || !ts.running) return;
    const elapsedSec = (Date.now() - new Date(ts.start_ts).getTime()) / 1000;
    const ring = el("ring-progress");
    const timeEl = el("ring-time");
    const statusEl = el("ring-status");

    if (ts.mode === "countdown" && ts.target_sec) {
      const remaining = ts.target_sec - elapsedSec;
      if (remaining >= 0) {
        timeEl.textContent = WT.timerRing.formatDuration(remaining);
        WT.timerRing.setProgress(ring, remaining / ts.target_sec);
        ring.className = "ring-progress count";
        statusEl.textContent = "COUNTDOWN";
        statusEl.className = "ring-status count";
      } else {
        timeEl.textContent = WT.timerRing.formatDuration(remaining, true);
        WT.timerRing.setProgress(ring, 1);
        ring.className = "ring-progress danger";
        statusEl.textContent = "OVERTIME";
        statusEl.className = "ring-status danger";
        if (!ts._notifiedDone) {
          ts._notifiedDone = true;
          WT.toast("Your countdown reached zero.", { kind: "info", title: "Time's up" });
        }
      }
    } else {
      timeEl.textContent = WT.timerRing.formatDuration(elapsedSec);
      WT.timerRing.setProgress(ring, 1);
      ring.className = "ring-progress run";
      statusEl.textContent = "RUNNING";
      statusEl.className = "ring-status run";
    }

    if (nextReminderSec > 0 && elapsedSec >= nextReminderSec && !smartReminderShowing) {
      showSmartReminder(Math.floor(elapsedSec / 60));
    }
  }

  function showSmartReminder(minutes) {
    smartReminderShowing = true;
    el("smart-overlay-text").textContent = `You've been working for ${minutes} minutes.`;
    document.getElementById("smart-overlay").classList.remove("hidden");
    requestAnimationFrame(() => document.getElementById("smart-overlay").classList.add("show"));
  }

  function hideSmartReminder() {
    smartReminderShowing = false;
    const overlay = document.getElementById("smart-overlay");
    overlay.classList.remove("show");
    setTimeout(() => overlay.classList.add("hidden"), 180);
  }

  function bindSmartReminder() {
    document.querySelectorAll("#smart-overlay .btn-overlay").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const action = btn.dataset.action;
        const settings = WT.state.settings || {};
        hideSmartReminder();
        if (action === "break") {
          await stopTimer();
          selectedMode = "countdown";
          setMode("countdown");
          selectedCountdownMin = 5;
          selectedProjectId = null;
          renderProjectPicker();
          el("comment-input").value = "Coffee Break ☕";
          await startTimer();
        } else if (action === "switch") {
          await stopTimer();
          WT.navigateTo("projects");
        } else if (action === "stop") {
          await stopTimer();
        } else {
          nextReminderSec += (settings.smart_interval_min || 50) * 60;
        }
      });
    });
  }

  function bindIdleOverlay() {
    let countdownInterval = null;
    window.__onIdleWarning = (warningSec) => {
      let remaining = warningSec;
      const overlay = document.getElementById("idle-overlay");
      overlay.classList.remove("hidden");
      requestAnimationFrame(() => overlay.classList.add("show"));
      el("idle-countdown").textContent = remaining;
      clearInterval(countdownInterval);
      countdownInterval = setInterval(async () => {
        remaining -= 1;
        el("idle-countdown").textContent = Math.max(0, remaining);
        if (remaining <= 0) {
          clearInterval(countdownInterval);
          hideIdleOverlay();
          const res = await WT.api.idle_warning_resolved(true);
          WT.state.timerState = res.state;
          applyStoppedUi();
          WT.toast("You were idle, so the timer auto-paused.", { kind: "info", title: "Auto-paused" });
        }
      }, 1000);
    };

    function hideIdleOverlay() {
      const overlay = document.getElementById("idle-overlay");
      overlay.classList.remove("show");
      setTimeout(() => overlay.classList.add("hidden"), 180);
    }

    el("btn-idle-here").addEventListener("click", async () => {
      clearInterval(countdownInterval);
      hideIdleOverlay();
      await WT.api.idle_warning_resolved(false);
    });

    window.__onAutoResumeAvailable = () => {
      WT.toast("Welcome back! Click Start to resume tracking.", { kind: "info", title: "You're back" });
      WT.api.clear_auto_pause();
    };
  }

  function bindHotkey() {
    window.__onHotkeyToggle = async () => {
      if (WT.state.timerState.running) await stopTimer();
      else await startTimer();
    };
  }

  async function refreshProjectDependents() {
    WT.state.projects = await WT.api.get_projects();
    renderProjectPicker();
    renderQuickstart();
  }

  async function openGoalsManager() {
    const goals = await WT.api.get_goals();
    const projects = WT.state.projects || [];
    const projOptions = projects.map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("");

    WT.modal.open(`
      <div class="modal-header"><h2>Goals</h2><button class="btn-icon modal-close">${WT.icons.iconHTML("x")}</button></div>
      <div class="modal-body">
        <div class="goals-manage-list">
          ${goals.length ? goals.map((g) => `
            <div class="goal-manage-row">
              <span>${g.scope === "project" ? escapeHtml(g.project_name || "Project") : "Overall"} - ${g.period} - ${(g.target_sec / 3600).toFixed(1)}h</span>
              <button class="btn-icon" data-del-goal="${g.id}">${WT.icons.iconHTML("trash-2")}</button>
            </div>`).join("") : `<div class="empty-hint">No goals yet.</div>`}
        </div>
        <hr class="modal-divider" />
        <div class="form-row">
          <label>Scope</label>
          <select id="goal-scope"><option value="overall">Overall</option><option value="project">Project</option></select>
        </div>
        <div class="form-row hidden" id="goal-project-row">
          <label>Project</label>
          <select id="goal-project">${projOptions}</select>
        </div>
        <div class="form-row">
          <label>Period</label>
          <select id="goal-period"><option value="daily">Daily</option><option value="weekly">Weekly</option></select>
        </div>
        <div class="form-row">
          <label>Target hours</label>
          <input type="number" id="goal-hours" min="0.5" step="0.5" value="4" />
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary modal-close">Close</button>
        <button class="btn-primary" id="btn-goal-save">Save goal</button>
      </div>
    `, {
      onMount: (box) => {
        box.querySelectorAll(".modal-close").forEach((b) => b.addEventListener("click", WT.modal.close));
        box.querySelectorAll("[data-del-goal]").forEach((b) => b.addEventListener("click", async () => {
          await WT.api.delete_goal(parseInt(b.dataset.delGoal, 10));
          openGoalsManager();
        }));
        box.querySelector("#goal-scope").addEventListener("change", (e) => {
          box.querySelector("#goal-project-row").classList.toggle("hidden", e.target.value !== "project");
        });
        box.querySelector("#btn-goal-save").addEventListener("click", async () => {
          const scope = box.querySelector("#goal-scope").value;
          const period = box.querySelector("#goal-period").value;
          const hours = parseFloat(box.querySelector("#goal-hours").value) || 0;
          const projectId = scope === "project" ? parseInt(box.querySelector("#goal-project").value, 10) : null;
          await WT.api.upsert_goal(scope, period, hours, projectId);
          WT.modal.close();
          await WT.refreshDashboardStats();
          WT.toast("Goal saved.", { kind: "success" });
        });
      },
    });
  }

  function init() {
    renderHeader();
    bindModeSwitch();
    bindToggleButton();
    bindSmartReminder();
    bindIdleOverlay();
    bindHotkey();
    el("btn-manage-goals").addEventListener("click", openGoalsManager);
    el("btn-week-calendar").addEventListener("click", () => WT.navigateTo("calendar"));
    setInterval(renderHeader, 60000);

    const ts = WT.state.timerState;
    if (ts.mode === "countdown") setMode("countdown");
    if (ts.running) {
      selectedMode = ts.mode;
      selectedProjectId = ts.project_id;
      el("comment-input").value = ts.comment || "";
      applyRunningUi();
      const settings = WT.state.settings || {};
      if (settings.smart_enabled) nextReminderSec = (settings.smart_interval_min || 50) * 60;
    } else {
      applyStoppedUi();
    }
  }

  function refresh() {
    renderHeader();
    renderStreak();
    renderProjectPicker();
    renderQuickstart();
    renderQuickComments();
    renderKpis();
    renderGoals();
    renderWeekGlance();
  }

  window.WT = window.WT || {};
  window.WT.viewDashboard = { init, refresh, tick, refreshProjectDependents };
})();
