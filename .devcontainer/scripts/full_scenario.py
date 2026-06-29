"""
scripts/full_scenario.py
Real-case scenario: canopy steel frame job using IPE 200 profile.
Exercises every tab and major function. Screenshots → docs/img/.

Tabs: 0=Jobs  1=Cuts  2=Nesting  3=Costs  4=Profiles&Tubes  5=Stock

Usage:
    QT_QPA_PLATFORM=offscreen python scripts/full_scenario.py
"""
import os, sys, time, traceback

os.environ["QT_QPA_PLATFORM"] = "offscreen"
# This script lives in .devcontainer/scripts/; the project root is two levels up.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _ROOT)

OUTDIR = os.path.join(_ROOT, "docs", "img")
os.makedirs(OUTDIR, exist_ok=True)

BUGS = []
NOTES = []

def goto(win, app, idx):
    """Switch tab without triggering _on_main_tab_changed callbacks."""
    win._tabs.blockSignals(True)
    win._tabs.setCurrentIndex(idx)
    win._tabs.blockSignals(False)
    win._last_main_tab = idx
    app.processEvents()

def shot(win, app, name, caption=""):
    app.processEvents()
    path = os.path.join(OUTDIR, f"{name}.png")
    ok = win.grab().save(path)
    print(f"  📸  {name}.png {'✓' if ok else '✗'}  {caption}")
    return path

def note(msg):
    print(f"       [ok] {msg}")
    NOTES.append(msg)

def bug(msg):
    print(f"       [BUG] {msg}")
    BUGS.append(msg)

# ──────────────────────────────────────────────────────────────────────────────
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from nestify.ui_qt.app import NestifyApp
from nestify.models import Corte, TipoPerfil
from nestify.logic import calcular_barras
from nestify.context_sync import ensure_material_contexts, apply_auto_barras
from nestify.profile_catalog import ensure_catalog_profiles

win = NestifyApp()
# Disarm the startup About dialog timer — it fires after 800ms via
# QTimer.singleShot and calls AboutDialog.exec(), blocking offscreen runs.
win._show_about_startup = lambda: None
win._set_theme("dark")
win.resize(1400, 860)
win.show()
app.processEvents()

print("\n═══════════════════════════════════════════════════════")
print("  Nestify — Full Scenario: Canopy Steel Frame Job")
print("═══════════════════════════════════════════════════════\n")

# ═════════════════════════════════════════════════════════════════════════════
# Build scenario state DIRECTLY (no UI dialogs possible)
# ═════════════════════════════════════════════════════════════════════════════
BAR_LEN  = 6000.0
KERF     = 3.0
MARGIN   = 50.0
BAR_H    = 200.0   # IPE 200 section height

CUTS = [
    # (desc, largo, qty, i1, i1d, i1deg, i2, i2d, i2deg)
    ("Viga principal",  3500, 4, False, "up", 45.0, False, "up", 45.0),
    ("Correa",          1200, 6, False, "up", 45.0, False, "up", 45.0),
    ("Montante",         800, 8, False, "up", 45.0, False, "up", 45.0),
    ("Diagonal",        2800, 2, True,  "up", 45.0, True,  "down", 45.0),
    ("Placa base",       400, 4, False, "up", 45.0, False, "up", 45.0),
]

cortes = []
for desc, largo, qty, i1, i1d, i1deg, i2, i2d, i2deg in CUTS:
    c = Corte()
    c.descripcion  = desc
    c.largo        = float(largo)
    c.cantidad     = qty
    c.inglete1     = i1
    c.inglete1_dir = i1d
    c.inglete1_deg = i1deg
    c.inglete2     = i2
    c.inglete2_dir = i2d
    c.inglete2_deg = i2deg
    cortes.append(c)

# Run the packing engine
barras = calcular_barras(BAR_LEN, cortes, system="ffd", gap=KERF + MARGIN)
n_bars = len(barras)
used   = sum(sum(b) for b in barras)
total  = n_bars * BAR_LEN
eff    = used / total * 100 if total else 0
note(f"FFD: {n_bars} bars, {sum(c.cantidad for c in cortes)} pieces, {eff:.1f}% efficiency")

# Populate AppState
state = win._state
state.longitud_barra = BAR_LEN
state.perdida_corte  = KERF
state.margen_tubo    = MARGIN
state.nesting_height_override = BAR_H
state.cortes         = cortes
state.calc_system    = "ffd"
state.cliente = "Cliente Demo SL"
state.pedido  = "PED-2026-001"
state.oferta  = "OFR-2026-042"

ensure_material_contexts(state)
ctx = state.material_contexts[0]
ctx.longitud_barra  = BAR_LEN
ctx.perdida_corte   = KERF
ctx.margen_tubo     = MARGIN
ctx.cortes          = cortes
ctx.nesting_height_override = BAR_H
apply_auto_barras(state, ctx, barras)

