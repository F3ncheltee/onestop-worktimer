(function () {
  let hoursChart = null;
  let projectsChart = null;
  let timeOfDayChart = null;
  let weekdayChart = null;

  function el(id) { return document.getElementById(id); }
  function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  function currentDays() {
    const v = el("analytics-range").value;
    return v === "all" ? null : parseInt(v, 10);
  }

  function chartDefaults(text, grid) {
    return {
      responsive: true,
      animation: { duration: 500, easing: "easeOutCubic" },
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: text, maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } },
        y: { beginAtZero: true, grid: { color: grid }, ticks: { color: text } },
      },
    };
  }

  async function refresh() {
    const days = currentDays();
    const [stats, daily, projects, heatmap, timeOfDay, weekday] = await Promise.all([
      WT.api.get_range_stats(days),
      days && days <= 31 ? WT.api.get_daily_hours(days) : WT.api.get_weekly_hours(days),
      WT.api.get_project_hours(days, 6),
      WT.api.get_heatmap(365),
      WT.api.get_hours_by_time_of_day(days),
      WT.api.get_hours_by_weekday(days),
    ]);

    renderSummary(stats, days);
    renderHoursChart(daily, days);
    renderProjectsChart(projects);
    renderTimeOfDayChart(timeOfDay);
    renderWeekdayChart(weekday);
    renderHeatmap(heatmap);
  }

  function renderSummary(stats, days) {
    const rangeLabel = days === null ? "All time" : `Last ${days} days`;
    el("range-summary").innerHTML = `
      <div class="range-summary-grid">
        <div><span class="rs-value">${stats.total_hours}h</span><span class="rs-label">${rangeLabel}</span></div>
        <div><span class="rs-value">${stats.session_count}</span><span class="rs-label">sessions</span></div>
        <div><span class="rs-value">${stats.avg_session_hours}h</span><span class="rs-label">avg/session</span></div>
        <div><span class="rs-value">${stats.mean_daily_hours}h</span><span class="rs-label">mean/day</span></div>
        <div><span class="rs-value">${stats.mean_weekly_hours}h</span><span class="rs-label">mean/week</span></div>
        <div><span class="rs-value">${stats.median_daily_hours}h</span><span class="rs-label">median/day</span></div>
      </div>`;
  }

  function renderHoursChart(data, days) {
    const ctx = document.getElementById("chart-hours");
    const accent = cssVar("--accent-run-1") || "#10e0a2";
    const grid = "rgba(255,255,255,0.06)";
    const text = cssVar("--text-2") || "#8b93a7";

    if (hoursChart) hoursChart.destroy();
    hoursChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.dates,
        datasets: [{
          label: "Hours",
          data: data.hours,
          backgroundColor: accent,
          borderRadius: 6,
          maxBarThickness: days && days > 40 ? 10 : 26,
        }],
      },
      options: {
        ...chartDefaults(text, grid),
      },
    });
  }

  function renderProjectsChart(data) {
    const ctx = document.getElementById("chart-projects");
    const text = cssVar("--text-2") || "#8b93a7";
    if (projectsChart) projectsChart.destroy();

    if (!data.names.length || data.hours.every((h) => h === 0)) {
      projectsChart = null;
      ctx.getContext("2d").clearRect(0, 0, ctx.width, ctx.height);
      return;
    }

    projectsChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.names,
        datasets: [{ data: data.hours, backgroundColor: data.colors, borderWidth: 0 }],
      },
      options: {
        responsive: true,
        animation: { duration: 500 },
        plugins: {
          legend: { position: "bottom", labels: { color: text, boxWidth: 10, font: { size: 11 } } },
        },
        cutout: "62%",
      },
    });
  }

  function renderTimeOfDayChart(data) {
    const ctx = document.getElementById("chart-timeofday");
    const grid = "rgba(255,255,255,0.06)";
    const text = cssVar("--text-2") || "#8b93a7";
    if (timeOfDayChart) timeOfDayChart.destroy();

    const hasData = data.hours && data.hours.some((h) => h > 0);
    if (!hasData) {
      timeOfDayChart = null;
      ctx.getContext("2d").clearRect(0, 0, ctx.width, ctx.height);
      return;
    }

    timeOfDayChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [{
          label: "Hours",
          data: data.hours,
          backgroundColor: data.hours.map((h) => {
            const peak = Math.max(...data.hours, 0.01);
            const a = h <= 0 ? 0.1 : 0.28 + (h / peak) * 0.62;
            return `rgba(139, 92, 246, ${a.toFixed(2)})`;
          }),
          borderRadius: 4,
          maxBarThickness: 14,
        }],
      },
      options: chartDefaults(text, grid),
    });
  }

  function renderWeekdayChart(data) {
    const ctx = document.getElementById("chart-weekday");
    const accent = cssVar("--accent-run-1") || "#10e0a2";
    const weekend = cssVar("--text-3") || "#6b7280";
    const grid = "rgba(255,255,255,0.06)";
    const text = cssVar("--text-2") || "#8b93a7";
    if (weekdayChart) weekdayChart.destroy();

    const hasData = data.hours && data.hours.some((h) => h > 0);
    if (!hasData) {
      weekdayChart = null;
      ctx.getContext("2d").clearRect(0, 0, ctx.width, ctx.height);
      return;
    }

    weekdayChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [{
          label: "Hours",
          data: data.hours,
          backgroundColor: data.labels.map((_, i) => (i >= 5 ? weekend : accent)),
          borderRadius: 6,
          maxBarThickness: 36,
        }],
      },
      options: chartDefaults(text, grid),
    });
  }

  function renderHeatmap(data) {
    const grid = el("heatmap-grid");
    if (!data.length) { grid.innerHTML = ""; return; }

    const first = new Date(data[0].date + "T00:00:00");
    const leadingBlanks = (first.getDay() + 6) % 7;

    let html = "";
    for (let i = 0; i < leadingBlanks; i++) html += `<div class="heat-cell empty"></div>`;
    data.forEach((d) => {
      const h = d.hours;
      let cls = "heat-0";
      if (h >= 8) cls = "heat-4"; else if (h >= 4) cls = "heat-3"; else if (h >= 1) cls = "heat-2"; else if (h > 0) cls = "heat-1";
      html += `<div class="heat-cell ${cls}" title="${d.date}: ${h}h"></div>`;
    });
    grid.innerHTML = html;
  }

  function init() {
    el("analytics-range").addEventListener("change", refresh);
    refresh();
  }

  window.WT = window.WT || {};
  window.WT.viewAnalytics = { init, refresh };
})();
