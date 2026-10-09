/* ==========================================================================
   NesTube web UI — Nesting canvas (MOCKUP STAGE)
   --------------------------------------------------------------------------
   View logic mirrors nestube/ui_qt/nesting_view.py + tab_nesting.py:
     · 1 world unit = 1 mm; bar i sits at y = i * (sectionH + BAR_GAP_MM)
     · wheel = zoom at cursor (×1.15 per notch, clamped 0.05–40 of px/mm)
     · pan  = middle-drag, Ctrl+left-drag, or left-drag on empty canvas while
              nothing is selected/floating
     · click sidebar piece → it floats under the cursor → click on a bar drops it
     · click placed piece = select · Ctrl+click = multi-select · click a lone
       selected piece again = pick it up · drag past 5 px = move
     · drag on empty canvas with a selection = marquee select
   Placement validity here is a SIMPLE 1D interval check so the mockup feels
   right. In the functional stage these calls go to the Python engine
   (TabNesting._find_best_snap / _fits_physically → nesting_engine NFP), so the
   real contour collision logic is reused unchanged.
   ========================================================================== */
(function () {
  "use strict";

  const BAR_GAP_MM = 500;          // nesting_scene.BAR_GAP_MM
  const ZOOM_STEP = 1.15;          // nesting_view._ZOOM_STEP
  const ZOOM_MIN = 0.005, ZOOM_MAX = 40;
  const SVGNS = "http://www.w3.org/2000/svg";

  // ── sample job (marked as example data in the UI) ───────────────────────
  const state = {
    material: "IPE 200 · S235",
    barLen: 6000, sectionH: 200, kerf: 3, margin: 0,
    commonCut: false, snap: true, advanced: true,
    strategy: "length", calcSystem: "ffd", optLevel: 0, autoMode: "all",
    useStock: false, autoStock: false,
    cuts: [
      { id: 1, name: "Viga principal", len: 3500, qty: 4, aL: 0,  aR: 0,  color: "#4E79A7" },
      { id: 2, name: "Correa",         len: 1200, qty: 6, aL: 0,  aR: 0,  color: "#F28E2B" },
      { id: 3, name: "Montante",       len: 800,  qty: 8, aL: 0,  aR: 0,  color: "#E15759" },
      { id: 4, name: "Diagonal",       len: 2800, qty: 2, aL: 45, aR: 45, color: "#76B7B2" },
      { id: 5, name: "Placa base",     len: 400,  qty: 4, aL: 0,  aR: 0,  color: "#59A14F" },
    ],
    bars: [],                 // [{ id, len, pieces: [{ cut, x, fh, fv }] }]
    filter: "all",            // sidebar: all | complete | incomplete
    filteredBar: null,        // show only one bar (bar-list header click)
    expandedBars: new Set(),
    sel: [],                  // selected placed pieces (refs)
    floating: null,           // { cut, fh, fv, from?: {bar, piece} }
    ghost: null,              // { bar, x, ok, snapped }
    remnants: [],             // [{ bar, x, w }]
    remMin: 500, remMargin: 0,
    undo: [], redo: [],
    nesting: false,
  };
  let nextBarId = 1;

  const cutById = (id) => state.cuts.find((c) => c.id === id);

  // ── geometry ────────────────────────────────────────────────────────────
  function polyLocal(cut, fh, fv) {
    const L = cut.len, H = state.sectionH;
    const dL = Math.min(H * Math.tan((cut.aL || 0) * Math.PI / 180), L / 2);
    const dR = Math.min(H * Math.tan((cut.aR || 0) * Math.PI / 180), L / 2);
    let pts = [[0, 0], [L - dR, 0], [L, H], [dL, H]];
    if (fh) pts = pts.map(([x, y]) => [L - x, y]);
    if (fv) pts = pts.map(([x, y]) => [x, H - y]);
    return pts;
  }
  const barY = (visIdx) => visIdx * (state.sectionH + BAR_GAP_MM);
  const visibleBars = () => state.bars.filter((b) => b.pieces.length || b.manual)
    .filter((b) => state.filteredBar == null || b.id === state.filteredBar);
  const usedEnd = (bar) => bar.pieces.reduce((m, p) => Math.max(m, p.x + p.cut.len), 0);
  const gapFor = () => (state.commonCut ? state.kerf : state.kerf + state.margin);

  // 1D interval check (placeholder for the Python NFP collision test)
  function fits(bar, cut, x, exclude) {
    if (x < state.margin - 1e-6 || x + cut.len > bar.len - state.margin + 1e-6) return false;
    const g = state.kerf;
    return bar.pieces.every((p) => p === exclude || x + cut.len + g <= p.x + 1e-6 || x >= p.x + p.cut.len + g - 1e-6);
  }
  function snapCandidates(bar, cut, exclude) {
    const xs = [state.margin];
    bar.pieces.forEach((p) => { if (p !== exclude) xs.push(p.x + p.cut.len + state.kerf, p.x - state.kerf - cut.len); });
    return xs.filter((x) => fits(bar, cut, x, exclude));
  }

  // ── pieces bookkeeping ──────────────────────────────────────────────────
  function placedCount(cut) {
    let n = 0;
    state.bars.forEach((b) => b.pieces.forEach((p) => { if (p.cut === cut) n++; }));
    if (state.floating && state.floating.from && state.floating.cut === cut) n++;
    return n;
  }
  const remaining = (cut) => cut.qty - placedCount(cut);

  function efficiency() {
    const bars = state.bars.filter((b) => b.pieces.length);
    if (!bars.length) return 0;
    const used = bars.reduce((s, b) => s + b.pieces.reduce((t, p) => t + p.cut.len, 0), 0);
    return used / bars.reduce((s, b) => s + b.len, 0) * 100;
  }

  // ── undo / redo (snapshots, like TabNesting._serialize_bars) ────────────
  const snapshot = () => state.bars.map((b) => ({ id: b.id, len: b.len, manual: !!b.manual,
    pieces: b.pieces.map((p) => ({ c: p.cut.id, x: p.x, fh: p.fh, fv: p.fv })) }));
  function restore(snap) {
    state.bars = snap.map((b) => ({ id: b.id, len: b.len, manual: b.manual,
      pieces: b.pieces.map((p) => ({ cut: cutById(p.c), x: p.x, fh: p.fh, fv: p.fv })) }));
    state.sel = [];
  }
  function pushUndo() { state.undo.push(snapshot()); if (state.undo.length > 100) state.undo.shift(); state.redo = []; markDirty(); }
  function undo() { if (!state.undo.length) return; state.redo.push(snapshot()); restore(state.undo.pop()); refreshAll(); }
  function redo() { if (!state.redo.length) return; state.undo.push(snapshot()); restore(state.redo.pop()); refreshAll(); }

  // ── simple FFD / BFD / NFD (placeholder for nesting_engine) ─────────────
  function runSimpleNest(mode) {
    const keep = mode === "remaining";
    if (!keep) state.bars = [];
    const pool = [];
    state.cuts.forEach((c) => { for (let i = 0; i < (keep ? remaining(c) : c.qty); i++) pool.push(c); });
    pool.sort((a, b) => b.len - a.len);
    const fresh = [];
    const sys = state.advanced ? "ffd" : state.calcSystem;
    pool.forEach((cut) => {
      const free = (b) => b.len - state.margin - (b.pieces.length ? usedEnd(b) + gapFor() : state.margin);
      let target = null;
      if (sys === "nfd") { const last = fresh[fresh.length - 1]; if (last && free(last) >= cut.len) target = last; }
      else if (sys === "bfd") { target = fresh.filter((b) => free(b) >= cut.len).sort((a, b) => free(a) - free(b))[0] || null; }
      else { target = fresh.find((b) => free(b) >= cut.len) || null; }
      if (!target) { target = { id: nextBarId++, len: state.barLen, pieces: [] }; fresh.push(target); }
      const x = target.pieces.length ? usedEnd(target) + gapFor() : state.margin;
      target.pieces.push({ cut, x, fh: false, fv: false });
    });
    state.bars.push(...fresh);
  }

  // ── DOM refs ────────────────────────────────────────────────────────────
  let wrap, svg, world, overlay, rulerTop, rulerLeft;
  const view = { s: 0.12, tx: 40, ty: 60, fit: 0.12 };

  function el(tag, attrs, parent) {
    const n = document.createElementNS(SVGNS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  // text colour per WCAG (nesting_scene._text_color_for_bg)
  function textOn(hex) {
    const c = hex.replace("#", ""); const ch = [0, 2, 4].map((i) => parseInt(c.substr(i, 2), 16) / 255)
      .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    const L = 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
    return (1.05 / (L + 0.05)) >= ((L + 0.05) / 0.062) ? "#FFFFFF" : "#1C1C1E";
  }

  // ── render ──────────────────────────────────────────────────────────────
  function renderWorld() {
    world.replaceChildren();
    const bars = visibleBars();
    bars.forEach((bar, vi) => {
      const y = barY(vi);
      el("rect", { class: "bar-rect", x: 0, y, width: bar.len, height: state.sectionH, "data-bar": bar.id }, world);
      state.remnants.filter((r) => r.bar === bar.id).forEach((r) =>
        el("rect", { class: "remnant", x: r.x, y, width: r.w, height: state.sectionH }, world));
      bar.pieces.forEach((p) => {
        const pts = polyLocal(p.cut, p.fh, p.fv).map(([x, yy]) => `${x + p.x},${yy + y}`).join(" ");
        const isSel = state.sel.includes(p);
        const poly = el("polygon", { points: pts, fill: p.cut.color,
          class: "piece" + (isSel ? " sel" + (state.sel.length > 1 ? " multi" : "") : "") + (p.hl ? " hl" : "") }, world);
        poly._piece = p; poly._bar = bar;
      });
    });
    if (state.ghost && state.floating) {
      const f = state.floating, g = state.ghost;
      const pts = polyLocal(f.cut, f.fh, f.fv).map(([x, yy]) => `${x + g.x},${yy + g.y}`).join(" ");
      el("polygon", { points: pts, fill: f.cut.color, class: "piece ghost" + (g.ok ? (g.snapped ? " snap" : "") : " bad") }, world);
    }
    if (rubber) el("rect", { class: "rubber", x: Math.min(rubber.x0, rubber.x1), y: Math.min(rubber.y0, rubber.y1),
      width: Math.abs(rubber.x1 - rubber.x0), height: Math.abs(rubber.y1 - rubber.y0) }, world);
    renderOverlay();
  }

  // Labels live in pixel space (constant size at any zoom), anchored to the
  // bars — same idea as NestingView.drawForeground's sticky "Bar N" labels.
  function renderOverlay() {
    world.setAttribute("transform", `translate(${view.tx} ${view.ty}) scale(${view.s})`);
    overlay.replaceChildren();
    const bars = visibleBars();
    bars.forEach((bar, vi) => {
      const y = barY(vi) * view.s + view.ty;
      const x0 = view.tx;
      const n = state.bars.indexOf(bar) + 1;
      const t = el("text", { class: "bar-label", x: x0 + 2, y: y - 8 }, overlay);
      t.textContent = `Barra ${n}`;
      const used = bar.pieces.reduce((s, p) => s + p.cut.len, 0);
      const m = el("text", { class: "bar-meta", x: x0 + bar.len * view.s, y: y - 8, "text-anchor": "end" }, overlay);
      m.textContent = `${(used / bar.len * 100).toFixed(1)}% · R${Math.max(0, Math.round(bar.len - usedEnd(bar) - state.margin))}`;
      const h = state.sectionH * view.s;
      bar.pieces.forEach((p) => {
        const w = p.cut.len * view.s;
        if (w < 28 || h < 11) return;
        const lt = el("text", { class: "piece-label", x: view.tx + (p.x + p.cut.len / 2) * view.s, y: y + h / 2 + 4,
          "text-anchor": "middle", fill: textOn(p.cut.color) }, overlay);
        lt.textContent = p.cut.len;
      });
      // legend under the bar (one entry per distinct cut)
      const seen = [];
      bar.pieces.forEach((p) => { if (!seen.includes(p.cut)) seen.push(p.cut); });
      let lx = x0;
      const ly = y + h + 18;
      if (BAR_GAP_MM * view.s > 40) seen.forEach((c) => {
        el("rect", { x: lx, y: ly - 9, width: 9, height: 9, rx: 2, fill: c.color }, overlay);
        const lt = el("text", { x: lx + 14, y: ly, class: "bar-meta", style: "font-family:var(--font-ui);font-size:11px" }, overlay);
        lt.textContent = `${c.name} ${c.len} mm`;
        lx += 30 + (c.name.length + String(c.len).length + 3) * 6.2;
      });
    });
    // live dimension while floating
    if (state.ghost && state.floating && state.ghost.bar) {
      const g = state.ghost, y = g.y * view.s + view.ty - 6;
      const xa = view.tx + state.margin * view.s, xb = view.tx + g.x * view.s;
      if (xb - xa > 30) {
        el("line", { class: "dim-line", x1: xa, y1: y, x2: xb, y2: y }, overlay);
        const dt = el("text", { class: "dim-text", x: (xa + xb) / 2, y: y - 4, "text-anchor": "middle" }, overlay);
        dt.textContent = `x = ${Math.round(g.x)} mm`;
      }
    }
    renderRulers();
    document.dispatchEvent(new CustomEvent("nest:zoom", { detail: Math.max(1, Math.round(view.s / view.fit * 100)) }));
  }

  function niceStep(pxPerMm) {
    const target = 80 / pxPerMm; const p = 10 ** Math.floor(Math.log10(target));
    return [1, 2, 5, 10].map((k) => k * p).find((v) => v >= target) || 10 * p;
  }
  function renderRulers() {
    const w = rulerTop.clientWidth, h = rulerLeft.clientHeight;
    const step = niceStep(view.s);
    let out = "";
    const start = Math.floor((-view.tx + 20) / view.s / step) * step;
    for (let mm = start; (mm * view.s + view.tx - 20) < w; mm += step / 5) {
      const x = mm * view.s + view.tx - 20;
      const major = Math.abs(mm / step - Math.round(mm / step)) < 1e-6;
      out += `<line x1="${x}" x2="${x}" y1="${major ? 8 : 15}" y2="20" stroke="currentColor" stroke-opacity="${major ? 0.6 : 0.3}"/>`;
      if (major) out += `<text x="${x + 3}" y="9" fill="currentColor">${Math.round(mm)}</text>`;
    }
    rulerTop.innerHTML = `<svg>${out}</svg>`;
    out = "";
    const st2 = Math.floor((-view.ty + 20) / view.s / step) * step;
    for (let mm = st2; (mm * view.s + view.ty - 20) < h; mm += step / 5) {
      const y = mm * view.s + view.ty - 20;
      const major = Math.abs(mm / step - Math.round(mm / step)) < 1e-6;
      out += `<line y1="${y}" y2="${y}" x1="${major ? 8 : 15}" x2="20" stroke="currentColor" stroke-opacity="${major ? 0.6 : 0.3}"/>`;
      if (major) out += `<text transform="translate(9 ${y + 3}) rotate(-90)" fill="currentColor" text-anchor="end">${Math.round(mm)}</text>`;
    }
    rulerLeft.innerHTML = `<svg>${out}</svg>`;
  }

  // ── zoom / fit (NestingView.fit_scene / _zoom_at) ────────────────────────
  function fit() {
    const bars = visibleBars();
    const wMM = Math.max(state.barLen, ...bars.map((b) => b.len)) + 200;
    const hMM = Math.max(1, bars.length) * (state.sectionH + BAR_GAP_MM);
    const vw = wrap.clientWidth - 20, vh = wrap.clientHeight - 20 - 90;
    const s = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.min(vw / wMM, vh / hMM)));
    view.s = s; view.fit = s;
    view.tx = 20 + (vw - (wMM - 200) * s) / 2;
    view.ty = 20 + 44 + Math.max(0, (vh - hMM * s) / 2);
    renderOverlay();
  }
  function zoomAt(px, py, dir) {
    const f = dir > 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
    const ns = view.s * f;
    if (ns < ZOOM_MIN || ns > ZOOM_MAX) return;
    view.tx = px - (px - view.tx) * f; view.ty = py - (py - view.ty) * f; view.s = ns;
    renderOverlay();
  }
  const toWorld = (px, py) => ({ x: (px - view.tx) / view.s, y: (py - view.ty) / view.s });
  function barAtY(wy) {
    const pitch = state.sectionH + BAR_GAP_MM; const bars = visibleBars();
    const vi = Math.floor((wy + BAR_GAP_MM / 2) / pitch);
    if (vi < 0 || vi >= bars.length) return null;
    return { bar: bars[vi], y: barY(vi) };
  }

  // ── floating piece (sidebar pick / move) ────────────────────────────────
  function startFloating(cut, from) {
    if (!from && remaining(cut) <= 0) return;
    state.floating = { cut, fh: from ? from.piece.fh : false, fv: from ? from.piece.fv : false, from };
    state.sel = [];
    wrap.classList.add("floating");
    emit("nest:floating", { cut });
    refreshAll();
  }
  function cancelFloating() {
    if (!state.floating) return;
    if (state.floating.from) state.floating.from.bar.pieces.push(state.floating.from.piece); // put it back
    state.floating = null; state.ghost = null;
    wrap.classList.remove("floating");
    emit("nest:floating", null);
    refreshAll();
  }
  function updateGhost(px, py) {
    const f = state.floating; if (!f) return;
    const w = toWorld(px, py);
    const hit = barAtY(w.y);
    let x = w.x - f.cut.len / 2;
    if (hit) {
      const exclude = null;
      let snapped = false;
      if (state.snap) {
        const zone = Math.max(f.cut.len, 300);
        const best = snapCandidates(hit.bar, f.cut, exclude).map((cx) => [cx, Math.abs(cx - x)])
          .filter(([, d]) => d <= zone).sort((a, b) => a[1] - b[1])[0];
        if (best) { x = best[0]; snapped = true; }
      }
      if (!snapped) x = Math.max(state.margin, Math.min(x, hit.bar.len - state.margin - f.cut.len));
      state.ghost = { bar: hit.bar, x, y: hit.y, ok: fits(hit.bar, f.cut, x), snapped };
    } else {
      state.ghost = { bar: null, x, y: w.y - state.sectionH / 2, ok: false, snapped: false };
    }
    renderWorld();
  }
  function dropFloating() {
    const f = state.floating, g = state.ghost;
    if (!f || !g || !g.bar || !g.ok) { flash(g && g.bar ? "Colisión: no cabe en esa posición" : "Suelta la pieza sobre una barra"); return false; }
    pushUndo();
    g.bar.pieces.push({ cut: f.cut, x: g.x, fh: f.fh, fv: f.fv });
    const keepCarrying = !f.from && remaining(f.cut) > 0;
    state.floating = keepCarrying ? { cut: f.cut, fh: f.fh, fv: f.fv } : null;
    if (!keepCarrying) { state.ghost = null; wrap.classList.remove("floating"); emit("nest:floating", null); }
    refreshAll();
    return true;
  }

  // ── orientation (Ctrl+Q / Ctrl+E / Ctrl+H / Ctrl+A) ──────────────────────
  const ORIENTS = [[false, false], [true, false], [true, true], [false, true]];
  function cycleOrientation(dir) {
    const f = state.floating; if (!f) { flash("Rotar aplica a la pieza flotante"); return; }
    const i = ORIENTS.findIndex(([h, v]) => h === f.fh && v === f.fv);
    [f.fh, f.fv] = ORIENTS[(i + dir + 4) % 4];
    renderWorld();
  }
  function flip(axis) {
    if (state.floating) { state.floating[axis] = !state.floating[axis]; renderWorld(); return; }
    if (!state.sel.length) return;
    pushUndo();
    state.sel.forEach((p) => { p[axis] = !p[axis]; });   // real app re-checks _fits_physically
    renderWorld();
  }

  // ── selection & delete ──────────────────────────────────────────────────
  function removeFromBars(pieces) {
    state.bars.forEach((b) => { b.pieces = b.pieces.filter((p) => !pieces.includes(p)); });
  }
  function deleteSelected() {
    if (!state.sel.length) return;
    pushUndo(); removeFromBars(state.sel); state.sel = []; refreshAll();
  }
  function removePermanently(cut) {
    const target = cut || (state.sel[0] && state.sel[0].cut); if (!target) return;
    emit("nest:confirm", { title: "Eliminar pieza", text: `¿Eliminar «${target.name}» del trabajo? Se quita de todas las barras y de la lista de cortes.`,
      ok: () => { pushUndo(); state.bars.forEach((b) => { b.pieces = b.pieces.filter((p) => p.cut !== target); });
        state.cuts = state.cuts.filter((c) => c !== target); state.sel = []; refreshAll(); } });
  }
  function clearSelection() { state.sel = []; state.bars.forEach((b) => b.pieces.forEach((p) => { p.hl = false; })); refreshAll(); }
  function escape() {
    if (state.nesting) cancelNest(); else if (state.floating) cancelFloating(); else clearSelection();
  }

  // ── pointer handling ────────────────────────────────────────────────────
  let pan = null, press = null, rubber = null;
  function onPointerDown(e) {
    const r = wrap.getBoundingClientRect(); const px = e.clientX - r.left, py = e.clientY - r.top;
    const target = e.target.closest && e.target.closest(".piece:not(.ghost)");
    if (e.button === 1 || (e.button === 0 && e.ctrlKey && !target)) { startPan(e, px, py); return; }
    if (e.button === 2) return;
    if (e.button !== 0) return;
    if (state.floating) { dropFloating(); return; }
    if (target) { press = { px, py, piece: target._piece, bar: target._bar, ctrl: e.ctrlKey, moved: false }; return; }
    if (!state.sel.length) { startPan(e, px, py); return; }
    const w = toWorld(px, py); rubber = { x0: w.x, y0: w.y, x1: w.x, y1: w.y, ctrl: e.ctrlKey, px, py };
  }
  function startPan(e, px, py) { pan = { px, py }; wrap.classList.add("panning"); e.preventDefault(); }
  function onPointerMove(e) {
    const r = wrap.getBoundingClientRect(); const px = e.clientX - r.left, py = e.clientY - r.top;
    emit("nest:cursor", toWorld(px, py));
    if (pan) { view.tx += px - pan.px; view.ty += py - pan.py; pan.px = px; pan.py = py; renderOverlay(); return; }
    if (rubber) { const w = toWorld(px, py); rubber.x1 = w.x; rubber.y1 = w.y; renderWorld(); return; }
    if (press && !press.moved && Math.hypot(px - press.px, py - press.py) > 5) {
      press.moved = true;
      pushUndo();
      press.bar.pieces = press.bar.pieces.filter((p) => p !== press.piece);
      startFloating(press.piece.cut, { bar: press.bar, piece: press.piece });
    }
    if (state.floating) updateGhost(px, py);
  }
  function onPointerUp(e) {
    if (pan) { pan = null; wrap.classList.remove("panning"); return; }
    if (rubber) {
      const rb = rubber; rubber = null;
      if (Math.abs(e.clientX - wrap.getBoundingClientRect().left - rb.px) > 4) {
        const x0 = Math.min(rb.x0, rb.x1), x1 = Math.max(rb.x0, rb.x1), y0 = Math.min(rb.y0, rb.y1), y1 = Math.max(rb.y0, rb.y1);
        if (!rb.ctrl) state.sel = [];
        visibleBars().forEach((b, vi) => { const y = barY(vi);
          b.pieces.forEach((p) => { if (p.x < x1 && p.x + p.cut.len > x0 && y < y1 && y + state.sectionH > y0 && !state.sel.includes(p)) state.sel.push(p); }); });
      } else if (!rb.ctrl) state.sel = [];
      refreshAll(); return;
    }
    if (press) {
      const p = press; press = null;
      if (p.moved) { if (state.floating && !dropFloating()) cancelFloating(); return; }
      if (p.ctrl) { const i = state.sel.indexOf(p.piece); i >= 0 ? state.sel.splice(i, 1) : state.sel.push(p.piece); }
      else if (state.sel.length === 1 && state.sel[0] === p.piece) {
        // click-to-move: second click on the lone selected piece picks it up
        pushUndo(); p.bar.pieces = p.bar.pieces.filter((q) => q !== p.piece);
        startFloating(p.piece.cut, { bar: p.bar, piece: p.piece }); return;
      } else state.sel = [p.piece];
      refreshAll();
    }
  }
  function onContextMenu(e) {
    e.preventDefault();
    const target = e.target.closest && e.target.closest(".piece:not(.ghost)");
    if (!target) return;
    if (!state.sel.includes(target._piece)) { state.sel = [target._piece]; refreshAll(); }
    emit("nest:piece-menu", { x: e.clientX, y: e.clientY, piece: target._piece, bar: target._bar });
  }

  // ── auto-nest (simulated progress; real one runs _AutoNestWorker) ───────
  let nestTimer = null;
  function toggleNest() { state.nesting ? cancelNest() : startNest(); }
  function startNest() {
    if (state.floating) cancelFloating();
    state.nesting = true; emit("nest:running", { pct: 0 });
    let pct = 0;
    nestTimer = setInterval(() => {
      pct += 9 + Math.random() * 12;
      if (pct >= 100) { clearInterval(nestTimer); nestTimer = null; finishNest(); return; }
      emit("nest:running", { pct: Math.round(pct) });
    }, 120);
  }
  function finishNest() {
    pushUndo(); runSimpleNest(state.autoMode); state.nesting = false; state.sel = []; state.remnants = [];
    emit("nest:done", {}); refreshAll(); fit();
  }
  function cancelNest() { if (nestTimer) clearInterval(nestTimer); nestTimer = null; state.nesting = false; emit("nest:done", { cancelled: true }); }

  // ── bars / remnants ─────────────────────────────────────────────────────
  function addBar() { pushUndo(); state.bars.push({ id: nextBarId++, len: state.barLen, pieces: [], manual: true }); refreshAll(); fit(); }
  function moveBar(id, dir) {
    const vis = state.bars; const i = vis.findIndex((b) => b.id === id); const j = i + dir;
    if (i < 0 || j < 0 || j >= vis.length) return;
    pushUndo(); [vis[i], vis[j]] = [vis[j], vis[i]]; refreshAll();
  }
  function filterBar(id) { state.filteredBar = state.filteredBar === id ? null : id; refreshAll(); fit(); }
  function toggleBarExpanded(id) { state.expandedBars.has(id) ? state.expandedBars.delete(id) : state.expandedBars.add(id); emit("nest:changed"); }
  function highlight(cut, barId) {
    state.bars.forEach((b) => b.pieces.forEach((p) => { p.hl = p.cut === cut && (barId == null || b.id === barId); }));
    renderWorld();
  }
  function refreshRemnants() {
    state.remnants = [];
    state.bars.forEach((b) => {
      if (!b.pieces.length) return;
      const x = usedEnd(b) + state.kerf + state.remMargin; const w = b.len - state.margin - x;
      if (w >= state.remMin) state.remnants.push({ bar: b.id, x, w });
    });
    renderWorld(); emit("nest:changed");
  }
  function clearRemnants() { state.remnants = []; renderWorld(); emit("nest:changed"); }
  function clearNesting() {
    emit("nest:confirm", { title: "Limpiar anidado", text: "Se quitarán todas las piezas colocadas de todas las barras. Puedes deshacerlo con Ctrl+Z.",
      ok: () => { pushUndo(); state.bars = []; state.sel = []; state.remnants = []; refreshAll(); fit(); } });
  }

  // ── misc ────────────────────────────────────────────────────────────────
  let dirty = false;
  function markDirty() { dirty = true; emit("nest:dirty", true); }
  function save() { dirty = false; emit("nest:dirty", false); flash("Anidado guardado"); }
  function emit(name, detail) { document.dispatchEvent(new CustomEvent(name, { detail })); }
  function flash(msg) { emit("nest:flash", msg); }
  function refreshAll() { renderWorld(); emit("nest:changed"); }

  function setParam(key, val) {
    state[key] = val;
    if (["kerf", "margin", "barLen", "sectionH", "commonCut"].includes(key)) {
      if (key === "barLen") state.bars.forEach((b) => { b.len = val; });
      renderWorld(); fit();
    }
    emit("nest:changed");
  }

  function init() {
    wrap = document.getElementById("nest-canvas");
    svg = document.getElementById("nest-svg");
    rulerTop = wrap.querySelector(".ruler.top");
    rulerLeft = wrap.querySelector(".ruler.left");
    world = el("g", { id: "world" }, svg);
    overlay = el("g", { id: "overlay" }, svg);

    // initial example layout: FFD, then leave three pieces pending so the
    // sidebar shows both complete and pending states
    runSimpleNest("all");
    const last = state.bars[state.bars.length - 1];
    last.pieces.splice(-2, 2);
    state.bars[state.bars.length - 2].pieces.splice(-1, 1);
    state.expandedBars.add(state.bars[0].id);

    wrap.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    wrap.addEventListener("contextmenu", onContextMenu);
    wrap.addEventListener("wheel", (e) => { e.preventDefault(); const r = wrap.getBoundingClientRect();
      zoomAt(e.clientX - r.left, e.clientY - r.top, -e.deltaY); }, { passive: false });
    wrap.addEventListener("pointerleave", () => { if (state.floating) { state.ghost = null; renderWorld(); } });
    new ResizeObserver(() => fit()).observe(wrap);
    renderWorld(); fit(); emit("nest:changed");
  }

  window.NestCanvas = {
    init, state, fit, undo, redo, save, escape, addBar, moveBar, filterBar, toggleBarExpanded,
    startFloating, cancelFloating, cycleOrientation, flip, deleteSelected, removePermanently,
    clearSelection, toggleNest, highlight, refreshRemnants, clearRemnants, clearNesting, setParam,
    remaining, placedCount, efficiency, usedEnd, cutById, polyLocal,
    zoomBy: (dir) => zoomAt(wrap.clientWidth / 2, wrap.clientHeight / 2, dir),
    showAll: () => { state.filteredBar = null; refreshAll(); fit(); },
    isDirty: () => dirty,
  };
})();