# Sync to tab_cortes UI (no calc dialog needed)
tab_c = win._tab_cortes
tab_c.load_state(state)
app.processEvents()

# ═════════════════════════════════════════════════════════════════════════════
print("\n0. Jobs Explorer")
goto(win, app, 0)
shot(win, app, "01_jobs_empty", "Jobs Explorer – empty state on first launch")

# ═════════════════════════════════════════════════════════════════════════════
print("\n1. Cuts – bar parameters & cut list")
goto(win, app, 1)
shot(win, app, "02_cuts_params", "Cuts – bar parameters (6000 mm, kerf 3 mm, margin 50 mm)")

# Manually trigger the result label (bypass _calcular dialog risk)
from nestify.i18n import t as _t
tab_c._result_lbl.setText(f"{n_bars} {_t('bars_abbr')} · {eff:.1f}%")
tab_c._preview.set_state(state)
tab_c._assign_row_colors()
app.processEvents()
shot(win, app, "03_cuts_list", "Cuts – 5 cut types entered (24 pieces total)")
shot(win, app, "04_cuts_result", f"Cuts – FFD result: {n_bars} bars, {eff:.1f}% efficiency")
shot(win, app, "cuts", "Cuts – master README screenshot (dark)")

# Button / tooltip check
for attr, label in [("btn_template","Template"), ("btn_import","Import"), ("btn_export_pdf","Export PDF")]:
    btn = getattr(tab_c, attr, None)
    if btn is None:
        bug(f"tab_cortes missing {attr}")
    elif not btn.isVisible():
        bug(f"{attr} not visible")
    else:
        tt = btn.toolTip()
        note(f"{label}: text={btn.text()!r}, tooltip={tt!r}")
        if not tt:
            bug(f"{attr} has no tooltip")

# ═════════════════════════════════════════════════════════════════════════════
print("\n2. Nesting tab")
goto(win, app, 2)
tab_n = win._tab_nesting

# Ensure material context has profile name so auto-nest doesn't prompt for material
ctx = state.material_contexts[state.active_material_index]
ctx.profile_name = "IPE 200"
ctx.material     = "S235"

# Load state into nesting tab so _pieces gets populated from cortes
tab_n.load_state(state)
app.processEvents()

status0 = tab_n.ui.status_lbl.text()
note(f"Nesting status (initial after load_state): {status0!r}")
shot(win, app, "05_nesting_initial", "Nesting – initial state (pieces loaded)")

# Verify status updates after _add_bar
n_bars_before = len(tab_n._bars)
tab_n._add_bar()
app.processEvents()
status1 = tab_n.ui.status_lbl.text()
note(f"Nesting status after _add_bar: {status1!r}")
if len(tab_n._bars) <= n_bars_before:
    bug("_add_bar() didn't add a bar")
shot(win, app, "06_nesting_bar_added", "Nesting – one bar added")

# Auto-nest — use SIMPLE mode (1D packer, synchronous, no thread)
print("  Running auto-nest (simple / 1D mode)...")
try:
    # Ensure simple mode (mode_switch unchecked = simple)
    if hasattr(tab_n, "_mode_switch") and tab_n._mode_switch.isChecked():
        tab_n._mode_switch.setChecked(False)
        app.processEvents()

    tab_n._run_auto_nest(skip_clear_warning=True)
    # Wait for worker thread (advanced) or instant (simple)
    deadline = time.time() + 20
    while tab_n._auto_nesting and time.time() < deadline:
        app.processEvents()
        time.sleep(0.05)
    if tab_n._auto_nesting:
        tab_n._cancel_auto_nest()
        app.processEvents()
        note("Auto-nest cancelled after 20s")
    else:
        placed = sum(len(b) for b in (tab_n._bars or []))
        note(f"Auto-nest: {len(tab_n._bars or [])} bars, {placed} pieces placed")
        if placed == 0:
            bug("Auto-nest placed 0 pieces")
except Exception as e:
    bug(f"Auto-nest error: {e}")
    traceback.print_exc()

app.processEvents()
shot(win, app, "07_nesting_autonest", "Nesting – after auto-nest")
shot(win, app, "nesting", "Nesting – master README screenshot (dark)")

# Flush nesting state so the "unsaved changes" dialog doesn't block tab switch
tab_n.sync_to_state()
tab_n._nesting_dirty = False

# ═════════════════════════════════════════════════════════════════════════════
print("\n3. Costs & Weight tab")
goto(win, app, 3)
tab_p = win._tab_perfiles

ensure_catalog_profiles()
tab_p.refresh_profile_selector()
app.processEvents()

