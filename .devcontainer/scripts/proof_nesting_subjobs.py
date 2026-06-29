"""
Proof driver for the nesting-subjobs / material-selection / theming batch.

Each capture runs in its own subprocess that ends with os._exit(0) so close-time
"unsaved changes" dialogs can never block the run.

Usage: QT_QPA_PLATFORM=offscreen python scripts/proof_nesting_subjobs.py
"""
import os, sys, subprocess

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(repo, "docs")

CHILD = r"""
import os, sys
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, {repo!r})
from PySide6.QtWidgets import QApplication
app = QApplication([])
from nestify.ui_qt.app import NestifyApp
from nestify.models import Corte
from nestify.context_sync import save_state_to_context

def pe():
    app.processEvents(); app.processEvents()

w = NestifyApp(); w._set_theme({theme!r}); w.resize(1480, 880); w.show(); pe()
nest = w._tab_nesting
state = w._state
MODE = {mode!r}

if MODE == 'toolbar':
    w._tabs.setCurrentIndex(2); pe()
    print('sel_material button text =', repr(nest._sel_material_btn.text()), flush=True)
    ok = w.grab().save({out!r}); print('saved' if ok else 'FAIL', {out!r}, flush=True)

elif MODE == 'persist':
    w._tabs.setCurrentIndex(2); pe()
    state.cortes = [Corte(descripcion='A-cut', largo=1000, cantidad=3)]
    nest.sync_to_state(); save_state_to_context(state, state.active_material_index)
    print('contexts before add:', len(state.material_contexts), flush=True)
    nest._subtabs._on_add_clicked(); pe()
    print('contexts after add :', len(state.material_contexts), 'active:', state.active_material_index, flush=True)
    state.cortes = [Corte(descripcion='B-cut', largo=500, cantidad=7)]
    nest.sync_to_state(); save_state_to_context(state, state.active_material_index)
    nest._subtabs._on_tab_clicked(0); pe()
    a = [c.descripcion for c in state.cortes]
    print('switch->subjob1 cuts:', a, flush=True)
    assert a == ['A-cut'], 'subjob1 data lost'
    nest._subtabs._on_tab_clicked(1); pe()
    b = [c.descripcion for c in state.cortes]
    print('switch->subjob2 cuts:', b, flush=True)
    assert b == ['B-cut'], 'subjob2 data lost'
    print('PERSISTENCE OK', flush=True)
    ok = w.grab().save({out!r}); print('saved' if ok else 'FAIL', {out!r}, flush=True)

elif MODE == 'completer':
    w._tabs.setCurrentIndex(1); pe()
    bar = w._tab_cortes._search_bar
    bar._entry.setFocus(); bar._entry.setText('a'); bar._update_suggestions('a')
    comp = bar._completer; comp.setCompletionPrefix('a'); comp.complete(); pe()
    popup = comp.popup()
    if popup is not None:
        base = popup.palette().base().color()
        lum = round(0.2126*base.redF()+0.7152*base.greenF()+0.0722*base.blueF(), 2)
        print('completer popup Base =', base.name(), 'luminance', lum, flush=True)
    ok = w.grab().save({out!r}); print('saved' if ok else 'FAIL', {out!r}, flush=True)

sys.stdout.flush()
os._exit(0)
"""

jobs = [
    ("toolbar", "dark",  os.path.join(OUT, "proof_nesting_toolbar.png")),
    ("toolbar", "light", os.path.join(OUT, "proof_nesting_toolbar_light.png")),
    ("persist", "dark",  os.path.join(OUT, "proof_nesting_subtabs.png")),
    ("completer", "light", os.path.join(OUT, "proof_light_completer_popup.png")),
]

for mode, theme, out in jobs:
    print(f"\n=== {mode} / {theme} ===")
    code = CHILD.format(repo=repo, theme=theme, mode=mode, out=out)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    print(r.stdout.strip())
    if r.returncode != 0:
        print("CHILD FAILED rc=", r.returncode)
        print(r.stderr.strip()[-1500:])

print("\nDone.")
