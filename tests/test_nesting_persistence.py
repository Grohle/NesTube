"""
test_nesting_persistence.py — regression tests for manual-placement persistence
across material sub-tab switches and the "Only Remaining" auto-nest mode (§16).

Manual placements live in TabNesting._bars and are only mirrored into
state.nesting_layout via sync_to_state(). Switching material sub-tabs must flush
that layout into the leaving context and restore the entering context's own
layout — otherwise placements made since the last save are silently lost.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# These tests need the real PySide6 widgets. Skip cleanly if Qt can't start
# (e.g. a headless box without the offscreen plugin) rather than failing.
pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _place(tab, pi, x, *, fv=False, bar_len=6000.0):
    """Replace the tab's bars with a single bar holding one placed piece."""
    from nestube.ui_qt.tab_nesting import PlacedPiece
    poly = tab._compute_poly_local(pi.corte, False, fv)
    tab._bars = [[PlacedPiece(corte=pi.corte, bar_index=0, x_offset=x,
                              flipped_h=False, flipped_v=fv,
                              color=pi.color, poly_local=poly)]]
    tab._bar_lengths = [bar_len]
    pi.placed_qty = 1


def _build_two_context_tab():
    from nestube.models import AppState, Corte, MaterialContext
    from nestube.context_sync import ensure_material_contexts
    from nestube.ui_qt.tab_nesting import TabNesting

    st = AppState()
    st.longitud_barra = 6000.0
    st.perdida_corte = 3.0
    st.margen_tubo = 0.0
    st.cortes = [Corte(descripcion="A", largo=2000.0, cantidad=3)]
    ensure_material_contexts(st)
    st.material_contexts[0].cortes = list(st.cortes)
    st.material_contexts.append(
        MaterialContext(name="Nesting 2",
                        cortes=[Corte(descripcion="Z", largo=1000.0, cantidad=1)])
    )
    return TabNesting(st), st


def test_manual_placement_survives_subtab_switch(qapp):
    """A manual placement in context 0 must still be there after switching to
    context 1 and back (the §16 persistence bug)."""
    tab, st = _build_two_context_tab()
    tab._subtabs.set_active(0)
    tab._on_subtab_change(0)

    pa = next(p for p in tab._pieces if p.corte.descripcion == "A")
    _place(tab, pa, 555.0, fv=True)

    # Switch away (no Ctrl+S) and back.
    tab._on_before_subtab(0, 1)
    tab._subtabs.set_active(1)
    tab._on_subtab_change(1)
    tab._on_before_subtab(1, 0)
    tab._subtabs.set_active(0)
    tab._on_subtab_change(0)

    placed = [pp for bar in tab._bars for pp in bar]
    assert len(placed) == 1
    assert placed[0].corte.descripcion == "A"
    assert round(placed[0].x_offset) == 555
    assert placed[0].flipped_v is True


def test_contexts_keep_independent_layouts(qapp):
    """Each material context restores its own layout/bar-lengths, not the other's."""
    tab, st = _build_two_context_tab()
    tab._subtabs.set_active(0)
    tab._on_subtab_change(0)

    pa = next(p for p in tab._pieces if p.corte.descripcion == "A")
    _place(tab, pa, 555.0, bar_len=6000.0)

    # Switch to context 1: should show no placed pieces from context 0.
    tab._on_before_subtab(0, 1)
    tab._subtabs.set_active(1)
    tab._on_subtab_change(1)
    assert not any(tab._bars)  # no pieces carried over

    pz = next(p for p in tab._pieces if p.corte.descripcion == "Z")
    _place(tab, pz, 10.0, bar_len=4000.0)

    # Back to context 0: original A placement + its bar length restored.
    tab._on_before_subtab(1, 0)
    tab._subtabs.set_active(0)
    tab._on_subtab_change(0)
    placed = [pp for bar in tab._bars for pp in bar]
    assert [pp.corte.descripcion for pp in placed] == ["A"]
    assert tab._bar_lengths == [6000.0]

    # Back to context 1: Z placement + its (different) bar length restored.
    tab._on_before_subtab(0, 1)
    tab._subtabs.set_active(1)
    tab._on_subtab_change(1)
    placed = [pp for bar in tab._bars for pp in bar]
    assert [pp.corte.descripcion for pp in placed] == ["Z"]
    assert tab._bar_lengths == [4000.0]


def test_only_remaining_preserves_manual_placement(qapp):
    """'Only Remaining' (simple 1D) keeps manual placements and nests the rest
    without duplicating or dropping pieces."""
    from nestube.models import AppState, Corte
    from nestube.ui_qt.tab_nesting import TabNesting

    st = AppState()
    st.longitud_barra = 6000.0
    st.perdida_corte = 3.0
    st.margen_tubo = 0.0
    st.cortes = [Corte(descripcion="A", largo=2000.0, cantidad=3),
                 Corte(descripcion="B", largo=1500.0, cantidad=2)]
    tab = TabNesting(st)
    tab._mode_switch.setChecked(False)
    tab._update_mode_controls()

    pa = next(p for p in tab._pieces if p.corte.descripcion == "A")
    _place(tab, pa, 1234.0, fv=True)

    tab._auto_mode_combo.setCurrentIndex(tab._auto_mode_combo.findData("remaining"))
    tab._run_simple_nest()

    total_a = sum(1 for bar in tab._bars for pp in bar if pp.corte.descripcion == "A")
    total_b = sum(1 for bar in tab._bars for pp in bar if pp.corte.descripcion == "B")
    assert total_a == 3
    assert total_b == 2
    # The original manual piece is still on bar 0 at its exact position.
    assert tab._bars[0][0].corte.descripcion == "A"
    assert round(tab._bars[0][0].x_offset) == 1234
    assert tab._bars[0][0].flipped_v is True