shot(win, app, "08_costs_builtin", "Costs – initial builtin profile")

# Select IPE 200 — catalog profiles live in custom_profiles with key "custom:<name>",
# not necessarily in the visible _tiles (which shows only recent/builtin favourites).
from nestify import app_config as _ac
ipe_key = next(
    (f"custom:{cp.name}" for cp in _ac.get().custom_profiles if cp.name == "IPE 200"),
    None,
)
if ipe_key:
    tab_p._select_profile(ipe_key)
    app.processEvents()
    kg_m = tab_p.ui.e_kg_m.text().strip()
    note(f"IPE 200 kg/m = {kg_m!r}")
    if not kg_m:
        bug("IPE 200 e_kg_m empty — catalog not loading weight")
    if tab_p.ui.e_peso_esp.isEnabled():
        bug("e_peso_esp should be disabled while catalog kg/m is set")
    else:
        note("e_peso_esp correctly disabled (kg/m overrides it)")
    shot(win, app, "09_costs_ipe200", "Costs – IPE 200 catalog profile")
else:
    bug("IPE 200 not found in catalog")
    shot(win, app, "09_costs_ipe200", "Costs – builtin H (IPE 200 not in catalog)")

# Enter pricing
tab_p.ui.e_precio_kg.setText("0.85")
tab_p.ui.e_margen_beneficio.setText("15")
tab_p.ui.e_t_recto.setText("3")
tab_p.ui.e_pct_inglete.setText("35")
tab_p.ui.e_coste_op.setText("30")
app.processEvents()

# Test catalog→builtin switch
tab_p._select_profile("builtin:redondo")
app.processEvents()
if tab_p.ui.e_kg_m.text().strip():
    bug(f"e_kg_m not cleared on catalog→builtin switch: {tab_p.ui.e_kg_m.text()!r}")
else:
    note("e_kg_m cleared correctly on catalog→builtin switch")
if not tab_p.ui.e_peso_esp.isEnabled():
    bug("e_peso_esp still disabled after catalog→builtin switch")
else:
    note("e_peso_esp re-enabled correctly after catalog→builtin switch")

# Switch back to IPE 200 for calculation
if ipe_key:
    tab_p._select_profile(ipe_key)
    tab_p.ui.e_precio_kg.setText("0.85")
    tab_p.ui.e_margen_beneficio.setText("15")
    tab_p.ui.e_t_recto.setText("3")
    tab_p.ui.e_pct_inglete.setText("35")
    tab_p.ui.e_coste_op.setText("30")
    app.processEvents()

# Calculate costs directly via logic (no QMessageBox risk)
try:
    from nestify.logic import calcular_resultado
    from nestify.context_sync import save_state_to_context
    from nestify.ui_qt.tab_perfiles import _ResultCard

    # Ensure costs tab has current cuts in its context
    ensure_material_contexts(state)
    ctx_p = state.material_contexts[state.active_material_index]
    if not ctx_p.cortes:
        ctx_p.cortes = cortes
    ctx_p.longitud_barra = BAR_LEN

    perfil = tab_p._build_config()
    if perfil:
        state.perfil = perfil
        from nestify.ui_qt.tab_perfiles import _ResultCard
        tab_p._clear_results()
        total = 0.0
        n_ingletes = sum(1 for c in cortes if c.inglete1 or c.inglete2)
        barras_p = calcular_barras(BAR_LEN, cortes, system="ffd", gap=KERF + MARGIN)
        for c in cortes:
            res = calcular_resultado(c, perfil, barras_p, BAR_LEN, n_ingletes)
            total += res.precio_total_linea
            card = _ResultCard(res, "EUR")
            tab_p.ui.results_layout.insertWidget(tab_p.ui.results_layout.count() - 1, card)
        note(f"Costs calculated: total={total:.2f} EUR")
        app.processEvents()
    else:
        note("perfil build returned None — skipping cost cards")
except Exception as e:
    bug(f"Cost calculation: {e}")

shot(win, app, "10_costs_result", "Costs – calculation result")
shot(win, app, "costs", "Costs – master README screenshot (dark)")

# ═════════════════════════════════════════════════════════════════════════════
print("\n4. Profiles & Tubes tab")
goto(win, app, 4)
tab_mat = win._tab_materiales

shot(win, app, "11_profiles_list", "Profiles & Tubes – list view")
shot(win, app, "profiles", "Profiles & Tubes – master README (dark)")

if hasattr(tab_mat, "_btn_view_grid"):
    tab_mat._btn_view_grid.click()
    app.processEvents()
    shot(win, app, "12_profiles_grid", "Profiles & Tubes – grid view")
    tab_mat._btn_view_list.click()
    app.processEvents()

