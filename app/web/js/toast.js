(function () {
  const ICONS_BY_KIND = {
    success: "check",
    error: "x-circle",
    info: "sparkles",
    milestone: "trophy",
  };

  function show(message, opts = {}) {
    const { kind = "info", title = "", duration = 4200 } = opts;
    const stack = document.getElementById("toast-stack");
    if (!stack) return;

    const el = document.createElement("div");
    el.className = `toast toast-${kind}`;
    el.innerHTML = `
      <div class="toast-icon">${WT.icons.iconHTML(ICONS_BY_KIND[kind] || "info")}</div>
      <div class="toast-body">
        ${title ? `<div class="toast-title">${title}</div>` : ""}
        <div class="toast-msg">${message}</div>
      </div>
      <button class="toast-close">${WT.icons.iconHTML("x")}</button>
    `;
    stack.appendChild(el);

    if (kind === "milestone") spawnConfetti(el);

    const remove = () => {
      el.style.animation = "toastOut 220ms ease forwards";
      setTimeout(() => el.remove(), 220);
    };
    el.querySelector(".toast-close").addEventListener("click", remove);
    if (duration) setTimeout(remove, duration);
  }

  function spawnConfetti(anchorEl) {
    const colors = ["#10e0a2", "#3b82f6", "#8b5cf6", "#f59e0b", "#ec4899"];
    for (let i = 0; i < 14; i++) {
      const bit = document.createElement("span");
      bit.className = "confetti-bit";
      bit.style.left = `${10 + Math.random() * 80}%`;
      bit.style.background = colors[i % colors.length];
      bit.style.animationDelay = `${Math.random() * 120}ms`;
      anchorEl.appendChild(bit);
      setTimeout(() => bit.remove(), 1400);
    }
  }

  window.WT = window.WT || {};
  window.WT.toast = show;
})();
