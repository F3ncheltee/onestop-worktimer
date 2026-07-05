(function () {
  const VIEWS = ["dashboard", "sessions", "calendar", "analytics", "projects", "settings"];
  const initializedViews = new Set();

  window.WT = window.WT || {};
  WT.state = {
    timerState: { running: false, mode: "countup" },
    projects: [],
    quickComments: [],
    settings: {},
    kpis: {},
    streak: { current_streak: 0, longest_streak: 0 },
    goalProgress: [],
    weekGlance: [],
  };

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
  }
  WT.setTheme = setTheme;

  function navigateTo(view) {
    if (!VIEWS.includes(view)) return;
    document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
    document.querySelectorAll(".nav-btn[data-view]").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
    ensureViewInitialized(view);
  }
  WT.navigateTo = navigateTo;

  function ensureViewInitialized(view) {
    if (initializedViews.has(view)) return;
    initializedViews.add(view);
    const map = {
      dashboard: WT.viewDashboard,
      sessions: WT.viewSessions,
      calendar: WT.viewCalendar,
      analytics: WT.viewAnalytics,
      projects: WT.viewProjects,
      settings: WT.viewSettings,
    };
    if (map[view] && map[view].init) map[view].init();
  }

  function bindNav() {
    document.querySelectorAll(".nav-btn[data-view]").forEach((btn) => {
      btn.addEventListener("click", () => navigateTo(btn.dataset.view));
    });
  }

  function bindTitlebar() {
    document.getElementById("btn-tray").addEventListener("click", () => WT.api.minimize_to_tray());
    document.getElementById("btn-quit").addEventListener("click", () => WT.api.quit_app());

    let compact = false;
    document.getElementById("btn-compact").addEventListener("click", async () => {
      compact = !compact;
      document.body.classList.toggle("compact-mode", compact);
      await WT.api.set_compact_mode(compact);
    });
  }

  function registerCommandPaletteActions() {
    const actions = [
      { label: "Go to Timer", group: "Navigate", icon: "home", run: () => navigateTo("dashboard") },
      { label: "Go to History", group: "Navigate", icon: "list", run: () => navigateTo("sessions") },
      { label: "Go to Calendar", group: "Navigate", icon: "calendar", run: () => navigateTo("calendar") },
      { label: "Go to Analytics", group: "Navigate", icon: "bar-chart", run: () => navigateTo("analytics") },
      { label: "Go to Projects", group: "Navigate", icon: "folder", run: () => navigateTo("projects") },
      { label: "Go to Settings", group: "Navigate", icon: "settings", run: () => navigateTo("settings") },
      {
        label: WT.state.timerState.running ? "Stop timer" : "Start timer",
        group: "Timer",
        icon: WT.state.timerState.running ? "square" : "play",
        run: () => document.getElementById("btn-timer-toggle").click(),
      },
      { label: "Add past session", group: "Sessions", icon: "plus", run: () => { navigateTo("sessions"); WT.viewSessions.openEditor(null); } },
      { label: "New project", group: "Projects", icon: "plus", run: () => { navigateTo("projects"); WT.viewProjects.openEditor(null); } },
      { label: "Manage goals", group: "Analytics", icon: "target", run: () => { navigateTo("dashboard"); document.getElementById("btn-manage-goals").click(); } },
      { label: "Toggle theme", group: "Appearance", icon: "palette", run: toggleTheme },
      { label: "Backup database now", group: "Data", icon: "shield", run: () => WT.api.backup_now().then(() => WT.toast("Backup created.", { kind: "success" })) },
    ];
    WT.commandPalette.setActions(actions);
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    setTheme(next);
    WT.api.save_settings({ theme: next }).then((res) => { WT.state.settings = res.settings; });
  }

  function globalTick() {
    if (WT.viewDashboard) WT.viewDashboard.tick();
  }

  function showBootstrapMilestones(milestones) {
    (milestones || []).forEach((m, i) => {
      setTimeout(() => WT.toast(m.message, { kind: "milestone", title: m.title }), 400 + i * 350);
    });
  }

  async function refreshDashboardStats() {
    const [kpis, streak, goalProgress, weekGlance] = await Promise.all([
      WT.api.get_kpis(), WT.api.get_streak(), WT.api.get_goal_progress(), WT.api.get_week_glance(),
    ]);
    WT.state.kpis = kpis;
    WT.state.streak = streak;
    WT.state.goalProgress = goalProgress;
    WT.state.weekGlance = weekGlance;
    if (WT.viewDashboard) WT.viewDashboard.refresh();
  }
  WT.refreshDashboardStats = refreshDashboardStats;

  async function boot() {
    WT.icons.hydrateStaticIcons(document);
    bindNav();
    bindTitlebar();

    const bootstrap = await WT.api.get_bootstrap();
    if (bootstrap) {
      WT.state.timerState = bootstrap.timer_state;
      WT.state.projects = bootstrap.projects;
      WT.state.quickComments = bootstrap.quick_comments;
      WT.state.settings = bootstrap.settings;
      WT.state.kpis = bootstrap.kpis;
      WT.state.streak = bootstrap.streak;
      WT.state.goalProgress = bootstrap.goal_progress;
      WT.state.weekGlance = bootstrap.week_glance || [];
      setTheme(bootstrap.settings.theme || "dark");
    }

    ensureViewInitialized("dashboard");
    WT.viewDashboard.refresh();
    registerCommandPaletteActions();
    WT.icons.hydrateStaticIcons(document);

    setInterval(globalTick, 250);
    setInterval(async () => {
      // Lightweight periodic refresh so KPIs/streak stay fresh across long sessions.
      if (document.getElementById("view-dashboard").classList.contains("active")) {
        await refreshDashboardStats();
      }
    }, 60000);

    if (bootstrap) showBootstrapMilestones(bootstrap.milestones);
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
