/* Minimal hand-built stroke icon set (24x24, feather-style conventions: currentColor, round caps). */
(function () {
  const ICONS = {
    "home": '<path d="M4 11.5 12 4l8 7.5"/><path d="M6 10v9a1 1 0 0 0 1 1h4v-6h2v6h4a1 1 0 0 0 1-1v-9"/>',
    "list": '<circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/><path d="M9 6h11M9 12h11M9 18h11"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="16" rx="2.5"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/>',
    "bar-chart": '<path d="M5 20V11M12 20V4M19 20v-7"/>',
    "folder": '<path d="M3.5 6.5A1.5 1.5 0 0 1 5 5h4l2 2.5h8A1.5 1.5 0 0 1 20.5 9v9A1.5 1.5 0 0 1 19 19.5H5A1.5 1.5 0 0 1 3.5 18z"/>',
    "folder-plus": '<path d="M3.5 6.5A1.5 1.5 0 0 1 5 5h4l2 2.5h8A1.5 1.5 0 0 1 20.5 9v9A1.5 1.5 0 0 1 19 19.5H5A1.5 1.5 0 0 1 3.5 18z"/><path d="M12 11v5M9.5 13.5h5"/>',
    "settings": '<circle cx="12" cy="12" r="3.2"/><path d="M12 3.5v2.3M12 18.2v2.3M4.9 6.1l1.9 1.4M17.2 16.5l1.9 1.4M3.5 12h2.3M18.2 12h2.3M4.9 17.9l1.9-1.4M17.2 7.5l1.9-1.4"/>',
    "flame": '<path d="M12 3c1 3-3 4-3 8a4 4 0 0 0 8 0c0-1.5-.7-2.2-1.2-3.2.6 2.4-.8 3.2-1.8 3.2-1.3 0-2-1-1.5-2.4C13 6.8 13 4.6 12 3Z"/><path d="M9.2 15.5A5 5 0 0 0 12 20a5 5 0 0 0 4.7-6.8"/>',
    "play": '<path d="M6.5 4.5v15l13-7.5z"/>',
    "pause": '<rect x="6" y="4.5" width="4.5" height="15" rx="1"/><rect x="13.5" y="4.5" width="4.5" height="15" rx="1"/>',
    "square": '<rect x="5.5" y="5.5" width="13" height="13" rx="2"/>',
    "download": '<path d="M12 3.5v11M7.5 10l4.5 4.5L16.5 10"/><path d="M4.5 17v1.7A1.8 1.8 0 0 0 6.3 20.5h11.4a1.8 1.8 0 0 0 1.8-1.8V17"/>',
    "upload": '<path d="M12 15V4M7.5 8.5 12 4l4.5 4.5"/><path d="M4.5 17v1.7A1.8 1.8 0 0 0 6.3 20.5h11.4a1.8 1.8 0 0 0 1.8-1.8V17"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "minimize-2": '<path d="M15 9l5.5-5.5M9 15l-5.5 5.5"/><path d="M20 8.2V3h-5.2M4 15.8V21h5.2"/>',
    "chevron-left": '<path d="M15 5l-7 7 7 7"/>',
    "chevron-right": '<path d="M9 5l7 7-7 7"/>',
    "chevron-down": '<path d="M5 9l7 7 7-7"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.8-4.8"/>',
    "coffee": '<path d="M4 9h13v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5Z"/><path d="M17 10.5h1.5a2.5 2.5 0 0 1 0 5H17"/><path d="M7 3.5c-.7.6-.7 1.4 0 2M11 3.5c-.7.6-.7 1.4 0 2"/>',
    "zap": '<path d="M12.5 3 5 13.5h5.5L10 21l7.5-10.5H12z"/>',
    "shuffle": '<path d="M4 6.5h3.2c2 0 3 1 4.3 2.9M4 17.5h3.2c2 0 3-1 4.3-2.9M15 6.5h5M15 17.5h5"/><path d="M17.5 4l2.5 2.5-2.5 2.5M17.5 15l2.5 2.5-2.5 2.5"/>',
    "shield": '<path d="M12 3.5 5 6v6c0 4.5 3 7.2 7 8.5 4-1.3 7-4 7-8.5V6z"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z"/>',
    "sun": '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.3M12 19.2v2.3M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.3M19.2 12h2.3M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6"/>',
    "edit-2": '<path d="M15.5 4.5 19 8l-11 11H4.5V15.5Z"/>',
    "trash-2": '<path d="M4.5 7h15M9.5 7V5a1.5 1.5 0 0 1 1.5-1.5h2A1.5 1.5 0 0 1 14.5 5v2M18 7l-.8 12a2 2 0 0 1-2 1.9H8.8a2 2 0 0 1-2-1.9L6 7"/>',
    "check": '<path d="M4.5 12.5 9 17l10.5-10.5"/>',
    "x-circle": '<circle cx="12" cy="12" r="8.5"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "star": '<path d="M12 3.5l2.6 5.6 6 .7-4.5 4.1 1.2 6-5.3-3.1-5.3 3.1 1.2-6-4.5-4.1 6-.7Z"/>',
    "sparkles": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><path d="M6 6l2 2M16 16l2 2M18 6l-2 2M8 16l-2 2"/>',
    "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4.2"/><circle cx="12" cy="12" r="0.6" fill="currentColor"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3.2 2"/>',
    "arrow-up-right": '<path d="M7 17 17 7M9 7h8v8"/>',
    "more-vertical": '<circle cx="12" cy="5.5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="18.5" r="1"/>',
    "filter": '<path d="M4 5h16L14 12.5V19l-4 2v-8.5Z"/>',
    "tag": '<path d="M12.5 4.5H6A1.5 1.5 0 0 0 4.5 6v6.5l9 9a1.5 1.5 0 0 0 2.1 0l5.4-5.4a1.5 1.5 0 0 0 0-2.1Z"/><circle cx="8.5" cy="8.5" r="1.2"/>',
    "palette": '<path d="M12 3.5a8.5 8.5 0 1 0 0 17c1 0 1.8-.8 1.8-1.8 0-.5-.2-.9-.5-1.2-.3-.3-.5-.7-.5-1.2 0-1 .8-1.8 1.8-1.8H16a4.5 4.5 0 0 0 4.5-4.5c0-3.6-4-6.5-8.5-6.5Z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7.5" r="1"/><circle cx="14.5" cy="7.5" r="1"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><circle cx="12" cy="8" r="0.8" fill="currentColor"/>',
    "trophy": '<path d="M8 4.5h8v4.2A4 4 0 0 1 12 12.7 4 4 0 0 1 8 8.7Z"/><path d="M8 5H5.5v2A2.5 2.5 0 0 0 8 9.5M16 5h2.5v2A2.5 2.5 0 0 1 16 9.5"/><path d="M12 12.7V16M9 19.5h6M9.5 16.3h5"/>',
  };

  function buildSprite() {
    const sprite = document.getElementById("icon-sprite");
    if (!sprite) return;
    let defs = "";
    for (const [name, inner] of Object.entries(ICONS)) {
      defs += `<symbol id="ic-${name}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${inner}</symbol>`;
    }
    sprite.innerHTML = defs;
  }

  function iconHTML(name, extraClass) {
    if (!ICONS[name]) return "";
    return `<svg class="icon ${extraClass || ""}"><use href="#ic-${name}"></use></svg>`;
  }

  function hydrateStaticIcons(root) {
    (root || document).querySelectorAll("[data-icon]").forEach((el) => {
      const name = el.getAttribute("data-icon");
      if (el.querySelector("svg.icon")) return;
      el.insertAdjacentHTML("afterbegin", iconHTML(name));
    });
  }

  window.WT = window.WT || {};
  window.WT.icons = { buildSprite, iconHTML, hydrateStaticIcons, names: Object.keys(ICONS) };

  buildSprite();
})();
