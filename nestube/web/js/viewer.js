/* ==========================================================================
   NesTube web UI — profile image viewer (MOCKUP)
   Full-window viewer for profile thumbnails (Profiles/*.png). Opened from the
   Profiles inspector, the catalog grid, the Costs gallery, the profile manager
   and the drawing module's image panel.
   Keys: ← → previous/next · + − zoom · 0 fit · 1 = 100 % · B background · Esc close
   ========================================================================== */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const I = (id, cls = "sm") => `<svg class="icon ${cls}"><use href="#i-${id}"/></svg>`;
  let list = [], idx = 0, zoom = 1, fitZoom = 1, bg = "checker", onAssign = null;

  function el() {
    let v = $("#img-viewer");
    if (v) return v;
    v = document.createElement("div");
    v.id = "img-viewer"; v.className = "viewer"; v.hidden = true;
    v.setAttribute("role", "dialog"); v.setAttribute("aria-modal", "true"); v.setAttribute("aria-label", "Visor de imagen de perfil");
    v.innerHTML = `
      <div class="viewer-top">
        <div class="viewer-title"><strong id="vw-name"></strong><span id="vw-meta" class="mono"></span></div>
        <div class="viewer-tools">
          <button class="btn icon-only" data-vw="prev" title="Anterior (←)">${I("chevron-right", "")}</button>
          <span class="mono" id="vw-pos" style="min-width:48px;text-align:center;color:var(--text-sec)"></span>
          <button class="btn icon-only" data-vw="next" title="Siguiente (→)">${I("chevron-right", "")}</button>
          <span class="vsep"></span>
          <button class="btn icon-only" data-vw="out" title="Alejar (−)">${I("minus", "")}</button>
          <button class="btn zoom-pill" data-vw="fit" id="vw-zoom" title="Ajustar a la ventana (0)">100%</button>
          <button class="btn icon-only" data-vw="in" title="Acercar (+)">${I("plus", "")}</button>
          <button class="btn" data-vw="one" title="Tamaño real (1)">1:1</button>
          <span class="vsep"></span>
          <div class="segmented" style="width:210px" role="group" aria-label="Fondo">
            <button data-bg="checker" title="Fondo de transparencia (B)">Cuadros</button><button data-bg="light">Claro</button><button data-bg="dark">Oscuro</button>
          </div>
          <span class="vsep"></span>
          <button class="btn outline" data-vw="assign">${I("image")}Asignar imagen…</button>
          <button class="btn outline" data-vw="export">${I("export")}Exportar PNG</button>
          <button class="btn icon-only" data-vw="close" title="Cerrar (Esc)">${I("x", "")}</button>
        </div>
      </div>
      <div class="viewer-stage" id="vw-stage"><img id="vw-img" alt="" draggable="false"></div>
      <div class="viewer-strip" id="vw-strip"></div>`;
    document.body.appendChild(v);
    v.querySelector('[data-vw="prev"] svg').style.transform = "rotate(180deg)";
    v.addEventListener("click", (e) => {
      const b = e.target.closest("[data-vw]"); const g = e.target.closest("[data-bg]"); const t = e.target.closest("[data-thumb]");
      if (g) { bg = g.dataset.bg; paint(); return; }
      if (t) { idx = +t.dataset.thumb; load(); return; }
      if (!b) return;
      ({ prev: () => step(-1), next: () => step(1), in: () => setZoom(zoom * 1.25), out: () => setZoom(zoom / 1.25),
        fit: () => setZoom(fitZoom), one: () => setZoom(1), close, export: () => window.NT.toast(`${list[idx].name}.png exportado (transparente)`),
        assign: () => (onAssign ? onAssign(list[idx]) : window.NT.toast("Elige un PNG o JPEG para este perfil…")) })[b.dataset.vw]();
    });
    $("#vw-stage", v).addEventListener("wheel", (e) => { e.preventDefault(); setZoom(zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15)); }, { passive: false });
    document.addEventListener("keydown", (e) => {
      if (v.hidden) return;
      const k = e.key;
      if (k === "Escape") { e.stopPropagation(); close(); }
      else if (k === "ArrowRight") step(1); else if (k === "ArrowLeft") step(-1);
      else if (k === "+" || k === "=") setZoom(zoom * 1.25); else if (k === "-") setZoom(zoom / 1.25);
      else if (k === "0") setZoom(fitZoom); else if (k === "1") setZoom(1);
      else if (k.toLowerCase() === "b") { bg = { checker: "light", light: "dark", dark: "checker" }[bg]; paint(); }
      else return;
      e.preventDefault(); e.stopPropagation();
    }, true);
    return v;
  }

  function step(d) { if (list.length > 1) { idx = (idx + d + list.length) % list.length; load(); } }
  function setZoom(z) { zoom = Math.max(0.25, Math.min(16, z)); paint(); }
  function paint() {
    const v = el(), img = $("#vw-img", v), it = list[idx];
    img.style.width = (it.w || 128) * zoom + "px";
    $("#vw-zoom", v).textContent = Math.round(zoom * 100) + "%";
    $("#vw-stage", v).dataset.bg = bg;
    v.querySelectorAll("[data-bg]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.bg === bg)));
  }
  function load() {
    const v = el(), it = list[idx];
    $("#vw-img", v).src = it.src; $("#vw-img", v).alt = it.name;
    $("#vw-name", v).textContent = it.name;
    $("#vw-meta", v).textContent = `${it.file || it.name + ".png"} · ${it.w || 128}×${it.h || 128} px · PNG con transparencia${it.material ? " · " + it.material : ""}`;
    $("#vw-pos", v).textContent = `${idx + 1}/${list.length}`;
    const st = $("#vw-stage", v);
    fitZoom = Math.max(1, Math.min(4, Math.floor(Math.min((st.clientWidth || 800) - 80, (st.clientHeight || 500) - 80) / (it.w || 128) * 4) / 4));
    zoom = fitZoom;
    $("#vw-strip", v).innerHTML = list.map((x, i) => `<button class="vw-thumb${i === idx ? " active" : ""}" data-thumb="${i}" title="${x.name}"><img src="${x.src}" alt=""></button>`).join("");
    const a = $("#vw-strip .active", v); if (a) a.scrollIntoView({ block: "nearest", inline: "center" });
    paint();
  }
  function open(items, start = 0, opts = {}) {
    list = items.filter((x) => x && x.src); if (!list.length) return;
    idx = Math.max(0, Math.min(start, list.length - 1)); onAssign = opts.onAssign || null;
    const v = el(); v.hidden = false; requestAnimationFrame(load);
  }
  function close() { el().hidden = true; }

  window.NT_VIEWER = { open, close };
})();
