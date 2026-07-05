(function () {
  let actions = [];
  let filtered = [];
  let activeIndex = 0;

  function setActions(list) {
    actions = list;
  }

  function backdrop() {
    return document.getElementById("cmdk-backdrop");
  }

  function open() {
    filtered = actions;
    activeIndex = 0;
    render();
    backdrop().classList.remove("hidden");
    requestAnimationFrame(() => backdrop().classList.add("show"));
    const input = document.getElementById("cmdk-input");
    input.value = "";
    setTimeout(() => input.focus(), 30);
  }

  function close() {
    backdrop().classList.remove("show");
    setTimeout(() => backdrop().classList.add("hidden"), 150);
  }

  function toggle() {
    if (backdrop().classList.contains("hidden")) open();
    else close();
  }

  function score(query, action) {
    const q = query.toLowerCase();
    const hay = `${action.label} ${action.group || ""}`.toLowerCase();
    if (!q) return 1;
    if (!hay.includes(q)) return -1;
    return hay.startsWith(q) ? 2 : 1;
  }

  function filter(query) {
    filtered = actions
      .map((a) => ({ a, s: score(query, a) }))
      .filter((x) => x.s >= 0)
      .sort((x, y) => y.s - x.s)
      .map((x) => x.a);
    activeIndex = 0;
    render();
  }

  function render() {
    const results = document.getElementById("cmdk-results");
    if (!filtered.length) {
      results.innerHTML = `<div class="cmdk-empty">No matching commands</div>`;
      return;
    }
    results.innerHTML = filtered
      .map(
        (a, i) => `
      <div class="cmdk-item ${i === activeIndex ? "active" : ""}" data-index="${i}">
        <span class="cmdk-item-icon">${WT.icons.iconHTML(a.icon || "arrow-up-right")}</span>
        <span class="cmdk-item-label">${a.label}</span>
        ${a.group ? `<span class="cmdk-item-group">${a.group}</span>` : ""}
      </div>`
      )
      .join("");
    results.querySelectorAll(".cmdk-item").forEach((el) => {
      el.addEventListener("click", () => runAtIndex(parseInt(el.dataset.index, 10)));
    });
  }

  function runAtIndex(i) {
    const action = filtered[i];
    if (!action) return;
    close();
    action.run();
  }

  function onKeydown(e) {
    if (e.ctrlKey && e.key.toLowerCase() === "k") {
      e.preventDefault();
      toggle();
      return;
    }
    if (backdrop().classList.contains("hidden")) return;
    if (e.key === "Escape") {
      close();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(activeIndex + 1, filtered.length - 1);
      render();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
      render();
    } else if (e.key === "Enter") {
      e.preventDefault();
      runAtIndex(activeIndex);
    }
  }

  document.addEventListener("keydown", onKeydown);
  document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("cmdk-input");
    if (input) input.addEventListener("input", (e) => filter(e.target.value));
    const bd = backdrop();
    if (bd) bd.addEventListener("click", (e) => { if (e.target === bd) close(); });
  });

  window.WT = window.WT || {};
  window.WT.commandPalette = { setActions, open, close, toggle };
})();
