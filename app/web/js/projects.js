(function () {
  const PALETTE = ["#10e0a2", "#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#ff5d5d", "#06b6d4", "#84cc16", "#f97316", "#6366f1", "#14b8a6", "#e11d48"];

  function el(id) { return document.getElementById(id); }
  function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  async function refresh() {
    WT.state.projects = await WT.api.get_projects();
    render();
  }

  function render() {
    const grid = el("projects-grid");
    const projects = WT.state.projects || [];
    if (!projects.length) {
      grid.innerHTML = `<div class="empty-state">${WT.icons.iconHTML("folder")}<div>No projects yet. Create one to start organizing sessions.</div></div>`;
      return;
    }
    grid.innerHTML = projects.map((p) => `
      <div class="project-card" style="--proj-color:${p.color || "#3b82f6"}">
        <div class="project-card-top">
          <span class="proj-dot lg"></span>
          <span class="project-card-name">${escapeHtml(p.name)}</span>
        </div>
        <div class="project-card-actions">
          <button class="btn-icon" data-edit="${p.id}">${WT.icons.iconHTML("edit-2")}</button>
          <button class="btn-icon danger" data-del="${p.id}">${WT.icons.iconHTML("trash-2")}</button>
        </div>
      </div>`).join("");

    grid.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => openEditor(projects.find((p) => p.id === parseInt(b.dataset.edit, 10)))));
    grid.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => confirmDelete(parseInt(b.dataset.del, 10))));
  }

  function confirmDelete(id) {
    WT.modal.open(`
      <div class="modal-header"><h2>Delete project?</h2></div>
      <div class="modal-body"><p>Past sessions stay in your history, just unlinked from this project.</p></div>
      <div class="modal-footer">
        <button class="btn-secondary" id="cancel-del">Cancel</button>
        <button class="btn-primary danger" id="confirm-del">Delete</button>
      </div>`, {
      onMount: (box) => {
        box.querySelector("#cancel-del").addEventListener("click", WT.modal.close);
        box.querySelector("#confirm-del").addEventListener("click", async () => {
          await WT.api.delete_project(id);
          WT.modal.close();
          await refresh();
          if (WT.viewDashboard) WT.viewDashboard.refreshProjectDependents();
          WT.toast("Project deleted.", { kind: "success" });
        });
      },
    });
  }

  function openEditor(project, onDone) {
    let chosenColor = project ? (project.color || PALETTE[0]) : PALETTE[Math.floor(Math.random() * PALETTE.length)];

    WT.modal.open(`
      <div class="modal-header"><h2>${project ? "Edit project" : "New project"}</h2><button class="btn-icon modal-close">${WT.icons.iconHTML("x")}</button></div>
      <div class="modal-body">
        <div class="form-row"><label>Name</label><input type="text" id="f-name" value="${project ? escapeHtml(project.name) : ""}" maxlength="60" placeholder="e.g. Client Website" /></div>
        <div class="form-row">
          <label>Color</label>
          <div class="swatch-grid" id="swatch-grid">
            ${PALETTE.map((c) => `<button class="swatch ${c === chosenColor ? "active" : ""}" data-color="${c}" style="background:${c}"></button>`).join("")}
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary modal-close">Cancel</button>
        <button class="btn-primary" id="btn-save-project">Save</button>
      </div>`, {
      onMount: (box) => {
        box.querySelectorAll(".modal-close").forEach((b) => b.addEventListener("click", WT.modal.close));
        box.querySelectorAll(".swatch").forEach((sw) => sw.addEventListener("click", () => {
          chosenColor = sw.dataset.color;
          box.querySelectorAll(".swatch").forEach((s) => s.classList.toggle("active", s === sw));
        }));
        box.querySelector("#btn-save-project").addEventListener("click", async () => {
          const name = box.querySelector("#f-name").value.trim();
          if (!name) { WT.toast("Give the project a name.", { kind: "error" }); return; }
          const result = project
            ? await WT.api.update_project(project.id, name, chosenColor)
            : await WT.api.add_project(name, chosenColor);
          if (!result.success) { WT.toast(result.error || "Could not save project.", { kind: "error" }); return; }
          WT.modal.close();
          await refresh();
          if (WT.viewDashboard) WT.viewDashboard.refreshProjectDependents();
          WT.toast(project ? "Project updated." : "Project created.", { kind: "success" });
          if (onDone) onDone();
        });
      },
    });
  }

  function init() {
    el("btn-add-project").addEventListener("click", () => openEditor(null));
    refresh();
  }

  window.WT = window.WT || {};
  window.WT.viewProjects = { init, refresh, openEditor };
})();
