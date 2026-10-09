"""
tests/test_web_dialogs.py — engine dialogs drawn by the HTML interface.

While a bridge call runs, the material search, cutting-face, profile-save and
export-selection dialogs do not open as Qt windows: the call returns ``needs``
(what the page must draw) and, repeated with ``_answers``, the dialog is
accepted with that answer (nestube/ui_web/dialogs.py).
"""
import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


class _Cap:
    def __init__(self, answers=None):
        self.answers = dict(answers or {})
        self.needs = None

    def ask(self, needs):
        if self.needs is None:
            self.needs = needs


def _run(dialog, cap):
    from nestube.ui_web.dialogs import web_dialogs
    with web_dialogs(cap):
        return dialog.exec()


def test_material_search_asks_then_accepts_the_answer(qapp):
    from nestube.ui_qt.dialogs.stock_material_search_dialog import StockMaterialSearchDialog
    dlg = StockMaterialSearchDialog(None, initial_query="IPE")
    cap = _Cap()
    assert _run(dlg, cap) == 0
    assert cap.needs["dialog"] == "material" and cap.needs["query"] == "IPE"
    assert dlg.result_selection is None

    cap = _Cap({"material": {"source": "fictitious", "profile_name": "",
                             "material": "Aluminio", "quality": "6063-T5"}})
    assert _run(dlg, cap) == 1 and cap.needs is None
    sel = dlg.result_selection
    assert (sel.source, sel.material, sel.quality) == ("fictitious", "Aluminio", "6063-T5")


def test_material_options_lists_the_same_rows_as_the_dialog(qapp):
    from nestube.ui_web.dialogs import material_options
    res = material_options("fictitious", "")
    assert res["mode"] == "fictitious"
    assert all(r["source"] == "fictitious" and r["material"] for r in res["rows"])


def test_cutting_face_dialog(qapp):
    from nestube.ui_qt.dialogs.profile_height_dialog import ProfileHeightDialog
    dlg = ProfileHeightDialog([("200 mm (alma)", 200.0), ("100 mm (ala)", 100.0)])
    cap = _Cap()
    assert _run(dlg, cap) == 0
    assert cap.needs == {"dialog": "height", "heights": [["200 mm (alma)", 200.0], ["100 mm (ala)", 100.0]],
                         "chosen": 200.0}
    assert _run(dlg, _Cap({"height": {"value": 100}})) == 1
    assert dlg.chosen_height() == 100.0


def test_profile_save_dialog_confirms_with_the_answer(qapp):
    from nestube.ui_qt.dialogs.profile_save_dialog import ProfileSaveDialog
    got = []
    dlg = ProfileSaveDialog(None, fields=["h (mm)", "b (mm)"], on_confirm=got.append)
    cap = _Cap()
    assert _run(dlg, cap) == 0 and not got
    assert cap.needs["dialog"] == "profile_save"
    assert cap.needs["fields"] == "h (mm), b (mm)"
    assert any(label for label, _sw in cap.needs["materials"])

    # A blank name is refused, as in the Qt dialog.
    assert _run(dlg, _Cap({"profile_save": {"name": "  "}})) == 0 and not got

    ans = {"name": "U 50x40 test", "quality": "S235", "notes": "web", "fields": "h (mm), t (mm)",
           "material": cap.needs["materials"][1][0]}
    assert _run(dlg, _Cap({"profile_save": ans})) == 1
    assert got and got[0]["name"] == "U 50x40 test"
    assert got[0]["fields"] == ["h (mm)", "t (mm)"] and got[0]["quality"] == "S235"


def test_nesting_selector_dialog(qapp):
    from nestube.models import AppState, Corte
    from nestube.context_sync import ensure_material_contexts
    from nestube.ui_qt.dialogs.nesting_selector_dialog import NestingSelectorDialog
    st = AppState()
    st.cortes = [Corte("A", 1000, 2)]
    ensure_material_contexts(st)
    bars = [[object(), object()]]
    dlg = NestingSelectorDialog(st, 0, bars, [6000.0], 80.0)
    cap = _Cap()
    assert _run(dlg, cap) == 0
    assert cap.needs["dialog"] == "nesting_selector"
    assert cap.needs["rows"][0][0] == 0 and cap.needs["rows"][0][2:] == [1, 2]
    assert _run(dlg, _Cap({"nesting_selector": {"indices": []}})) == 0
    assert _run(dlg, _Cap({"nesting_selector": {"indices": [0]}})) == 1
    assert dlg.selected_context_indices() == [0]


def test_bridge_returns_needs_and_applies_the_answer(qapp):
    """End to end: Nesting → Select material, answered from the page."""
    from nestube.ui_qt.app import NesTubeApp
    from nestube.ui_web.bridge import Bridge
    engine = NesTubeApp(headless=True)
    bridge = Bridge(engine)
    try:
        json.loads(bridge.call("data.set_view", json.dumps({"name": "nesting"})))
        res = json.loads(bridge.call("nest.action", json.dumps({"name": "sel_material"})))
        assert res["ok"] and res["needs"]["dialog"] == "material"

        answer = {"source": "fictitious", "profile_name": "", "material": "Aluminio", "quality": "6063-T5"}
        res = json.loads(bridge.call("nest.action", json.dumps(
            {"name": "sel_material", "_answers": {"material": answer}})))
        assert res["ok"] and "needs" not in res, res
        assert "Aluminio" in res["result"]["params"]["material"]
        # The unsaved-changes check must not wipe a material picked in Nesting
        # (it used to copy the Cuts tab's empty material search over it).
        engine._is_dirty()
        ctx = engine._state.material_contexts[engine._state.active_material_index]
        assert (ctx.material, ctx.quality) == ("Aluminio", "6063-T5")

        # The dialogs are only swapped during a call.
        from nestube.ui_qt.dialogs.stock_material_search_dialog import StockMaterialSearchDialog
        assert "exec" not in StockMaterialSearchDialog.__dict__
    finally:
        engine._is_dirty = lambda: False
        engine.deleteLater()
