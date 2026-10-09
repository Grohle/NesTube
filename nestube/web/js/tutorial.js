/* ==========================================================================
   NesTube web UI — interactive tutorial (MOCKUP)
   Same 14 steps and texts as nestube/ui_qt/tutorial.py. Keys: → Enter Space
   next · ← back · Esc exit. A click anywhere also advances.
   ========================================================================== */
(function () {
  "use strict";
  const STEPS = [
    ["welcome", null, null, "Bienvenido a NesTube", "NesTube convierte tu lista de cortes en un plan de corte optimizado. Este tour de 1 minuto te enseña dónde está cada cosa. Usa las flechas del teclado o haz clic en cualquier parte para avanzar; Esc para salir."],
    ["tabs", null, ".workspace-tabs", "Las pestañas", "El flujo va de izquierda a derecha: Trabajos (abrir/guardar), Cortes (qué piezas necesitas), Anidado (cómo se distribuyen en las barras), Costes y Peso, Perfiles y Tubos, y Stock (inventario y retales)."],
    ["cuts_add", "cuts", '[data-act="add-cut"]', "Añade tus cortes", "Cada fila es una pieza: descripción, longitud, cantidad y, si la lleva, el inglete de cada extremo (dirección y ángulo). Pulsa este botón para añadir filas."],
    ["cuts_params", "cuts", "#c-barlen", "Parámetros de barra", "Longitud de la barra comercial, kerf (lo que se come el disco en cada corte) y margen. Estos valores se aplican a todo el cálculo."],
    ["cuts_calc", "cuts", '[data-act="calc-cuts"]', "Calcular", "Ejecuta el empaquetado con el algoritmo elegido en el desplegable (FFD, BFD o NFD) y muestra cuántas barras necesitas y su eficiencia. El resultado se ve en detalle en la pestaña Anidado."],
    ["nest_auto", "nesting", "#auto-nest-btn", "Auto-anidar", "Recalcula la distribución automáticamente. En modo Avanzado usa geometría real de ingletes (NFP): las piezas biseladas se encajan entre sí. Durante la búsqueda el botón muestra el progreso y permite detener conservando el mejor resultado."],
    ["nest_strategy", "nesting", "#strategy", "Estrategia", "Qué optimiza el anidado: Por longitud (compacto), Compactación NFP, Retales reutilizables (consolida el sobrante en un retal grande), Simetría (equilibra las barras) o Longitud total mínima."],
    ["nest_opt", "nesting", "#opt-level", "Tiempo de optimización", "Niveles 1–6: cuánto tiempo dedica la búsqueda a mejorar el resultado (1s a 30s, o ilimitado). Más tiempo = más combinaciones probadas. Los tiempos se configuran en Ajustes."],
    ["nest_manual", "nesting", "#nest-canvas", "Ajuste manual", "Arrastra una pieza para moverla: con Imán activado se encaja a ras de sus vecinas, y siempre puedes devolverla exactamente a su sitio. Botón derecho para opciones, y los botones de girar/voltear rotan la pieza (en el aire o ya colocada — nunca dejará piezas solapadas)."],
    ["costs", "costs", null, "Costes y Peso", "Con el perfil y el material configurados, calcula peso por pieza, coste de material, mano de obra y el total del trabajo. Exportable a PDF, Excel y Word."],
    ["profiles", "profiles", null, "Perfiles y Tubos", "Catálogo de perfiles comerciales (IPE, HEA, UPN, tubos…) con sus dimensiones y peso lineal, más tus perfiles personalizados. Seleccionar uno alimenta el cálculo de costes y la altura de sección del anidado."],
    ["stock", "stock", null, "Stock", "Inventario de barras y retales con trazabilidad. Activa \"Usar stock\" en Anidado para anidar sobre tus existencias reales y reaprovechar retales."],
    ["jobs_save", "jobs", '#view-jobs .content-head [data-act="job-new"]', "Trabajos", "Crea un trabajo nuevo aquí y guárdalo en cualquier momento con Ctrl+S. Todo queda en una base de datos local (SQLite) con copias de seguridad automáticas al arrancar."],
    ["done", null, null, "¡Listo!", "Eso es lo esencial. Puedes repetir este tour cuando quieras desde Ayuda → Tutorial interactivo. ¡A cortar!"],
  ];
  let i = 0, root = null;

  function build() {
    root = document.createElement("div"); root.id = "tour";
    root.innerHTML = `<div class="tour-mask"></div><div class="tour-hole"></div>
      <div class="tour-card" role="dialog" aria-modal="true" aria-labelledby="tour-h"><h3 id="tour-h"></h3><p id="tour-p"></p>
        <div class="tour-foot"><span class="step" id="tour-step"></span><button class="btn" data-t="skip">Saltar</button><button class="btn outline" data-t="back">Atrás</button><button class="btn primary" data-t="next">Siguiente</button></div></div>`;
    document.body.appendChild(root);
    root.addEventListener("click", (e) => {
      const b = e.target.closest("[data-t]");
      if (b) { ({ skip: finish, back: () => go(i - 1), next: () => go(i + 1) })[b.dataset.t](); return; }
      if (!e.target.closest(".tour-card")) go(i + 1);
    });
    document.addEventListener("keydown", (e) => {
      if (!root || root.hidden) return;
      if (e.key === "Escape") finish();
      else if (["ArrowRight", "Enter", " "].includes(e.key)) go(i + 1);
      else if (e.key === "ArrowLeft") go(i - 1);
      else return;
      e.preventDefault(); e.stopPropagation();
    }, true);
    window.addEventListener("resize", () => root && !root.hidden && place());
  }
  function go(n) {
    if (n >= STEPS.length) return finish();
    i = Math.max(0, n);
    const [, view] = STEPS[i];
    if (view && document.body.dataset.view !== view) window.NT.showView(view);
    requestAnimationFrame(() => requestAnimationFrame(place));
  }
  function place() {
    const [, , sel, title, body] = STEPS[i];
    root.querySelector("#tour-h").textContent = title;
    root.querySelector("#tour-p").textContent = body;
    root.querySelector("#tour-step").textContent = `Paso ${i + 1} de ${STEPS.length}`;
    root.querySelector('[data-t="next"]').textContent = i === STEPS.length - 1 ? "Terminar" : "Siguiente";
    root.querySelector('[data-t="back"]').disabled = i === 0;
    const hole = root.querySelector(".tour-hole"), card = root.querySelector(".tour-card");
    let t = sel && document.querySelector(sel);
    if (t && sel === "#c-barlen") t = t.closest(".section");
    if (t && (sel === "#strategy" || sel === "#opt-level")) t = t.closest(".field");
    const r = t && t.getBoundingClientRect();
    if (!r || !r.width) { hole.style.cssText = `left:50%;top:50%;width:0;height:0`; card.style.left = `calc(50% - ${card.offsetWidth / 2}px)`; card.style.top = `calc(50% - ${card.offsetHeight / 2}px)`; return; }
    const pad = 6;
    hole.style.cssText = `left:${r.left - pad}px;top:${r.top - pad}px;width:${r.width + pad * 2}px;height:${r.height + pad * 2}px`;
    const cw = card.offsetWidth, ch = card.offsetHeight;
    let left = r.left, top = r.bottom + 14;
    if (top + ch > innerHeight - 12) top = r.top - ch - 14;
    if (top < 12) { top = Math.min(innerHeight - ch - 12, Math.max(12, r.top)); left = r.right + 14; if (left + cw > innerWidth - 12) left = r.left - cw - 14; }
    card.style.left = Math.max(12, Math.min(left, innerWidth - cw - 12)) + "px"; card.style.top = Math.max(12, top) + "px";
  }
  function start() { if (!root) build(); root.hidden = false; go(0); }
  function finish() { if (root) root.hidden = true; }
  window.NT_TOUR = { start, finish };
})();