if hasattr(tab_mat, "_search"):
    tab_mat._search.setText("IPE")
    app.processEvents()
    shot(win, app, "13_profiles_search", "Profiles & Tubes – search 'IPE'")
    tab_mat._search.clear()
    app.processEvents()

# ═════════════════════════════════════════════════════════════════════════════
print("\n5. Stock tab")
goto(win, app, 5)
tab_s = win._tab_stock

shot(win, app, "14_stock_empty", "Stock – initial state")

from nestify import stock_db as sdb
for i in range(3):
    sdb.add_bar("IPE 200", "S235", 6000, notes=f"Lote A{i+1}")
sdb.add_bar("HEA 140", "S275", 12000, quantity=2, notes="Proyecto B")

tab_s._refresh_list()
app.processEvents()
note("Stock refreshed via _refresh_list()")

shot(win, app, "15_stock_filled", "Stock – 4 bar entries")
shot(win, app, "stock", "Stock – master README screenshot (dark)")

# ID uniqueness test
db = sdb.get_stock()
if db.bars:
    del_id = db.bars[-1].id
    sdb.remove_bar(del_id)
    new_bar = sdb.add_bar("UPN 100", "S235", 9000, notes="Test")
    db2 = sdb.load_stock()
    ids = [b.id for b in db2.bars]
    if len(ids) != len(set(ids)):
        bug(f"Duplicate stock IDs after delete+add: {ids}")
    else:
        note(f"Stock IDs unique after delete+add (n={len(ids)}, last={ids[-1]})")

# ═════════════════════════════════════════════════════════════════════════════
print("\n6. About dialog – donate URLs")
try:
    from nestify.ui_qt.dialogs.about_dialog import AboutDialog
    prefs = win._prefs
    dlg = AboutDialog(win, github_url=win._github_url(),
                      paypal_url=prefs.paypal_url,
                      buymeacoffee_url=prefs.buymeacoffee_url)
    dlg.show()
    app.processEvents()
    for attr, url in [("paypal_btn", prefs.paypal_url), ("coffee_btn", prefs.buymeacoffee_url)]:
        btn = getattr(dlg.ui, attr)
        if btn.isVisible():
            note(f"{attr} visible — {url!r}")
        else:
            bug(f"{attr} hidden — url={url!r}")
    dlg.grab().save(os.path.join(OUTDIR, "16_about.png"))
    print(f"  📸  16_about.png ✓  About dialog")
    dlg.close()
    app.processEvents()
except Exception as e:
    bug(f"About dialog: {e}")

# ═════════════════════════════════════════════════════════════════════════════
print("\n7. Export utils cross-platform check")
import nestify.export_utils as eu
if not hasattr(eu, "_open_file"):
    bug("_open_file helper missing — os.startfile still used?")
else:
    import inspect
    src = inspect.getsource(eu._open_file)
    if "xdg-open" in src and "win32" in src and "darwin" in src:
        note("_open_file: cross-platform (win32/darwin/linux) ✓")
    else:
        bug("_open_file missing some platforms")

# ═════════════════════════════════════════════════════════════════════════════
print("\n8. Save job → Jobs Explorer")
try:
    state.descripcion = "Marquesina Acero - Demo"
    win._save_job_to_db()
    note("Job saved to geometry DB")
except Exception as e:
    bug(f"_save_job_to_db(): {e}")

goto(win, app, 0)
win._tab_jobs.refresh_list()
app.processEvents()
shot(win, app, "17_jobs_saved", "Jobs Explorer – after saving job")
shot(win, app, "jobs", "Jobs – master README screenshot (dark)")

# ═════════════════════════════════════════════════════════════════════════════
print("\n9. Light theme screenshots")
win._set_theme("light")
app.processEvents()
for idx, name in [(1, "cuts_light"), (2, "nesting_light"), (3, "costs_light"),
                   (4, "profiles_light"), (5, "stock_light")]:
    goto(win, app, idx)
    shot(win, app, name, f"Light theme – tab {idx}")

win._set_theme("dark")
app.processEvents()

# ═════════════════════════════════════════════════════════════════════════════
print("\n10. Final verification – dark master screenshots")
for idx, name in [(0,"jobs"), (1,"cuts"), (2,"nesting"), (3,"costs"), (4,"profiles"), (5,"stock")]:
    goto(win, app, idx)
    shot(win, app, name, f"Master dark – {name}")

# ═════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*57)
print("  SCENARIO COMPLETE")
print("═"*57)
print(f"\n  Notes ({len(NOTES)}):")
for n in NOTES:
    print(f"    • {n}")
print(f"\n  Bugs/improvements ({len(BUGS)}):")
if BUGS:
    for b in BUGS:
        print(f"    🐛 {b}")
else:
    print("    (none)")
print(f"\n  Screenshots → {OUTDIR}\n")
app.quit()
