/* ==========================================================================
   NesTube web UI — engine dialogs drawn in the page (NATIVE mode)
   When the engine is about to open one of these Qt dialogs during a bridge
   call, the call returns `needs` instead (nestube/ui_web/dialogs.py). The
   bootstrap calls NT_ASK(needs); the promise resolves with the answer (the
   call is then repeated with it) or null when the user cancels.
   ========================================================================== */
(function () {
  "use strict";
  if (!window.NT_NATIVE) return;
  const { $, $$, ICON, openModal, closeModal } = window.NT;
  const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  const field = (label, html) => `<div class="field"><label>${label}</label>${html}</div>`;
  const input = (id, val, ph = "", extra = "") => `<div class="input"><input id="${id}" value="${esc(val)}" placeholder="${esc(ph)}"${extra}></div>`;
  const hint = (t) => `<p style="margin:0;font-size:var(--fs-sm);color:var(--text-sec)">${t}</p>`;
  const foot = (ok) => `<button class="btn outline" data-close>Cancelar</button><button class="btn primary" id="ask-ok">${ok}</button>`;

  // Opens the modal and settles exactly once: with the answer, or null when
  // the modal is closed any other way (Cancel, ×, Esc, backdrop).
  function ask(title, body, okLabel, wide, collect, setup) {
    return new Promise((resolve) => {
      let done = false;
      const finish = (v) => { if (done) return; done = true; obs.disconnect(); resolve(v); };
      openModal(title, body, foot(okLabel), wide);
      const backdrop = $("#modal-backdrop");
      const obs = new MutationObserver(() => { if (backdrop.hidden) finish(null); });
      obs.observe(backdrop, { attributes: true, attributeFilter: ["hidden"] });
      const ok = () => { const v = collect(); if (v === undefined) return; finish(v); closeModal(); };
      $("#ask-ok").addEventListener("click", ok);
      $("#modal-body").addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.tagName === "INPUT") { e.preventDefault(); ok(); } });
      if (setup) setup(ok);
    });
  }

  // ── material / stock search ─────────────────────────────────────────────
  const MODES = [["profile", "Perfiles y tubos"], ["fictitious", "Material"], ["stock", "Stock"]];
  function material(n) {
    let mode = n.mode || "profile", rows = [], pick = -1, timer = null, seq = 0;
    const body = `<div class="segmented" id="mat-mode" style="width:360px;max-width:100%">${MODES.map(([m, l]) => `<button data-m="${m}" aria-pressed="${m === mode}">${l}</button>`).join("")}</div>
      <div style="display:grid;grid-template-columns:1fr 150px;gap:8px">
        <div class="search">${ICON("search", "")}<input id="mat-q" value="${esc(n.query)}" placeholder="Buscar perfil, material o calidad…"></div>
        <div class="input" id="mat-min-wrap"><input id="mat-min" class="num" value="${esc(n.min_len)}" placeholder="Largo mín."><span class="unit">mm</span></div>
      </div>
      <div class="list" id="mat-list" style="max-height:340px;overflow:auto" role="listbox" aria-label="Resultados"></div>`;
    return ask("Buscar perfiles y tubos", body, "Seleccionar", true, () => (pick >= 0 ? rows[pick] : undefined), (ok) => {
      const list = $("#mat-list");
      const render = () => {
        $("#mat-min-wrap").style.visibility = mode === "stock" ? "visible" : "hidden";
        list.innerHTML = rows.length ? rows.map((r, i) => `<div class="row${i === pick ? " active" : ""}" data-i="${i}" role="option" tabindex="0">
            <div class="row-main"><span class="row-title">${esc(r.profile_name || r.material)}</span><span class="row-sub">${esc([r.material && r.profile_name ? r.material : "", r.quality].filter(Boolean).join(" · ") || "—")}</span></div>
            ${r.length ? `<span class="row-trail mono">${Math.round(r.length)} mm · ×${r.quantity}</span>` : ""}</div>`).join("")
          : `<div class="empty-hint">Sin resultados</div>`;
        $$("[data-i]", list).forEach((el) => {
          el.addEventListener("click", () => { pick = +el.dataset.i; render(); });
          el.addEventListener("dblclick", () => { pick = +el.dataset.i; ok(); });
        });
      };
      // Only the latest request may fill the list (switching mode or typing
      // while an older search is still answering must not bring it back).
      const load = () => {
        const mine = ++seq;
        return window.NTB.call("data.material_options", { mode, query: $("#mat-q").value, min_len: $("#mat-min").value })
          .then((r) => { if (mine !== seq) return; rows = (r && r.ok && r.result.rows) || []; pick = rows.length === 1 ? 0 : -1; render(); });
      };
      const later = () => { clearTimeout(timer); timer = setTimeout(load, 180); };
      $$("#mat-mode [data-m]").forEach((b) => b.addEventListener("click", () => {
        mode = b.dataset.m; $$("#mat-mode [data-m]").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); load();
      }));
      $("#mat-q").addEventListener("input", later); $("#mat-min").addEventListener("input", later);
      load();
    });
  }

  // ── cutting height (which face is cut) ──────────────────────────────────
  function height(n) {
    let chosen = n.chosen != null ? n.chosen : (n.heights[0] || [])[1];
    const body = hint("Este perfil tiene varias caras. Elige la altura de corte (se recordará para este perfil).") +
      `<div class="segmented" id="h-opts">${n.heights.map(([l, v]) => `<button data-v="${v}" aria-pressed="${v === chosen}">${esc(l)} · ${+(+v).toFixed(1)} mm</button>`).join("")}</div>`;
    return ask("Seleccionar altura de corte", body, "Aceptar", false, () => ({ value: chosen }), () => {
      $$("#h-opts [data-v]").forEach((b) => b.addEventListener("click", () => {
        chosen = +b.dataset.v; $$("#h-opts [data-v]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      }));
    });
  }

  // ── save a drawn profile ────────────────────────────────────────────────
  function profileSave(n) {
    const mats = n.materials || [];
    const body = hint("El perfil se guardará directamente en la base de datos.") +
      `<datalist id="ps-names">${(n.names || []).map((x) => `<option value="${esc(x)}">`).join("")}</datalist>
      <div class="field-grid">
        ${field("Nombre *", input("ps-name", n.name, "Nombre", ' list="ps-names" required'))}
        ${field("Material", `<select class="select" id="ps-mat">${mats.map(([l, sw]) => `<option value="${esc(l)}" data-sw="${sw}"${l === n.material ? " selected" : ""}>${esc(l || "—")}</option>`).join("")}</select>`)}
        ${field("Calidad", input("ps-quality", n.quality, "S235"))}
        ${field("Peso específico", `<div class="input"><input id="ps-sw" class="num" readonly><span class="unit">t/m³</span></div>`)}
      </div>
      ${field("Campos (separados por comas)", input("ps-fields", n.fields))}
      ${field("Notas", `<textarea id="ps-notes" class="textarea" rows="3" style="width:100%;resize:vertical">${esc(n.notes)}</textarea>`)}`;
    return ask(n.title || "Guardar perfil", body, "Guardar", true, () => {
      const name = $("#ps-name").value.trim();
      if (!name) { $("#ps-name").focus(); return undefined; }
      return { name, material: $("#ps-mat").value, quality: $("#ps-quality").value.trim(),
        fields: $("#ps-fields").value.trim(), notes: $("#ps-notes").value.trim() };
    }, () => {
      const sw = () => { const o = $("#ps-mat").selectedOptions[0]; const v = o && +o.dataset.sw; $("#ps-sw").value = v ? v.toFixed(2) : "—"; };
      $("#ps-mat").addEventListener("change", sw); sw();
      $("#ps-name").focus();
    });
  }

  // ── choose the nestings to export ───────────────────────────────────────
  function nestingSelector(n) {
    const body = hint("Elige qué anidados de material incluir en el archivo exportado.") +
      `<div class="list" id="ns-list">${n.rows.map(([i, name, bars, pieces]) => `<label class="row" style="cursor:pointer"><input type="checkbox" data-i="${i}" checked style="accent-color:var(--accent)"><span class="row-main"><span class="row-title">${esc(name)}</span></span><span class="row-trail mono">${bars} barras · ${pieces} piezas</span></label>`).join("")}</div>
      <div style="display:flex;gap:6px"><button class="btn outline" id="ns-all">Seleccionar todos</button><button class="btn outline" id="ns-none">Deseleccionar todos</button></div>`;
    return ask("Seleccionar anidados para exportar", body, "Exportar seleccionados", false, () => {
      const indices = $$("#ns-list [data-i]").filter((c) => c.checked).map((c) => +c.dataset.i);
      return indices.length ? { indices } : undefined;
    }, () => {
      const sync = () => { $("#ask-ok").disabled = !$$("#ns-list [data-i]").some((c) => c.checked); };
      $$("#ns-list [data-i]").forEach((c) => c.addEventListener("change", sync));
      $("#ns-all").addEventListener("click", () => { $$("#ns-list [data-i]").forEach((c) => { c.checked = true; }); sync(); });
      $("#ns-none").addEventListener("click", () => { $$("#ns-list [data-i]").forEach((c) => { c.checked = false; }); sync(); });
    });
  }

  const DIALOGS = { material, height, profile_save: profileSave, nesting_selector: nestingSelector };
  window.NT_ASK = (needs) => (DIALOGS[needs.dialog] ? DIALOGS[needs.dialog](needs) : Promise.resolve(null));
})();
