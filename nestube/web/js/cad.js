/* ==========================================================================
   NesTube web UI — drawing module (profile creator), AutoCAD-style (MOCKUP)
   Same tools and behaviour as nestube/ui_qt/dialogs/profile_creator.py, laid
   out so an AutoCAD user recognises it at once:
     · ribbon (Dibujo / Modificar / Perfil / Utilidades / Archivo)
     · dark model space, crosshair + pickbox, UCS icon, grid
     · object snap markers (Punto final, Punto medio, Centro, Cercano, Rejilla)
     · dynamic input next to the cursor (type a length, Tab or < for angle)
     · command line with aliases: L, PL, POL, REC, C, A, ACIF, AE, B/E, TR,
       EX/AL, VANO, Z, U — Enter or Space repeats the last command
     · status bar toggles REJILLA F7, FORZC F9, ORTO F8, REFENT F3, DIN F12
     · Properties palette: profile image, selection, dimensions, sides, data
   World units are mm with Y up (like AutoCAD). The Qt module keeps the real
   geometry/thumbnail/DXF code; stage 2 calls it through the bridge.
   ========================================================================== */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const I = (id, cls = "") => `<svg class="icon ${cls}"><use href="#i-${id}"/></svg>`;
  const NS = "http://www.w3.org/2000/svg";
  const SNAP_PX = 10, GRID = 10;

  // ── tools: id → label, icon, aliases, prompts (steps) ───────────────────
  const TOOLS = {
    select:   { label: "Seleccionar", icon: "cursor", alias: "Esc", cmd: "", steps: ["Designe objetos:"] },
    line:     { label: "Línea", icon: "line", alias: "L", cmd: "LINEA", steps: ["Precise primer punto:", "Precise punto siguiente o [Deshacer]:"] },
    polygon:  { label: "Polígono", icon: "polygon", alias: "POL", cmd: "POLIGONO", steps: ["Indique el número de lados <6>:", "Precise centro del polígono:", "Precise radio del círculo:"] },
    rect:     { label: "Rectángulo", icon: "rect", alias: "REC", cmd: "RECTANG", steps: ["Precise primer punto de esquina:", "Precise esquina opuesta:"] },
    circle:   { label: "Círculo", icon: "circle", alias: "C", cmd: "CIRCULO", steps: ["Precise punto central:", "Precise radio del círculo:"] },
    arc3:     { label: "Arco 3 puntos", icon: "arc3", alias: "A", cmd: "ARCO", steps: ["Precise punto inicial del arco:", "Precise segundo punto del arco:", "Precise punto final del arco:"] },
    arccse:   { label: "Arco centro, inicio, fin", icon: "arccse", alias: "ACIF", cmd: "ARCO", steps: ["Precise centro del arco:", "Precise punto inicial del arco:", "Precise punto final del arco:"] },
    arcexact: { label: "Arco exacto…", icon: "arc3", alias: "AE", cmd: "ARCOEXACTO", steps: ["Introduzca centro, radio y ángulos en el cuadro:"] },
    eraser:   { label: "Borrar", icon: "x", alias: "B / E", cmd: "BORRA", steps: ["Designe objetos a borrar:"] },
    trim:     { label: "Recortar", icon: "trim", alias: "TR", cmd: "RECORTA", steps: ["Designe objeto a recortar:"] },
    extend:   { label: "Extender", icon: "extend", alias: "EX / AL", cmd: "ALARGA", steps: ["Designe objeto a alargar:"] },
    void:     { label: "Marcar vano", icon: "void", alias: "VANO", cmd: "VANO", steps: ["Designe contorno cerrado a marcar como hueco:"] },
  };
  const ALIASES = { L: "line", LINEA: "line", LINE: "line", PL: "line", POL: "polygon", POLIGONO: "polygon", POLYGON: "polygon",
    REC: "rect", RECTANG: "rect", RECTANGLE: "rect", C: "circle", CIRCULO: "circle", CIRCLE: "circle", A: "arc3", ARCO: "arc3", ARC: "arc3",
    ACIF: "arccse", AE: "arcexact", ARCOEXACTO: "arcexact", B: "eraser", E: "eraser", BORRA: "eraser", ERASE: "eraser",
    TR: "trim", RECORTA: "trim", TRIM: "trim", EX: "extend", AL: "extend", ALARGA: "extend", EXTEND: "extend", VANO: "void" };
  const SNAP_LBL = { end: "Punto final", mid: "Punto medio", cen: "Centro", near: "Cercano", grid: "Rejilla" };

  // ── state ───────────────────────────────────────────────────────────────
  const st = {
    ents: [], sel: new Set(), tool: "select", step: 0, pts: [], last: "line",
    ortho: false, osnap: true, grid: true, snapGrid: false, dyn: true,
    osnapModes: { end: true, mid: true, cen: true, near: true },
    view: { s: 1.4, ox: 0, oy: 0 }, cursor: { x: 0, y: 0 }, snap: null, dynLen: "", dynAng: "", dynField: "len",
    polySides: 6, undo: [], redo: [], hist: [], image: "", sides: [], dims: [],
  };
  let root, svg, gGrid, gEnts, gTmp, gOver, cmdIn, raf = 0;

  function ipe200() {
    const h = 200, b = 100, tw = 5.6, tf = 8.5, x0 = -b / 2;
    const xw = -tw / 2;
    return { type: "poly", closed: true, pts: [[x0, 0], [x0 + b, 0], [x0 + b, tf], [-xw, tf], [-xw, h - tf], [x0 + b, h - tf], [x0 + b, h], [x0, h], [x0, h - tf], [xw, h - tf], [xw, tf], [x0, tf]] };
  }

  // ── geometry helpers ────────────────────────────────────────────────────
  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
  function segs(e) {
    if (e.type === "poly") { const s = []; for (let i = 0; i < e.pts.length - 1; i++) s.push([e.pts[i], e.pts[i + 1]]); if (e.closed) s.push([e.pts[e.pts.length - 1], e.pts[0]]); return s; }
    if (e.type === "arc") { const p = arcPts(e, 24), s = []; for (let i = 0; i < p.length - 1; i++) s.push([p[i], p[i + 1]]); return s; }
    return [];
  }
  function arcPts(e, n) { let a0 = e.a0, a1 = e.a1; if (a1 < a0) a1 += Math.PI * 2; const out = []; for (let i = 0; i <= n; i++) { const a = a0 + (a1 - a0) * i / n; out.push([e.c[0] + e.r * Math.cos(a), e.c[1] + e.r * Math.sin(a)]); } return out; }
  function projSeg(p, a, b) { const dx = b[0] - a[0], dy = b[1] - a[1], L = dx * dx + dy * dy || 1; let t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L; t = Math.max(0, Math.min(1, t)); return [a[0] + t * dx, a[1] + t * dy]; }
  function entDist(e, p) {
    if (e.type === "circle") return Math.abs(dist(p, e.c) - e.r);
    return Math.min(...segs(e).map(([a, b]) => dist(p, projSeg(p, a, b))));
  }
  function circle3(a, b, c) {
    const d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1])); if (Math.abs(d) < 1e-9) return null;
    const ux = ((a[0] ** 2 + a[1] ** 2) * (b[1] - c[1]) + (b[0] ** 2 + b[1] ** 2) * (c[1] - a[1]) + (c[0] ** 2 + c[1] ** 2) * (a[1] - b[1])) / d;
    const uy = ((a[0] ** 2 + a[1] ** 2) * (c[0] - b[0]) + (b[0] ** 2 + b[1] ** 2) * (a[0] - c[0]) + (c[0] ** 2 + c[1] ** 2) * (b[0] - a[0])) / d;
    return [ux, uy];
  }
  function arcFrom3(a, b, c) {
    const cc = circle3(a, b, c); if (!cc) return null;
    const ang = (p) => Math.atan2(p[1] - cc[1], p[0] - cc[0]);
    let a0 = ang(a), a1 = ang(c); const am = ang(b);
    const norm = (x) => (x % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI);
    if (norm(am - a0) > norm(a1 - a0)) [a0, a1] = [a1, a0];
    return { type: "arc", c: cc, r: dist(cc, a), a0, a1 };
  }

  // ── view transforms ─────────────────────────────────────────────────────
  const toScr = (p) => [p[0] * st.view.s + st.view.ox, -p[1] * st.view.s + st.view.oy];
  const toWld = (x, y) => [(x - st.view.ox) / st.view.s, -(y - st.view.oy) / st.view.s];
  function zoomExtents() {
    const pts = st.ents.flatMap((e) => e.type === "circle" ? [[e.c[0] - e.r, e.c[1] - e.r], [e.c[0] + e.r, e.c[1] + e.r]] : e.type === "arc" ? arcPts(e, 12) : e.pts);
    const r = svg.getBoundingClientRect();
    if (!pts.length) { st.view = { s: 1.4, ox: r.width / 2, oy: r.height / 2 }; draw(); return; }
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    const w = Math.max(...xs) - Math.min(...xs) || 1, h = Math.max(...ys) - Math.min(...ys) || 1;
    const s = Math.min((r.width - 160) / w, (r.height - 120) / h);
    st.view.s = s; st.view.ox = r.width / 2 - (Math.min(...xs) + w / 2) * s; st.view.oy = r.height / 2 + (Math.min(...ys) + h / 2) * s;
    draw();
  }

  // ── object snap (priority as in ProfileCreator._snap) ───────────────────
  function snapAt(sx, sy) {
    const p = toWld(sx, sy), tol = SNAP_PX / st.view.s;
    if (st.osnap) {
      const M = st.osnapModes;
      for (const e of st.ents) {
        if (M.end) for (const v of (e.type === "poly" ? e.pts : e.type === "arc" ? [arcPts(e, 1)[0], arcPts(e, 1)[1]] : [])) if (dist(p, v) <= tol) return { p: v, t: "end" };
      }
      if (M.mid) for (const e of st.ents) for (const [a, b] of (e.type === "poly" ? segs(e) : [])) { const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2]; if (dist(p, m) <= tol) return { p: m, t: "mid" }; }
      if (M.cen) for (const e of st.ents) if ((e.type === "circle" || e.type === "arc") && (dist(p, e.c) <= tol || Math.abs(dist(p, e.c) - e.r) <= tol * 0.6)) return { p: e.c, t: "cen" };
    }
    if (st.snapGrid) { const g = [Math.round(p[0] / GRID) * GRID, Math.round(p[1] / GRID) * GRID]; if (dist(p, g) <= tol) return { p: g, t: "grid" }; }
    if (st.osnap && st.osnapModes.near) {
      let best = null, bd = tol;
      for (const e of st.ents) {
        if (e.type === "circle") { const d = Math.abs(dist(p, e.c) - e.r); if (d < bd) { const a = Math.atan2(p[1] - e.c[1], p[0] - e.c[0]); bd = d; best = [e.c[0] + e.r * Math.cos(a), e.c[1] + e.r * Math.sin(a)]; } continue; }
        for (const [a, b] of segs(e)) { const q = projSeg(p, a, b); const d = dist(p, q); if (d < bd) { bd = d; best = q; } }
      }
      if (best) return { p: best, t: "near" };
    }
    return null;
  }
  function orthoFrom(ref, p) { return Math.abs(p[0] - ref[0]) >= Math.abs(p[1] - ref[1]) ? [p[0], ref[1]] : [ref[0], p[1]]; }
  function pickPoint() {
    let p = st.snap ? st.snap.p : st.cursor.w;
    const ref = st.pts[st.pts.length - 1];
    if (st.ortho && ref && !st.snap) p = orthoFrom(ref, p);
    return p;
  }

  // ── drawing ─────────────────────────────────────────────────────────────
  function el(tag, a, parent) { const n = document.createElementNS(NS, tag); for (const k in a) n.setAttribute(k, a[k]); parent.appendChild(n); return n; }
  function path(e) {
    if (e.type === "circle") { const c = toScr(e.c); return { tag: "circle", a: { cx: c[0], cy: c[1], r: e.r * st.view.s } }; }
    const pts = e.type === "arc" ? arcPts(e, 48) : e.pts;
    return { tag: "path", a: { d: pts.map((p, i) => (i ? "L" : "M") + toScr(p).join(" ")).join(" ") + (e.closed ? " Z" : "") } };
  }
  function draw() { cancelAnimationFrame(raf); raf = requestAnimationFrame(drawNow); }
  function drawNow() {
    if (!svg) return;
    const r = svg.getBoundingClientRect();
    gGrid.replaceChildren(); gEnts.replaceChildren(); gTmp.replaceChildren(); gOver.replaceChildren();
    // grid (REJILLA): minor every 10 mm, major every 50 mm, adapts to zoom
    if (st.grid) {
      let step = GRID; while (step * st.view.s < 8) step *= 5;
      const w0 = toWld(0, r.height), w1 = toWld(r.width, 0);
      for (let x = Math.floor(w0[0] / step) * step; x <= w1[0]; x += step) { const sx = toScr([x, 0])[0]; el("line", { x1: sx, x2: sx, y1: 0, y2: r.height, class: Math.round(x / step) % 5 ? "cad-grid" : "cad-grid major" }, gGrid); }
      for (let y = Math.floor(w0[1] / step) * step; y <= w1[1]; y += step) { const sy = toScr([0, y])[1]; el("line", { y1: sy, y2: sy, x1: 0, x2: r.width, class: Math.round(y / step) % 5 ? "cad-grid" : "cad-grid major" }, gGrid); }
    }
    // entities
    st.ents.forEach((e, i) => {
      const { tag, a } = path(e);
      const n = el(tag, Object.assign(a, { class: "cad-ent" + (e.void ? " void" : "") + (st.sel.has(i) ? " sel" : "") }), gEnts);
      n.dataset.i = i;
      if (st.sel.has(i)) (e.type === "circle" ? [e.c] : e.type === "arc" ? [arcPts(e, 1)[0], arcPts(e, 1)[1], e.c] : e.pts).forEach((v) => { const s = toScr(v); el("rect", { x: s[0] - 4, y: s[1] - 4, width: 8, height: 8, class: "cad-grip" }, gOver); });
    });
    // rubber band for the active command
    const cur = st.cursor.w ? pickPoint() : null;
    if (cur && st.pts.length) {
      const t = st.tool, P = st.pts;
      let prev = null;
      if (t === "line") { prev = { type: "poly", pts: [...P, cur] }; }
      else if (t === "rect") { const a = P[0]; prev = { type: "poly", closed: true, pts: [a, [cur[0], a[1]], cur, [a[0], cur[1]]] }; }
      else if (t === "circle") { prev = { type: "circle", c: P[0], r: dist(P[0], cur) }; }
      else if (t === "polygon") { prev = regPoly(P[0], dist(P[0], cur), st.polySides, Math.atan2(cur[1] - P[0][1], cur[0] - P[0][0])); }
      else if (t === "arc3") { prev = P.length === 1 ? { type: "poly", pts: [P[0], cur] } : arcFrom3(P[0], P[1], cur); }
      else if (t === "arccse") { prev = P.length === 1 ? { type: "poly", pts: [P[0], cur] } : { type: "arc", c: P[0], r: dist(P[0], P[1]), a0: Math.atan2(P[1][1] - P[0][1], P[1][0] - P[0][0]), a1: Math.atan2(cur[1] - P[0][1], cur[0] - P[0][0]) }; }
      if (prev) { const { tag, a } = path(prev); el(tag, Object.assign(a, { class: "cad-rubber" }), gTmp); }
    }
    // osnap marker + tooltip
    if (st.snap) {
      const s = toScr(st.snap.p), k = 6, cls = "cad-snap";
      if (st.snap.t === "end") el("rect", { x: s[0] - k, y: s[1] - k, width: 2 * k, height: 2 * k, class: cls }, gOver);
      else if (st.snap.t === "mid") el("path", { d: `M${s[0]} ${s[1] - k - 1}L${s[0] + k + 1} ${s[1] + k}L${s[0] - k - 1} ${s[1] + k}Z`, class: cls }, gOver);
      else if (st.snap.t === "cen") el("circle", { cx: s[0], cy: s[1], r: k, class: cls }, gOver);
      else if (st.snap.t === "near") el("path", { d: `M${s[0] - k} ${s[1] - k}L${s[0] + k} ${s[1] - k}L${s[0] - k} ${s[1] + k}L${s[0] + k} ${s[1] + k}Z`, class: cls }, gOver);
      else el("path", { d: `M${s[0] - k} ${s[1]}H${s[0] + k}M${s[0]} ${s[1] - k}V${s[1] + k}`, class: cls }, gOver);
      const tt = el("g", { transform: `translate(${s[0] + 12} ${s[1] + 14})` }, gOver);
      el("rect", { x: 0, y: 0, width: SNAP_LBL[st.snap.t].length * 6.4 + 12, height: 18, rx: 3, class: "cad-tip" }, tt);
      const tx = el("text", { x: 6, y: 13, class: "cad-tip-text" }, tt); tx.textContent = SNAP_LBL[st.snap.t];
    }
    // crosshair + pickbox
    if (st.cursor.sx != null) {
      const { sx, sy } = st.cursor;
      el("line", { x1: 0, x2: r.width, y1: sy, y2: sy, class: "cad-cross" }, gOver);
      el("line", { y1: 0, y2: r.height, x1: sx, x2: sx, class: "cad-cross" }, gOver);
      el("rect", { x: sx - 4, y: sy - 4, width: 8, height: 8, class: "cad-pickbox" }, gOver);
      // dynamic input (DIN): length / angle fields next to the cursor
      if (st.dyn && cur && st.pts.length && st.tool === "line") {
        const ref = st.pts[st.pts.length - 1];
        const L = st.dynLen || dist(ref, cur).toFixed(1);
        const A = st.dynAng || ((Math.atan2(cur[1] - ref[1], cur[0] - ref[0]) * 180 / Math.PI + 360) % 360).toFixed(0);
        const g = el("g", { transform: `translate(${sx + 18} ${sy - 34})` }, gOver);
        [["len", L], ["ang", A + "°"]].forEach(([k, v], i) => {
          el("rect", { x: i * 76, y: 0, width: 70, height: 20, rx: 2, class: "cad-dyn" + (st.dynField === k ? " active" : "") }, g);
          const t = el("text", { x: i * 76 + 6, y: 14, class: "cad-dyn-text" }, g); t.textContent = (k === "ang" ? "∠ " : "") + v;
        });
      }
    }
    // status coords
    const w = st.cursor.w || [0, 0];
    $("#cad-coords").textContent = `${w[0].toFixed(2)}, ${w[1].toFixed(2)}, 0.00`;
  }
  // Drawing → the Qt drawing module's shape dicts (nestube/ui_qt/dialogs/
  // profile_creator.py, ProfileShape.to_dict). Qt uses screen axes (y down), so
  // y is flipped; arcs are flattened to open polylines.
  function toQtShapes() {
    const P = (p) => [+p[0].toFixed(4), +(-p[1]).toFixed(4)];
    return st.ents.map((e) => {
      if (e.type === "circle") return { type: "circle", points: [P(e.c), P([e.c[0] + e.r, e.c[1]])], is_void: !!e.void, dim_name: "", closed: true };
      if (e.type === "arc") return { type: "line", points: arcPts(e, 24).map(P), is_void: false, dim_name: "", closed: false };
      const closed = !!e.closed && e.pts.length > 2;
      return { type: closed ? "polygon" : "line", points: e.pts.map(P), is_void: closed && !!e.void, dim_name: "", closed };
    });
  }
  function saveDrawing() {
    if (!st.ents.length) return log("No hay nada que guardar", "warn");
    if (!window.NT_NATIVE) { window.NT.toast("Perfil guardado en la base de datos"); closeCad(); return; }
    const meta = {};
    $$("[data-meta]", root).forEach((i) => { if (i.value.trim()) meta[i.dataset.meta] = i.value.trim(); });
    const sides = st.sides.filter((s) => s.manual).map((s) => ({ name: s.name, length: parseFloat(s.len) || 0, thickness: parseFloat(s.t) || 0 }));
    // The engine asks for the name/fields in its profile-save dialog, which
    // the page draws (ask-native.js); cancelling it keeps the drawing open.
    window.NTB.call("data.save_drawing", { shapes: toQtShapes(), meta, sides }).then((r) => {
      if (!r || r.cancelled) return;
      if (!r.ok) { window.NT.alert({ kind: "critical", title: "Error", msg: r.error }); return; }
      (r.alerts || []).forEach((a) => a.kind !== "question" && window.NT.alert({ kind: a.kind, title: a.title, msg: a.msg }));
      window.NT.toast("Perfil guardado en la base de datos");
      closeCad();
      if (window.NT_VIEWS) window.NT_VIEWS.reload();
    });
  }
  function regPoly(c, r, n, rot) { const pts = []; for (let i = 0; i < n; i++) { const a = rot + i * 2 * Math.PI / n; pts.push([c[0] + r * Math.cos(a), c[1] + r * Math.sin(a)]); } return { type: "poly", closed: true, pts }; }

  // ── commands ────────────────────────────────────────────────────────────
  const snapshot = () => JSON.stringify(st.ents);
  function commit(fn) { st.undo.push(snapshot()); if (st.undo.length > 50) st.undo.shift(); st.redo = []; fn(); refreshProps(); draw(); }
  function undo() { if (!st.undo.length) return log("Nada que deshacer"); st.redo.push(snapshot()); st.ents = JSON.parse(st.undo.pop()); st.sel.clear(); log("DESHACER"); refreshProps(); draw(); }
  function redo() { if (!st.redo.length) return log("Nada que rehacer"); st.undo.push(snapshot()); st.ents = JSON.parse(st.redo.pop()); log("REHACER"); refreshProps(); draw(); }
  function log(line, cls = "") { st.hist.push([line, cls]); if (st.hist.length > 60) st.hist.shift(); const h = $("#cad-hist"); h.innerHTML = st.hist.slice(-3).map(([t, c]) => `<div class="${c}">${t}</div>`).join(""); }
  function prompt() {
    const T = TOOLS[st.tool];
    const step = st.tool === "line" ? Math.min(st.step, 1) : Math.min(st.step, T.steps.length - 1);
    $("#cad-prompt").textContent = st.tool === "select" ? "Comando:" : `${T.cmd} ${T.steps[step]}`;
    $$("[data-tool]", root).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tool === st.tool)));
  }
  function setTool(t) {
    if (!TOOLS[t]) return;
    finishLine();
    if (t === "eraser" && st.sel.size) { const n = st.sel.size; commit(() => { st.ents = st.ents.filter((_, i) => !st.sel.has(i)); st.sel.clear(); }); log(`BORRA ${n} objeto(s) borrado(s)`); return; }
    if (t === "arcexact") { arcExactForm(); return; }
    st.tool = t; st.step = 0; st.pts = []; st.dynLen = st.dynAng = ""; st.dynField = "len";
    if (t !== "select") { st.last = t; log(`Comando: ${TOOLS[t].cmd}`, "cmd"); }
    prompt(); draw();
  }
  function cancel() {
    if (st.tool === "line" && st.pts.length > 1) { finishLine(); }
    else if (st.tool !== "select" || st.pts.length) log("*Cancelar*", "dim");
    else st.sel.clear();
    st.tool = "select"; st.step = 0; st.pts = []; st.dynLen = st.dynAng = ""; prompt(); draw(); refreshProps();
  }
  function finishLine() {
    if (st.tool === "line" && st.pts.length > 1) { const pts = st.pts.slice(); const closed = pts.length > 2 && dist(pts[0], pts[pts.length - 1]) < 1e-6; if (closed) pts.pop(); commit(() => st.ents.push({ type: "poly", closed, pts })); }
    if (st.tool === "line") { st.pts = []; st.step = 0; }
  }
  function click(p, hitIdx) {
    const t = st.tool;
    if (t === "select") { if (hitIdx == null) st.sel.clear(); else st.sel.has(hitIdx) ? st.sel.delete(hitIdx) : st.sel.add(hitIdx); refreshProps(); draw(); return; }
    if (t === "eraser") { if (hitIdx != null) { commit(() => st.ents.splice(hitIdx, 1)); log("1 objeto borrado"); } return; }
    if (t === "void") { if (hitIdx != null) { const e = st.ents[hitIdx]; if (e.closed || e.type === "circle") { commit(() => { e.void = !e.void; }); log(e.void ? "Contorno marcado como vano (hueco)" : "Vano desmarcado"); } else log("El objeto no es un contorno cerrado", "warn"); } return; }
    if (t === "trim") { if (hitIdx != null) trimAt(hitIdx, p); return; }
    if (t === "extend") { if (hitIdx != null) log("ALARGA: se alarga hasta el borde más cercano (geometría real en la fase 2)", "dim"); return; }
    st.pts.push(p); st.step++;
    if (t === "line") { st.dynLen = st.dynAng = ""; st.dynField = "len"; }
    if (t === "rect" && st.pts.length === 2) { const [a, b] = st.pts; commit(() => st.ents.push({ type: "poly", closed: true, pts: [a, [b[0], a[1]], b, [a[0], b[1]]] })); st.pts = []; st.step = 0; }
    if (t === "circle" && st.pts.length === 2) { const [c, q] = st.pts; commit(() => st.ents.push({ type: "circle", c, r: dist(c, q) })); st.pts = []; st.step = 0; }
    if (t === "polygon" && st.pts.length === 2) { const [c, q] = st.pts; commit(() => st.ents.push(regPoly(c, dist(c, q), st.polySides, Math.atan2(q[1] - c[1], q[0] - c[0])))); st.pts = []; st.step = 0; }
    if (t === "arc3" && st.pts.length === 3) { const a = arcFrom3(...st.pts); if (a) commit(() => st.ents.push(a)); st.pts = []; st.step = 0; }
    if (t === "arccse" && st.pts.length === 3) { const [c, a, b] = st.pts; commit(() => st.ents.push({ type: "arc", c, r: dist(c, a), a0: Math.atan2(a[1] - c[1], a[0] - c[0]), a1: Math.atan2(b[1] - c[1], b[0] - c[0]) })); st.pts = []; st.step = 0; }
    if (t === "polygon" && st.step === 1 && st.pts.length === 1) st.step = 2;
    prompt(); draw();
  }
  function trimAt(i, p) {
    const e = st.ents[i];
    if (e.type !== "poly") { commit(() => st.ents.splice(i, 1)); log("Objeto recortado"); return; }
    const S = segs(e); let k = 0, bd = Infinity; S.forEach(([a, b], j) => { const d = dist(p, projSeg(p, a, b)); if (d < bd) { bd = d; k = j; } });
    commit(() => {
      const n = e.pts.length; let chain;
      if (e.closed) { chain = []; for (let j = 1; j <= n; j++) chain.push(e.pts[(k + j) % n]); st.ents.splice(i, 1, { type: "poly", closed: false, pts: chain }); }
      else { const a = e.pts.slice(0, k + 1), b = e.pts.slice(k + 1); st.ents.splice(i, 1, ...[a, b].filter((x) => x.length > 1).map((pts) => ({ type: "poly", closed: false, pts }))); }
    });
    log("Segmento recortado");
  }
  // dynamic numeric entry (ProfileCreator.keyPressEvent): digits → length,
  // Tab or "<" → angle, Enter commits the point, Backspace edits.
  function dynCommit() {
    const ref = st.pts[st.pts.length - 1]; if (!ref) return false;
    const cur = pickPoint();
    const L = parseFloat(st.dynLen); if (!(L > 0)) return false;
    const A = st.dynAng !== "" ? parseFloat(st.dynAng) * Math.PI / 180 : Math.atan2(cur[1] - ref[1], cur[0] - ref[0]);
    const p = [ref[0] + L * Math.cos(A), ref[1] + L * Math.sin(A)];
    log(`Longitud ${L}${st.dynAng !== "" ? " < " + st.dynAng + "°" : ""}`, "dim");
    click(p, null); return true;
  }
  function runCommand(txt) {
    const raw = txt.trim().toUpperCase();
    if (!raw) { // Enter on empty: finish/repeat
      if (st.tool === "line" && st.pts.length) { if (!dynCommit()) { finishLine(); cancel(); } return; }
      if (st.tool === "polygon" && st.step === 0) { st.step = 1; prompt(); return; }
      if (st.tool === "select") { setTool(st.last); return; }
      cancel(); return;
    }
    if (st.tool === "polygon" && st.step === 0 && /^\d+$/.test(raw)) { st.polySides = Math.max(3, Math.min(64, +raw)); st.step = 1; log(`Número de lados: ${st.polySides}`, "dim"); prompt(); return; }
    const m = raw.match(/^(-?[\d.]+)\s*,\s*(-?[\d.]+)$/); // absolute X,Y
    if (m && st.tool !== "select") { click([+m[1], +m[2]], null); return; }
    const last = st.pts[st.pts.length - 1];
    if (last && st.tool !== "select") {
      const rel = raw.match(/^@(-?[\d.]+)\s*,\s*(-?[\d.]+)$/);          // @dX,dY relative
      if (rel) { click([last[0] + +rel[1], last[1] + +rel[2]], null); return; }
      const pol = raw.match(/^@?([\d.]+)\s*<\s*(-?[\d.]+)$/);           // @L<angle polar
      if (pol) { const a = +pol[2] * Math.PI / 180; click([last[0] + +pol[1] * Math.cos(a), last[1] + +pol[1] * Math.sin(a)], null); return; }
      if (/^[\d.]+$/.test(raw) && +raw > 0) {
        // A bare number: radius for circle/polygon, otherwise a length along
        // the cursor direction (AutoCAD "direct distance entry").
        if ((st.tool === "circle" || st.tool === "polygon") && st.pts.length === 1) { click([last[0] + +raw, last[1]], null); return; }
        st.dynLen = raw; st.dynAng = "";
        if (dynCommit()) { st.dynLen = ""; return; }
        st.dynLen = "";
      }
    }
    if (ALIASES[raw]) { setTool(ALIASES[raw]); return; }
    if (raw === "U" || raw === "H" || raw === "DESHACER") return undo();
    if (raw === "REHACER" || raw === "REDO") return redo();
    if (raw === "Z" || raw === "ZOOM" || raw === "ZE") { log("ZOOM Extensión", "cmd"); return zoomExtents(); }
    if (raw === "ORTO" || raw === "ORTHO") return toggle("ortho");
    if (raw === "REFENT" || raw === "OS" || raw === "OSNAP") return osnapMenu($("[data-osmenu]", root));
    log(`Comando desconocido "${raw}". Pulse F1 o vea la cinta para la lista de órdenes.`, "warn");
  }
  function toggle(k) {
    st[k] = !st[k];
    const names = { ortho: "Orto", osnap: "Referencia a objetos", grid: "Rejilla", snapGrid: "Forzcursor", dyn: "Entrada dinámica" };
    log(`<${names[k]} ${st[k] ? "act" : "desact"}>`, "dim");
    $$("[data-tg]", root).forEach((b) => b.setAttribute("aria-pressed", String(!!st[b.dataset.tg])));
    draw();
  }
  function osnapMenu(btn) {
    const r = btn.getBoundingClientRect();
    const items = Object.keys(st.osnapModes).map((k) => ({ label: SNAP_LBL[k], check: () => st.osnapModes[k], action: () => { st.osnapModes[k] = !st.osnapModes[k]; } }));
    window.NT.openMenu([{ header: "Referencia a objetos" }, ...items, "-", { label: st.osnap ? "Desactivar REFENT (F3)" : "Activar REFENT (F3)", action: () => toggle("osnap") }], r.left, r.top - 200);
  }
  function arcExactForm() {
    const f = $("#cad-arcform"); f.hidden = false; log("Comando: ARCOEXACTO", "cmd"); $("#cad-prompt").textContent = "ARCOEXACTO " + TOOLS.arcexact.steps[0];
    $("#af-cx").focus();
  }

  // ── properties palette ──────────────────────────────────────────────────
  function refreshProps() {
    const n = st.sel.size;
    $("#cad-sel").textContent = n ? `${n} objeto(s) seleccionado(s)` : "Ninguna selección";
    const e = n === 1 ? st.ents[[...st.sel][0]] : null;
    const kind = e ? { poly: e.closed ? "Polilínea cerrada" : "Polilínea", circle: "Círculo", arc: "Arco" }[e.type] : n ? "Varios" : "—";
    let len = "—";
    if (e) len = e.type === "circle" ? (2 * Math.PI * e.r).toFixed(2) : segs(e).reduce((s, [a, b]) => s + dist(a, b), 0).toFixed(2);
    $("#cad-sel-type").value = kind; $("#cad-sel-len").value = len; $("#cad-sel-void").value = e ? (e.void ? "Sí" : "No") : "—";
    $("#cad-sides").innerHTML = st.sides.length ? st.sides.map((s) => `<tr><td>${s.name}</td><td class="num">${s.len}</td><td class="num">${s.t}</td></tr>`).join("") : `<tr><td colspan="3" style="color:var(--cad-dim)">Sin lados asignados</td></tr>`;
  }
  function thumbnail() {
    // same look as the catalog PNGs: grey line art, light fill, transparent bg
    const pts = st.ents.flatMap((e) => e.type === "circle" ? [[e.c[0] - e.r, e.c[1] - e.r], [e.c[0] + e.r, e.c[1] + e.r]] : e.type === "arc" ? arcPts(e, 12) : e.pts);
    if (!pts.length) return "";
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]); const x0 = Math.min(...xs), y0 = Math.min(...ys), w = Math.max(...xs) - x0 || 1, h = Math.max(...ys) - y0 || 1;
    const s = 112 / Math.max(w, h), ox = 64 - (x0 + w / 2) * s, oy = 64 + (y0 + h / 2) * s;
    const P = (p) => `${(p[0] * s + ox).toFixed(1)} ${(-p[1] * s + oy).toFixed(1)}`;
    const body = st.ents.map((e) => e.type === "circle" ? `<circle cx="${e.c[0] * s + ox}" cy="${-e.c[1] * s + oy}" r="${e.r * s}" fill="${e.void ? "#fff" : "#C9C9CF"}" stroke="#55555C"/>`
      : `<path d="${(e.type === "arc" ? arcPts(e, 32) : e.pts).map((p, i) => (i ? "L" : "M") + P(p)).join("")}${e.closed ? "Z" : ""}" fill="${e.closed ? (e.void ? "#fff" : "#C9C9CF") : "none"}" stroke="#55555C"/>`).join("");
    return "data:image/svg+xml;utf8," + encodeURIComponent(`<svg xmlns="${NS}" width="128" height="128" viewBox="0 0 128 128">${body}</svg>`);
  }
  function setImage(src) { st.image = src; $("#cad-img").innerHTML = src ? `<img src="${src}" alt="Imagen del perfil">` : `<span style="color:#888;font-size:var(--fs-sm)">(sin imagen)</span>`; }

  // ── DOM ─────────────────────────────────────────────────────────────────
  const rb = (t, big) => { const T = TOOLS[t]; return `<button class="rb${big ? " big" : ""}" data-tool="${t}" title="${T.label} (${T.alias})${T.cmd ? " · orden " + T.cmd : ""}">${I(T.icon, big ? "lg" : "")}<span>${T.label}</span>${big ? "" : `<kbd>${T.alias}</kbd>`}</button>`; };
  function build() {
    root = document.createElement("div"); root.id = "cad"; root.className = "cad"; root.hidden = true;
    root.setAttribute("role", "dialog"); root.setAttribute("aria-modal", "true"); root.setAttribute("aria-label", "Módulo de dibujo");
    root.innerHTML = `
    <div class="cad-title">
      <svg class="brand-mark" style="width:18px;height:18px" aria-hidden="true"><use href="#logo"/></svg>
      <strong>Módulo de dibujo</strong><span class="cad-dim">— <span id="cad-docname">IPE 200</span>.perfil</span>
      <span style="flex:1"></span>
      <button class="btn" data-cad="clear">Limpiar</button>
      <button class="btn" data-cad="generate">⮕ Generar perfil (dibujo actual)</button>
      <button class="btn primary" data-cad="save">${I("save", "sm")}Guardar</button>
      <button class="btn icon-only" data-cad="close" title="Cerrar">${I("x")}</button>
    </div>
    <div class="cad-ribbon" role="toolbar" aria-label="Cinta de opciones">
      <div class="rpanel"><div class="rbody">${rb("line", true)}<div class="rcol">${rb("polygon")}${rb("rect")}${rb("circle")}</div><div class="rcol">${rb("arc3")}${rb("arccse")}${rb("arcexact")}</div></div><div class="rlabel">Dibujo</div></div>
      <div class="rpanel"><div class="rbody"><div class="rcol">${rb("eraser")}${rb("trim")}${rb("extend")}</div></div><div class="rlabel">Modificar</div></div>
      <div class="rpanel"><div class="rbody">${rb("void", true)}<div class="rcol"><button class="rb" data-cad="dim" title="Asigna un nombre de dimensión (h, b, tw…) a la selección">${I("ortho")}<span>Asignar dimensión</span><kbd>DIM</kbd></button><button class="rb" data-cad="thick" title="Asignar espesor a la selección">${I("common")}<span>Asignar espesor</span></button></div></div><div class="rlabel">Perfil</div></div>
      <div class="rpanel"><div class="rbody">${rb("select", true)}<div class="rcol"><button class="rb" data-cad="undo" title="Deshacer (Ctrl+Z · U)">${I("undo")}<span>Deshacer</span><kbd>Ctrl+Z</kbd></button><button class="rb" data-cad="redo" title="Rehacer (Ctrl+Y)">${I("redo")}<span>Rehacer</span><kbd>Ctrl+Y</kbd></button><button class="rb" data-cad="zext" title="Zoom extensión (Z · doble clic con la rueda)">${I("fit")}<span>Zoom extensión</span><kbd>Z</kbd></button></div></div><div class="rlabel">Utilidades</div></div>
      <div class="rpanel"><div class="rbody"><div class="rcol"><button class="rb" data-cad="idxf">${I("import")}<span>Importar DXF</span></button><button class="rb" data-cad="edxf">${I("dxf")}<span>Exportar DXF</span></button><button class="rb" data-cad="epng">${I("image")}<span>Exportar PNG (transparente)</span></button></div></div><div class="rlabel">Archivo</div></div>
    </div>
    <div class="cad-body">
      <div class="cad-model" id="cad-model">
        <span class="cad-vplabel">[−][Superior][2D Estructura alámbrica] · mm</span>
        <svg id="cad-svg"><g id="cad-grid"></g><g id="cad-ents"></g><g id="cad-tmp"></g><g id="cad-over"></g></svg>
        <svg class="cad-ucs" viewBox="0 0 60 60" aria-hidden="true"><path d="M10 50H46M10 50V14" stroke="#E5484D" stroke-width="2" fill="none"/><path d="M10 50V14" stroke="#46A758" stroke-width="2"/><path d="M46 50l-6-3v6zM10 14l-3 6h6z" fill="#E5484D"/><path d="M10 14l-3 6h6z" fill="#46A758"/><text x="48" y="54" fill="#E5484D" font-size="10">X</text><text x="4" y="12" fill="#46A758" font-size="10">Y</text></svg>
        <form class="cad-pop" id="cad-arcform" hidden>
          <strong>Arco con datos exactos</strong>
          <div class="field-grid"><label class="field">Centro X (mm)<input class="cad-in" id="af-cx" value="0"></label><label class="field">Centro Y (mm)<input class="cad-in" id="af-cy" value="100"></label>
          <label class="field">Radio (mm)<input class="cad-in" id="af-r" value="40"></label><label class="field">Ángulo inicial (°)<input class="cad-in" id="af-a0" value="0"></label>
          <label class="field">Ángulo final (°)<input class="cad-in" id="af-a1" value="180"></label></div>
          <div style="display:flex;gap:6px;justify-content:flex-end"><button type="button" class="btn" data-cad="arc-cancel">Cancelar</button><button class="btn primary">Aceptar</button></div>
        </form>
      </div>
      <aside class="cad-props" aria-label="Propiedades">
        <div class="cad-ph">Propiedades</div>
        <details open><summary>Imagen del perfil</summary>
          <div class="img-tile zoomable" id="cad-img" style="height:120px" title="Abrir en el visor de imágenes"></div>
          <div style="display:flex;gap:6px"><button class="btn" style="flex:1" data-cad="generate">⮕ Generar</button><button class="btn" style="flex:1" data-cad="importimg">Importar imagen</button></div>
          <input type="file" id="cad-imgfile" accept="image/png,image/jpeg,image/svg+xml" hidden>
        </details>
        <details open><summary>Selección</summary>
          <div class="cad-kv"><span>Estado</span><span id="cad-sel">Ninguna selección</span></div>
          <div class="cad-kv"><span>Tipo</span><input class="cad-in" id="cad-sel-type" readonly></div>
          <div class="cad-kv"><span>Longitud</span><input class="cad-in" id="cad-sel-len" readonly></div>
          <div class="cad-kv"><span>Vano</span><input class="cad-in" id="cad-sel-void" readonly></div>
        </details>
        <details open><summary>Asignar dimensión</summary>
          <div style="display:flex;gap:6px"><input class="cad-in" id="cad-dimname" placeholder="Nombre del campo (h, b, tw…)" style="flex:1"><button class="btn" data-cad="dim">Asignar a selección</button></div>
          <div style="display:flex;gap:6px"><input class="cad-in" id="cad-thick" placeholder="Espesor 0.0" style="flex:1"><button class="btn" data-cad="thick">Asignar espesor</button></div>
        </details>
        <details open><summary>Lados y espesores</summary>
          <table class="cad-table"><thead><tr><th>Lado</th><th class="num">Largo mm</th><th class="num">t</th></tr></thead><tbody id="cad-sides"></tbody></table>
          <div style="display:grid;grid-template-columns:1fr 64px 44px auto;gap:4px"><input class="cad-in" id="ms-name" placeholder="Nombre"><input class="cad-in" id="ms-len" placeholder="Largo"><input class="cad-in" id="ms-t" placeholder="t"><button class="btn icon-only" data-cad="side-add" title="Añadir lado manualmente">${I("plus", "sm")}</button></div>
          <button class="btn" data-cad="side-del">Quitar último lado manual</button>
        </details>
        <details open><summary>Datos del perfil</summary>
          ${[["profile_name", "Perfil/Material", "IPE 200"], ["material", "Material", "Acero al Carbono"], ["quality", "Calidad", "S235"], ["h", "h (mm)", "200"], ["b", "b (mm)", "100"], ["tw", "tw (mm)", "5.6"], ["tf", "tf (mm)", "8.5"], ["seccion_cm2", "Sección (cm²)", "28.5"], ["peso_lineal_kg_m", "Peso lineal", "22.4"], ["kg_por_m", "Kg por metro (kg/m)", "22.4"], ["precio_kg", "Precio €/kg", "0.85"], ["precio_m", "Precio €/m", ""], ["peso_especifico", "Peso específico (t/m³)", "7.85"]]
            .map(([key, k, v]) => `<div class="cad-kv"><span>${k}</span><input class="cad-in" data-meta="${key}" value="${window.NT_NATIVE && key !== "peso_especifico" ? "" : v}"></div>`).join("")}
        </details>
      </aside>
    </div>
    <div class="cad-cmd">
      <div id="cad-hist" class="cad-hist"></div>
      <div class="cad-cmdline">${I("chevron-right", "sm")}<span id="cad-prompt">Comando:</span><input id="cad-cmdin" autocomplete="off" spellcheck="false" aria-label="Línea de comandos" placeholder="Escriba una orden (L, REC, C, A, TR…)"></div>
    </div>
    <div class="cad-status">
      <span class="mono" id="cad-coords">0.00, 0.00, 0.00</span>
      <span class="cad-tab">MODELO</span>
      <span style="flex:1"></span>
      <button data-tg="grid" title="Rejilla (F7)">REJILLA</button>
      <button data-tg="snapGrid" title="Forzcursor: forzar a la rejilla (F9)">FORZC</button>
      <button data-tg="ortho" title="Modo orto (F8)">ORTO</button>
      <button data-tg="osnap" title="Referencia a objetos (F3) · clic derecho: modos">REFENT</button><button data-osmenu title="Modos de referencia a objetos" style="padding:0 4px">▾</button>
      <button data-tg="dyn" title="Entrada dinámica (F12)">DIN</button>
      <span class="cad-dim">mm</span>
    </div>`;
    document.body.appendChild(root);
    svg = $("#cad-svg", root); gGrid = $("#cad-grid", root); gEnts = $("#cad-ents", root); gTmp = $("#cad-tmp", root); gOver = $("#cad-over", root); cmdIn = $("#cad-cmdin", root);
    wire();
  }

  function wire() {
    root.addEventListener("click", (e) => {
      const tb = e.target.closest("[data-tool]"); if (tb) { setTool(tb.dataset.tool); cmdIn.focus(); return; }
      if (e.target.closest("[data-osmenu]")) { osnapMenu(e.target.closest("[data-osmenu]")); return; }
      const tg = e.target.closest("[data-tg]"); if (tg) { toggle(tg.dataset.tg); return; }
      const c = e.target.closest("[data-cad]"); if (!c) return;
      ({
        close: closeCad, save: saveDrawing,
        clear: () => window.NT.confirmDialog({ title: "Limpiar", text: "¿Borrar todo el dibujo?", ok: () => commit(() => { st.ents = []; st.sel.clear(); }) }),
        generate: () => { const s = thumbnail(); if (!s) return log("No hay nada dibujado", "warn"); setImage(s); log("Imagen del perfil generada desde el dibujo"); },
        importimg: () => $("#cad-imgfile", root).click(),
        undo, redo, zext: zoomExtents,
        dim: () => { const n = $("#cad-dimname", root).value.trim(); if (!st.sel.size) return log("Designe primero el objeto a acotar", "warn"); if (!n) return $("#cad-dimname", root).focus(); st.dims.push(n); log(`Dimensión «${n}» asignada a ${st.sel.size} objeto(s)`); },
        thick: () => { const v = parseFloat($("#cad-thick", root).value); if (!st.sel.size) return log("Designe primero los lados", "warn"); if (!(v > 0)) return $("#cad-thick", root).focus();
          [...st.sel].forEach((i) => { const e = st.ents[i]; st.sides.push({ name: `Lado ${st.sides.length + 1}`, len: (e.type === "circle" ? 2 * Math.PI * e.r : segs(e).reduce((s, [a, b]) => s + dist(a, b), 0)).toFixed(1), t: v }); }); refreshProps(); log(`Espesor ${v} mm asignado`); },
        "side-add": () => { const n = $("#ms-name", root).value || `Lado ${st.sides.length + 1}`, l = $("#ms-len", root).value, t = $("#ms-t", root).value; if (!l) return $("#ms-len", root).focus(); st.sides.push({ name: n, len: l, t: t || "—", manual: true }); refreshProps(); },
        "side-del": () => { const i = st.sides.map((s) => !!s.manual).lastIndexOf(true); if (i >= 0) { st.sides.splice(i, 1); refreshProps(); } },
        idxf: () => window.NT.toast("Importar DXF: líneas, polilíneas, círculos y arcos"), edxf: () => window.NT.toast("Dibujo exportado a DXF"), epng: () => window.NT.toast("PNG transparente exportado"),
        "arc-cancel": () => { $("#cad-arcform", root).hidden = true; cancel(); },
      })[c.dataset.cad]();
    });
    $("#cad-img", root).addEventListener("click", () => st.image && window.NT_VIEWER.open([{ name: $("#cad-docname", root).textContent, src: st.image, file: "perfil.png" }], 0, { onAssign: () => $("#cad-imgfile", root).click() }));
    $("#cad-imgfile", root).addEventListener("change", (e) => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => { setImage(r.result); log(`Imagen importada: ${f.name}`); }; r.readAsDataURL(f); e.target.value = ""; });
    $("#cad-arcform", root).addEventListener("submit", (e) => {
      e.preventDefault(); const v = (id) => parseFloat($(id, root).value) || 0;
      commit(() => st.ents.push({ type: "arc", c: [v("#af-cx"), v("#af-cy")], r: Math.abs(v("#af-r")) || 1, a0: v("#af-a0") * Math.PI / 180, a1: v("#af-a1") * Math.PI / 180 }));
      $("#cad-arcform", root).hidden = true; log("Arco exacto creado"); cancel();
    });
    $('[data-tg="osnap"]', root).addEventListener("contextmenu", (e) => { e.preventDefault(); osnapMenu(e.currentTarget); });

    const model = $("#cad-model", root);
    let pan = null, lastMid = 0;
    model.addEventListener("pointermove", (e) => {
      const r = svg.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top;
      if (pan) { st.view.ox += sx - pan[0]; st.view.oy += sy - pan[1]; pan = [sx, sy]; }
      st.cursor = { sx, sy, w: toWld(sx, sy) };
      st.snap = (st.tool !== "select" && st.tool !== "eraser" && st.tool !== "void" && st.tool !== "trim" && st.tool !== "extend") ? snapAt(sx, sy) : null;
      draw();
    });
    model.addEventListener("pointerleave", () => { st.cursor = { w: st.cursor.w }; st.snap = null; draw(); });
    model.addEventListener("pointerdown", (e) => {
      if (e.target.closest(".cad-pop")) return;
      const r = svg.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top;
      if (e.button === 1) { e.preventDefault(); const now = Date.now(); if (now - lastMid < 350) zoomExtents(); lastMid = now; pan = [sx, sy]; model.classList.add("panning"); return; }
      if (e.button !== 0) return;
      const w = toWld(sx, sy), tol = 6 / st.view.s;
      let hit = null, bd = tol; st.ents.forEach((en, i) => { const d = entDist(en, w); if (d < bd) { bd = d; hit = i; } });
      click(st.tool === "select" || ["eraser", "void", "trim", "extend"].includes(st.tool) ? w : pickPoint(), hit);
      cmdIn.focus({ preventScroll: true });
    });
    window.addEventListener("pointerup", () => { if (pan) { pan = null; model.classList.remove("panning"); } });
    model.addEventListener("dblclick", () => { if (st.tool === "line") { st.pts.pop(); finishLine(); cancel(); } });
    model.addEventListener("contextmenu", (e) => { e.preventDefault(); if (st.tool === "line" && st.pts.length) { finishLine(); cancel(); } else if (st.tool === "select") setTool(st.last); else cancel(); });
    model.addEventListener("wheel", (e) => {
      e.preventDefault(); const r = svg.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top;
      const f = e.deltaY < 0 ? 1.15 : 1 / 1.15, ns = Math.max(0.05, Math.min(80, st.view.s * f)), k = ns / st.view.s;
      st.view.ox = sx - (sx - st.view.ox) * k; st.view.oy = sy - (sy - st.view.oy) * k; st.view.s = ns; draw();
    }, { passive: false });

    // keyboard: AutoCAD sends typing to the command line from anywhere
    // keep focus on the command line when clicking the model (the browser
    // would otherwise move focus to <body> on mousedown)
    model.addEventListener("mousedown", (e) => { if (!e.target.closest(".cad-pop")) e.preventDefault(); });
    document.addEventListener("keydown", (e) => {
      if (root.hidden) return;
      if (e.target.closest && (e.target.closest(".cad-props") || e.target.closest(".cad-pop") || e.target.closest(".modal"))) { if (e.key === "Escape") { $("#cad-arcform", root).hidden = true; cmdIn.focus(); } return; }
      const k = e.key;
      const fk = { F3: "osnap", F7: "grid", F8: "ortho", F9: "snapGrid", F12: "dyn" }[k];
      if (fk) { e.preventDefault(); toggle(fk); return; }
      if (e.ctrlKey && k.toLowerCase() === "z") { e.preventDefault(); undo(); return; }
      if (e.ctrlKey && k.toLowerCase() === "y") { e.preventDefault(); redo(); return; }
      if (k === "Escape") { e.preventDefault(); e.stopPropagation(); cmdIn.value = ""; cancel(); return; }
      if (k === "Delete" && st.sel.size && st.tool === "select") { e.preventDefault(); setTool("eraser"); return; }
      const drawing = st.tool === "line" && st.pts.length && !cmdIn.value;
      if (drawing && st.dyn) {
        if (k === "Tab") { e.preventDefault(); st.dynField = st.dynField === "len" ? "ang" : "len"; draw(); return; }
        if (k === "<") { e.preventDefault(); st.dynField = "ang"; draw(); return; }
        if (/^[\d.\-]$/.test(k)) { e.preventDefault(); st.dynField === "ang" ? (st.dynAng += k) : (st.dynLen += k); draw(); return; }
        if (k === "Backspace" && (st.dynLen || st.dynAng)) { e.preventDefault(); st.dynField === "ang" && st.dynAng ? (st.dynAng = st.dynAng.slice(0, -1)) : (st.dynLen = st.dynLen.slice(0, -1)); draw(); return; }
      }
      if (k === "Enter" || (k === " " && !cmdIn.value.includes(","))) {
        e.preventDefault(); const v = cmdIn.value; cmdIn.value = "";
        if (v.trim()) log(`${$("#cad-prompt", root).textContent} ${v.toUpperCase()}`, "echo");
        runCommand(v); return;
      }
      if (document.activeElement !== cmdIn && k.length === 1 && !e.ctrlKey && !e.metaKey) { cmdIn.focus(); }
    });
    new ResizeObserver(() => draw()).observe(model);
  }

  function open(name = "IPE 200") {
    if (!root) build();
    root.hidden = false;
    $("#cad-docname", root).textContent = name;
    if (window.NT_NATIVE) {
      // Real app: every open is a new, blank drawing.
      st.ents = []; st.sel.clear(); st.undo = []; st.redo = []; st.sides = []; setImage("");
    } else {
      if (!st.ents.length) st.ents = [ipe200()];
      st.sides = [{ name: "Alma", len: "183.0", t: 5.6 }, { name: "Ala sup.", len: "100.0", t: 8.5 }, { name: "Ala inf.", len: "100.0", t: 8.5 }];
      setImage((window.NT_PROFILE_IMAGES || {})["catalog-ac-ipe-200"] || "");
    }
    $$("[data-tg]", root).forEach((b) => b.setAttribute("aria-pressed", String(!!st[b.dataset.tg])));
    st.hist = []; log("Módulo de dibujo · escriba una orden o elija una herramienta en la cinta", "dim");
    log("Clic para añadir puntos. Doble clic, Enter o Esc para terminar. Escriba una longitud y pulse Enter; Tab o < para el ángulo.", "dim");
    prompt(); refreshProps();
    requestAnimationFrame(() => { zoomExtents(); cmdIn.focus(); });
  }
  function closeCad() { cancel(); root.hidden = true; }

  window.NT_CAD = { open, close: closeCad, state: st };
})();
