"""
test_subtab_delete.py — deleting a material sub-tab must not corrupt the others (§27).

Two bugs are covered:
  • MaterialSubTabs.remove_tab kept _active pointing one tab too far right when a
    tab BEFORE the active one was removed → the wrong MaterialContext loaded
    (phantom pieces / wrong cuts shown).
  • Deleting a non-active sub-tab reloaded the active context and wiped a
    survivor's freshly-edited cuts.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_remove_tab_keeps_active_on_same_tab(qapp):
    from nestify.ui_qt.widgets.material_subtabs import MaterialSubTabs
    # Delete a tab BEFORE the active one → active must still point to the same tab.
    w = MaterialSubTabs()
    w.set_tabs(["A", "B", "C"], active=1)   # B active
    w.remove_tab(0)                          # delete A
    assert w._tabs == ["B", "C"]
    assert w.tab_name(w.active_index()) == "B"

    # Delete the last while active is last → clamp to new last.
    w2 = MaterialSubTabs()
    w2.set_tabs(["A", "B", "C"], active=2)
    w2.remove_tab(2)
    assert w2.tab_name(w2.active_index()) == "B"

    # Delete a tab AFTER the active one → active unchanged.
    w3 = MaterialSubTabs()
    w3.set_tabs(["A", "B", "C"], active=0)
    w3.remove_tab(2)
    assert w3.tab_name(w3.active_index()) == "A"


def test_delete_subtab_preserves_survivor_cuts(qapp):
    from nestify.models import AppState, Corte, MaterialContext
    from nestify.context_sync import (
        ensure_material_contexts, save_cuts_tab_to_context, load_context_to_state)
    from nestify.ui_qt.tab_cortes import TabCortes

    st = AppState()
    st.material_contexts = [MaterialContext(), MaterialContext(), MaterialContext()]
    ensure_material_contexts(st)
    tab = TabCortes(st)
    tab.load_state(st)
    tab._subtabs.set_tabs(["A", "B", "C"], active=0)
    save_cuts_tab_to_context(st, 0, [Corte(descripcion="a", largo=100.0, cantidad=1)])
    save_cuts_tab_to_context(st, 1, [Corte(descripcion="b", largo=200.0, cantidad=1)])
    save_cuts_tab_to_context(st, 2, [Corte(descripcion="c", largo=300.0, cantidad=1)])

    # Make B active and load it into the UI (as clicking the tab would).
    st.active_material_index = 1
    load_context_to_state(st, 1)
    tab._apply_context_to_ui()
    tab._subtabs.set_active(1)

    # Delete A (a non-active tab before the active one).
    tab._subtabs.remove_tab(0)

    def cuts(i):
        return [(c.descripcion, c.largo) for c in st.material_contexts[i].cortes]

    # B is now index 0 and active; C is index 1. Both keep their cuts.
    assert st.active_material_index == 0
    assert cuts(0) == [("b", 200.0)]
    assert cuts(1) == [("c", 300.0)]
