/* ==========================================================================
   NesTube web UI — Nesting canvas, NATIVE mode (inside the desktop app)
   --------------------------------------------------------------------------
   Replaces the mockup canvas when the page runs in the app (window.NT_NATIVE).
   Every interaction is delegated to the real TabNesting through the bridge
   (nestube/ui_web/api_nesting.py): press / move / release are forwarded in
   scene millimetres and the canvas draws exactly the state the engine returns
   — real miter contours, NFP collision, snap, same-slot guarantee, flip guard.
   Only view concerns stay here: zoom, pan, filtering by bar, hover.
   ========================================================================== */
(function () {
  "use strict";
  if (!window.NT_NATIVE) return;

  const ZOOM_STEP = 1.15, ZOOM_MIN = 0.005, ZOOM_MAX = 40;
  const SVGNS = "http://www.w3.org/2000/svg";

  // Shape the app.js panels expect (same fields as the mockup's state).
  const S = {
    cuts: [], bars: [], sel: [], floating: null, remnants: [], filter: "all", filteredBar: null,
    expandedBars: new Set(), nesting: false, advanced: true, calcSystem: "ffd", autoMode: "all",
    useStock: false, autoStock: false, remMin: 500, remMargin: 0, sectionH: 200, snap: true,
    commonCut: false, params: {}, snap0: null, pct: 0, status: "", subtabs: null,
  };
  let snap = null;                 // last raw snapshot from Python
  let wrap, svg, world, overlay, rulerTop, rulerLeft;
  const view = { s: 0.12, tx: 40, ty: 60, fit: 0.12 };
  let fitted = false;

  // ── bridge plumbing: serial queue, moves coalesced ──────────────────────
  let chain = Promise.resolve(), pendingMove = null, moveBusy = false;
  function call(method, args) {
    const p = chain.then(() => window.NTB.call(method, args));
    chain = p.catch(() => {});
    return p.then(handle);
  }
  function handle(res) {
    if (!res) return null;
    (res.alerts || []).forEach((a) => {
      if (a.kind === "question") return;          // asked in the web UI beforehand
      if (a.kind === "information") window.NT.toast(a.msg || a.title);
      else window.NT.alert({ kind: a.kind, title: a.title, msg: a.msg });
    });
    if (!res.ok) { window.NT.alert({ kind: "critical", title: "Error", msg: res.error }); return null; }
    const r = res.result;
    if (r && r.bars && r.pieces) apply(r);
    else if (r && r.state && r.state.bars) apply(r.state);
    return r;
  }
  function sendMove(x, y) {
    pendingMove = { x, y };
    if (moveBusy) return;
    const loop = () => {
      if (!pendingMove) { moveBusy = false; return; }
      const m = pendingMove; pendingMove = null; moveBusy = true;
      call("nest.move", { x: m.x, y: m.y, zoom: view.s }).then(loop, loop);
    };
    loop();
  }

  // ── snapshot → app.js-compatible model ──────────────────────────────────
  function apply(s) {
    const wasNesting = S.nesting;
    snap = s;
    S.sectionH = s.sh; S.params = s.params; S.status = s.status; S.subtabs = s.subtabs;
    S.advanced = s.params.advanced; S.calcSystem = s.params.calc; S.autoMode = s.params.auto_mode;
    S.useStock = s.params.use_stock; S.autoStock = s.params.auto_stock; S.snap = s.params.snap;
    S.commonCut = s.params.common; S.nesting = s.auto_nesting; S.pct = s.pct;
    S.remMin = parseFloat(s.params.rem_min) || 0; S.remMargin = parseFloat(s.params.rem_margin) || 0;
    S.cuts = s.pieces.map((p) => ({ id: p.i, name: p.name, len: p.len, qty: p.total, placed: p.placed,
      remaining: p.remaining, aL: p.aL, aR: p.aR, color: p.color }));
    S.bars = s.bars.map((b) => ({ id: b.i, len: b.len, y: b.y, eff: b.eff, rem: b.rem, manual: true,
      pieces: b.pieces.map((p) => ({ k: p.k, cut: S.cuts[p.cut] || { name: p.name, len: p.len, color: p.color },
        x: p.x, fh: p.fh, fv: p.fv, poly: p.poly, sel: p.sel, hl: p.hl, bar: b.i })) }));
    S.sel = [].concat(...S.bars.map((b) => b.pieces.filter((p) => p.sel)));
    S.floating = s.floating ? { cut: S.cuts[s.floating.cut], fh: s.floating.fh, fv: s.floating.fv,
      from: s.floating.moving, ghost: s.floating.ghost, remaining: s.floating.remaining } : null;
    S.remnants = (s.remnants || []).map((r) => ({ bar: r.bar, x: r.x, w: r.w, name: r.name }));
    if (S.filteredBar != null && !S.bars.some((b) => b.id === S.filteredBar)) S.filteredBar = null;
    wrap.classList.toggle("floating", !!S.floating);
    renderWorld();
    emit("nest:changed");
    emit("nest:dirty", !!s.dirty);
    emit("nest:floating", S.floating ? { cut: S.floating.cut } : null);
    if (!fitted && S.bars.length) { fitted = true; fit(); }
    // The run ended (finished, cancelled, or the 1D packer that never runs
    // threaded): close the progress banner and restore the button.
    if (wasNesting && !S.nesting) emit("nest:done", {});
  }

  // ── rendering (real contours from the engine) ───────────────────────────
  function el(tag, attrs, parent) {
    const n = document.createElementNS(SVGNS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function textOn(hex) {
    const c = (hex || "#888888").replace("#", "");
    const ch = [0, 2, 4].map((i) => parseInt(c.substr(i, 2), 16) / 255)
      .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    const L = 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
    return (1.05 / (L + 0.05)) >= ((L + 0.05) / 0.062) ? "#FFFFFF" : "#1C1C1E";
  }
  const shown = () => S.bars.filter((b) => S.filteredBar == null || b.id === S.filteredBar);
  function renderWorld() {
    if (!world) return;
    world.replaceChildren();
    shown().forEach((bar) => {
      el("rect", { class: "bar-rect", x: 0, y: bar.y, width: bar.len, height: S.sectionH }, world);
      S.remnants.filter((r) => r.bar === bar.id).forEach((r) =>
        el("rect", { class: "remnant", x: r.x, y: bar.y, width: r.w, height: S.sectionH }, world));
      bar.pieces.forEach((p) => {
        const pts = p.poly.map(([x, y]) => `${x + p.x},${y + bar.y}`).join(" ");
        el("polygon", { points: pts, fill: p.cut.color, class: "piece" + (p.sel ? " sel" + (S.sel.length > 1 ? " multi" : "") : "") + (p.hl ? " hl" : "") }, world);
      });
    });
    const g = S.floating && S.floating.ghost;
    if (g) el("polygon", { points: g.poly.map((q) => q.join(",")).join(" "), fill: S.floating.cut ? S.floating.cut.color : "#888",
      class: "piece ghost" + (g.snapped ? " snap" : "") }, world);
    if (rubber) el("rect", { class: "rubber", x: Math.min(rubber.x0, rubber.x1), y: Math.min(rubber.y0, rubber.y1),
      width: Math.abs(rubber.x1 - rubber.x0), height: Math.abs(rubber.y1 - rubber.y0) }, world);
    renderOverlay();
  }
  function renderOverlay() {
    world.setAttribute("transform", `translate(${view.tx} ${view.ty}) scale(${view.s})`);
    overlay.replaceChildren();
    const h = S.sectionH * view.s;
    shown().forEach((bar) => {
      const y = bar.y * view.s + view.ty, x0 = view.tx;
      const t = el("text", { class: "bar-label", x: x0 + 2, y: y - 8 }, overlay); t.textContent = `Barra ${bar.id + 1}`;
      const m = el("text", { class: "bar-meta", x: x0 + bar.len * view.s, y: y - 8, "text-anchor": "end" }, overlay);
      m.textContent = `${bar.eff.toFixed(1)}% · R${bar.rem}`;
      bar.pieces.forEach((p) => {
        const w = p.cut.len * view.s; if (w < 28 || h < 11) return;
        const xs = p.poly.map((q) => q[0]); const cx = (Math.min(...xs) + Math.max(...xs)) / 2 + p.x;
        const lt = el("text", { class: "piece-label", x: view.tx + cx * view.s, y: y + h / 2 + 4, "text-anchor": "middle", fill: textOn(p.cut.color) }, overlay);
        lt.textContent = Math.round(p.cut.len);
      });
      const seen = []; bar.pieces.forEach((p) => { if (!seen.includes(p.cut)) seen.push(p.cut); });
      let lx = x0; const ly = y + h + 18;
      if ((snap ? snap.gap : 500) * view.s > 40) seen.forEach((c) => {
        el("rect", { x: lx, y: ly - 9, width: 9, height: 9, rx: 2, fill: c.color }, overlay);
        const lt = el("text", { x: lx + 14, y: ly, class: "bar-meta", style: "font-family:var(--font-ui);font-size:11px" }, overlay);
        lt.textContent = `${c.name} ${Math.round(c.len)} mm`;
        lx += 30 + (String(c.name).length + String(Math.round(c.len)).length + 3) * 6.2;
      });
    });
    renderRulers();
    emit("nest:zoom", Math.max(1, Math.round(view.s / view.fit * 100)));
  }
  function niceStep(pxPerMm) { const target = 80 / pxPerMm; const p = 10 ** Math.floor(Math.log10(target)); return [1, 2, 5, 10].map((k) => k * p).find((v) => v >= target) || 10 * p; }
  function renderRulers() {
    const w = rulerTop.clientWidth, hh = rulerLeft.clientHeight, step = niceStep(view.s);
    let out = "";
    for (let mm = Math.floor((-view.tx + 20) / view.s / step) * step; (mm * view.s + view.tx - 20) < w; mm += step / 5) {
      const x = mm * view.s + view.tx - 20, major = Math.abs(mm / step - Math.round(mm / step)) < 1e-6;
      out += `<line x1="${x}" x2="${x}" y1="${major ? 8 : 15}" y2="20" stroke="currentColor" stroke-opacity="${major ? 0.6 : 0.3}"/>`;
      if (major) out += `<text x="${x + 3}" y="9" fill="currentColor">${Math.round(mm)}</text>`;
    }
    rulerTop.innerHTML = `<svg>${out}</svg>`; out = "";
    for (let mm = Math.floor((-view.ty + 20) / view.s / step) * step; (mm * view.s + view.ty - 20) < hh; mm += step / 5) {
      const y = mm * view.s + view.ty - 20, major = Math.abs(mm / step - Math.round(mm / step)) < 1e-6;
      out += `<line y1="${y}" y2="${y}" x1="${major ? 8 : 15}" x2="20" stroke="currentColor" stroke-opacity="${major ? 0.6 : 0.3}"/>`;
      if (major) out += `<text transform="translate(9 ${y + 3}) rotate(-90)" fill="currentColor" text-anchor="end">${Math.round(mm)}</text>`;
    }
    rulerLeft.innerHTML = `<svg>${out}</svg>`;
  }
  function fit() {
    const bars = shown();
    if (!wrap) return;
    const maxLen = Math.max(6000, ...bars.map((b) => b.len));
    const wMM = maxLen + 200;
    const y0 = bars.length ? Math.min(...bars.map((b) => b.y)) : 0;
    const y1 = bars.length ? Math.max(...bars.map((b) => b.y)) + S.sectionH + (snap ? snap.gap : 500) : 1000;
    const hMM = Math.max(1, y1 - y0);
    const vw = wrap.clientWidth - 20, vh = wrap.clientHeight - 20 - 90;
    const s = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.min(vw / wMM, vh / hMM)));
    view.s = s; view.fit = s;
    view.tx = 20 + (vw - maxLen * s) / 2;
    view.ty = 20 + 44 - y0 * s + Math.max(0, (vh - hMM * s) / 2);
    renderOverlay();
  }
  function zoomAt(px, py, dir) {
    const f = dir > 0 ? ZOOM_STEP : 1 / ZOOM_STEP, ns = view.s * f;
    if (ns < ZOOM_MIN || ns > ZOOM_MAX) return;
    view.tx = px - (px - view.tx) * f; view.ty = py - (py - view.ty) * f; view.s = ns; renderOverlay();
  }
  const toWorld = (px, py) => ({ x: (px - view.tx) / view.s, y: (py - view.ty) / view.s });

  // Same padded hit area as PlacedPieceItem._hit_rect (thin bars are easy to grab).
  function hitPiece(w) {
    const pad = Math.min(Math.max(S.sectionH * 0.6, 40), 180);
    for (const b of shown()) for (const p of b.pieces) {
      const xs = p.poly.map((q) => q[0] + p.x);
      if (w.x >= Math.min(...xs) && w.x <= Math.max(...xs) && w.y >= b.y - pad && w.y <= b.y + S.sectionH + pad) return p;
    }
    return null;
  }

  // ── pointer handling ────────────────────────────────────────────────────
  let pan = null, down = false, rubber = null;
  function rel(e) { const r = wrap.getBoundingClientRect(); return { px: e.clientX - r.left, py: e.clientY - r.top }; }
  function onDown(e) {
    const { px, py } = rel(e), w = toWorld(px, py);
    if (e.button === 1) { pan = { px, py }; wrap.classList.add("panning"); e.preventDefault(); return; }
    if (e.button !== 0) return;
    const hit = hitPiece(w);
    if ((e.ctrlKey && !hit && !S.floating) || (!S.floating && snap && snap.left_pan && !hit)) {
      pan = { px, py }; wrap.classList.add("panning"); e.preventDefault(); return;
    }
    down = true;
    if (!hit && !S.floating && S.sel.length) rubber = { x0: w.x, y0: w.y, x1: w.x, y1: w.y };
    call("nest.press", { x: w.x, y: w.y, zoom: view.s });
  }
  function onMove(e) {
    const { px, py } = rel(e), w = toWorld(px, py);
    if (pan) { view.tx += px - pan.px; view.ty += py - pan.py; pan.px = px; pan.py = py; renderOverlay(); return; }
    const inside = px >= 0 && py >= 0 && px <= wrap.clientWidth && py <= wrap.clientHeight;
    if (inside && wrap.offsetParent) emit("nest:cursor", w);
    if (rubber) { rubber.x1 = w.x; rubber.y1 = w.y; renderWorld(); }
    if (down || S.floating) sendMove(w.x, w.y);
  }
  function onUp(e) {
    if (pan) { pan = null; wrap.classList.remove("panning"); return; }
    if (!down) return;
    down = false; rubber = null;
    const { px, py } = rel(e), w = toWorld(px, py);
    pendingMove = null;
    call("nest.release", { x: w.x, y: w.y, ctrl: e.ctrlKey, zoom: view.s });
  }
  function onContext(e) {
    e.preventDefault();
    const { px, py } = rel(e), w = toWorld(px, py);
    call("nest.context", { x: w.x, y: w.y }).then((r) => {
      if (r && r.piece) emit("nest:piece-menu", { x: e.clientX, y: e.clientY, piece: S.sel[0] || null, cutIndex: r.piece.cut });
    });
  }

  // ── public API (same surface as the mockup NestCanvas) ──────────────────
  const act = (name) => call("nest.action", { name });
  const API = {
    native: true, state: S,
    init() {
      wrap = document.getElementById("nest-canvas"); svg = document.getElementById("nest-svg");
      rulerTop = wrap.querySelector(".ruler.top"); rulerLeft = wrap.querySelector(".ruler.left");
      svg.replaceChildren(); world = el("g", { id: "world" }, svg); overlay = el("g", { id: "overlay" }, svg);
      wrap.addEventListener("pointerdown", onDown);
      window.addEventListener("pointermove", onMove);
      window.addEventListener("pointerup", onUp);
      wrap.addEventListener("contextmenu", onContext);
      wrap.addEventListener("wheel", (e) => { e.preventDefault(); const { px, py } = rel(e); zoomAt(px, py, -e.deltaY); }, { passive: false });
      new ResizeObserver(() => renderOverlay()).observe(wrap);
      window.NTB.on("nest:progress", (d) => emit("nest:running", { pct: d.pct < 0 ? "∞" : d.pct }));
      window.NTB.on("nest:state", (s) => apply(s));
      window.NTB.on("nest:finished", (s) => { apply(s); fit(); });   // apply() emits nest:done
      API.refresh();
    },
    refresh: () => call("nest.state"),
    fit, zoomBy: (dir) => zoomAt(wrap.clientWidth / 2, wrap.clientHeight / 2, dir),
    undo: () => act("undo"), redo: () => act("redo"), save: () => act("save"),
    escape: () => act("escape"),
    addBar: () => act("add_bar"),
    moveBar: (id, dir) => call("nest.move_bar", { i: id, direction: dir }),
    filterBar: (id) => { S.filteredBar = S.filteredBar === id ? null : id; renderWorld(); fit(); emit("nest:changed"); },
    showAll: () => { S.filteredBar = null; renderWorld(); fit(); emit("nest:changed"); },
    toggleBarExpanded: (id) => { S.expandedBars.has(id) ? S.expandedBars.delete(id) : S.expandedBars.add(id); emit("nest:changed"); },
    startFloating: (cut) => call("nest.select_piece", { i: cut.id }),
    cancelFloating: () => act("cancel_float"),
    cycleOrientation: (dir) => act(dir < 0 ? "rotate_left" : "rotate_right"),
    flip: (axis) => act(axis === "fh" ? "flip_h" : "flip_v"),
    deleteSelected: () => act("delete"),
    removePermanently: (cut) => {
      const n = cut ? 1 : Math.max(1, S.sel.length);
      emit("nest:confirm", { title: "Eliminar pieza", text: n > 1 ? `¿Eliminar ${n} piezas permanentemente?` : "¿Eliminar pieza permanentemente?",
        ok: () => (cut && !S.sel.some((p) => p.cut === cut) ? call("nest.piece_action", { i: cut.id, name: "remove" }) : act("remove")) });
    },
    clearSelection: () => act("clear_selection"),
    highlight: (cut, barId) => (barId == null ? call("nest.piece_action", { i: cut.id, name: "highlight" })
      : call("nest.highlight_in_bar", { bar: barId, cut: cut.id })),
    refreshRemnants: () => act("rem_refresh"), clearRemnants: () => act("rem_clear"),
    applyRemnants: () => act("rem_apply"), deleteAllRemnants: () => act("rem_delete_all"),
    clearNesting: () => emit("nest:confirm", { title: "Limpiar", text: "¿Borrar el anidado actual? Esta acción no se puede deshacer.", ok: () => act("clear") }),
    toggleNest() {
      if (S.nesting) { call("nest.stop_auto_nest"); return; }
      const placed = S.bars.reduce((n, b) => n + b.pieces.length, 0);
      const go = () => window.NTB.call("nest.needs_material").then((r) => {
        const run = () => { emit("nest:running", { pct: 0 }); call("nest.auto_nest", { continue_without_material: true }).then((st) => {
          if (st && !st.auto_nesting) { fit(); emit("nest:done", {}); } }); };
        if (r && r.ok && r.result) {
          window.NT.alert({ kind: "question", title: "Auto-anidar", msg: "No hay material seleccionado para este anidado.\n\nPuedes elegirlo ahora o continuar sin material.",
            buttons: [{ label: "Cancelar" }, { label: "Continuar sin material", action: run },
              { label: "Seleccionar material", primary: true, action: () => act("sel_material").then(run) }] });
        } else run();
      });
      if (S.autoMode === "all" && placed > 0) {
        emit("nest:confirm", { title: "¿Borrar piezas colocadas?", text: `El modo 'Todo' eliminará las ${placed} pieza(s) ya colocadas.\n\n¿Continuar?`, danger: false, ok: go });
      } else go();
    },
    setParam(key, val) {
      const map = { kerf: "kerf", margin: "margin", barLen: "bar_len", sectionH: "height", commonCut: "common", snap: "snap",
        remMin: "rem_min", remMargin: "rem_margin", useStock: "use_stock", autoStock: "auto_stock", advanced: "advanced",
        strategy: "strategy", calcSystem: "calc", autoMode: "auto_mode", optLevel: "opt" };
      if (!map[key]) return;
      call("nest.set_params", { [map[key]]: val });
    },
    setCutValues: (cut, values, renest) => call("nest.set_cut_values", { i: cut.id, values, renest: !!renest }),
    moveSelected: () => act("move_selected"),
    editDrawing: (target) => (target && target.id != null && !target.poly ? call("nest.piece_action", { i: target.id, name: "edit_drawing" }) : act("edit_drawing")),
    exportPieceDxf: (target) => (target && target.id != null && !target.poly ? call("nest.piece_action", { i: target.id, name: "export_piece_dxf" }) : act("export_piece_dxf")),
    exportAction: (name) => act(name),
    selMaterial: () => act("sel_material").then((r) => { if (window.NT.refreshJob) window.NT.refreshJob(); return r; }),
    remaining: (c) => (c && c.remaining != null ? c.remaining : 0),
    placedCount: (c) => (c ? c.placed : 0),
    efficiency() {
      const bars = S.bars.filter((b) => b.pieces.length);
      if (!bars.length) return 0;
      const used = bars.reduce((s, b) => s + b.pieces.reduce((t, p) => t + p.cut.len, 0), 0);
      return used / bars.reduce((s, b) => s + b.len, 0) * 100;
    },
    usedEnd: (bar) => bar.len - (bar.rem || 0),
    cutById: (id) => S.cuts[id], polyLocal: () => [],
    isDirty: () => !!(snap && snap.dirty), discardDirty() {},
    snapshot: () => snap,
    // scene mm → canvas pixels (used by the end-to-end tests)
    toScreen: (x, y) => ({ px: x * view.s + view.tx, py: y * view.s + view.ty }),
  };
  function emit(name, detail) { document.dispatchEvent(new CustomEvent(name, { detail })); }
  window.NestCanvas = API;
})();
