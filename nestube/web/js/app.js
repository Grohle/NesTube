/* ==========================================================================
   NesTube web UI — wiring (MOCKUP STAGE)
   Menu definitions (same items/order as nestube/ui_qt/app.py), keyboard
   shortcuts (same keys as the Qt app), and the Nesting panels bound to
   NestCanvas. Actions that open Qt dialogs show a dialog shell for now.
   ========================================================================== */
(function () {
  "use strict";
  const { $, $$, ICON, toast, openMenu, openMenuAt, openModal, closeModal, confirmDialog, setTheme, currentTheme } = window.NT;
  const alertBox = window.NT.alert;

  // Leaving Nesting with unsaved changes asks first (TabNesting via
  // MainWindow._on_main_tab_changed: Save / Discard / Cancel).
  function showView(name) {
    if (document.body.dataset.view === "nesting" && name !== "nesting" && N.isDirty()) {
      alertBox({ kind: "question", title: "Cambios sin guardar en el Nesting", msg: "El nesting tiene cambios sin guardar.\n\n¿Guardar antes de salir de esta pestaña?",
        buttons: [{ label: "Cancelar" }, { label: "Descartar", danger: true, action: () => { N.discardDirty(); window.NT.showView(name); } },
          { label: "Guardar", primary: true, action: () => { N.save(); window.NT.showView(name); } }] });
      return;
    }
    window.NT.showView(name);
  }
  window.NT.go = showView;
  const N = window.NestCanvas;
  const S = N.state;

  // ── dialog shells (functional stage: real forms + Python bridge) ────────
  const DIALOGS = window.NT_DIALOGS || {};
  function dialog(id) {
    const d = DIALOGS[id];
    if (!d) { toast("Pendiente: " + id); return; }
    if (d.open) { closeModal(); d.open(); return; }
    openModal(d.title, typeof d.body === "function" ? d.body() : d.body, d.foot || `<button class="btn outline" data-close>Cancelar</button><button class="btn primary" data-close${d.done ? ` data-toast="${d.done}"` : ""}>${d.ok || "Aceptar"}</button>`, d.wide);
    if (d.init) d.init();
  }
  window.NT.dialog = dialog;

  // ── main menu (Figma-style: one button, menus as submenus) ──────────────
  let unitSystem = "metric", lang = "es", cutColors = true;
  const MAIN_MENU = () => [
    { label: "Archivo", sub: [
      { label: "Abrir…", sc: "", action: () => dialog("open") },
      { label: "Guardar", sc: "Ctrl+S", action: saveAll },
      { label: "Guardar como…", action: () => dialog("save-as") },
      "-",
      { label: "Guardar configuración del programa…", action: () => toast("Configuración guardada (.json)") },
      { label: "Cargar configuración del programa…", action: () => dialog("open-config") },
      { label: "Copias de seguridad…", action: () => dialog("backups") },
      { label: "Gestión de base de datos…", action: () => dialog("db") },
      "-",
      { label: "Salir", action: () => (N.isDirty()
        ? alertBox({ kind: "question", title: "Cambios sin guardar en el Nesting", msg: "El nesting tiene cambios sin guardar.\n\n¿Guardar antes de salir?",
            buttons: [{ label: "Cancelar" }, { label: "Descartar", danger: true, action: () => toast("La app se cerraría aquí") }, { label: "Guardar", primary: true, action: () => { N.save(); toast("La app se cerraría aquí"); } }] })
        : toast("La app se cerraría aquí")) },
    ] },
    { label: "Vista", sub: [
      { label: "Tema", sub: [
        { label: "Oscuro", check: () => currentTheme() === "dark", action: () => setTheme("dark") },
        { label: "Claro", check: () => currentTheme() === "light", action: () => setTheme("light") },
      ] },
      { label: "Idioma", sub: [
        { label: "English", check: () => lang === "en", action: () => { lang = "en"; toast("Language: English (fase funcional)"); } },
        { label: "Español", check: () => lang === "es", action: () => { lang = "es"; toast("Idioma: Español"); } },
      ] },
      { label: "Sistema de unidades", sub: [
        { label: "Métrico (mm, kg)", check: () => unitSystem === "metric", action: () => { unitSystem = "metric"; toast("Unidades: métrico"); } },
        { label: "Imperial (in, lb)", check: () => unitSystem === "imperial", action: () => { unitSystem = "imperial"; toast("Unidades: imperial"); } },
      ] },
      "-",
      { label: "Colores por corte en anidado", check: () => cutColors, action: () => { cutColors = !cutColors; toast(cutColors ? "Colores por corte activados" : "Colores por corte desactivados"); } },
      "-",
      { label: "Atajos de teclado", sc: "?", action: showShortcuts },
    ] },
    { label: "Configuración", sub: [
      { label: "Materiales", sub: [
        { label: "Añadir material…", action: () => dialog("material-add") },
        { label: "Gestionar materiales…", action: () => dialog("materials") },
      ] },
      { label: "Perfiles y tubos", sub: [
        { label: "Añadir perfil…", action: () => dialog("profile-creator") },
        { label: "Editar perfiles…", action: () => dialog("profile-manager") },
      ] },
      { label: "Configuración PDF", sub: [
        { label: "Fuente PDF…", action: () => dialog("pdf-font") },
        { label: "Plantilla PDF base…", action: () => dialog("pdf-template") },
        { label: "Editar plantillas…", action: () => dialog("pdf-templates") },
      ] },
      { label: "Valores de coste por defecto…", action: () => dialog("cost-defaults") },
      { label: "Tiempos de optimización (1–6)…", action: () => dialog("opt-times") },
      { label: "Disposición del anidado…", action: () => dialog("nesting-layout") },
      { label: "Asignación de nombres…", action: () => dialog("naming") },
      "-",
      { label: "Restablecer ajustes…", danger: true, action: () => confirmDialog({ title: "Restablecer ajustes", text: "¿Restablecer todos los ajustes a valores predeterminados (inglés, EUR, métrico)?", ok: () => toast("Ajustes restablecidos") }) },
    ] },
    { label: "Acerca de", sub: [
      { label: "Acerca de NesTube…", action: () => dialog("about") },
    ] },
    { label: "Ayuda", sub: [
      { label: "Tutorial interactivo", action: () => window.NT_TOUR.start() },
      { label: "GitHub / Issues", action: () => toast("github.com/Grohle/nestube/issues") },
      "-",
      { label: "Catálogo de ventanas y avisos (maqueta)", action: showCatalog },
    ] },
  ];

  const EXPORT_MENU = () => [
    { header: "Anidado" },
    { label: "Exportar PDF", action: () => exportGuard(() => dialog("nest-selector")) },
    { label: "Imprimir…", action: () => exportGuard(() => dialog("nest-selector")) },
    "-",
    { label: "Exportar DXF", action: () => exportGuard(() => toast("Diagrama de anidado guardado en: C:\\NesTube\\exports\\PED-2026-001.dxf")) },
    "-",
    { label: "Exportar anidado (PNG)", action: () => exportGuard(() => toast("Diagrama de anidado guardado en: C:\\NesTube\\exports\\PED-2026-001.png")) },
  ];

  function pieceMenu(piece) {
    return [
      { label: "Mover", action: () => { const bar = S.bars.find((b) => b.pieces.includes(piece)); if (!bar) return;
        bar.pieces = bar.pieces.filter((p) => p !== piece); N.startFloating(piece.cut, { bar, piece }); } },
      { label: "Cambiar valores…", action: () => changeValues(piece.cut) },
      "-",
      { label: "Voltear horizontal", sc: "Ctrl+H", action: () => N.flip("fh") },
      { label: "Voltear vertical", sc: "Ctrl+A", action: () => N.flip("fv") },
      "-",
      { label: "Editar dibujo…", action: () => dialog("profile-creator") },
      { label: "Exportar DXF", action: () => toast(`DXF de «${piece.cut.name}» exportado`) },
      "-",
      { label: "Quitar de barra", sc: "Supr", action: () => N.deleteSelected() },
      { label: "Eliminar pieza", danger: true, action: () => N.removePermanently(piece.cut) },
    ];
  }
  function sidebarMenu(cut) {
    return [
      { label: "Cambiar valores…", action: () => changeValues(cut) },
      "-",
      { label: "Editar dibujo…", action: () => dialog("profile-creator") },
      { label: "Exportar DXF", action: () => toast(`DXF de «${cut.name}» exportado`) },
      "-",
      { label: "Eliminar pieza", danger: true, action: () => N.removePermanently(cut) },
    ];
  }

  function changeValues(cut) {
    openModal(`Cambiar valores · ${cut.name}`, `
      <div class="field-grid">
        <div class="field"><label for="cv-name">Descripción</label><div class="input"><input id="cv-name" value="${cut.name}"></div></div>
        <div class="field"><label for="cv-qty">Cantidad</label><div class="input"><span class="pre">×</span><input class="num" id="cv-qty" value="${cut.qty}"></div></div>
        <div class="field"><label for="cv-len">Longitud</label><div class="input"><span class="pre">L</span><input class="num" id="cv-len" value="${cut.len}"><span class="unit">mm</span></div></div>
        <div class="field"><label for="cv-color">Color</label><div class="input"><input type="color" id="cv-color" value="${cut.color}" style="height:20px;padding:0"></div></div>
        <div class="field"><label for="cv-al">Inglete izq.</label><div class="input"><span class="pre">∠</span><input class="num" id="cv-al" value="${cut.aL}"><span class="unit">°</span></div></div>
        <div class="field"><label for="cv-ar">Inglete der.</label><div class="input"><span class="pre">∠</span><input class="num" id="cv-ar" value="${cut.aR}"><span class="unit">°</span></div></div>
      </div>
      <p style="margin:0;font-size:var(--fs-xs);color:var(--text-dim)">Los cambios se aplican a todas las instancias colocadas y a la lista de cortes.</p>`,
    `<button class="btn outline" data-close>Cancelar</button><button class="btn primary" id="cv-ok">Aplicar</button>`);
    $("#cv-ok").onclick = () => {
      cut.name = $("#cv-name").value; cut.qty = Math.max(1, parseInt($("#cv-qty").value, 10) || cut.qty);
      cut.len = parseFloat($("#cv-len").value) || cut.len; cut.color = $("#cv-color").value;
      cut.aL = parseFloat($("#cv-al").value) || 0; cut.aR = parseFloat($("#cv-ar").value) || 0;
      closeModal(); N.setParam("cuts", S.cuts); N.clearSelection();
    };
  }

  function exportGuard(fn) {
    if (!S.bars.some((b) => b.pieces.length)) return alertBox({ title: "Exportar", msg: "Sin datos de anidado. Ejecuta el anidado automático o coloca piezas primero." });
    fn();
  }

  // ── catalog of every window and alert (review aid for the mockup) ───────
  const KIND_LBL = { information: "Información", warning: "Advertencia", critical: "Error", question: "Pregunta" };
  const KIND_ICON = { information: "info", warning: "warning", critical: "error", question: "question" };
  function showCatalog(tab = "windows", filter = "") {
    const dlg = window.NT_DIALOGS || {}, alerts = window.NT_ALERTS || [];
    const f = filter.toLowerCase();
    const rows = tab === "windows"
      ? Object.entries(dlg).filter(([, d]) => !f || d.title.toLowerCase().includes(f)).map(([id, d]) =>
        `<div class="catalog-row" data-cat-dialog="${id}"><span class="k" style="color:var(--text-sec)">${ICON("layers", "sm")}</span><div style="min-width:0"><div class="t">${d.title}</div></div><span class="src mono">${id}</span></div>`).join("")
      : alerts.map((a, i) => [a, i]).filter(([a]) => !f || (a.title + a.msg + a.src).toLowerCase().includes(f)).map(([a, i]) =>
        `<div class="catalog-row alert-${a.kind}" data-cat-alert="${i}"><span class="k alert-icon" style="width:22px;height:22px">${ICON(KIND_ICON[a.kind], "sm")}</span><div style="min-width:0"><div class="t">${a.title}</div><div class="m">${a.msg.replace(/</g, "&lt;")}</div></div><span class="src">${a.src}</span></div>`).join("");
    const counts = alerts.reduce((m, a) => (m[a.kind] = (m[a.kind] || 0) + 1, m), {});
    openModal("Catálogo de ventanas y avisos", `
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <div class="segmented" style="width:300px;max-width:100%"><button aria-pressed="${tab === "windows"}" data-cat-tab="windows">Ventanas (${Object.keys(dlg).length})</button><button aria-pressed="${tab === "alerts"}" data-cat-tab="alerts">Avisos (${alerts.length})</button></div>
        <div class="search" style="flex:1;min-width:160px">${ICON("search")}<input id="cat-filter" placeholder="Filtrar…" value="${filter}"></div>
      </div>
      ${tab === "alerts" ? `<div style="display:flex;gap:6px;flex-wrap:wrap">${Object.entries(counts).map(([k, n]) => `<span class="chip">${KIND_LBL[k]} · ${n}</span>`).join("")}</div>` : ""}
      <div style="display:grid;gap:1px;max-height:52vh;overflow:auto">${rows || '<div class="empty-hint">Sin resultados</div>'}</div>`, null, true);
    $$("[data-cat-tab]").forEach((b) => b.addEventListener("click", () => showCatalog(b.dataset.catTab, $("#cat-filter").value)));
    $("#cat-filter").addEventListener("input", (e) => { const v = e.target.value, pos = e.target.selectionStart; showCatalog(tab, v); const i = $("#cat-filter"); i.focus(); i.setSelectionRange(pos, pos); });
    $$("[data-cat-dialog]").forEach((r) => r.addEventListener("click", () => dialog(r.dataset.catDialog)));
    $$("[data-cat-alert]").forEach((r) => r.addEventListener("click", () => { const a = alerts[+r.dataset.catAlert]; alertBox({ kind: a.kind, title: a.title, msg: a.msg }); }));
  }
  window.NT.showCatalog = showCatalog;

  // ── shortcuts (identical keys to the Qt app) ────────────────────────────
  const SHORTCUTS = [
    ["Archivo", [["Guardar trabajo / anidado", "Ctrl+S"]]],
    ["Anidado", [
      ["Deshacer", "Ctrl+Z"], ["Rehacer", "Ctrl+Y"],
      ["Rotar pieza 90° antihorario", "Ctrl+Q"], ["Rotar pieza 90° horario", "Ctrl+E"],
      ["Reflejar horizontal", "Ctrl+H"], ["Reflejar vertical", "Ctrl+A"],
      ["Quitar de barra la selección", "Supr"],
      ["Detener auto-anidado · soltar pieza flotante · deseleccionar", "Esc"],
    ]],
    ["Lienzo", [
      ["Zoom en el cursor", "Rueda"], ["Desplazar", "Botón central · Ctrl + arrastrar"],
      ["Desplazar (sin selección)", "Arrastrar en vacío"], ["Selección múltiple", "Ctrl + clic"],
      ["Selección por área (con selección activa)", "Arrastrar en vacío"],
      ["Mover pieza", "Arrastrar · o clic sobre la ya seleccionada"],
      ["Volver al 100 % y centrar", "Clic en el % de zoom"],
    ]],
  ];
  function showShortcuts() {
    const rows = SHORTCUTS.map(([g, list]) => `<tr><td colspan="2" class="shortcut-group">${g}</td></tr>` +
      list.map(([l, k]) => `<tr><td>${l}</td><td>${k.split(" · ").map((x) => x.split(" + ").map((y) => /^[A-Z][a-z]+$|^Ctrl|^Supr|^Esc|^Rueda/.test(y) ? `<kbd>${y}</kbd>` : y).join(" + ")).join(" · ")}</td></tr>`).join("")).join("");
    openModal("Atajos de teclado", `<table class="shortcut-table">${rows}</table>`);
  }

  function inField(e) { const t = e.target; return t && (t.tagName === "INPUT" || t.tagName === "SELECT" || t.tagName === "TEXTAREA" || t.isContentEditable); }
  document.addEventListener("keydown", (e) => {
    const k = e.key.toLowerCase();
    const overlayOpen = (id) => { const o = document.getElementById(id); return o && !o.hidden; };
    if (overlayOpen("cad") || overlayOpen("img-viewer") || overlayOpen("tour")) return; // they own the keyboard
    if (!$("#modal-backdrop").hidden) { if (k === "escape") closeModal(); return; }
    if (k === "escape") { window.NT.closeMenus(); }
    // Ctrl+S is global (File → Save), like QAction shortcut in app.py
    if (e.ctrlKey && k === "s") { e.preventDefault(); saveAll(); return; }
    if (e.key === "?" && !inField(e)) { showShortcuts(); return; }
    // The rest are scoped to the Nesting tab (WidgetWithChildrenShortcut)
    if (document.body.dataset.view !== "nesting" || inField(e)) return;
    const map = { z: N.undo, y: N.redo, q: () => N.cycleOrientation(-1), e: () => N.cycleOrientation(1),
      h: () => N.flip("fh"), a: () => N.flip("fv") };
    if (e.ctrlKey && map[k]) { e.preventDefault(); map[k](); return; }
    if (e.key === "Delete") { e.preventDefault(); N.deleteSelected(); return; }
    if (k === "escape") { N.escape(); }
  });
  function saveAll() { if (document.body.dataset.view === "nesting") N.save(); else toast("Trabajo guardado"); setDirty(false); }

  // ── nesting panels ──────────────────────────────────────────────────────
  function renderPieces() {
    const list = $("#piece-list"); list.replaceChildren();
    const rem = S.cuts.reduce((s, c) => s + N.remaining(c), 0);
    $("#pieces-pending").textContent = `${rem} pendiente${rem === 1 ? "" : "s"}`;
    $("#pieces-pending").className = "chip " + (rem ? "warn" : "success");
    const vis = S.cuts.filter((c) => S.filter === "all" || (S.filter === "complete" ? N.remaining(c) === 0 : N.remaining(c) > 0));
    if (!vis.length) { list.innerHTML = `<div class="empty-hint">Selecciona una pieza de la lista y haz clic en la barra</div>`; return; }
    vis.forEach((c) => {
      const r = N.remaining(c), placed = c.qty - r;
      const row = document.createElement("div");
      row.className = "row" + (r === 0 ? " done" : "") + (S.floating && S.floating.cut === c ? " active" : "");
      row.tabIndex = 0;
      row.title = r ? "Clic: coger una pieza y colocarla en una barra" : "Clic: resaltar todas sus instancias";
      row.innerHTML = `<span class="swatch" style="background:${c.color}"></span>
        <div class="row-main"><span class="row-title">${c.name}</span><span class="row-sub">${c.len} mm${c.aL || c.aR ? ` · ∠${c.aL}/${c.aR}°` : ""}</span></div>
        <div class="row-trail"><span class="progress"><i style="width:${placed / c.qty * 100}%"></i></span><span class="mono">${placed}/${c.qty}</span></div>
        <button class="btn icon-only more" title="Más acciones" data-menu>${ICON("more", "sm")}</button>`;
      row.addEventListener("click", (e) => {
        if (e.target.closest(".more")) { const b = e.target.closest(".more").getBoundingClientRect(); openMenu(sidebarMenu(c), b.left, b.bottom + 4); return; }
        r ? N.startFloating(c) : N.highlight(c);
      });
      row.addEventListener("contextmenu", (e) => { e.preventDefault(); openMenu(sidebarMenu(c), e.clientX, e.clientY); });
      list.appendChild(row);
    });
  }

  function renderBars() {
    const list = $("#bar-list"); list.replaceChildren();
    const bars = S.bars.filter((b) => b.pieces.length || b.manual);
    $("#bars-count").textContent = bars.length;
    bars.forEach((b, i) => {
      const used = b.pieces.reduce((s, p) => s + p.cut.len, 0);
      const it = document.createElement("div");
      it.className = "bar-item" + (S.filteredBar === b.id ? " filtered" : "");
      const exp = S.expandedBars.has(b.id);
      const segs = b.pieces.slice().sort((p, q) => p.x - q.x).map((p) => `<i style="width:${p.cut.len / b.len * 100}%;background:${p.cut.color}"></i>`).join("");
      it.innerHTML = `<div class="bar-item-head">
          <button class="btn icon-only" data-exp title="${exp ? "Contraer" : "Expandir"}">${ICON(exp ? "chevron-down" : "chevron-right", "sm")}</button>
          <span class="name">Barra ${i + 1} <span style="color:var(--text-dim);font-weight:400">(${b.pieces.length})</span></span>
          <span class="eff">${(used / b.len * 100).toFixed(1)}%</span>
          <button class="btn icon-only" data-up title="Subir barra" ${i === 0 ? "disabled" : ""}>${ICON("arrow-up", "sm")}</button>
          <button class="btn icon-only" data-down title="Bajar barra" ${i === bars.length - 1 ? "disabled" : ""}>${ICON("arrow-down", "sm")}</button>
        </div><div class="mini-bar">${segs}</div>`;
      if (exp) {
        const counts = new Map(); b.pieces.forEach((p) => counts.set(p.cut, (counts.get(p.cut) || 0) + 1));
        const lg = document.createElement("div"); lg.className = "legend";
        counts.forEach((n, c) => { const d = document.createElement("div");
          d.innerHTML = `<span class="swatch" style="background:${c.color}"></span>${c.name} ×${n}`;
          d.addEventListener("click", (e) => { e.stopPropagation(); N.highlight(c, b.id); }); lg.appendChild(d); });
        it.appendChild(lg);
      }
      it.addEventListener("click", (e) => {
        if (e.target.closest("[data-exp]")) { N.toggleBarExpanded(b.id); return; }
        if (e.target.closest("[data-up]")) { N.moveBar(b.id, -1); return; }
        if (e.target.closest("[data-down]")) { N.moveBar(b.id, 1); return; }
        N.filterBar(b.id);
      });
      list.appendChild(it);
    });
  }

  function renderRemnants() {
    const list = $("#rem-list"); list.replaceChildren();
    if (S.remnantsBlocked) { list.innerHTML = `<div class="empty-hint" style="padding:12px;color:var(--warning)">Solo se pueden generar retales si se ha usado stock.</div>`; $("#rem-apply").disabled = true; return; }
    if (!S.remnants.length) { list.innerHTML = `<div class="empty-hint" style="padding:12px">Pulsa ↻ para calcular los retales ≥ ${S.remMin} mm</div>`; $("#rem-apply").disabled = true; return; }
    S.remnants.forEach((r) => {
      const n = S.bars.findIndex((b) => b.id === r.bar) + 1;
      const row = document.createElement("div"); row.className = "row";
      row.innerHTML = `<span class="swatch" style="background:var(--remnant)"></span><div class="row-main"><span class="row-title">Retal barra ${n}</span><span class="row-sub">${Math.round(r.w)} mm · desde x=${Math.round(r.x)}</span></div>`;
      list.appendChild(row);
    });
    $("#rem-apply").disabled = !S.useStock;
  }

  function renderSelection() {
    const sel = S.sel; const bar = $("#selection-bar"); const sec = $("#sel-section");
    bar.hidden = !sel.length; sec.hidden = !sel.length;
    if (!sel.length) return;
    const p = sel[0]; const b = S.bars.find((x) => x.pieces.includes(p));
    $("#sel-count").innerHTML = sel.length > 1 ? `${sel.length} piezas seleccionadas`
      : `<span class="swatch" style="background:${p.cut.color}"></span>${p.cut.name} · ${p.cut.len} mm`;
    $("#sel-chip").textContent = sel.length > 1 ? `${sel.length} piezas` : p.cut.name;
    $("#sel-bar").value = b ? S.bars.indexOf(b) + 1 : "—";
    $("#sel-x").value = sel.length > 1 ? "Mixto" : p.x.toFixed(1);
    $("#sel-len").value = sel.length > 1 ? "Mixto" : p.cut.len;
    $("#sel-ang").value = sel.length > 1 ? "Mixto" : `${p.cut.aL}° / ${p.cut.aR}°${p.fh ? " · ⇄" : ""}${p.fv ? " · ⇕" : ""}`;
  }

  function renderStatus() {
    const bars = S.bars.filter((b) => b.pieces.length).length;
    const total = S.cuts.reduce((s, c) => s + c.qty, 0);
    const placed = S.cuts.reduce((s, c) => s + (c.qty - N.remaining(c)), 0);
    const eff = N.efficiency();
    const waste = S.bars.filter((b) => b.pieces.length).reduce((s, b) => s + b.len - b.pieces.reduce((t, p) => t + p.cut.len, 0), 0) / 1000;
    const engine = S.advanced ? $("#strategy").selectedOptions[0].textContent : S.calcSystem.toUpperCase();
    $("#status-main").textContent = `${engine} · ${bars} barras · ${placed}/${total} colocadas · ${eff.toFixed(1)}%`;
    $("#st-bars").textContent = bars; $("#st-placed").textContent = `${placed}/${total}`; $("#st-waste").textContent = waste.toFixed(2);
    $("#eff-chip").textContent = eff.toFixed(1) + "%";
    $("#eff-chip").className = "chip " + (eff >= 80 ? "success" : eff >= 60 ? "warn" : "");
  }

  function renderAll() { renderPieces(); renderBars(); renderRemnants(); renderSelection(); renderStatus(); }
  document.addEventListener("nest:changed", renderAll);
  document.addEventListener("nest:zoom", (e) => { $("#zoom-btn").textContent = e.detail + "%"; });
  document.addEventListener("nest:flash", (e) => toast(e.detail));
  document.addEventListener("nest:dirty", (e) => setDirty(e.detail));
  document.addEventListener("nest:confirm", (e) => confirmDialog(e.detail));
  document.addEventListener("nest:piece-menu", (e) => openMenu(pieceMenu(e.detail.piece), e.detail.x, e.detail.y));
  document.addEventListener("nest:cursor", (e) => { $("#status-cursor").textContent = `X ${Math.round(e.detail.x)}  Y ${Math.round(e.detail.y)} mm`; });
  document.addEventListener("nest:floating", (e) => {
    const h = $("#float-hint");
    if (e.detail) { const c = e.detail.cut; h.innerHTML = `Colocando <b>${c.name} ${c.len} mm</b> · quedan ${N.remaining(c)} · <kbd>Ctrl+Q</kbd>/<kbd>Ctrl+E</kbd> rotar · <kbd>Esc</kbd> soltar`; h.hidden = false; }
    else h.hidden = true;
  });
  document.addEventListener("nest:running", (e) => {
    $("#nest-progress").hidden = false; $("#nest-pct").textContent = e.detail.pct + "%"; $("#nest-pct-bar").style.width = e.detail.pct + "%";
    const b = $("#auto-nest-btn"); b.classList.add("danger", "solid"); b.classList.remove("primary");
    b.innerHTML = `${ICON("stop", "sm")}Detener`;
  });
  document.addEventListener("nest:done", (e) => {
    $("#nest-progress").hidden = true;
    const b = $("#auto-nest-btn"); b.classList.remove("danger", "solid"); b.classList.add("primary");
    b.innerHTML = `${ICON("gear", "sm")}Auto-anidar`;
    toast(e.detail && e.detail.cancelled ? "Auto-anidado detenido" : "Auto-anidado completado");
  });

  function setDirty(on) { $("#dirty-dot").hidden = !on; }

  // ── action routing (data-act) ───────────────────────────────────────────
  const ACTIONS = {
    "save-nesting": () => N.save(), "clear-nesting": () => N.clearNesting(), undo: N.undo, redo: N.redo,
    "rotate-left": () => N.cycleOrientation(-1), "rotate-right": () => N.cycleOrientation(1),
    "flip-h": () => N.flip("fh"), "flip-v": () => N.flip("fv"),
    "delete-from-bar": () => N.deleteSelected(), "remove-permanently": () => N.removePermanently(), escape: () => N.escape(),
    "add-bar": () => (S.useStock && !S.autoStock ? dialog("stock-bar-picker") : N.addBar()),
    "open-remnants": () => selectPTab("remnants"),
    "show-all-bars": () => N.showAll(),
    "rem-refresh": () => N.refreshRemnants(), "rem-clear": () => N.clearRemnants(),
    "rem-apply": () => {
      if (!S.useStock) return alertBox({ title: "Generar Retales", msg: "Solo se pueden generar retales si se ha usado stock." });
      if (!S.remnants.length) return alertBox({ title: "Generar Retales", msg: "No hay retales que cumplan el largo minimo." });
      toast("Retales guardados en stock.");
    },
    "rem-delete-all": () => confirmDialog({ title: "Borrar todos los retales", text: "¿Borrar todos los retales de este material del stock?", ok: () => { const n = S.remnants.length; N.clearRemnants(); toast(`${n} retales borrados del stock.`); } }),
    "change-values": () => S.sel[0] && changeValues(S.sel[0].cut),
    "edit-drawing": () => dialog("profile-creator"),
    "sel-material": () => dialog("material-search"),
    "clear-stock": () => { $("#sw-stock").checked = false; $("#sw-stock").dispatchEvent(new Event("change")); },
    "subtab-add": () => toast("Nueva sub-pestaña de material"),
    "auto-nest": () => N.toggleNest(),
    "fit": () => N.fit(),
    "zoom-in": () => N.zoomBy(1), "zoom-out": () => N.zoomBy(-1),
    "shortcuts": showShortcuts,
    "catalog": () => showCatalog(),
    "backup-restore": () => confirmDialog({ title: "Copias de seguridad de la base de datos", text: "¿Restaurar esta copia? La app deberá reiniciarse.", danger: false,
      ok: () => alertBox({ title: "Copias de seguridad de la base de datos", msg: "Copia restaurada. Reinicia NesTube." }) }),
  };
  window.NT.ACTIONS = ACTIONS;
  document.addEventListener("click", (e) => {
    const a = e.target.closest("[data-act]"); if (a && ACTIONS[a.dataset.act]) { ACTIONS[a.dataset.act](a); return; }
    const d = e.target.closest("[data-dialog]"); if (d) { dialog(d.dataset.dialog); return; }
    const vi = e.target.closest("[data-viewimg]");
    if (vi && window.NT_PROFILES) { const P = window.NT_PROFILES, all = P.PROFILES; window.NT_VIEWER.open(P.viewerItems(all), all.findIndex((p) => p[0] === vi.dataset.viewimg)); return; }
    if (e.target.closest("[data-close]") || e.target.id === "modal-backdrop") closeModal();
  });

  function selectPTab(name) {
    $$("[data-ptab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.ptab === name)));
    $$("[data-ppanel]").forEach((p) => { p.hidden = p.dataset.ppanel !== name; });
  }

  // ── controls ────────────────────────────────────────────────────────────
  function bindControls() {
    $$(".workspace-tabs [data-view]").forEach((b) => b.addEventListener("click", () => showView(b.dataset.view)));
    $("#sw-stock").addEventListener("change", () => { if (S.remnantsBlocked && S.useStock) { S.remnantsBlocked = false; renderRemnants(); } });
    $$("[data-ptab]").forEach((b) => b.addEventListener("click", () => selectPTab(b.dataset.ptab)));
    $$("#piece-filter [data-filter]").forEach((b) => b.addEventListener("click", () => {
      $$("#piece-filter button").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); S.filter = b.dataset.filter; renderPieces(); }));
    $$("#nest-pages .page-row").forEach((r) => r.addEventListener("click", () => {
      $$("#nest-pages .page-row").forEach((x) => x.classList.toggle("active", x === r));
      const name = r.querySelector(".row-title").textContent; $("#doc-material").textContent = name; $("#sel-material").value = name;
    }));
    $$("#mode-seg [data-mode]").forEach((b) => b.addEventListener("click", () => {
      $$("#mode-seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      S.advanced = b.dataset.mode === "advanced"; $("#adv-controls").hidden = !S.advanced; $("#simple-controls").hidden = S.advanced; renderStatus(); }));
    $("#strategy").addEventListener("change", renderStatus);
    $("#calc-system").addEventListener("change", (e) => { S.calcSystem = e.target.value; renderStatus(); });
    $("#auto-mode").addEventListener("change", (e) => { S.autoMode = e.target.value; });
    const num = (id, key) => $(id).addEventListener("change", (e) => { const v = parseFloat(e.target.value); if (!isNaN(v)) N.setParam(key, v); });
    num("#p-barlen", "barLen"); num("#p-height", "sectionH"); num("#p-kerf", "kerf"); num("#p-margin", "margin");
    num("#rem-min", "remMin"); num("#rem-margin", "remMargin");
    const syncToggle = (sw, btn, key) => {
      const set = (v) => { $(sw).checked = v; $(btn).setAttribute("aria-pressed", String(v)); N.setParam(key, v); };
      $(sw).addEventListener("change", (e) => set(e.target.checked));
      $(btn).addEventListener("click", () => set(!$(sw).checked));
    };
    syncToggle("#sw-snap", "#tb-snap", "snap"); syncToggle("#sw-common", "#tb-common", "commonCut");
    $("#sw-stock").addEventListener("change", (e) => {
      S.useStock = e.target.checked; $("#sw-autostock").disabled = !S.useStock; if (!S.useStock) $("#sw-autostock").checked = false;
      $("#stock-chip").hidden = !S.useStock; renderRemnants(); });
    $("#sw-autostock").addEventListener("change", (e) => { S.autoStock = e.target.checked; });

    $("#brand-btn").addEventListener("click", (e) => openMenuAt(e.currentTarget, MAIN_MENU()));
    $("#export-btn").addEventListener("click", (e) => openMenuAt(e.currentTarget, EXPORT_MENU(), "right"));
    $("#auto-nest-mode").addEventListener("click", (e) => openMenuAt(e.currentTarget, [
      { header: "Al auto-anidar" },
      { label: "Todo — recalcular desde cero", check: () => S.autoMode === "all", action: () => { S.autoMode = "all"; $("#auto-mode").value = "all"; } },
      { label: "Solo pendientes — conservar lo colocado", check: () => S.autoMode === "remaining", action: () => { S.autoMode = "remaining"; $("#auto-mode").value = "remaining"; } },
    ], "right"));
    $("#zoom-btn").addEventListener("click", (e) => openMenuAt(e.currentTarget, [
      { label: "Acercar", action: () => N.zoomBy(1) }, { label: "Alejar", action: () => N.zoomBy(-1) },
      { label: "Ajustar a la vista (100 %)", action: () => N.fit() },
    ], "right"));
    $("#theme-btn").addEventListener("click", () => setTheme(currentTheme() === "dark" ? "light" : "dark"));
  }

  // ── boot ────────────────────────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    try { const t = localStorage.getItem("nt.theme"); if (t) document.documentElement.dataset.theme = t; } catch (e) { /* storage unavailable */ }
    $("#theme-btn").innerHTML = ICON(currentTheme() === "dark" ? "sun" : "moon");
    bindControls();
    N.init();
    if (window.NT_VIEWS) window.NT_VIEWS.init();
    let start = "nesting";
    try { start = localStorage.getItem("nt.view") || start; } catch (e) { /* storage unavailable */ }
    if (location.hash && document.getElementById("view-" + location.hash.slice(1))) start = location.hash.slice(1);
    showView(start);
  });
})();
