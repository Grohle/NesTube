/* ==========================================================================
   NesTube web UI — Jobs, Cuts, Costs, Profiles and Stock, NATIVE mode
   Same markup as the mockup views; data and actions come from the engine
   (nestube/ui_web/api_data.py → database, stock, catalogue, cost formulas).
   ========================================================================== */
(function () {
  "use strict";
  if (!window.NT_NATIVE) return;
  const { $, $$, ICON, toast, confirmDialog, openMenu, openModal, closeModal } = window.NT;
  const call = (m, a) => window.NT.call(m, a);
  const go = (v) => window.NT.go(v);
  const fmt = (v, d = 2) => Number(v || 0).toLocaleString("es-ES", { minimumFractionDigits: d, maximumFractionDigits: d });
  const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  const num = (v) => (v == null || v === "" ? "—" : v);
  const D = { view: "jobs", jobs: [], current: null, jobSel: null, detail: null, cuts: null, costs: null, profiles: [], stock: null,
    stockSel: null, checked: new Set(), subtabs: null, profFamily: "all", profView: "list", profSel: null };

  // ── material pages (Cuts / Costs) ───────────────────────────────────────
  function renderPages() {
    const st = D.subtabs; if (!st) return;
    $$("[data-pages]").forEach((list) => {
      const total = !!list.dataset.total;
      const items = st.names.map((n, i) => ({ n, i, active: i === st.active && !st.total_view }));
      if (total) items.push({ n: "<b>Total</b> · todos los materiales", i: st.names.length, active: !!st.total_view });
      list.innerHTML = items.map((it) => `<div class="row page-row${it.active ? " active" : ""}" tabindex="0" data-pg="${it.i}">${ICON("check", "sm check")}<div class="row-main"><span class="row-title">${it.n}</span></div>${it.i < st.names.length ? `<span class="row-trail mono">${st.counts[it.i] || 0} pzs</span>` : ""}</div>`).join("");
      $$("[data-pg]", list).forEach((r) => {
        r.addEventListener("click", () => call("data.subtab_switch", { i: +r.dataset.pg }).then(() => reload()));
        if (+r.dataset.pg < st.names.length) r.addEventListener("contextmenu", (e) => { e.preventDefault(); window.NT.pageMenu(+r.dataset.pg, e.clientX, e.clientY, () => reload()); });
      });
    });
  }

  // ── Jobs ────────────────────────────────────────────────────────────────
  function renderJobs() {
    const q = ($("#jobs-search").value || "").toLowerCase(), f = $("#jobs-field").value;
    const vis = D.jobs.filter((j) => !q || String(j[f] || "").toLowerCase().includes(q));
    $("#jobs-count").textContent = vis.length;
    $("#jobs-list").innerHTML = vis.length ? vis.map((j) => `<div class="row${j.id === D.jobSel ? " active" : ""}" data-job="${j.id}" tabindex="0">
        ${ICON("folder", "sm")}<div class="row-main"><span class="row-title mono">${esc(j.name)}${j.id === D.current ? ' <span class="chip accent" style="height:16px;font-size:9px">abierto</span>' : ""}</span><span class="row-sub" style="font-family:var(--font-ui)">${esc(j.client || "—")} · ${esc(j.created)}</span></div></div>`).join("")
      : `<div class="empty-hint">${D.jobs.length ? "No hay jobs que coincidan" : "No hay jobs guardados"}</div>`;
    $$("#jobs-list [data-job]").forEach((r) => {
      r.addEventListener("click", () => selectJob(+r.dataset.job));
      r.addEventListener("dblclick", () => openJob(+r.dataset.job));
    });
    renderJobDetail();
  }
  function selectJob(id) { D.jobSel = id; call("data.job_detail", { id }).then((d) => { D.detail = d; renderJobs(); }); }
  function renderJobDetail() {
    const j = D.detail, on = !!j;
    $$("#view-jobs .content-body, #view-jobs .panel.right .panel-scroll").forEach((e) => { e.style.opacity = on ? "" : ".4"; });
    if (!j) { $("#job-title").textContent = "Selecciona un job de la lista"; $("#job-kpis").innerHTML = ""; $("#job-pieces tbody").innerHTML = ""; $("#job-trace").innerHTML = ""; return; }
    $("#job-title").textContent = j.name; $("#job-date").lastChild.textContent = j.created;
    $("#job-name").value = j.name; $("#job-desc").value = j.desc; $("#job-client").value = j.client; $("#job-order").value = j.order; $("#job-offer").value = j.offer;
    const nPcs = j.pieces.reduce((s, p) => s + (+p.qty || 0), 0);
    $("#job-kpis").innerHTML = [["Material", j.materials.join(" · ") || "—"], ["Piezas", `${nPcs}`], ["Barras anidadas", `${j.bars}`], ["Cliente", j.client || "—"]]
      .map(([k, v], i) => `<div class="kpi"><span class="k">${k}</span><span class="v" style="${i === 0 || i === 3 ? "font-family:var(--font-ui);font-size:var(--fs-lg)" : ""}">${esc(v)}</span></div>`).join("");
    $("#job-pieces tbody").innerHTML = j.pieces.map((p, i) => `<tr><td class="idx">${i + 1}</td><td>${esc(p.name)}</td><td>${esc(p.material)}</td><td class="num">${p.len}</td><td class="num">${p.qty}</td></tr>`).join("")
      || `<tr><td colspan="5" class="empty-hint">Este trabajo aún no tiene cortes.</td></tr>`;
    const lines = j.stock.concat(j.retales);
    $("#job-trace").innerHTML = lines.length ? lines.map((l) => `<div>${esc(l)}</div>`).join("") : `<span style="color:var(--text-dim)">Este trabajo no usó barras del stock ni generó retales.</span>`;
  }
  function openJob(id) {
    const doOpen = () => call("data.job_open", { id }).then((r) => r && window.NT.afterJobChange(r));
    const snap = window.NestCanvas.snapshot && window.NestCanvas.snapshot();
    if (snap && snap.dirty && id !== D.current) {
      window.NT.alert({ kind: "question", title: "Cambios sin guardar", msg: "El trabajo abierto tiene cambios sin guardar.\n\n¿Guardar antes de abrir otro?",
        buttons: [{ label: "Cancelar" }, { label: "Descartar", danger: true, action: doOpen },
          { label: "Guardar", primary: true, action: () => call("data.menu", { name: "save" }).then(doOpen) }] });
    } else doOpen();
  }

  // ── Cuts ────────────────────────────────────────────────────────────────
  function shapeThumb(c) {
    const H = 18, W = 44, d = c.inglete1 ? 10 : 0, e = c.inglete2 ? 10 : 0;
    const top = [c.inglete1 && c.inglete1_dir === "up" ? d : 0, c.inglete2 && c.inglete2_dir === "up" ? W - e : W];
    const bot = [c.inglete1 && c.inglete1_dir !== "up" ? d : 0, c.inglete2 && c.inglete2_dir !== "up" ? W - e : W];
    return `<svg class="shape-thumb" viewBox="0 0 ${W} ${H}"><polygon points="${top[0]},0 ${top[1]},0 ${bot[1]},${H} ${bot[0]},${H}" fill="${c.color}" stroke="var(--bar-stroke)" stroke-width="1"/></svg>`;
  }
  function renderCuts() {
    const C = D.cuts; if (!C) return;
    const h = C.header, P = C.params;
    $("#c-material").value = [h.profile, h.material, h.quality].filter(Boolean).join(" · ");
    $("#c-material").readOnly = true; $("#c-material").placeholder = "Pulsa 🔍 para elegir perfil, material o calidad";
    setIf("#c-order", h.order); setIf("#c-offer", h.offer); setIf("#c-client", h.client);
    setIf("#c-barlen", P.bar_len); setIf("#c-kerf", P.kerf); setIf("#c-margin", P.margin); setIf("#c-height", P.height);
    $("#c-height").readOnly = !!P.height_ro;
    const sys = $("#c-system");
    if (!sys.dataset.native) { sys.innerHTML = `<option value="ffd">FFD (First Fit Decreasing)</option><option value="bfd">BFD (Best Fit Decreasing)</option><option value="nfd">NFD (Next Fit Decreasing)</option>`; sys.dataset.native = "1"; }
    sys.value = P.calc;
    $("#cuts-table tbody").innerHTML = C.rows.map((c, i) => `<tr data-row="${i}">
      <td class="idx">${i + 1}</td>
      <td><input class="cell-input" value="${esc(c.descripcion)}" aria-label="Descripción" data-k="descripcion"></td>
      <td class="num" style="width:96px"><input class="cell-input num mono" value="${c.largo}" aria-label="Longitud" data-k="largo"></td>
      <td class="num" style="width:70px"><input class="cell-input num mono" value="${c.cantidad}" aria-label="Cantidad" data-k="cantidad"></td>
      ${[1, 2].map((n) => `<td><span class="angle"><input type="checkbox" ${c["inglete" + n] ? "checked" : ""} aria-label="Inglete ${n}" data-k="inglete${n}"><button class="btn icon-only" style="width:22px;height:22px" title="Dirección del inglete (arriba/abajo)" data-dir="${n}">${ICON(c["inglete" + n + "_dir"] === "up" ? "arrow-up" : "arrow-down", "sm")}</button><input class="cell-input num mono" value="${c["inglete" + n + "_deg"]}" aria-label="Grados inglete ${n}" data-k="inglete${n}_deg"><span style="color:var(--text-dim)">°</span></span></td>`).join("")}
      <td><button class="btn" style="padding:0 4px" title="Editar dibujo de la pieza" data-shape="${i}">${shapeThumb(c)}</button></td>
      <td style="width:36px"><button class="btn icon-only danger" title="Eliminar corte" data-del="${i}">${ICON("x", "sm")}</button></td></tr>`).join("")
      || `<tr><td colspan="8" class="empty-hint">Sin cortes. Pulsa «Añadir corte».</td></tr>`;
    $$("#cuts-table [data-del]").forEach((b) => b.addEventListener("click", () => {
      const i = +b.dataset.del, c = C.rows[i];
      confirmDialog({ title: "Eliminar corte", text: `¿Eliminar «${c.descripcion || c.largo + " mm"}»?`, ok: () => { C.rows.splice(i, 1); pushCuts(); } });
    }));
    $$("#cuts-table [data-dir]").forEach((b) => b.addEventListener("click", () => {
      const i = +b.closest("tr").dataset.row, n = b.dataset.dir, k = "inglete" + n + "_dir";
      C.rows[i][k] = C.rows[i][k] === "up" ? "down" : "up"; pushCuts();
    }));
    $$("#cuts-table [data-shape]").forEach((b) => b.addEventListener("click", () => call("data.cut_piece_dialog", { i: +b.dataset.shape }).then((d) => { if (d) { D.cuts = d; renderCuts(); } })));
    $$("#cuts-table input").forEach((inp) => inp.addEventListener("change", () => {
      const i = +inp.closest("tr").dataset.row, k = inp.dataset.k, c = C.rows[i];
      if (inp.type === "checkbox") c[k] = inp.checked;
      else if (k === "descripcion") c[k] = inp.value;
      else if (k === "cantidad") c[k] = Math.max(1, parseInt(inp.value, 10) || c[k]);
      else c[k] = parseFloat(inp.value) || c[k];
      pushCuts();
    }));
    // preview
    const colorFor = (len) => (C.rows.find((r) => Math.abs(r.largo - len) < 1e-6) || {}).color || "var(--text-dim)";
    $("#cuts-summary").textContent = C.result || "—";
    $("#cuts-preview").innerHTML = C.bars.map((b, i) => {
      const used = b.reduce((s, l) => s + l, 0);
      return `<div class="bar-item" style="cursor:default"><div class="bar-item-head"><span class="name">Barra ${i + 1}</span><span class="eff">${(used / C.bar_len * 100).toFixed(1)}% · R${Math.round(C.bar_len - used)}</span></div><div class="mini-bar">${b.map((l) => `<i style="width:${l / C.bar_len * 100}%;background:${colorFor(l)}"></i>`).join("")}</div></div>`;
    }).join("") || `<div class="empty-hint">Pulsa Calcular para ver el anidado</div>`;
  }
  function setIf(sel, v) { const e = $(sel); if (e && document.activeElement !== e) e.value = v == null ? "" : v; }
  let cutsTimer = null;
  function pushCuts() {
    clearTimeout(cutsTimer);
    renderCuts();
    cutsTimer = setTimeout(() => call("data.cuts_set", { rows: D.cuts.rows }).then((d) => { if (d) { D.cuts = d; renderCuts(); window.NT.refreshJob(); } }), 120);
  }

  // ── Costs ───────────────────────────────────────────────────────────────
  const TYPE_SHAPE = { redondo: "O", rectangular: "T", L: "L", U: "U", H: "H" };
  function profileThumb(p, size) {
    if (p.image) return `<img src="${p.image}" alt="">`;
    return window.NT_VIEWS_MOCK.sectionSVG(TYPE_SHAPE[p.type] || "T", size || 64);
  }
  function renderCosts() {
    const K = D.costs; if (!K) return;
    const F = K.fields;
    setIf("#k-kgm", F.kg_m); setIf("#k-dens", F.dens); setIf("#k-wall", F.wall); setIf("#k-pkg", F.price_kg);
    setIf("#k-pm", F.price_m); setIf("#k-pbar", F.price_bar); setIf("#k-margin", F.margin); setIf("#k-tcut", F.t_cut);
    setIf("#k-miter", F.miter); setIf("#k-op", F.op);
    const cur = $("#k-cur");
    if (cur.options.length !== K.currencies.length) cur.innerHTML = K.currencies.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join("");
    cur.value = F.currency;
    const mode = $("#k-mode");
    if (!mode.dataset.native) { mode.innerHTML = `<option value="shared">Cortes compartidos (optimizado)</option><option value="individual">Cortes individuales</option>`; mode.dataset.native = "1"; }
    mode.value = F.mode;
    $('input[aria-label="Sección maciza"]').checked = !!F.solid;
    $('input[aria-label="Repartir coste de retales"]').checked = !!F.scrap;
    $('input[aria-label="Confirmar configuración"]').checked = !!F.confirm;
    // builtin profile dimensions
    let dimSec = $("#k-dims");
    if (!dimSec) { dimSec = document.createElement("div"); dimSec.className = "section"; dimSec.id = "k-dims"; $("#view-costs .panel.right .panel-scroll").prepend(dimSec); }
    dimSec.hidden = !K.dims.length;
    dimSec.innerHTML = `<div class="section-head"><span class="section-title">Dimensiones del perfil</span></div><div class="field-grid">${K.dims.map(([k, v]) =>
      `<div class="field"><label>${esc(k)}</label><div class="input"><input class="num" data-dim="${esc(k)}" value="${esc(v)}"><span class="unit">mm</span></div></div>`).join("")}</div>`;
    $$("[data-dim]", dimSec).forEach((i) => i.addEventListener("change", () => call("data.costs_set", { dims: { [i.dataset.dim]: i.value } }).then(setCosts)));
    // results
    const sym = (K.currencies.find(([v]) => v === F.currency) || ["", "€"])[1].split("|")[0].trim() || F.currency;
    const chip = $("#view-costs .content-head .chip");
    chip.className = "chip " + (K.using_nesting ? "success" : "");
    chip.innerHTML = K.using_nesting ? `${ICON("check", "sm")}Basado en el anidado completado` : "Cálculo rápido — sin anidado completado";
    if (K.total_view) {
      $("#cost-kpis").innerHTML = `<div class="kpi" style="border-color:var(--accent)"><span class="k">Total pedido · todos los materiales</span><span class="v" style="color:var(--accent)">${fmt(K.grand)} ${esc(sym)}</span></div>`;
      $("#cost-table tbody").innerHTML = K.totals.map((t) => `<tr><td colspan="8"><b style="font-weight:500">${esc(t.name)}</b></td><td class="num"><b>${fmt(t.total)} ${esc(sym)}</b></td></tr>`).join("")
        || `<tr><td colspan="9" class="empty-hint">Ningún material tiene cortes y perfil configurados.</td></tr>`;
      $("#cost-table tfoot").innerHTML = `<tr><td colspan="8" style="text-align:right;font-weight:700;padding:10px">TOTAL PEDIDO</td><td class="num" style="font-weight:700;color:var(--accent)">${fmt(K.grand)} ${esc(sym)}</td></tr>`;
    } else {
      const R = K.results;
      const totW = R.reduce((s, r) => s + r.kg * r.qty, 0), totM = R.reduce((s, r) => s + r.mat * r.qty, 0),
        totL = R.reduce((s, r) => s + r.labour * r.qty, 0), tot = K.total;
      $("#cost-kpis").innerHTML = R.length ? [["Peso total", fmt(totW, 1) + " kg", K.profile.name || ""], ["Material", fmt(totM) + " " + sym, F.price_kg ? `${F.price_kg} ${sym}/kg` : ""],
        ["Mano de obra", fmt(totL) + " " + sym, `${F.t_cut} min/corte · ${F.op} ${sym}/h`], ["Total pedido", fmt(tot) + " " + sym, `margen ${F.margin || 0} % incluido`]]
        .map(([k, v, d], i) => `<div class="kpi"${i === 3 ? ' style="border-color:var(--accent)"' : ""}><span class="k">${k}</span><span class="v"${i === 3 ? ' style="color:var(--accent)"' : ""}>${v}</span><span class="d">${esc(d)}</span></div>`).join("") : "";
      $("#cost-table tbody").innerHTML = R.map((r) => `<tr><td><b style="font-weight:500">${esc(r.name)}</b> <span class="mono" style="color:var(--text-dim)">${Math.round(r.len)} mm</span></td><td class="num">${r.qty}</td>
        <td class="num">${fmt(r.kg, 3)} kg</td><td class="num">${fmt(r.m2, 4)} m²</td><td class="num">${fmt(r.mat)}</td><td class="num">${fmt(r.labour)}</td><td class="num">${fmt(r.unit)}</td><td class="num">${fmt(r.per_m)}</td><td class="num"><b>${fmt(r.line)} ${esc(sym)}</b></td></tr>`).join("")
        || `<tr><td colspan="9" class="empty-hint">Elige un perfil, rellena los precios y pulsa Calcular.</td></tr>`;
      $("#cost-table tfoot").innerHTML = R.length ? `<tr><td colspan="8" style="text-align:right;font-weight:700;padding:10px">TOTAL PEDIDO</td><td class="num" style="font-weight:700;color:var(--accent)">${fmt(tot)} ${esc(sym)}</td></tr>` : "";
    }
    // profile gallery: most used first (ProfileTile row)
    const all = K.profiles.slice();
    const mru = all.slice().sort((a, b) => (b.uses || 0) - (a.uses || 0) || (a.builtin ? -1 : 1)).slice(0, 5);
    if (K.profile_key && !mru.some((p) => p.key === K.profile_key)) { const cur2 = all.find((p) => p.key === K.profile_key); if (cur2) mru[mru.length - 1] = cur2; }
    $("#cost-gallery").innerHTML = mru.map((p) => `<div class="ptile${p.key === K.profile_key ? " active" : ""}" data-cp="${esc(p.key)}" title="${esc(p.name)}"><div class="img-tile">${profileThumb(p, 56)}</div><span>${esc(p.name)}</span></div>`).join("") +
      `<button class="ptile add" data-dialog="profile-creator" title="Añadir perfil (módulo de dibujo)">+</button>`;
    $$("#cost-gallery [data-cp]").forEach((t) => {
      t.addEventListener("click", () => call("data.costs_select_profile", { key: t.dataset.cp }).then(setCosts));
      t.addEventListener("dblclick", () => { const imgs = mru.filter((p) => p.image); const i = imgs.findIndex((p) => p.key === t.dataset.cp);
        if (i >= 0) window.NT_VIEWER.open(imgs.map((p) => ({ name: p.name, src: p.image, material: p.material })), i); });
    });
    const combo = $("#cost-profile-combo");
    combo.innerHTML = `<option value="">Todos los perfiles…</option>` + all.map((p) => `<option value="${esc(p.key)}"${p.key === K.profile_key ? " selected" : ""}>${esc(p.name)}</option>`).join("");
    const pc = K.profile;
    $("#cost-profile-img").innerHTML = pc.image ? `<img src="${pc.image}" alt="Imagen del perfil ${esc(pc.name)}">` : profileThumb({ type: (all.find((p) => p.key === pc.key) || {}).type }, 90);
    $("#cost-profile-img").onclick = () => pc.image && window.NT_VIEWER.open([{ name: pc.name, src: pc.image, material: pc.material }], 0);
    $("#cost-profile-name").textContent = pc.name || "Sin perfil"; $("#cost-profile-mat").textContent = pc.material || "—";
    $("#cost-profile-dims").innerHTML = pc.locked ? [["h", pc.h, "mm"], ["b", pc.b, "mm"], ["tw", pc.tw, "mm"], ["tf", pc.tf, "mm"], ["Sección", pc.section, "cm²"], ["Peso lineal", pc.kg_m, "kg/m"]]
      .map(([k, v, u]) => `<span>${k}</span><span>${v ? v + " " + u : "—"}</span>`).join("") : `<span>Tipo</span><span>${esc(pc.name || "—")}</span>`;
  }
  function setCosts(d) { if (d) { D.costs = d; renderCosts(); } }

  // ── Profiles ────────────────────────────────────────────────────────────
  const FAMILIES = [["all", "Todos"], ["vigas", "Vigas I / H / U"], ["Angular", "Angulares"], ["tubos", "Tubos"], ["cz", "Correas C / Z"],
    ["macizos", "Macizos y pletinas"], ["Ranurado", "Ranurados"], ["Personalizado", "Personalizados"]];
  function famOf(p) {
    const f = p.geometry || "";
    if (/^Viga /.test(f)) return "vigas";
    if (f === "Perfil C" || f === "Perfil Z") return "cz";
    if (f === "Pletina" || /Macizo/i.test(p.name)) return "macizos";
    if (f === "Redondo" || f === "Cuadrado") return "tubos";
    return f || "Personalizado";
  }
  function renderProfiles() {
    const P = D.profiles;
    $("#prof-families").innerHTML = FAMILIES.map(([k, l]) => `<button role="tab" aria-selected="${k === D.profFamily}" data-fam="${k}">${l} <span style="color:var(--text-dim)">${k === "all" ? P.length : P.filter((p) => famOf(p) === k).length}</span></button>`).join("");
    $$("#prof-families [data-fam]").forEach((b) => b.addEventListener("click", () => { D.profFamily = b.dataset.fam; renderProfiles(); }));
    const q = ($("#prof-search").value || "").toLowerCase();
    const vis = P.filter((p) => (D.profFamily === "all" || famOf(p) === D.profFamily) && (!q || (p.name + p.material).toLowerCase().includes(q)));
    const img = (p) => p.image ? `<img src="${p.image}" alt="" loading="lazy">` : "";
    const body = $("#prof-body");
    if (!vis.length) body.innerHTML = `<div class="empty-hint">Ningún perfil aquí. Crea uno con «Nuevo perfil/tubo».</div>`;
    else if (D.profView === "list") {
      body.innerHTML = `<div style="overflow-x:auto"><table class="table"><thead><tr><th style="width:56px"></th><th>Nombre</th><th>Tipo</th><th>Material</th><th class="num">h</th><th class="num">b</th><th class="num">tw</th><th class="num">tf</th><th class="num">Sección cm²</th><th class="num">Peso kg/m</th></tr></thead><tbody>${
        vis.map((p) => `<tr data-prof="${esc(p.id)}" class="${p.id === D.profSel ? "selected" : ""}" style="cursor:pointer"><td style="padding:3px 6px"><div class="img-tile" style="width:40px;height:40px">${img(p)}</div></td><td>${esc(p.name)}</td><td style="color:var(--text-sec)">${esc(p.geometry || "Personalizado")}</td><td style="color:var(--text-sec)">${esc(p.material)}</td><td class="num">${num(p.h)}</td><td class="num">${num(p.b)}</td><td class="num">${num(p.tw)}</td><td class="num">${num(p.tf)}</td><td class="num">${num(p.section)}</td><td class="num">${num(p.kg_m)}</td></tr>`).join("")}</tbody></table></div>`;
    } else {
      body.innerHTML = `<div class="cards">${vis.map((p) => `<div class="card${p.id === D.profSel ? " active" : ""}" data-prof="${esc(p.id)}"><div class="img-tile zoomable" data-zoom="1" style="height:120px" title="Ver imagen">${img(p)}</div><h3>${esc(p.name)}</h3><div class="meta"><span>${esc(p.material)}</span><span class="mono">${num(p.kg_m)} kg/m</span></div></div>`).join("")}</div>`;
    }
    const withImg = vis.filter((p) => p.image);
    const openViewer = (id) => { const i = withImg.findIndex((p) => p.id === id); if (i >= 0) window.NT_VIEWER.open(withImg.map((p) => ({ name: p.name, src: p.image, material: p.material, file: p.name + ".png" })), i,
      { onAssign: (it) => { const pr = withImg.find((p) => p.name === it.name); if (pr) profAction("edit", pr.id); } }); };
    $$("#prof-body [data-prof]").forEach((r) => {
      r.addEventListener("click", (e) => { if (e.target.closest("[data-zoom]")) { openViewer(r.dataset.prof); return; } D.profSel = r.dataset.prof; renderProfiles(); });
      r.addEventListener("dblclick", () => profAction("edit", r.dataset.prof));
    });
    const p = P.find((x) => x.id === D.profSel) || vis[0];
    if (!p) { $("#prof-inspector").innerHTML = `<div class="empty-hint">Sin perfiles</div>`; return; }
    D.profSel = p.id;
    $("#prof-inspector").innerHTML = `<div class="section">
        <div class="img-tile zoomable" id="prof-img" style="height:180px" title="Abrir en el visor de imágenes">${img(p) || '<span style="color:#888">(sin imagen)</span>'}</div>
        <div style="display:flex;gap:6px"><button class="btn outline" style="flex:1" id="prof-img-open"${p.image ? "" : " disabled"}>${ICON("fit", "sm")}Ver imagen</button><button class="btn outline" style="flex:1" data-pa="edit">${ICON("image", "sm")}Asignar imagen</button></div>
        <div class="section-head"><span class="section-title" style="font-size:var(--fs-lg)">${esc(p.name)}</span><span class="chip">${esc(p.geometry || "Personalizado")}</span></div>
        <div style="font-size:var(--fs-sm);color:var(--text-sec)">${esc(p.material)}${p.quality ? " · " + esc(p.quality) : ""}</div></div>
      <div class="section"><div class="section-head"><span class="section-title">Geometría</span></div><div class="field-grid">
        ${[["h", p.h], ["b", p.b], ["tw", p.tw], ["tf", p.tf]].map(([k, v]) => `<div class="field"><span class="label">${k}</span><div class="input"><span class="pre">${k}</span><input class="num" value="${num(v)}" readonly><span class="unit">mm</span></div></div>`).join("")}
      </div></div>
      <div class="section"><div class="stats" style="grid-template-columns:1fr 1fr"><div class="stat"><span class="v">${num(p.section)}</span><span class="k">sección cm²</span></div><div class="stat"><span class="v">${num(p.kg_m)}</span><span class="k">peso kg/m</span></div></div></div>
      <div class="section"><button class="btn outline block" data-pa="edit">${ICON("pencil", "sm")}Editar perfil y dibujo</button><button class="btn outline block" data-pa="materials">Materiales</button><button class="btn primary block" data-pa="use_in_costs">Usar en Costes</button></div>`;
    $("#prof-img").addEventListener("click", () => openViewer(p.id)); $("#prof-img-open").addEventListener("click", () => openViewer(p.id));
    $$("#prof-inspector [data-pa]").forEach((b) => b.addEventListener("click", () => profAction(b.dataset.pa, p.id)));
  }
  function profAction(name, id) {
    call("data.profiles_action", { name, id: id || "" }).then((d) => {
      if (d) { D.profiles = d.profiles; renderProfiles(); }
      if (name === "use_in_costs") go("costs");
    });
  }

  // ── Stock ───────────────────────────────────────────────────────────────
  function renderStock() {
    const S = D.stock; if (!S) return;
    const q = ($("#stock-search").value || "").toLowerCase(), pf = $("#stock-profile").value;
    const profs = Array.from(new Set(S.bars.map((b) => b.profile).filter(Boolean))).sort();
    const sel = $("#stock-profile");
    const want = `<option value="">Todos los perfiles</option>` + profs.map((p) => `<option${p === pf ? " selected" : ""}>${esc(p)}</option>`).join("");
    if (sel.innerHTML !== want) sel.innerHTML = want;
    const vis = S.bars.filter((b) => (!q || (b.profile + b.material + b.quality + b.name).toLowerCase().includes(q)) && (!pf || b.profile === pf));
    $("#stock-count").textContent = `${vis.length} items · ${vis.reduce((t, b) => t + b.qty, 0)} ud`;
    const jobLink = (n) => n ? `<a href="#jobs" class="mono" data-jobname="${esc(n)}" style="color:var(--accent);font-size:var(--fs-sm)" title="Clic para abrir en el Explorador de Jobs">${esc(n)}</a>` : "";
    $("#stock-table tbody").innerHTML = vis.map((b) => `<tr data-stock="${esc(b.id)}" class="${b.id === D.stockSel ? "selected" : ""}" style="cursor:pointer">
      <td><input type="checkbox" style="accent-color:var(--accent)" aria-label="Seleccionar"${D.checked.has(b.id) ? " checked" : ""}></td>
      <td><span class="status-dot" style="background:${b.available ? "var(--success)" : "var(--text-dim)"}"></span></td>
      <td>${esc(b.profile || b.material)}</td><td class="mono" style="font-size:var(--fs-sm)">${esc(b.quality || b.name)}</td><td class="num">${Math.round(b.len)}</td><td class="num">${b.qty}</td>
      <td>${b.available ? '<span class="chip success">OK</span>' : '<span class="chip">Agotada</span>'}</td>
      <td>${b.retal ? '<span class="chip accent">Retal</span>' : ""}</td>
      <td>${jobLink(b.created_in)}</td><td>${b.used_in.map(jobLink).join(" ")}</td></tr>`).join("")
      || `<tr><td colspan="10" class="empty-hint">Sin stock. Añade barras o perfiles.</td></tr>`;
    $$("#stock-table [data-stock]").forEach((r) => r.addEventListener("click", (e) => {
      const a = e.target.closest("[data-jobname]");
      if (a) { e.preventDefault(); const j = D.jobs.find((x) => x.name === a.dataset.jobname); go("jobs"); if (j) setTimeout(() => selectJob(j.id), 50); return; }
      if (e.target.type === "checkbox") { e.target.checked ? D.checked.add(r.dataset.stock) : D.checked.delete(r.dataset.stock); return; }
      D.stockSel = r.dataset.stock; renderStock();
    }));
    $$("#stock-table [data-stock]").forEach((r) => r.addEventListener("dblclick", () => stockAction("edit", [r.dataset.stock])));
    const b = S.bars.find((x) => x.id === D.stockSel);
    const totalM = S.bars.reduce((t, x) => t + (x.available ? x.len * x.qty : 0), 0) / 1000;
    $("#stock-inspector").innerHTML = `<div class="section"><div class="stats"><div class="stat"><span class="v">${S.bars.filter((x) => x.available && !x.retal).reduce((t, x) => t + x.qty, 0)}</span><span class="k">barras disp.</span></div>
      <div class="stat"><span class="v">${S.bars.filter((x) => x.retal).length}</span><span class="k">retales</span></div><div class="stat"><span class="v">${fmt(totalM, 1)}</span><span class="k">m lineales</span></div></div></div>` +
      (b ? `<div class="section"><div class="section-head"><span class="section-title">Seleccionado</span>${b.retal ? '<span class="chip accent">Retal</span>' : ""}</div>
      <div class="field"><span class="label">Perfil / material</span><div class="input"><input value="${esc([b.profile, b.material].filter(Boolean).join(" · "))}" readonly></div></div>
      <div class="field"><span class="label">Calidad / referencia</span><div class="input"><input class="num" value="${esc(b.quality || b.name)}" readonly></div></div>
      <div class="field-grid"><div class="field"><span class="label">Largo</span><div class="input"><span class="pre">L</span><input class="num" value="${Math.round(b.len)}" readonly><span class="unit">mm</span></div></div>
      <div class="field"><span class="label">Cantidad</span><div class="input"><span class="pre">×</span><input class="num" value="${b.qty}" readonly></div></div></div>
      <button class="btn outline block" id="stock-edit-btn">${ICON("pencil", "sm")}Editar…</button></div>
      <div class="section"><div class="section-head"><span class="section-title">Trazabilidad</span></div>
      <div style="display:grid;grid-template-columns:auto 1fr;gap:4px 10px;font-size:var(--fs-sm)"><span style="color:var(--text-sec)">Creado en</span><span class="mono">${esc(b.created_in || "—")}</span><span style="color:var(--text-sec)">Usado en</span><span class="mono">${esc(b.used_in.join(", ") || "—")}</span></div></div>`
        : `<div class="empty-hint">Selecciona una barra para ver su ficha.</div>`);
    const eb = $("#stock-edit-btn"); if (eb) eb.addEventListener("click", () => stockAction("edit", [b.id]));
    const mr = $('input[aria-label="Largo mínimo retal"]'); if (mr && document.activeElement !== mr) mr.value = S.min_retal;
  }
  function stockAction(name, ids, value) {
    return call("data.stock_action", { name, ids: ids || [], value }).then((d) => { if (d) { D.stock = d; D.checked.clear(); renderStock(); } });
  }

  // ── loading ─────────────────────────────────────────────────────────────
  function load(view) {
    D.view = view || D.view;
    const subs = () => call("data.subtabs").then((s) => { if (s) { D.subtabs = s; renderPages(); } });
    switch (D.view) {
      case "jobs": return call("data.jobs_list").then((d) => { if (!d) return; D.jobs = d.jobs; D.current = d.current;
        if (D.jobSel == null || !D.jobs.some((j) => j.id === D.jobSel)) D.jobSel = D.current != null ? D.current : (D.jobs[0] || {}).id;
        if (D.jobSel != null) selectJob(D.jobSel); else { D.detail = null; renderJobs(); } });
      case "cuts": subs(); return call("data.cuts_get").then((d) => { if (d) { D.cuts = d; renderCuts(); } });
      case "costs": subs(); return call("data.costs_get").then(setCosts);
      case "profiles": return call("data.profiles_list").then((d) => { if (d) { D.profiles = d.profiles; renderProfiles(); } });
      case "stock": return Promise.all([call("data.stock_list"), call("data.jobs_list")]).then(([s, j]) => { if (j) D.jobs = j.jobs; if (s) { D.stock = s; renderStock(); } });
      default: return Promise.resolve();
    }
  }
  function reload() { load(D.view); window.NT.refreshJob(); }

  function init() {
    // jobs
    $("#jobs-search").addEventListener("input", renderJobs); $("#jobs-field").addEventListener("change", renderJobs);
    // cuts header / params
    const cuts = (payload) => call("data.cuts_set", payload).then((d) => { if (d) { D.cuts = d; renderCuts(); window.NT.refreshJob(); } });
    [["#c-order", "order"], ["#c-offer", "offer"], ["#c-client", "client"]].forEach(([s, k]) => $(s).addEventListener("change", (e) => cuts({ header: { [k]: e.target.value } })));
    [["#c-barlen", "bar_len"], ["#c-kerf", "kerf"], ["#c-margin", "margin"], ["#c-height", "height"], ["#c-system", "calc"]].forEach(([s, k]) => $(s).addEventListener("change", (e) => cuts({ params: { [k]: e.target.value } })));
    $("#c-material").addEventListener("click", () => call("data.cuts_material_search").then((d) => { if (d) { D.cuts = d; renderCuts(); window.NT.refreshJob(); } }));
    const cutHeadBtns = $$("#view-cuts .content-head [data-toast]");
    ["template", "import", "export_xlsx", "export_pdf", "export_dxf"].forEach((name, i) => { const b = cutHeadBtns[i]; if (!b) return;
      b.removeAttribute("data-toast"); b.addEventListener("click", () => call("data.cuts_action", { name }).then((d) => { if (d) { D.cuts = d; renderCuts(); } })); });
    // costs fields
    const costs = (fields) => call("data.costs_set", { fields }).then(setCosts);
    [["#k-kgm", "kg_m"], ["#k-dens", "dens"], ["#k-wall", "wall"], ["#k-pkg", "price_kg"], ["#k-pm", "price_m"], ["#k-pbar", "price_bar"],
      ["#k-margin", "margin"], ["#k-tcut", "t_cut"], ["#k-miter", "miter"], ["#k-op", "op"], ["#k-cur", "currency"], ["#k-mode", "mode"]]
      .forEach(([s, k]) => $(s).addEventListener("change", (e) => costs({ [k]: e.target.value })));
    [['input[aria-label="Sección maciza"]', "solid"], ['input[aria-label="Repartir coste de retales"]', "scrap"], ['input[aria-label="Confirmar configuración"]', "confirm"]]
      .forEach(([s, k]) => $(s).addEventListener("change", (e) => costs({ [k]: e.target.checked })));
    $("#cost-profile-combo").addEventListener("change", (e) => e.target.value && call("data.costs_select_profile", { key: e.target.value }).then(setCosts));
    const costHeadBtns = $$("#view-costs .content-head [data-toast]");
    ["excel", "pdf", "docx", "print"].forEach((name, i) => { const b = costHeadBtns[i]; if (!b) return;
      b.removeAttribute("data-toast"); b.addEventListener("click", () => call("data.costs_action", { name }).then(setCosts)); });
    const costSearch = $('#view-costs .panel.left input[aria-label="Buscar perfil"]');
    if (costSearch) { costSearch.readOnly = true; costSearch.addEventListener("click", () => call("data.costs_action", { name: "material_search" }).then(setCosts)); }
    // profiles
    $("#prof-search").addEventListener("input", renderProfiles);
    $$("#prof-viewmode [data-pv]").forEach((b) => b.addEventListener("click", () => {
      D.profView = b.dataset.pv; $$("#prof-viewmode button").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); renderProfiles(); }));
    const ph = $("#view-profiles .content-head");
    const mat = $('[data-dialog="materials"]', ph); if (mat) { mat.removeAttribute("data-dialog"); mat.addEventListener("click", () => profAction("materials")); }
    const ed = $("#prof-edit-btn"); if (ed) { ed.removeAttribute("data-dialog"); ed.addEventListener("click", () => D.profSel && profAction("edit", D.profSel)); }
    // stock
    $("#stock-search").addEventListener("input", renderStock); $("#stock-profile").addEventListener("change", renderStock);
    $("#stock-all").addEventListener("change", (e) => { D.checked = new Set(e.target.checked && D.stock ? D.stock.bars.map((b) => b.id) : []); renderStock(); });
    const mr = $('input[aria-label="Largo mínimo retal"]'); if (mr) mr.addEventListener("change", (e) => stockAction("min_retal", [], e.target.value));
    const ef = $('#view-stock [data-dialog="stock-fields"]'); if (ef) { ef.removeAttribute("data-dialog"); ef.textContent = "Editar…";
      ef.addEventListener("click", () => { const id = D.stockSel || Array.from(D.checked)[0]; if (id) stockAction("edit", [id]); else window.NT.alert({ kind: "warning", title: "Advertencia", msg: "Selecciona un elemento del stock." }); }); }

    document.addEventListener("click", (e) => { const g = e.target.closest("[data-view-go]"); if (g) go(g.dataset.viewGo); });
    Object.assign(window.NT.ACTIONS, {
      "job-new": () => window.NT.dialog("job-new"),
      "job-open": () => D.jobSel != null && openJob(D.jobSel),
      "job-save": () => D.detail && confirmDialog({ title: "Guardar cambios", text: `¿Guardar los cambios del job «${D.detail.name}»?`, okLabel: "Guardar", danger: false,
        ok: () => call("data.job_save_meta", { id: D.detail.id, client: $("#job-client").value, offer: $("#job-offer").value, order: $("#job-order").value, desc: $("#job-desc").value })
          .then((d) => { if (d) { D.detail = d; toast("Cambios guardados"); load("jobs"); } }) }),
      "job-delete": () => D.detail && confirmDialog({ title: "Eliminar Job", text: `¿Eliminar el job «${D.detail.name}»?`,
        ok: () => call("data.job_delete", { id: D.detail.id }).then((d) => { if (d) { D.jobs = d.jobs; D.current = d.current; D.jobSel = null; D.detail = null; load("jobs"); } }) }),
      "add-cut": () => { D.cuts.rows.push({ descripcion: `Corte ${D.cuts.rows.length + 1}`, largo: 1000, cantidad: 1, inglete1: false, inglete2: false,
        inglete1_dir: "up", inglete2_dir: "up", inglete1_deg: 45, inglete2_deg: 45, color: "#888888" }); pushCuts();
        setTimeout(() => { const r = $$("#cuts-table tbody tr"); const last = r[r.length - 1]; if (last) { const i = last.querySelector('[data-k="descripcion"]'); if (i) { i.focus(); i.select(); } } }, 200); },
      "calc-cuts": () => call("data.cuts_calc").then((d) => { if (d) { D.cuts = d; renderCuts(); } }),
      "add-field": () => call("data.cuts_action", { name: "add_field" }).then((d) => { if (d) { D.cuts = d; renderCuts(); } }),
      "costs-calc": () => {
        const F = D.costs && D.costs.fields;
        const run = () => call("data.costs_calc").then(setCosts);
        if (F && F.confirm) {
          const curName = ($("#k-cur").selectedOptions[0] || {}).textContent || F.currency;
          confirmDialog({ title: "Confirmar configuración de costes", okLabel: "Sí", cancelLabel: "No", danger: false, ok: run,
            text: `¿Continuar con esta configuración de costes?\n\nMoneda: ${curName}\nModo de cálculo de costes: ${($("#k-mode").selectedOptions[0] || {}).textContent}\nMargen de beneficio: ${F.margin || 0} %\nRepartir coste de retales entre piezas: ${F.scrap ? "Sí" : "No"}` });
        } else run();
      },
      "costs-clear": () => call("data.costs_action", { name: "clear" }).then(setCosts),
      "stock-export": () => stockAction("export"),
      "stock-delete": () => {
        const ids = D.checked.size ? Array.from(D.checked) : (D.stockSel ? [D.stockSel] : []);
        if (!ids.length) return window.NT.alert({ kind: "warning", title: "Advertencia", msg: "Selecciona un elemento del stock." });
        confirmDialog({ title: "Eliminar", text: `Eliminar (${ids.length})?`, ok: () => stockAction("delete", ids) });
      },
      "use-profile": () => D.profSel && profAction("use_in_costs", D.profSel),
    });
  }

  window.NT_VIEWS_MOCK = window.NT_VIEWS;
  window.NT_VIEWS = { init, load, reload, renderCuts, renderStock, renderJobs, sectionSVG: window.NT_VIEWS && window.NT_VIEWS.sectionSVG };
})();
