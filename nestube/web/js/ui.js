/* ==========================================================================
   NesTube web UI — shell behaviour (MOCKUP STAGE)
   Menus, workspace tabs, inspector tabs, theme, dialogs, toasts and the
   keyboard shortcuts of the Qt app (TabNesting._setup_shortcuts + File menu).
   Every action is routed through `NT.action(id)` so the functional stage only
   has to swap the stub for a call into the Python bridge (pywebview js_api).
   ========================================================================== */
(function () {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const N = () => window.NestCanvas;
  const ICON = (id, cls = "") => `<svg class="icon ${cls}"><use href="#i-${id}"/></svg>`;

  // ── toasts ──────────────────────────────────────────────────────────────
  let toastTimer = null;
  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 2200);
  }

  // ── menus ───────────────────────────────────────────────────────────────
  // Item: { label, sc, action, check:()=>bool, danger, disabled, sub:[...] } | "-" | { header }
  const openMenus = [];
  function closeMenus(depth = 0) {
    while (openMenus.length > depth) { const m = openMenus.pop(); m.el.remove(); if (m.anchor) m.anchor.setAttribute("aria-expanded", "false"); }
  }
  function buildMenu(items, depth) {
    const m = document.createElement("div");
    m.className = "menu"; m.setAttribute("role", "menu");
    items.forEach((it) => {
      if (it === "-") { m.appendChild(document.createElement("hr")); return; }
      if (it.header) { const h = document.createElement("div"); h.className = "mh"; h.textContent = it.header; m.appendChild(h); return; }
      const mi = document.createElement("div");
      mi.className = "mi" + (it.danger ? " danger" : "") + (it.disabled ? " disabled" : "") + (it.check && it.check() ? " checked" : "");
      mi.setAttribute("role", "menuitem"); mi.tabIndex = -1;
      const hasTick = items.some((x) => x && x.check);
      mi.innerHTML = (hasTick ? ICON("check", "tick") : "") + `<span>${it.label}</span>` +
        (it.sc ? `<span class="sc">${it.sc}</span>` : "") + (it.sub ? ICON("chevron-right", "sub") : "");
      if (it.sub) {
        mi.addEventListener("mouseenter", () => {
          closeMenus(depth + 1); $$(".mi.open", m).forEach((x) => x.classList.remove("open")); mi.classList.add("open");
          const r = mi.getBoundingClientRect(); const sm = buildMenu(it.sub, depth + 1);
          document.body.appendChild(sm); openMenus.push({ el: sm });
          const sr = sm.getBoundingClientRect();
          let left = r.right + 4; if (left + sr.width > innerWidth - 8) left = r.left - sr.width - 4;
          sm.style.left = left + "px"; sm.style.top = Math.min(r.top - 6, innerHeight - sr.height - 8) + "px";
        });
      } else {
        mi.addEventListener("mouseenter", () => { closeMenus(depth + 1); $$(".mi.open", m).forEach((x) => x.classList.remove("open")); });
        mi.addEventListener("click", () => { closeMenus(); if (it.action) it.action(); });
      }
      m.appendChild(mi);
    });
    return m;
  }
  function openMenu(items, x, y, anchor) {
    closeMenus();
    const m = buildMenu(items, 0); document.body.appendChild(m);
    openMenus.push({ el: m, anchor });
    if (anchor) anchor.setAttribute("aria-expanded", "true");
    const r = m.getBoundingClientRect();
    m.style.left = Math.max(8, Math.min(x, innerWidth - r.width - 8)) + "px";
    m.style.top = Math.max(8, Math.min(y, innerHeight - r.height - 8)) + "px";
  }
  function openMenuAt(btn, items, align = "left") {
    if (btn.getAttribute("aria-expanded") === "true") { closeMenus(); return; }
    const r = btn.getBoundingClientRect();
    openMenu(items, align === "right" ? r.right - 220 : r.left, r.bottom + 4, btn);
  }
  document.addEventListener("pointerdown", (e) => { if (!e.target.closest(".menu") && !e.target.closest("[data-menu]")) closeMenus(); });

  // ── dialogs ─────────────────────────────────────────────────────────────
  function openModal(title, bodyHTML, footHTML, wide) {
    $("#modal-title").textContent = title;
    $("#modal-body").innerHTML = bodyHTML;
    $("#modal-foot").innerHTML = footHTML || `<button class="btn outline" data-close>Cerrar</button>`;
    $("#modal").style.width = wide === "xl" ? "min(1080px,100%)" : wide ? "min(760px,100%)" : "";
    $("#modal-backdrop").hidden = false;
    const f = $("#modal-body input, #modal-body select, #modal-foot .btn.primary"); if (f) f.focus();
  }
  function closeModal() { $("#modal-backdrop").hidden = true; $("#modal").classList.remove("modal-alert"); }
  function confirmDialog({ title, text, ok, okLabel = "Sí", cancelLabel = "No", danger = true }) {
    alertBox({ kind: "question", title, msg: text, buttons: [{ label: cancelLabel }, { label: okLabel, primary: true, danger, action: ok }] });
  }

  // ── workspace tabs ──────────────────────────────────────────────────────
  function showView(name) {
    $$(".workspace-tabs [data-view]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.view === name)));
    $$(".view").forEach((v) => { v.hidden = v.id !== "view-" + name; });
    document.body.dataset.view = name;
    try { localStorage.setItem("nt.view", name); } catch (e) { /* storage unavailable */ }
    if (name === "nesting") requestAnimationFrame(() => N().fit());
  }

  // ── theme ───────────────────────────────────────────────────────────────
  function currentTheme() {
    const t = document.documentElement.dataset.theme;
    if (t) return t;
    return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function setTheme(t) {
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem("nt.theme", t); } catch (e) { /* storage unavailable */ }
    $("#theme-btn").innerHTML = ICON(t === "dark" ? "sun" : "moon");
  }

  // ── alerts (QMessageBox equivalents) ────────────────────────────────────
  // kind: information | warning | critical | question.
  // buttons: [{ label, primary, danger, action }] — default depends on kind.
  const ALERT_ICON = { information: "info", warning: "warning", critical: "error", question: "question" };
  function alertBox({ kind = "information", title, msg, buttons }) {
    const esc = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;");
    const body = `<div class="alert alert-${kind}"><span class="alert-icon"><svg class="icon lg"><use href="#i-${ALERT_ICON[kind] || "info"}"/></svg></span>
      <div class="alert-text">${esc(msg).replace(/\n/g, "<br>")}</div></div>`;
    const btns = buttons || (kind === "question"
      ? [{ label: "No" }, { label: "Sí", primary: true }]
      : [{ label: "Aceptar", primary: true }]);
    openModal(title, body, btns.map((b, i) => `<button class="btn ${b.primary ? (b.danger ? "danger solid" : "primary") : b.danger ? "danger" : "outline"}" data-alert-btn="${i}">${b.label}</button>`).join(""));
    $("#modal").classList.add("modal-alert");
    $$("[data-alert-btn]").forEach((el) => el.addEventListener("click", () => { closeModal(); const b = btns[+el.dataset.alertBtn]; if (b.action) b.action(); }));
    const p = $("#modal-foot .btn.primary, #modal-foot .btn.solid"); if (p) p.focus();
  }

  window.NT = { $, $$, ICON, toast, alert: alertBox, openMenu, openMenuAt, closeMenus, openModal, closeModal, confirmDialog,
    showView, setTheme, currentTheme };
})();
