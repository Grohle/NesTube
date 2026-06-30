"""
test_stock_bar_picker.py — §16 stock-bar picker material scoping.

The "Add bar" picker must show ONLY the material being nested when one is already
selected; when none is selected, the chosen bar defines the material for the
whole app (context + shared state, with a cost/weight prefill).
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def stock(monkeypatch):
    import nestify.stock_db as sdb
    from nestify.stock_db import StockBar, StockDB
    db = StockDB(bars=[
        StockBar(id="000001", profile_name="U60x60x2", material_desc="Acero",
                 length=6000, quantity=8, quality="S355J2"),
        StockBar(id="000002", profile_name="Tubo40", material_desc="Aluminio",
                 length=5500, quantity=5, quality="6061-T6"),
        StockBar(id="000003", profile_name="U60x60x2", material_desc="Acero",
                 length=6000, quantity=1, quality="S355J2", is_retal=True,
                 retal_length=2150),
    ])
    monkeypatch.setattr(sdb, "_db", db)
    return db


def test_picker_locked_to_selected_material(qapp, stock):
    from nestify.ui_qt.dialogs.stock_bar_picker_dialog import StockBarPickerDialog
    dlg = StockBarPickerDialog(profile_name="U60x60x2", material="Acero",
                               quality="S355J2")
    assert dlg._locked is True
    # Only the two steel bars (full + remnant) match.
    assert dlg._table.rowCount() == 2
    for r in range(dlg._table.rowCount()):
        assert dlg._table.item(r, dlg._COL_MATERIAL).text() == "Acero"


def test_picker_unlocked_shows_all(qapp, stock):
    from nestify.ui_qt.dialogs.stock_bar_picker_dialog import StockBarPickerDialog
    dlg = StockBarPickerDialog()
    assert dlg._locked is False
    assert dlg._table.rowCount() == 3


def test_picker_material_only_filter(qapp, stock):
    from nestify.ui_qt.dialogs.stock_bar_picker_dialog import StockBarPickerDialog
    dlg = StockBarPickerDialog(material="Aluminio")
    assert dlg._table.rowCount() == 1
    assert dlg._table.item(0, dlg._COL_MATERIAL).text() == "Aluminio"


def test_adopt_material_sets_app_wide(qapp, stock, monkeypatch):
    from PySide6.QtWidgets import QDialog
    from nestify.models import AppState, Corte
    from nestify.context_sync import ensure_material_contexts
    from nestify.ui_qt.tab_nesting import TabNesting

    st = AppState()
    st.longitud_barra = 6000.0
    st.cortes = [Corte(descripcion="A", largo=1000.0, cantidad=2)]
    fired = {"n": 0}
    tab = TabNesting(st, on_state_change=lambda: fired.__setitem__("n", fired["n"] + 1))
    ensure_material_contexts(st)
    ctx = st.material_contexts[st.active_material_index]
    ctx.use_stock = True
    ctx.cortes = st.cortes
    assert not ctx.material  # nothing selected yet

    # Auto-accept the picker, returning the aluminium bar.
    import nestify.ui_qt.dialogs.stock_bar_picker_dialog as picker_mod
    alu = stock.bars[1]

    class FakeDlg:
        DialogCode = QDialog.DialogCode

        def __init__(self, *a, **kw):
            self.result_bar = alu

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(picker_mod, "StockBarPickerDialog", FakeDlg)
    tab._add_bar()

    # Material adopted on the context and the shared state.
    assert ctx.material == "Aluminio"
    assert ctx.profile_name == "Tubo40"
    assert ctx.quality == "6061-T6"
    assert st.descripcion == "Aluminio"
    assert st.calidad == "6061-T6"
    assert tab._subtabs.tab_name(0) == "Tubo40 · Aluminio"
    assert fired["n"] >= 1
    # The bar was still added with the bar's real length and stock id.
    assert tab._bar_lengths == [5500]
    assert tab._bar_stock_ids == ["000002"]
