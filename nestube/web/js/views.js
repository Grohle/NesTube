/* ==========================================================================
   NesTube web UI — Jobs, Cuts, Costs, Profiles and Stock views (MOCKUP)
   Example data only. In the functional stage each render function is fed
   from the Python bridge (database.py, stock_db.py, profile_catalog.py,
   logic.py) instead of the constants below.
   ========================================================================== */
(function () {
  "use strict";
  const { $, $$, ICON, toast, confirmDialog, openMenu } = window.NT;
  const showView = (v) => (window.NT.go || window.NT.showView)(v);
  const N = () => window.NestCanvas;
  const fmt = (v, d = 2) => Number(v).toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d });

  // ── example data ────────────────────────────────────────────────────────
  const JOBS = [
    { name: "JOB-260629-0001", client: "Cliente Demo SL", date: "29/06/2026 11:48", order: "PED-2026-001", offer: "OFR-2026-042", desc: "Estructura nave A", material: "IPE 200 · S235", bars: 7, eff: 82.9, total: 800.07 },
    { name: "JOB-260702-0002", client: "Talleres Arrieta", date: "02/07/2026 09:15", order: "PED-2026-007", offer: "OFR-2026-051", desc: "Pórtico de carga", material: "HEA 140 · S275", bars: 3, eff: 76.4, total: 1214.30 },
    { name: "JOB-260715-0003", client: "Carpintería Metálica Sur", date: "15/07/2026 16:02", order: "PED-2026-012", offer: "", desc: "Barandilla inox", material: "Tubo □ 40×40×2 · Inox", bars: 5, eff: 88.1, total: 642.90 },
    { name: "JOB-260801-0004", client: "Cliente Demo SL", date: "01/08/2026 08:40", order: "PED-2026-019", offer: "OFR-2026-060", desc: "Correas cubierta", material: "Correa C 125×50×2 · Galv.", bars: 12, eff: 91.3, total: 1570.00 },
  ];
  let jobSel = 0;

  const PAGES = ["IPE 200 · S235", "HEA 140 · S275", "Tubo □ 40×40×2 · Inox"];

  const COSTS = [
    ["Viga principal", 3500, 4, 78.40, 2.10, 76.64, 1.50, 78.14, 21.90, 312.54],
    ["Correa", 1200, 6, 26.88, 0.72, 26.28, 1.50, 27.78, 21.90, 166.65],
    ["Montante", 800, 8, 17.92, 0.48, 17.52, 1.50, 19.02, 21.90, 152.13],
    ["Diagonal", 2800, 2, 62.72, 1.68, 61.31, 2.55, 63.86, 21.90, 127.72],
    ["Placa base", 400, 4, 8.96, 0.24, 8.76, 1.50, 10.26, 21.90, 41.03],
  ];

  // profile_catalog.CATALOG + one custom profile (U-50x50x40x3 drawn in the
  // drawing module). [id, name, family, material, h, b, tw, tf, cm², kg/m, image]
  const PROFILES = [
    ["AC-IPE-100", "IPE 100", "Viga I", "Acero al Carbono", 100, 55, 4.1, 5.7, 10.3, 8.1, "catalog-ac-ipe-100"],
    ["AC-IPE-200", "IPE 200", "Viga I", "Acero al Carbono", 200, 100, 5.6, 8.5, 28.5, 22.4, "catalog-ac-ipe-200"],
    ["AC-HEA-140", "HEA 140", "Viga H", "Acero al Carbono", 133, 140, 5.5, 8.5, 31.4, 24.7, "catalog-ac-hea-140"],
    ["AC-UPN-100", "UPN 100", "Viga U", "Acero al Carbono", 100, 50, 6, 8.5, 13.5, 10.6, "catalog-ac-upn-100"],
    ["AC-ANG-50", "L 50x50x5", "Angular", "Acero al Carbono", 50, 50, 5, 5, 4.8, 3.77, "catalog-ac-ang-50"],
    ["AC-TUB-C40", "TC 40x40x3", "Cuadrado", "Acero al Carbono", 40, 40, 3, 3, 4.2, 3.3, "catalog-ac-tub-c40"],
    ["AC-TUB-R60", "TR Ø60.3x3", "Redondo", "Acero al Carbono", 60.3, "", 3, "", 5.4, 4.24, "catalog-ac-tub-r60"],
    ["GALV-TC-1/2", "Tubo ISO Ø21.3x2.6 (1/2\")", "Redondo", "Acero Galvanizado", 21.3, "", 2.6, "", 1.53, 1.22, "catalog-galv-tc-1-2"],
    ["GALV-TC-1", "Tubo ISO Ø33.7x3.2 (1\")", "Redondo", "Acero Galvanizado", 33.7, "", 3.2, "", 3.07, 2.44, "catalog-galv-tc-1"],
    ["GALV-COR-C125", "Correa C 125x50x2", "Perfil C", "Acero Galvanizado", 125, 50, 2, 2, 4.5, 3.65, "catalog-galv-cor-c125"],
    ["GALV-COR-Z150", "Correa Z 150x50x2", "Perfil Z", "Acero Galvanizado", 150, 50, 2, 2, 5, 4.05, "catalog-galv-cor-z150"],
    ["INX-TR-42", "Tubo Inox Ø42.4x1.5", "Redondo", "Acero Inoxidable", 42.4, "", 1.5, "", 1.93, 1.54, "catalog-inx-tr-42"],
    ["INX-TR-50", "Tubo Inox Ø50.8x1.5", "Redondo", "Acero Inoxidable", 50.8, "", 1.5, "", 2.32, 1.85, "catalog-inx-tr-50"],
    ["INX-TC-40", "Tubo Inox 40x40x1.5", "Cuadrado", "Acero Inoxidable", 40, 40, 1.5, 1.5, 2.27, 1.81, "catalog-inx-tc-40"],
    ["INX-MAC-20", "Macizo Inox Ø20", "Redondo", "Acero Inoxidable", 20, "", "", "", 3.14, 2.49, "catalog-inx-mac-20"],
    ["INX-PLE-50", "Pletina Inox 50x5", "Pletina", "Acero Inoxidable", 50, 5, "", "", 2.5, 1.98, "catalog-inx-ple-50"],
    ["ALU-RAN-20", "Perfil Ranurado 20x20", "Ranurado", "Aluminio", 20, 20, "", "", 1.66, 0.45, "catalog-alu-ran-20"],
    ["ALU-RAN-40", "Perfil Ranurado 40x40", "Ranurado", "Aluminio", 40, 40, "", "", 5.37, 1.45, "catalog-alu-ran-40"],
    ["ALU-RAN-45", "Perfil Ranurado 45x45", "Ranurado", "Aluminio", 45, 45, "", "", 5.55, 1.5, "catalog-alu-ran-45"],
    ["ALU-RAN-4080", "Perfil Ranurado 40x80", "Ranurado", "Aluminio", 80, 40, "", "", 9.63, 2.6, "catalog-alu-ran-4080"],
    ["ALU-TUB-R50", "Tubo Al Ø50x2", "Redondo", "Aluminio", 50, "", 2, "", 3.01, 0.81, "catalog-alu-tub-r50"],
    ["ALU-ANG-30", "L Aluminio 30x30x3", "Angular", "Aluminio", 30, 30, 3, 3, 1.71, 0.46, "catalog-alu-ang-30"],
    ["CUSTOM-U50", "U-50x50x40x3", "Personalizado", "Acero al Carbono", 50, 50, 3, 3, 4.1, 3.22, "U-50x50x40x3"],
  ];
  const FAMILIES = [["all", "Todos"], ["vigas", "Vigas I / H / U"], ["Angular", "Angulares"], ["tubos", "Tubos"], ["cz", "Correas C / Z"],
    ["macizos", "Macizos y pletinas"], ["Ranurado", "Ranurados"], ["Personalizado", "Personalizados"]];
  function famOf(p) {
    const f = p[2];
    if (f === "Viga I" || f === "Viga H" || f === "Viga U") return "vigas";
    if (f === "Perfil C" || f === "Perfil Z") return "cz";
    if (f === "Pletina" || /Macizo/.test(p[1])) return "macizos";
    if (f === "Redondo" || f === "Cuadrado") return "tubos";
    return f;
  }
  const imgOf = (p) => (window.NT_PROFILE_IMAGES || {})[p[10]] || "";
  const viewerItems = (rows) => rows.map((p) => ({ name: p[1], src: imgOf(p), file: p[10] + ".png", material: p[3], w: 128, h: 128 }));
  window.NT_PROFILES = { PROFILES, imgOf, viewerItems };
  let profFamily = "all", profView = "list", profSel = 1;

  const STOCK = [
    { prof: "IPE 200", q: "S235-000001-00", len: 6000, qty: 1, ok: true, retal: false, job: "", used: "" },
    { prof: "IPE 200", q: "S235-000002-00", len: 6000, qty: 1, ok: true, retal: false, job: "", used: "" },
    { prof: "IPE 200", q: "S235-000003-00", len: 6000, qty: 1, ok: true, retal: false, job: "", used: "" },
    { prof: "HEA 140", q: "S275-000004-00", len: 12000, qty: 2, ok: true, retal: false, job: "", used: "" },
    { prof: "IPE 200", q: "S235-000001-R1", len: 1182, qty: 1, ok: true, retal: true, job: "JOB-260629-0001", used: "" },
    { prof: "IPE 200", q: "S235-000007-00", len: 6000, qty: 1, ok: false, retal: false, job: "", used: "JOB-260629-0001" },
  ];
  let stockSel = 4;

  // ── section drawings (profile thumbnails) ───────────────────────────────
  function sectionSVG(fam, size = 100) {
    const s = `fill="var(--bg-mid)" stroke="var(--text-sec)" stroke-width="2" stroke-linejoin="round"`;
    const shapes = {
      I: `<path d="M22 14h56v9H54v54h24v9H22v-9h24V23H22z" ${s}/>`,
      H: `<path d="M14 18h72v10H54v44h32v10H14V72h32V28H14z" ${s}/>`,
      U: `<path d="M30 14h44v8H40v56h34v8H30z" ${s}/>`,
      C: `<path d="M34 14h34v10h-4v-4H40v60h24v-4h4v10H34z" ${s}/>`,
      Z: `<path d="M44 14h26v6H50v60h-24v-6h18z" ${s}/>`,
      L: `<path d="M28 14h9v63h45v9H28z" ${s}/>`,
      O: `<circle cx="50" cy="50" r="32" ${s}/>`,
      T: `<path d="M18 18h64v64H18zM24 24v52h52V24z" fill-rule="evenodd" ${s}/>`,
      S: `<path d="M20 20h60v60H20z" ${s}/><circle cx="50" cy="50" r="13" fill="var(--bg-panel)" stroke="var(--text-sec)" stroke-width="2"/>`,
    };
    return `<svg viewBox="0 0 100 100" width="${size}" height="${size}" aria-hidden="true">${shapes[fam] || shapes.T}</svg>`;
  }

  // ── material pages (Cuts / Costs left panel) ────────────────────────────
  function renderPages() {
    $$("[data-pages]").forEach((list) => {
      const items = PAGES.slice(); if (list.dataset.total) items.push("Total");
      list.innerHTML = items.map((n, i) => `<div class="row page-row${i === 0 ? " active" : ""}" tabindex="0">${ICON("check", "sm check")}<div class="row-main"><span class="row-title">${n === "Total" ? "<b>Total</b> · todos los materiales" : n}</span></div></div>`).join("");
      $$(".page-row", list).forEach((r) => {
        r.addEventListener("click", () => { $$(".page-row", list).forEach((x) => x.classList.toggle("active", x === r)); });
        r.addEventListener("contextmenu", (e) => { e.preventDefault(); openMenu([{ label: "Renombrar pestaña…", action: () => toast("Renombrar sub-pestaña") }, "-", { label: "Eliminar pestaña", danger: true, action: () => toast("Sub-pestaña eliminada") }], e.clientX, e.clientY); });
      });
    });
  }

  // ── Jobs ────────────────────────────────────────────────────────────────
  function renderJobs() {
    const q = ($("#jobs-search").value || "").toLowerCase(); const f = $("#jobs-field").value;
    const keyOf = { name: "name", client: "client", material: "material", order: "order", offer: "offer" }[f];
    const vis = JOBS.map((j, i) => [j, i]).filter(([j]) => !q || String(j[keyOf]).toLowerCase().includes(q));
    $("#jobs-count").textContent = vis.length;
    $("#jobs-list").innerHTML = vis.length ? vis.map(([j, i]) => `<div class="row${i === jobSel ? " active" : ""}" data-job="${i}" tabindex="0">
        ${ICON("folder", "sm")}<div class="row-main"><span class="row-title mono">${j.name}</span><span class="row-sub" style="font-family:var(--font-ui)">${j.client} · ${j.date}</span></div></div>`).join("")
      : `<div class="empty-hint">No hay jobs que coincidan</div>`;
    $$("#jobs-list [data-job]").forEach((r) => r.addEventListener("click", () => { jobSel = +r.dataset.job; renderJobs(); }));
    const j = JOBS[jobSel];
    $("#job-title").textContent = j.name; $("#job-date").lastChild.textContent = j.date;
    $("#job-name").value = j.name; $("#job-desc").value = j.desc; $("#job-client").value = j.client; $("#job-order").value = j.order; $("#job-offer").value = j.offer;
    $("#job-kpis").innerHTML = [["Material", j.material, ""], ["Barras", j.bars, "de 6000 mm"], ["Aprovechamiento", j.eff.toFixed(1) + " %", ""], ["Total pedido", fmt(j.total) + " €", "IVA no incluido"]]
      .map(([k, v, d]) => `<div class="kpi"><span class="k">${k}</span><span class="v" style="${k === "Material" ? "font-family:var(--font-ui);font-size:var(--fs-xl)" : ""}">${v}</span><span class="d">${d}</span></div>`).join("");
    const pcs = jobSel === 0 ? N().state.cuts : N().state.cuts.slice(0, 3);
    $("#job-pieces tbody").innerHTML = pcs.map((c, i) => `<tr><td class="idx">${i + 1}</td><td>${c.name}</td><td>${j.material}</td><td class="num">${c.len}</td><td class="num">${c.qty}</td></tr>`).join("");
    $("#job-trace").innerHTML = jobSel === 0
      ? `<div>• IPE 200 · S235-000007-00 × 1 barra(s)</div><div>• Retal IPE 200 · S235-000001-R1 — 1182 mm</div>`
      : `<span style="color:var(--text-dim)">Este trabajo no usó barras del stock.</span>`;
  }

  // ── Cuts ────────────────────────────────────────────────────────────────
  function shapeThumb(c) {
    const H = 18, W = 44, d = c.aL ? 10 : 0, e = c.aR ? 10 : 0;
    return `<svg class="shape-thumb" viewBox="0 0 ${W} ${H}"><polygon points="0,0 ${W - e},0 ${W},${H} ${d},${H}" fill="${c.color}" stroke="var(--bar-stroke)" stroke-width="1"/></svg>`;
  }
  function renderCuts() {
    const S = N().state;
    $("#cuts-table tbody").innerHTML = S.cuts.map((c, i) => `<tr data-cut="${c.id}">
      <td class="idx">${i + 1}</td>
      <td><input class="cell-input" value="${c.name}" aria-label="Descripción" data-k="name"></td>
      <td class="num" style="width:96px"><input class="cell-input num mono" value="${c.len}" aria-label="Longitud" data-k="len"></td>
      <td class="num" style="width:70px"><input class="cell-input num mono" value="${c.qty}" aria-label="Cantidad" data-k="qty"></td>
      <td><span class="angle"><input type="checkbox" ${c.aL ? "checked" : ""} aria-label="Inglete 1" data-k="aLon"><button class="btn icon-only" style="width:22px;height:22px" title="Dirección del inglete">${ICON("arrow-up", "sm")}</button><input class="cell-input num mono" value="${c.aL || 45}" aria-label="Grados inglete 1" data-k="aL"><span style="color:var(--text-dim)">°</span></span></td>
      <td><span class="angle"><input type="checkbox" ${c.aR ? "checked" : ""} aria-label="Inglete 2" data-k="aRon"><button class="btn icon-only" style="width:22px;height:22px" title="Dirección del inglete">${ICON("arrow-down", "sm")}</button><input class="cell-input num mono" value="${c.aR || 45}" aria-label="Grados inglete 2" data-k="aR"><span style="color:var(--text-dim)">°</span></span></td>
      <td><button class="btn" style="padding:0 4px" title="Editar dibujo de la pieza / color" data-dialog="cut-piece">${shapeThumb(c)}</button></td>
      <td style="width:36px"><button class="btn icon-only danger" title="Eliminar corte" data-del="${c.id}">${ICON("x", "sm")}</button></td></tr>`).join("");
    $$("#cuts-table [data-del]").forEach((b) => b.addEventListener("click", () => {
      const c = N().cutById(+b.dataset.del);
      confirmDialog({ title: "Eliminar corte", text: `¿Eliminar «${c.name}»?`, ok: () => { S.cuts = S.cuts.filter((x) => x !== c); N().state.bars.forEach((bb) => { bb.pieces = bb.pieces.filter((p) => p.cut !== c); }); renderCuts(); document.dispatchEvent(new CustomEvent("nest:changed")); } });
    }));
    $$("#cuts-table input").forEach((inp) => inp.addEventListener("change", () => {
      const c = N().cutById(+inp.closest("tr").dataset.cut), k = inp.dataset.k;
      if (k === "name") c.name = inp.value;
      else if (k === "len" || k === "qty") c[k] = Math.max(k === "qty" ? 1 : 1, parseFloat(inp.value) || c[k]);
      else if (k === "aLon") c.aL = inp.checked ? 45 : 0; else if (k === "aRon") c.aR = inp.checked ? 45 : 0;
      else if (k === "aL" || k === "aR") { const on = inp.closest("td").querySelector("input[type=checkbox]").checked; c[k] = on ? parseFloat(inp.value) || 0 : 0; }
      renderCuts(); document.dispatchEvent(new CustomEvent("nest:changed"));
    }));
    renderCutsPreview();
  }
  function renderCutsPreview() {
    const S = N().state; const bars = S.bars.filter((b) => b.pieces.length);
    $("#cuts-summary").textContent = `${bars.length} barras · ${N().efficiency().toFixed(1)}%`;
    $("#cuts-preview").innerHTML = bars.map((b, i) => {
      const used = b.pieces.reduce((s, p) => s + p.cut.len, 0);
      const segs = b.pieces.slice().sort((p, q) => p.x - q.x).map((p) => `<i style="width:${p.cut.len / b.len * 100}%;background:${p.cut.color}"></i>`).join("");
      return `<div class="bar-item" style="cursor:default"><div class="bar-item-head"><span class="name">Barra ${i + 1}</span><span class="eff">${(used / b.len * 100).toFixed(1)}% · R${Math.round(b.len - N().usedEnd(b))}</span></div><div class="mini-bar">${segs}</div></div>`;
    }).join("") || `<div class="empty-hint">Pulsa Calcular para ver el anidado</div>`;
  }

  // ── Costs ───────────────────────────────────────────────────────────────
  function renderCosts() {
    const totW = COSTS.reduce((s, r) => s + r[3] * r[2], 0), totM = COSTS.reduce((s, r) => s + r[5] * r[2], 0),
      totL = COSTS.reduce((s, r) => s + r[6] * r[2], 0), tot = COSTS.reduce((s, r) => s + r[9], 0);
    $("#cost-kpis").innerHTML = [["Peso total", fmt(totW, 1) + " kg", "IPE 200 · 22,4 kg/m"], ["Material", fmt(totM) + " €", "0,85 €/kg"],
      ["Mano de obra", fmt(totL) + " €", "3 min/corte · 30 €/h"], ["Total pedido", fmt(tot) + " €", "margen 15 % incluido"]]
      .map(([k, v, d], i) => `<div class="kpi"${i === 3 ? ' style="border-color:var(--accent)"' : ""}><span class="k">${k}</span><span class="v"${i === 3 ? ' style="color:var(--accent)"' : ""}>${v}</span><span class="d">${d}</span></div>`).join("");
    $("#cost-table tbody").innerHTML = COSTS.map((r) => `<tr><td><b style="font-weight:500">${r[0]}</b> <span class="mono" style="color:var(--text-dim)">${r[1]} mm</span></td><td class="num">${r[2]}</td>
      <td class="num">${fmt(r[3])} kg</td><td class="num">${fmt(r[4], 3)} m²</td><td class="num">${fmt(r[5])}</td><td class="num">${fmt(r[6])}</td><td class="num">${fmt(r[7])}</td><td class="num">${fmt(r[8])}</td><td class="num"><b>${fmt(r[9])} €</b></td></tr>`).join("");
    $("#cost-table tfoot").innerHTML = `<tr><td colspan="8" style="text-align:right;font-weight:700;padding:10px">TOTAL PEDIDO</td><td class="num" style="font-weight:700;color:var(--accent)">${fmt(tot)} €</td></tr>`;
  }

  // ── Profiles ────────────────────────────────────────────────────────────
  function renderProfiles() {
    $("#prof-families").innerHTML = FAMILIES.map(([k, l]) => `<button role="tab" aria-selected="${k === profFamily}" data-fam="${k}">${l} <span style="color:var(--text-dim)">${k === "all" ? PROFILES.length : PROFILES.filter((p) => famOf(p) === k).length}</span></button>`).join("");
    $$("#prof-families [data-fam]").forEach((b) => b.addEventListener("click", () => { profFamily = b.dataset.fam; renderProfiles(); }));
    const q = ($("#prof-search").value || "").toLowerCase();
    const vis = PROFILES.map((p, i) => [p, i]).filter(([p]) => (profFamily === "all" || famOf(p) === profFamily) && (!q || (p[1] + p[3] + p[0]).toLowerCase().includes(q)));
    const body = $("#prof-body");
    const thumb = (p, size) => `<div class="img-tile" style="width:${size}px;height:${size}px"><img src="${imgOf(p)}" alt="" loading="lazy"></div>`;
    if (!vis.length) { body.innerHTML = `<div class="empty-hint">Ningún perfil en esta familia. Crea uno con «Nuevo perfil/tubo».</div>`; }
    else if (profView === "list") {
      body.innerHTML = `<div style="overflow-x:auto"><table class="table"><thead><tr><th style="width:56px"></th><th>Nombre</th><th>Tipo</th><th>Material</th><th class="num">h</th><th class="num">b</th><th class="num">tw</th><th class="num">tf</th><th class="num">Sección cm²</th><th class="num">Peso kg/m</th></tr></thead><tbody>${
        vis.map(([p, i]) => `<tr data-prof="${i}" class="${i === profSel ? "selected" : ""}" style="cursor:pointer"><td style="padding:3px 6px">${thumb(p, 40)}</td><td>${p[1]}</td><td style="color:var(--text-sec)">${p[2]}</td><td style="color:var(--text-sec)">${p[3]}</td><td class="num">${p[4]}</td><td class="num">${p[5]}</td><td class="num">${p[6]}</td><td class="num">${p[7]}</td><td class="num">${p[8]}</td><td class="num">${p[9]}</td></tr>`).join("")}</tbody></table></div>`;
    } else {
      body.innerHTML = `<div class="cards">${vis.map(([p, i]) => `<div class="card${i === profSel ? " active" : ""}" data-prof="${i}"><div class="img-tile zoomable" data-zoom="${i}" style="height:120px" title="Ver imagen"><img src="${imgOf(p)}" alt="" loading="lazy"></div><h3>${p[1]}</h3><div class="meta"><span>${p[3]}</span><span class="mono">${p[9]} kg/m</span></div></div>`).join("")}</div>`;
    }
    const visRows = vis.map(([p]) => p);
    $$("#prof-body [data-prof]").forEach((r) => {
      r.addEventListener("click", (e) => {
        if (e.target.closest("[data-zoom]")) { window.NT_VIEWER.open(viewerItems(visRows), vis.findIndex(([, i]) => i === +r.dataset.prof)); return; }
        profSel = +r.dataset.prof; renderProfiles(); });
      r.addEventListener("dblclick", () => window.NT.dialog("profile-creator"));
    });
    const p = PROFILES[profSel];
    $("#prof-inspector").innerHTML = `<div class="section">
        <div class="img-tile zoomable" id="prof-img" style="height:180px" title="Abrir en el visor de imágenes"><img src="${imgOf(p)}" alt="Imagen del perfil ${p[1]}"></div>
        <div style="display:flex;gap:6px"><button class="btn outline" style="flex:1" id="prof-img-open">${ICON("fit", "sm")}Ver imagen</button><button class="btn outline" style="flex:1" data-dialog="profile-manager">${ICON("image", "sm")}Asignar imagen</button></div>
        <div class="section-head"><span class="section-title" style="font-size:var(--fs-lg)">${p[1]}</span><span class="chip">${p[2]}</span></div>
        <div style="font-size:var(--fs-sm);color:var(--text-sec)">${p[3]} · <span class="mono">${p[0]}</span></div></div>
      <div class="section"><div class="section-head"><span class="section-title">Geometría</span></div><div class="field-grid">
        ${[["h", p[4], "mm"], ["b", p[5], "mm"], ["tw", p[6], "mm"], ["tf", p[7], "mm"]].map(([k, v, u]) => `<div class="field"><span class="label">${k}</span><div class="input"><span class="pre">${k}</span><input class="num" value="${v === "" ? "—" : v}" readonly><span class="unit">${u}</span></div></div>`).join("")}
      </div></div>
      <div class="section"><div class="stats" style="grid-template-columns:1fr 1fr"><div class="stat"><span class="v">${p[8]}</span><span class="k">sección cm²</span></div><div class="stat"><span class="v">${p[9]}</span><span class="k">peso kg/m</span></div></div></div>
      <div class="section"><button class="btn outline block" data-dialog="profile-creator">${ICON("pencil", "sm")}Editar dibujo</button><button class="btn outline block" data-dialog="materials">Cambiar material</button><button class="btn primary block" data-act="use-profile">Usar en Costes</button></div>`;
    const openViewer = () => window.NT_VIEWER.open(viewerItems(visRows.length ? visRows : PROFILES), Math.max(0, visRows.indexOf(p)));
    $("#prof-img").addEventListener("click", openViewer); $("#prof-img-open").addEventListener("click", openViewer);
  }

  // ── Costs profile gallery (ProfileTile row: MRU + builtins + "+") ───────
  let costProfile = "AC-IPE-200";
  function renderCostGallery() {
    const mru = ["AC-IPE-200", "AC-HEA-140", "AC-TUB-C40", "CUSTOM-U50", "AC-UPN-100"].map((id) => PROFILES.find((p) => p[0] === id));
    $("#cost-gallery").innerHTML = mru.map((p) => `<div class="ptile${p[0] === costProfile ? " active" : ""}" data-cp="${p[0]}" title="${p[1]} · ${p[3]}"><div class="img-tile"><img src="${imgOf(p)}" alt=""></div><span>${p[1]}</span></div>`).join("") +
      `<button class="ptile add" data-dialog="profile-creator" title="Añadir perfil (módulo de dibujo)">+</button>`;
    $$("#cost-gallery [data-cp]").forEach((t) => {
      t.addEventListener("click", () => { costProfile = t.dataset.cp; renderCostGallery(); });
      t.addEventListener("dblclick", () => window.NT_VIEWER.open(viewerItems(mru), mru.findIndex((p) => p[0] === t.dataset.cp)));
    });
    const p = PROFILES.find((x) => x[0] === costProfile);
    $("#cost-profile-img").innerHTML = `<img src="${imgOf(p)}" alt="Imagen del perfil ${p[1]}">`;
    $("#cost-profile-img").onclick = () => window.NT_VIEWER.open(viewerItems(mru), mru.indexOf(p));
    $("#cost-profile-name").textContent = p[1]; $("#cost-profile-mat").textContent = p[3];
    $("#cost-profile-dims").innerHTML = [["h", p[4], "mm"], ["b", p[5], "mm"], ["tw", p[6], "mm"], ["tf", p[7], "mm"], ["Sección", p[8], "cm²"], ["Peso lineal", p[9], "kg/m"]]
      .map(([k, v, u]) => `<span>${k}</span><span>${v === "" ? "—" : v + " " + u}</span>`).join("");
    const sel = $("#cost-profile-combo"); if (sel && !sel.options.length) sel.innerHTML = `<option>Todos los perfiles</option>` + PROFILES.map((x) => `<option value="${x[0]}">${x[1]}</option>`).join("");
  }

  // ── Stock ───────────────────────────────────────────────────────────────
  function renderStock() {
    const q = ($("#stock-search").value || "").toLowerCase(); const pf = $("#stock-profile").value;
    const vis = STOCK.map((s, i) => [s, i]).filter(([s]) => (!q || (s.prof + s.q).toLowerCase().includes(q)) && (pf === "Todos los perfiles" || s.prof === pf));
    $("#stock-count").textContent = `${vis.length} items · ${vis.reduce((t, [s]) => t + s.qty, 0)} ud`;
    $("#stock-table tbody").innerHTML = vis.map(([s, i]) => `<tr data-stock="${i}" class="${i === stockSel ? "selected" : ""}" style="cursor:pointer">
      <td><input type="checkbox" style="accent-color:var(--accent)" aria-label="Seleccionar"></td>
      <td><span class="status-dot" style="background:${s.ok ? "var(--success)" : "var(--text-dim)"}"></span></td>
      <td>${s.prof}</td><td class="mono" style="font-size:var(--fs-sm)">${s.q}</td><td class="num">${s.len}</td><td class="num">${s.qty}</td>
      <td>${s.ok ? '<span class="chip success">OK</span>' : '<span class="chip">Usada</span>'}</td>
      <td>${s.retal ? '<span class="chip accent">Retal</span>' : ""}</td>
      <td>${s.job ? `<a href="#jobs" class="mono" style="color:var(--accent);font-size:var(--fs-sm)" title="Clic para abrir en el Explorador de Jobs">${s.job}</a>` : ""}</td>
      <td>${s.used ? `<a href="#jobs" class="mono" style="color:var(--accent);font-size:var(--fs-sm)" title="Clic para abrir en el Explorador de Jobs">${s.used}</a>` : ""}</td></tr>`).join("")
      || `<tr><td colspan="10" class="empty-hint">Sin stock. Añade barras o perfiles.</td></tr>`;
    $$("#stock-table [data-stock]").forEach((r) => r.addEventListener("click", (e) => {
      if (e.target.closest("a")) { e.preventDefault(); showView("jobs"); return; }
      if (e.target.type === "checkbox") return; stockSel = +r.dataset.stock; renderStock(); }));
    const s = STOCK[stockSel]; const totalM = STOCK.reduce((t, x) => t + (x.ok ? x.len * x.qty : 0), 0) / 1000;
    $("#stock-inspector").innerHTML = `<div class="section"><div class="stats"><div class="stat"><span class="v">${STOCK.filter((x) => x.ok).reduce((t, x) => t + x.qty, 0)}</span><span class="k">barras disp.</span></div>
      <div class="stat"><span class="v">${STOCK.filter((x) => x.retal).length}</span><span class="k">retales</span></div><div class="stat"><span class="v">${fmt(totalM, 1)}</span><span class="k">m lineales</span></div></div></div>
      <div class="section"><div class="section-head"><span class="section-title">Seleccionado</span>${s.retal ? '<span class="chip accent">Retal</span>' : ""}</div>
      <div class="field"><span class="label">Perfil / material</span><div class="input"><input value="${s.prof}" readonly></div></div>
      <div class="field"><span class="label">Calidad / nº de serie</span><div class="input"><input class="num" value="${s.q}" readonly></div></div>
      <div class="field-grid"><div class="field"><span class="label">Largo</span><div class="input"><span class="pre">L</span><input class="num" value="${s.len}" readonly><span class="unit">mm</span></div></div>
      <div class="field"><span class="label">Cantidad</span><div class="input"><span class="pre">×</span><input class="num" value="${s.qty}" readonly></div></div></div>
      <div class="mini-bar" style="height:12px"><i style="width:${Math.min(100, s.len / 12000 * 100)}%;background:${s.retal ? "var(--remnant)" : "var(--accent)"}"></i></div></div>
      <div class="section"><div class="section-head"><span class="section-title">Trazabilidad</span></div>
      <div style="display:grid;grid-template-columns:auto 1fr;gap:4px 10px;font-size:var(--fs-sm)"><span style="color:var(--text-sec)">Creado en</span><span class="mono">${s.job || "—"}</span><span style="color:var(--text-sec)">Usado en</span><span class="mono">${s.used || "—"}</span></div></div>`;
  }

  // ── wiring ──────────────────────────────────────────────────────────────
  function init() {
    renderPages(); renderJobs(); renderCuts(); renderCosts(); renderCostGallery(); renderProfiles(); renderStock();
    $("#jobs-search").addEventListener("input", renderJobs); $("#jobs-field").addEventListener("change", renderJobs);
    $("#prof-search").addEventListener("input", renderProfiles);
    $$("#prof-viewmode [data-pv]").forEach((b) => b.addEventListener("click", () => {
      profView = b.dataset.pv; $$("#prof-viewmode button").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); renderProfiles(); }));
    $("#stock-search").addEventListener("input", renderStock); $("#stock-profile").addEventListener("change", renderStock);
    $("#stock-all").addEventListener("change", (e) => $$("#stock-table tbody input[type=checkbox]").forEach((c) => { c.checked = e.target.checked; }));
    document.addEventListener("nest:changed", renderCutsPreview);
    document.addEventListener("click", (e) => {
      const t = e.target.closest("[data-toast]"); if (t) toast(t.dataset.toast);
      const g = e.target.closest("[data-view-go]"); if (g) showView(g.dataset.viewGo);
    });
    const A = window.NT.ACTIONS;
    Object.assign(A, {
      "job-new": () => window.NT.dialog("job-new"),
      "job-open": () => { toast(`${JOBS[jobSel].name} abierto`); showView("cuts"); },
      "job-save": () => confirmDialog({ title: "Guardar cambios", text: `¿Guardar los cambios del job «${JOBS[jobSel].name}»?`, okLabel: "Guardar", danger: false,
        ok: () => { Object.assign(JOBS[jobSel], { desc: $("#job-desc").value, client: $("#job-client").value, order: $("#job-order").value, offer: $("#job-offer").value }); renderJobs(); toast("Cambios guardados"); } }),
      "job-delete": () => confirmDialog({ title: "Eliminar job", text: `¿Eliminar el job «${JOBS[jobSel].name}»?`, ok: () => { JOBS.splice(jobSel, 1); jobSel = 0; renderJobs(); } }),
      "add-cut": () => { const S = N().state; const id = Math.max(0, ...S.cuts.map((c) => c.id)) + 1;
        const pal = ["#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC"];
        S.cuts.push({ id, name: `Corte ${S.cuts.length + 1}`, len: 1000, qty: 1, aL: 0, aR: 0, color: pal[(id - 6 + pal.length * 10) % pal.length] }); renderCuts(); document.dispatchEvent(new CustomEvent("nest:changed")); },
      "calc-cuts": () => { window.NestCanvas.state.autoMode = "all"; window.NestCanvas.toggleNest(); },
      "add-field": () => window.NT.dialog("add-field"),
      "costs-calc": () => confirmDialog({ title: "Confirmar configuración de costes", text: "¿Continuar con esta configuración de costes? Modo: cortes compartidos (optimizado) · 0,85 €/kg · margen 15 %.", okLabel: "Calcular", danger: false, ok: () => { renderCosts(); toast("Costes recalculados"); } }),
      "costs-clear": () => { $("#cost-table tbody").innerHTML = `<tr><td colspan="9" class="empty-hint">Configura el perfil y pulsa Calcular</td></tr>`; $("#cost-table tfoot").innerHTML = ""; $("#cost-kpis").innerHTML = ""; },
      "stock-export": () => toast("Stock exportado a Excel"),
      "use-profile": () => { costProfile = PROFILES[profSel][0]; renderCostGallery(); showView("costs"); toast(`${PROFILES[profSel][1]} aplicado en Costes`); },
      "stock-delete": () => confirmDialog({ title: "Eliminar del stock", text: `¿Eliminar ${STOCK[stockSel].prof} · ${STOCK[stockSel].q}?`, ok: () => { STOCK.splice(stockSel, 1); stockSel = 0; renderStock(); } }),
    });
  }

  window.NT_VIEWS = { init, renderCuts, renderStock, renderJobs, sectionSVG };
})();
