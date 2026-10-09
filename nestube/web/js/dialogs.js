/* ==========================================================================
   NesTube web UI — dialog layouts (MOCKUP)
   One entry per Qt dialog in nestube/ui_qt/dialogs/, with the same fields,
   buttons and labels. Opened through NT.dialog(id). In the functional stage
   each "ok" posts the form to the Python bridge.
   ========================================================================== */
(function () {
  "use strict";
  const I = (id, cls = "sm") => `<svg class="icon ${cls}"><use href="#i-${id}"/></svg>`;
  const fld = (label, val = "", { unit = "", pre = "", num = false, ph = "", id = "", ro = false } = {}) =>
    `<div class="field"><label${id ? ` for="${id}"` : ""}>${label}</label><div class="input">${pre ? `<span class="pre">${pre}</span>` : ""}<input${id ? ` id="${id}"` : ""} class="${num ? "num" : ""}" value="${val}" placeholder="${ph}"${ro ? " readonly" : ""}>${unit ? `<span class="unit">${unit}</span>` : ""}</div></div>`;
  const sel = (label, opts, id = "") => `<div class="field"><label${id ? ` for="${id}"` : ""}>${label}</label><select class="select"${id ? ` id="${id}"` : ""}>${opts.map((o) => `<option>${o}</option>`).join("")}</select></div>`;
  const sw = (label, hint, on = false) => `<div class="switch-row"><span class="lbl"><span>${label}</span>${hint ? `<span class="hint">${hint}</span>` : ""}</span><label class="switch"><input type="checkbox"${on ? " checked" : ""} aria-label="${label}"><span class="track"></span></label></div>`;
  const hint = (t) => `<p style="margin:0;font-size:var(--fs-sm);color:var(--text-sec)">${t}</p>`;
  const grid = (...f) => `<div class="field-grid">${f.join("")}</div>`;
  const table = (cols, rows) => `<div style="overflow:auto;max-height:240px"><table class="table"><thead><tr>${cols.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  const foot = (...btns) => btns.join("");
  const B = { cancel: `<button class="btn outline" data-close>Cancelar</button>`, close: `<button class="btn outline" data-close>Cerrar</button>` };
  const pri = (l, done = "") => `<button class="btn primary" data-close${done ? ` data-toast="${done}"` : ""}>${l}</button>`;

  const TOOLS = [["cursor", "Seleccionar"], ["line", "Línea"], ["polygon", "Polígono"], ["rect", "Rectángulo"], ["circle", "Círculo"],
    ["arc3", "Arco 3pt"], ["arccse", "Arco CSE"], ["arc3", "Arco exacto"], ["x", "Borrar"], ["void", "Marcar vano"], ["trim", "Recortar"], ["extend", "Extender"]];

  window.NT_DIALOGS = {
    // ── File ──────────────────────────────────────────────────────────────
    open: { title: "Abrir trabajo", ok: "Abrir", body: hint("Abre un trabajo guardado en la base de datos local o un archivo <span class='mono'>.nestjob</span> exportado.") +
      `<div class="search">${I("search", "")}<input placeholder="Buscar trabajos…"></div>` +
      table(["Nombre", "Cliente", "Fecha"], [["JOB-260629-0001", "Cliente Demo SL", "29/06/2026"], ["JOB-260702-0002", "Talleres Arrieta", "02/07/2026"], ["JOB-260715-0003", "Carpintería Metálica Sur", "15/07/2026"]]) +
      `<button class="btn outline">${I("folder")}Abrir archivo .nestjob…</button>` },
    "save-as": { title: "Guardar como", ok: "Guardar", body: fld("Nombre", "JOB-260629-0001", { ro: true }) + fld("Descripción", "Estructura nave A") + sw("Exportar también como .nestjob", "Archivo para compartir un único trabajo") },
    "open-config": { title: "Cargar configuración del programa", ok: "Cargar", body: hint("Carga un archivo de configuración (.json) guardado con «Guardar configuración del programa». Sustituye las preferencias actuales.") + `<button class="btn outline">${I("folder")}Elegir archivo…</button>` },
    backups: { title: "Copias de seguridad de la base de datos", wide: true, body: hint("Se crea una copia automáticamente cada vez que se abre la app.") +
      table(["Copia", "Fecha", "Tamaño"], [["nestube_geometry_20261009_0812.db", "09/10/2026 08:12", "1,4 MB"], ["nestube_geometry_20261008_0905.db", "08/10/2026 09:05", "1,4 MB"], ["nestube_geometry_20261007_0758.db", "07/10/2026 07:58", "1,3 MB"]]),
      foot: foot(`<button class="btn outline">Crear copia ahora</button>`, `<button class="btn outline">Restaurar desde archivo…</button>`, B.close, pri("Restaurar seleccionada")) },
    db: { title: "Gestión de base de datos", body: hint("Configura dónde reside la base de datos (p. ej. una ruta de servidor compartida).") +
      `<div class="field"><label>Base de datos</label><div style="display:flex;gap:6px"><div class="input" style="flex:1"><input class="num" value="C:\\NesTube\\nestube_geometry.db" readonly></div><button class="btn outline">Examinar…</button></div></div>` +
      `<div class="field"><label>Carpeta de copias</label><div style="display:flex;gap:6px"><div class="input" style="flex:1"><input class="num" value="C:\\NesTube\\backups" readonly></div><button class="btn outline">Examinar…</button></div></div>` +
      grid(sel("Frecuencia de copia", ["Al abrir la app", "Diaria", "Semanal", "Nunca"]), fld("Última copia", "09/10/2026 08:12", { ro: true })) +
      `<div style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn outline">Cambiar ubicación…</button><button class="btn outline">Cargar base de datos…</button><button class="btn outline">Crear copia ahora</button><button class="btn outline" data-dialog="backups">Gestionar copias…</button></div>`,
      foot: B.close },

    // ── Settings ──────────────────────────────────────────────────────────
    "material-add": { title: "Añadir material", ok: "Guardar", body: grid(fld("Nombre del material", "", { ph: "Acero al Carbono" }), fld("Calidad", "", { ph: "S235" })) + fld("Peso específico", "7.85", { unit: "t/m³", num: true }) },
    materials: { title: "Gestionar materiales", wide: true, body: `<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div style="display:grid;gap:8px;align-content:start"><div class="search">${I("search", "")}<input placeholder="Buscar perfil, material o calidad…"></div>
        ${table(["Material", "Calidad", "t/m³"], [["Acero al Carbono", "S235", "7.85"], ["Acero al Carbono", "S275", "7.85"], ["Acero Galvanizado", "DX51D", "7.85"], ["Aluminio", "6063-T5", "2.70"], ["Inoxidable", "AISI 304", "7.93"]])}
        <div style="display:flex;gap:6px"><button class="btn outline">Nueva</button><button class="btn danger">Eliminar</button></div></div>
        <div style="display:grid;gap:10px;align-content:start">${hint("Completa los campos y pulsa Guardar. Selecciona un material de la lista para editarlo.")}${fld("Nombre del material", "Acero al Carbono")}${fld("Calidad", "S235")}${fld("Peso específico", "7.85", { unit: "t/m³", num: true })}</div></div>`,
      foot: foot(B.close, pri("Guardar", "Material guardado.")) },
    "profile-manager": { title: "Gestionar perfiles", wide: true, body: `<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div style="display:grid;gap:8px;align-content:start"><div class="search">${I("search", "")}<input placeholder="Buscar perfil, material o calidad…"></div>
        ${table(["Perfil", "Material"], [["Perfil Ranurado 40x80", "Aluminio"], ["Tubo □ 40×40×2", "Inoxidable"], ["U-50x50x40x3", "Acero al Carbono"]])}
        <div style="display:flex;gap:6px"><button class="btn outline" data-dialog="profile-creator">Módulo de dibujo</button><button class="btn danger">Eliminar</button></div></div>
        <div style="display:grid;gap:10px;align-content:start">${fld("Nombre", "Perfil Ranurado 40x80")}${grid(fld("Material", "Aluminio"), fld("Calidad", "6063-T5"))}${fld("Peso específico", "2.70", { unit: "t/m³", num: true })}
        <div class="section-head"><span class="section-title">Dimensiones</span><button class="btn outline" style="height:24px">Editar campos</button></div>${grid(fld("h", "80", { unit: "mm", num: true }), fld("b", "40", { unit: "mm", num: true }))}
        <button class="btn outline">Asignar imagen</button></div></div>`, foot: foot(B.close, pri("Guardar")) },
    "profile-creator": { title: "Módulo de dibujo · Editor de perfil", wide: "xl", body: `<div style="display:grid;grid-template-columns:150px 1fr 200px;gap:12px;min-height:380px">
        <div style="display:grid;gap:8px;align-content:start"><span class="eyebrow">Herramientas</span><div class="tool-rail" style="grid-template-columns:repeat(2,1fr)">
          ${TOOLS.map(([ic, l], i) => `<button class="btn${i === 1 ? " outline" : ""}" aria-pressed="${i === 1}" title="${l}">${I(ic, "")}<span>${l}</span></button>`).join("")}</div>
          <button class="btn outline" aria-pressed="false">${I("ortho")}Ortogonal</button>
          <div style="display:flex;gap:4px"><button class="btn icon-only outline" title="Deshacer (Ctrl+Z)">${I("undo")}</button><button class="btn icon-only outline" title="Rehacer (Ctrl+Y)">${I("redo")}</button></div></div>
        <div class="canvas-wrap" style="border-radius:8px;min-height:360px"><svg viewBox="0 0 300 260" style="position:absolute;inset:0;width:100%;height:100%"><path d="M70 40h160v22h-68v136h68v22H70v-22h68V62H70z" fill="color-mix(in srgb,var(--accent) 14%,transparent)" stroke="var(--accent)" stroke-width="1.5"/><text x="150" y="32" text-anchor="middle" class="dim-text">b = 100</text><text x="244" y="134" class="dim-text">h = 200</text></svg>
          <div class="hint-toast" style="bottom:12px">Clic para añadir puntos · <kbd>Enter</kbd> longitud · <kbd>Tab</kbd>/<kbd>&lt;</kbd> ángulo · Doble-clic o <kbd>Esc</kbd> para terminar</div></div>
        <div style="display:grid;gap:8px;align-content:start"><span class="eyebrow">Datos del perfil</span>${fld("Perfil/Material", "IPE 200")}${fld("Material", "Acero al Carbono")}${fld("Calidad", "S235")}
          ${grid(fld("Sección", "28.5", { unit: "cm²", num: true }), fld("Kg por metro", "22.4", { num: true }))}${grid(fld("Precio €/kg", "0.85", { num: true }), fld("Precio €/m", "", { num: true }))}
          <span class="eyebrow">Lados y espesores</span>${fld("Espesor", "5.6", { unit: "mm", num: true })}<button class="btn outline">Asignar espesor a la selección</button><button class="btn outline">Asignar dimensión</button></div></div>`,
      foot: foot(`<button class="btn outline">⭳ Importar DXF</button>`, `<button class="btn outline">⭱ Exportar DXF</button>`, `<button class="btn outline">⭱ Exportar PNG</button>`, `<button class="btn outline">Importar imagen</button>`, `<span style="flex:1"></span>`, `<button class="btn outline">Limpiar</button>`, `<button class="btn outline">⮕ Generar perfil (dibujo actual)</button>`, pri("Guardar")) },
    "pdf-font": { title: "Fuente PDF", ok: "Guardar", body: sel("Fuente", ["IBM Plex Sans", "DejaVu Sans", "DejaVu Sans Mono"]) + hint("Fuentes Unicode incluidas con la app; se usan en todos los PDF exportados.") },
    "pdf-template": { title: "Plantilla PDF base", ok: "Guardar", body: hint("Plantilla base usada por los PDF de anidado y de presupuesto.") +
      `<div class="field"><label>Plantilla FastReport</label><div style="display:flex;gap:6px"><div class="input" style="flex:1"><input placeholder="Sin plantilla FastReport configurada." readonly></div><button class="btn outline">Examinar…</button></div></div><div style="display:flex;gap:6px"><button class="btn outline">Abrir en FastReport</button><button class="btn outline">Descargar FastReport</button></div>` },
    "pdf-templates": { title: "Editar plantillas", wide: true, body: `<div class="sub-tabs" style="padding:0;border:0"><button aria-selected="true">Nesting PDF</button><button aria-selected="false">Presupuesto / Cortes PDF</button></div>` +
      hint("Haz clic en un campo para añadirlo a la plantilla. Arrastra para posicionarlo.") +
      `<div style="display:grid;grid-template-columns:180px 1fr;gap:12px"><div class="list">${["Nº Pedido", "Oferta", "Cliente", "Material", "Fecha", "Logo", "Total pedido"].map((f) => `<div class="row">${I("plus")}<span class="row-title">${f}</span></div>`).join("")}</div>
      <div style="aspect-ratio:1.414;background:#fff;border:1px solid var(--border);border-radius:4px;position:relative;max-width:100%"><span class="chip" style="position:absolute;left:8%;top:8%">Cliente</span><span class="chip" style="position:absolute;right:8%;top:8%">Nº Pedido</span><span class="chip accent" style="position:absolute;left:8%;top:20%">Material</span></div></div>`,
      foot: foot(`<button class="btn outline">Añadir campo</button>`, `<button class="btn danger">Quitar campo</button>`, B.close, pri("Guardar plantilla", "Plantilla guardada correctamente.")) },
    "cost-defaults": { title: "Valores de coste por defecto", ok: "Guardar", done: "Valores de coste por defecto guardados.", body: hint("Valores de coste no específicos de un perfil que se aplican a cada job nuevo.") +
      grid(fld("Coste operario", "30.00", { unit: "/h", num: true }), fld("Tiempo corte recto", "3.00", { unit: "min", num: true }), fld("Extra inglete", "35.0", { unit: "%", num: true }), fld("Margen de beneficio", "15.0", { unit: "%", num: true })) },
    "opt-times": { title: "Tiempos de optimización (1–6)", ok: "Guardar", done: "Tiempos de optimización guardados.", body: hint("Tiempo máximo de búsqueda del auto-anidado avanzado para cada nivel.") +
      grid(...[1, 5, 10, 20, 30].map((s, i) => fld(`Nivel ${i + 1} (s)`, s, { num: true }))) + fld("Nivel 6", "∞ (sin límite)", { ro: true }) },
    "nesting-layout": { title: "Disposición del anidado", ok: "Guardar", body: grid(sel("Panel piezas", ["Izquierda", "Derecha"]), sel("Panel barras", ["Derecha", "Izquierda"])) +
      hint("Si ambos paneles están al mismo lado, se apilan en vertical.") + fld("Zona snap", "300", { unit: "mm", num: true }) + sw("Colores por corte en anidado", "", true) },
    naming: { title: "Asignación de nombres", ok: "Guardar", body: hint("Configura los prefijos usados en los nombres auto-generados de jobs y retales.") + grid(fld("Prefijo de trabajo", "JOB"), fld("Prefijo de retal", "R")) +
      `<p class="mono" style="margin:0;font-size:var(--fs-sm);color:var(--text-dim)">Ejemplo: JOB-260629-0001 · S235-000001-R1</p>` },
    about: { title: "Acerca de NesTube", body: `<div style="display:flex;gap:12px;align-items:center"><span class="brand-mark" style="width:44px;height:44px;font-size:22px;border-radius:10px">N</span><div><strong style="font-size:var(--fs-xl)">NesTube</strong><div class="mono" style="color:var(--text-sec)">Versión instalada: 1.0.0-pre-alpha.1</div></div></div>` +
      hint("NesTube optimiza el corte de barras, tubos y perfiles metálicos: algoritmos de empaquetado, anidado 2D con ingletes, costes y stock. Todo en local, sin cuentas ni nube.") + hint("Idiomas: inglés y español.") + `<span class="chip success">${I("check")}Tienes la última versión (1.0.0-pre-alpha.1)</span>` + sw("No mostrar de nuevo", ""),
      foot: foot(`<button class="btn outline">Buscar actualización</button>`, B.close) },

    // ── Nesting / Cuts / Stock ────────────────────────────────────────────
    "nest-selector": { title: "Seleccionar anidados para exportar", body: hint("Elige qué anidados de material incluir en el archivo exportado.") +
      `<div class="list">${["IPE 200 · S235 — 6 barras", "HEA 140 · S275 — 2 barras", "Tubo □ 40×40×2 · Inox — sin anidado"].map((n, i) => `<label class="row" style="cursor:pointer"><input type="checkbox"${i < 2 ? " checked" : ""}${i === 2 ? " disabled" : ""} style="accent-color:var(--accent)"><span class="row-title"${i === 2 ? ' style="color:var(--text-dim)"' : ""}>${n}</span></label>`).join("")}</div>
      <div style="display:flex;gap:6px"><button class="btn outline">Seleccionar todos</button><button class="btn outline">Deseleccionar todos</button></div>`, foot: foot(B.cancel, pri("Exportar seleccionados")) },
    "material-search": { title: "Buscar perfiles y tubos", wide: true, body: `<div class="segmented" style="width:360px;max-width:100%"><button aria-pressed="true">Perfiles y Tubos</button><button aria-pressed="false">Material</button><button aria-pressed="false">Stock</button></div>
      <div style="display:grid;grid-template-columns:1fr 160px;gap:8px"><div class="search">${I("search", "")}<input placeholder="Buscar perfil, material o calidad…"></div>${fld("Largo mín.", "", { unit: "mm", num: true })}</div>` +
      table(["Perfil", "Material", "Calidad", "kg/m"], [["IPE 200", "Acero al Carbono", "S235", "22.4"], ["HEA 140", "Acero al Carbono", "S275", "24.7"], ["Tubo □ 40×40×2", "Inoxidable", "AISI 304", "2.35"]]),
      foot: foot(B.cancel, pri("Seleccionar")) },
    "stock-bar-picker": { title: "Seleccionar barra de stock", wide: true, body: hint("Elige una barra para añadir al layout de anidado. Los retales muestran su largo real.") +
      `<div style="display:flex;gap:8px;align-items:center"><div class="search" style="flex:1">${I("search", "")}<input placeholder="Buscar perfil, material o calidad…"></div><label style="display:flex;gap:6px;align-items:center;font-size:var(--fs-md)"><input type="checkbox" checked style="accent-color:var(--accent)">Ver retales</label></div>` +
      table(["Referencia", "Perfil", "Material", "Calidad", "Longitud", "Cantidad", "Retal", "Bloq."], [["S235-000001-00", "IPE 200", "Acero al Carbono", "S235", "6000", "1", "", ""], ["S235-000001-R1", "IPE 200", "Acero al Carbono", "S235", "1182", "1", "Sí", ""], ["S235-000002-00", "IPE 200", "Acero al Carbono", "S235", "6000", "1", "", "🔒"]]) +
      `<div class="mini-bar" style="height:14px"><i style="width:100%;background:var(--bg-mid)"></i></div>`,
      foot: foot(`<button class="btn outline">Añadir cant.</button>`, `<button class="btn outline">Borrar cant.</button>`, `<button class="btn outline">Crear nueva</button>`, `<button class="btn outline">Bloquear</button>`, `<span style="flex:1"></span>`, B.cancel, pri("OK")) },
    "stock-add": { title: "Añadir al stock", wide: true, done: "Stock guardado.", body: hint("Completa los campos del perfil/barra. Los campos de dimensiones dependen del tipo de perfil.") +
      grid(fld("Perfil/Material", "IPE 200"), sel("Tipo", ["Perfil H", "Redondo", "Rectangular", "Perfil L", "Perfil U"]), fld("Material", "Acero al Carbono"), fld("Calidad", "S235")) +
      `<span class="eyebrow">Dimensiones</span>` + grid(fld("Ala", "100", { unit: "mm", num: true }), fld("Alma", "200", { unit: "mm", num: true }), fld("Espesor de pared", "5.6", { unit: "mm", num: true }), fld("Largo", "6000", { unit: "mm", num: true }), fld("Cantidad", "1", { num: true })) +
      `<span class="eyebrow">Peso y precios</span>` + grid(fld("Kg por metro", "22.4", { num: true }), fld("Precio €/kg", "0.85", { num: true })) + sw("Disponible", "", true) + fld("Notas", ""), foot: foot(B.cancel, pri("Guardar", "Stock guardado.")) },
    "stock-fields": { title: "Editar campos", ok: "Guardar", body: hint("Elige qué columnas se muestran en la tabla de stock.") + ["Perfil/Material", "Calidad", "Largo", "Cantidad", "Disponible", "Retal", "Job de creación", "Usado en jobs"].map((c) => sw(c, "", true)).join("") },
    "job-new": { title: "Crear nuevo job", ok: "Crear", body: fld("Nombre", "JOB-261009-0005", { ro: true }) + hint("El nombre del job es el número generado automáticamente y no se puede modificar.") + fld("Descripción", "") + grid(fld("Cliente", ""), fld("Pedido", "")) + grid(fld("Longitud barra", "6000", { unit: "mm", num: true }), fld("Cantidad", "1", { num: true })) },
    "add-field": { title: "Añadir campo", ok: "Añadir", body: fld("Nombre del campo", "", { ph: "Proyecto, obra, plano…" }) + hint("Clic derecho sobre un campo personalizado para editarlo o eliminarlo.") },
    "cut-piece": { title: "Editar dibujo · pieza de corte", wide: true, body: `<div style="display:grid;grid-template-columns:1fr 220px;gap:12px"><div class="canvas-wrap" style="border-radius:8px;min-height:240px"><svg viewBox="0 0 400 120" style="position:absolute;inset:0;width:100%;height:100%"><polygon points="40,40 300,40 360,80 100,80" fill="#76B7B2" stroke="var(--bar-stroke)"/><text x="200" y="30" text-anchor="middle" class="dim-text">2800 mm</text></svg></div>
      <div style="display:grid;gap:8px;align-content:start">${fld("Largo", "2800", { unit: "mm", num: true })}${grid(fld("Inglete 1", "45", { unit: "°", num: true }), fld("Inglete 2", "45", { unit: "°", num: true }))}<div class="field"><label>Color</label><div class="input"><input type="color" value="#76B7B2" style="height:20px;padding:0"></div></div></div></div>`,
      foot: foot(`<button class="btn outline">Importar DXF</button>`, `<button class="btn outline">Exportar DXF</button>`, `<span style="flex:1"></span>`, B.cancel, `<button class="btn outline" data-close>Guardar como…</button>`, pri("Guardar")) },
    "profile-height": { title: "Seleccionar altura de corte", body: hint("Este perfil tiene varias caras. Elige la altura de corte (se recordará para este perfil).") +
      `<div class="segmented"><button aria-pressed="true">200 mm (alma)</button><button aria-pressed="false">100 mm (ala)</button></div>`, foot: foot(B.cancel, pri("Aceptar")) },
  };
})();
