"""
Generate the README screenshots for one locale, with the UI *and* the demo
content in that language, in light theme (the default), plus a dark-theme
nesting shot for the light/dark comparison.

Run once per locale (each in its own process so the DB singletons start fresh):

    QT_QPA_PLATFORM=offscreen python .devcontainer/scripts/shot_readme_localized.py en
    QT_QPA_PLATFORM=offscreen python .devcontainer/scripts/shot_readme_localized.py es

Output: docs/img/<lang>/{jobs,cuts,nesting,nesting_dark,costs,profiles,stock}.png
"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, _ROOT)

LANG = (sys.argv[1] if len(sys.argv) > 1 else "en").lower()
OUTDIR = os.path.join(_ROOT, "docs", "img", LANG)
os.makedirs(OUTDIR, exist_ok=True)

# Start from clean local databases so each locale's Jobs/Stock tabs show only
# this run's localized data (these files are git-ignored working data).
for _f in ("nestify_geometry.db", "stock_db.json"):
    try:
        os.remove(os.path.join(_ROOT, _f))
    except FileNotFoundError:
        pass

# Localized demo content: a small steel-canopy frame job.
CONTENT = {
    "en": {
        "client": "Demo Client Ltd",
        "order": "PO-2026-001",
        "offer": "QUO-2026-042",
        "desc": "Steel Canopy - Demo",
        "cuts": [
            ("Main beam", 3500, 4, False, False),
            ("Purlin", 1200, 6, False, False),
            ("Strut", 800, 8, False, False),
            ("Diagonal", 2800, 2, True, True),
            ("Base plate", 400, 4, False, False),
        ],
        "stock_notes": ["Batch A1", "Batch A2", "Batch A3", "Project B"],
    },
    "es": {
        "client": "Cliente Demo SL",
        "order": "PED-2026-001",
        "offer": "OFR-2026-042",
        "desc": "Marquesina Acero - Demo",
        "cuts": [
            ("Viga principal", 3500, 4, False, False),
            ("Correa", 1200, 6, False, False),
            ("Montante", 800, 8, False, False),
            ("Diagonal", 2800, 2, True, True),
            ("Placa base", 400, 4, False, False),
        ],
        "stock_notes": ["Lote A1", "Lote A2", "Lote A3", "Proyecto B"],
    },
}[LANG]

from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from nestify import i18n
i18n.set_language(LANG)

from nestify.ui_qt.app import NestifyApp
from nestify.models import Corte
from nestify.logic import calcular_barras, calcular_resultado
from nestify.context_sync import ensure_material_contexts, apply_auto_barras
from nestify.profile_catalog import ensure_catalog_profiles
from nestify import stock_db as sdb
from nestify import app_config as _ac

win = NestifyApp()
win._show_about_startup = lambda: None
# Make sure every t() string is rendered in the requested locale, then build a
# fresh window in that language.
win._set_language(LANG)
win._set_theme("light")
win.resize(1400, 860)
win.show()
app.processEvents()


def goto(idx):
    win._tabs.blockSignals(True)
    win._tabs.setCurrentIndex(idx)
    win._tabs.blockSignals(False)
    win._last_main_tab = idx
    app.processEvents()


def shot(name):
    app.processEvents()
    ok = win.grab().save(os.path.join(OUTDIR, f"{name}.png"))
    print(f"  {'OK ' if ok else 'FAIL'} {LANG}/{name}.png")


BAR_LEN, KERF, MARGIN, BAR_H = 6000.0, 3.0, 50.0, 200.0

cortes = []
for desc, largo, qty, i1, i2 in CONTENT["cuts"]:
    c = Corte()
    c.descripcion, c.largo, c.cantidad = desc, float(largo), qty
    c.inglete1, c.inglete1_dir, c.inglete1_deg = i1, "up", 45.0
    c.inglete2, c.inglete2_dir, c.inglete2_deg = i2, "down", 45.0
    cortes.append(c)

barras = calcular_barras(BAR_LEN, cortes, system="ffd", gap=KERF + MARGIN)

state = win._state
state.longitud_barra = BAR_LEN
state.perdida_corte = KERF
state.margen_tubo = MARGIN
state.nesting_height_override = BAR_H
state.cortes = cortes
state.calc_system = "ffd"
state.cliente = CONTENT["client"]
state.pedido = CONTENT["order"]
state.oferta = CONTENT["offer"]
state.descripcion = CONTENT["desc"]

ensure_material_contexts(state)
ctx = state.material_contexts[0]
ctx.longitud_barra, ctx.perdida_corte, ctx.margen_tubo = BAR_LEN, KERF, MARGIN
ctx.cortes, ctx.nesting_height_override = cortes, BAR_H
ctx.profile_name, ctx.material = "IPE 200", "S235"
apply_auto_barras(state, ctx, barras)

win._tab_cortes.load_state(state)
win._tab_nesting.load_state(state)
ensure_catalog_profiles()
win._tab_perfiles.refresh_profile_selector()
app.processEvents()

# Actually place the pieces on the canvas. The nesting tab must be the visible,
# laid-out tab first, otherwise the graphics view has no size and fit_scene()
# zooms to nothing. Use simple (1D) mode so auto-nest runs synchronously.
tab_n = win._tab_nesting
goto(2)
if hasattr(tab_n, "_mode_switch") and tab_n._mode_switch.isChecked():
    tab_n._mode_switch.setChecked(False)
    app.processEvents()
tab_n._run_auto_nest(skip_clear_warning=True)
_deadline = time.time() + 20
while getattr(tab_n, "_auto_nesting", False) and time.time() < _deadline:
    app.processEvents()
    time.sleep(0.05)
placed = sum(len(b) for b in (tab_n._bars or []))
print(f"  auto-nest: {len(tab_n._bars or [])} bars, {placed} pieces placed")
tab_n.sync_to_state()
tab_n._nesting_dirty = False
tab_n._view.fit_scene()
app.processEvents()


def fit_nesting():
    """Fit the nesting view to its content (the view must be visible)."""
    tab_n._view.fit_scene()
    app.processEvents()

# Cuts tab: refresh the result label + bar preview without the calc dialog.
from nestify.i18n import t as _t
n_bars = len(barras)
used = sum(sum(b) for b in barras)
eff = used / (n_bars * BAR_LEN) * 100 if n_bars else 0
win._tab_cortes._result_lbl.setText(f"{n_bars} {_t('bars_abbr')} · {eff:.1f}%")
win._tab_cortes._preview.set_state(state)
win._tab_cortes._assign_row_colors()
app.processEvents()

# Costs tab: select IPE 200, set pricing, compute result cards directly.
tab_p = win._tab_perfiles
ipe_key = next((f"custom:{cp.name}" for cp in _ac.get().custom_profiles
                if cp.name == "IPE 200"), None)
if ipe_key:
    tab_p._select_profile(ipe_key)
tab_p.ui.e_precio_kg.setText("0.85")
tab_p.ui.e_margen_beneficio.setText("15")
tab_p.ui.e_t_recto.setText("3")
tab_p.ui.e_pct_inglete.setText("35")
tab_p.ui.e_coste_op.setText("30")
app.processEvents()
try:
    ensure_material_contexts(state)
    ctx_p = state.material_contexts[state.active_material_index]
    ctx_p.cortes = ctx_p.cortes or cortes
    ctx_p.longitud_barra = BAR_LEN
    perfil = tab_p._build_config()
    if perfil:
        state.perfil = perfil
        from nestify.ui_qt.tab_perfiles import _ResultCard
        tab_p._clear_results()
        n_ing = sum(1 for c in cortes if c.inglete1 or c.inglete2)
        for c in cortes:
            res = calcular_resultado(c, perfil, barras, BAR_LEN, n_ing)
            card = _ResultCard(res, "EUR")
            tab_p.ui.results_layout.insertWidget(
                tab_p.ui.results_layout.count() - 1, card)
        app.processEvents()
except Exception as exc:  # pragma: no cover - screenshot helper
    print(f"  warn: cost cards skipped ({exc})")

# Stock inventory with localized notes.
for i in range(3):
    sdb.add_bar("IPE 200", "S235", 6000, notes=CONTENT["stock_notes"][i])
sdb.add_bar("HEA 140", "S275", 12000, quantity=2, notes=CONTENT["stock_notes"][3])
win._tab_stock._refresh_list()
app.processEvents()

# Save the job silently (silent=True avoids the modal "saved" dialog that blocks
# offscreen) so the Jobs Explorer shows a localized entry.
win._save_job_to_db(silent=True)
win._tab_jobs.refresh_list()
app.processEvents()

# Light-theme captures (default theme).
for idx, name in [(0, "jobs"), (1, "cuts"), (2, "nesting"),
                  (3, "costs"), (4, "profiles"), (5, "stock")]:
    goto(idx)
    if idx == 2:
        fit_nesting()
    shot(name)

# Dark-theme nesting for the light/dark comparison.
win._set_theme("dark")
app.processEvents()
goto(2)
fit_nesting()
shot("nesting_dark")

print(f"done ({LANG})")
app.quit()
