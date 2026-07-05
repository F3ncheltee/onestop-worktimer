(function () {
  const backdrop = () => document.getElementById("modal-backdrop");
  const box = () => document.getElementById("modal-box");

  function open(html, opts = {}) {
    box().innerHTML = html;
    backdrop().classList.remove("hidden");
    requestAnimationFrame(() => backdrop().classList.add("show"));
    WT.icons.hydrateStaticIcons(box());
    if (opts.onMount) opts.onMount(box());
    document.addEventListener("keydown", onKeydown);
  }

  function close() {
    backdrop().classList.remove("show");
    document.removeEventListener("keydown", onKeydown);
    setTimeout(() => {
      backdrop().classList.add("hidden");
      box().innerHTML = "";
    }, 180);
  }

  function onKeydown(e) {
    if (e.key === "Escape") close();
  }

  backdrop() && backdrop().addEventListener("click", (e) => {
    if (e.target === backdrop()) close();
  });

  window.WT = window.WT || {};
  window.WT.modal = { open, close };
})();
