(function () {
  function el(id) { return document.getElementById(id); }
  function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function applySettingsToForm() {
    const s = WT.state.settings || {};
    el("setting-idle-enabled").checked = !!s.idle_enabled;
    el("setting-idle-threshold").value = s.idle_threshold_min || 5;
    el("setting-idle-warning").value = s.idle_warning_sec || 30;
    el("setting-idle-autoresume").checked = s.idle_auto_resume !== false;
    el("setting-smart-enabled").checked = s.smart_enabled !== false;
    el("setting-smart-interval").value = s.smart_interval_min || 50;
    el("setting-hotkey-enabled").checked = s.hotkey_enabled !== false;
    document.querySelectorAll(".theme-opt").forEach((b) => b.classList.toggle("active", b.dataset.theme === (s.theme || "dark")));
  }

  async function persist(partial) {
    const res = await WT.api.save_settings(partial);
    WT.state.settings = res.settings;
  }

  function bindSettingInputs() {
    el("setting-idle-enabled").addEventListener("change", (e) => persist({ idle_enabled: e.target.checked }));
    el("setting-idle-threshold").addEventListener("change", (e) => persist({ idle_threshold_min: parseInt(e.target.value, 10) || 5 }));
    el("setting-idle-warning").addEventListener("change", (e) => persist({ idle_warning_sec: parseInt(e.target.value, 10) || 30 }));
    el("setting-idle-autoresume").addEventListener("change", (e) => persist({ idle_auto_resume: e.target.checked }));
    el("setting-smart-enabled").addEventListener("change", (e) => persist({ smart_enabled: e.target.checked }));
    el("setting-smart-interval").addEventListener("change", (e) => persist({ smart_interval_min: parseInt(e.target.value, 10) || 50 }));
    el("setting-hotkey-enabled").addEventListener("change", (e) => persist({ hotkey_enabled: e.target.checked }));

    document.querySelectorAll(".theme-opt").forEach((btn) => {
      btn.addEventListener("click", async () => {
        document.querySelectorAll(".theme-opt").forEach((b) => b.classList.toggle("active", b === btn));
        WT.setTheme(btn.dataset.theme);
        await persist({ theme: btn.dataset.theme });
      });
    });
  }

  function renderPresetChips() {
    const wrap = el("preset-chip-editor");
    const presets = WT.state.quickComments || [];
    wrap.innerHTML = presets.map((p, i) => `
      <span class="chip preset-chip">${escapeHtml(p)} <button data-idx="${i}">${WT.icons.iconHTML("x")}</button></span>`).join("")
      || `<div class="empty-hint">No presets yet.</div>`;
    wrap.querySelectorAll("button[data-idx]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const idx = parseInt(btn.dataset.idx, 10);
        const next = [...WT.state.quickComments];
        next.splice(idx, 1);
        WT.state.quickComments = next;
        await WT.api.save_quick_comments(next);
        renderPresetChips();
        if (WT.viewDashboard) WT.viewDashboard.refresh();
      });
    });
  }

  function bindPresetAdd() {
    const addPreset = async () => {
      const input = el("preset-new-input");
      const val = input.value.trim();
      if (!val) return;
      const next = [...(WT.state.quickComments || []), val];
      WT.state.quickComments = next;
      input.value = "";
      await WT.api.save_quick_comments(next);
      renderPresetChips();
      if (WT.viewDashboard) WT.viewDashboard.refresh();
    };
    el("btn-preset-add").addEventListener("click", addPreset);
    el("preset-new-input").addEventListener("keydown", (e) => { if (e.key === "Enter") addPreset(); });
  }

  function fmtBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  async function refreshDataPanel() {
    const [info, backups] = await Promise.all([WT.api.get_db_info(), WT.api.list_backups()]);
    el("db-info").innerHTML = `
      <div class="db-info-row"><span>Sessions</span><strong>${info.session_count}</strong></div>
      <div class="db-info-row"><span>Projects</span><strong>${info.project_count}</strong></div>
      <div class="db-info-row"><span>File size</span><strong>${fmtBytes(info.size_bytes)}</strong></div>
      <div class="db-info-row path"><span>Location</span><code>${escapeHtml(info.path)}</code></div>
    `;
    el("backups-list").innerHTML = backups.length
      ? `<div class="backups-title">Recent backups</div>` + backups.slice(0, 6).map((b) => `
          <div class="backup-row"><span>${escapeHtml(b.name)}</span><span>${fmtBytes(b.size_bytes)}</span></div>`).join("")
      : "";
  }

  function bindDataButtons() {
    el("btn-open-data-folder").addEventListener("click", () => WT.api.open_data_folder());
    el("btn-backup-now").addEventListener("click", async () => {
      const res = await WT.api.backup_now();
      if (res.success) { WT.toast("Backup created.", { kind: "success" }); refreshDataPanel(); }
      else WT.toast(res.error || "Backup failed.", { kind: "error" });
    });
    el("btn-restore-backup").addEventListener("click", async () => {
      WT.modal.open(`
        <div class="modal-header"><h2>Restore from backup</h2></div>
        <div class="modal-body"><p>This will replace your current data with the selected backup file. Your current database is backed up automatically first.</p></div>
        <div class="modal-footer">
          <button class="btn-secondary" id="cancel-restore">Cancel</button>
          <button class="btn-primary danger" id="confirm-restore">Choose file & restore</button>
        </div>`, {
        onMount: (box) => {
          box.querySelector("#cancel-restore").addEventListener("click", WT.modal.close);
          box.querySelector("#confirm-restore").addEventListener("click", async () => {
            const res = await WT.api.restore_from_backup_picker();
            WT.modal.close();
            if (res.success) { WT.toast("Data restored. Reloading...", { kind: "success" }); setTimeout(() => location.reload(), 900); }
            else if (res.error) WT.toast(res.error, { kind: "error" });
          });
        },
      });
    });
    el("btn-export-full").addEventListener("click", async () => {
      const res = await WT.api.export_full_backup();
      if (res.success) WT.toast(`Exported to ${res.path}`, { kind: "success" });
      else if (res.error) WT.toast(res.error, { kind: "error" });
    });
  }

  function init() {
    applySettingsToForm();
    bindSettingInputs();
    renderPresetChips();
    bindPresetAdd();
    bindDataButtons();
    refreshDataPanel();
  }

  window.WT = window.WT || {};
  window.WT.viewSettings = { init, refresh: () => { applySettingsToForm(); renderPresetChips(); refreshDataPanel(); } };
})();
