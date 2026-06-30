"""
test_nesting_reorder.py — regression tests for §3.6 bar reordering.

Reordering bars in the bars panel is purely visual: it must NOT change a bar's
side/orientation, must NOT let bars stack/merge, and must NOT modify any nesting
data (piece x_offsets, flips, contents, bar lengths, stock links). Only each
piece's bar_index is re-stamped to match its new slot.
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


def _three_bar_tab():
    from nestify.models import AppState, Corte
    from nestify.ui_qt.tab_nesting import TabNesting, PlacedPiece

    st = AppState()
    st.longitud_barra = 6000.0
    st.perdida_corte = 3.0
    st.margen_tubo = 0.0
    st.cortes = [Corte(descripcion="A", largo=2000.0, cantidad=1),
                 Corte(descripcion="B", largo=1500.0, cantidad=1),
                 Corte(descripcion="C", largo=1000.0, cantidad=1)]
    tab = TabNesting(st)
    pa, pb, pc = tab._pieces

    def mk(pi, x, fv):
        return PlacedPiece(corte=pi.corte, bar_index=0, x_offset=x, flipped_h=False,
                           flipped_v=fv, color=pi.color,
                           poly_local=tab._compute_poly_local(pi.corte, False, fv))

    tab._bars = [[mk(pa, 100, False)], [mk(pb, 200, True)], [mk(pc, 300, False)]]
    for i, bar in enumerate(tab._bars):
        for pp in bar:
            pp.bar_index = i
    tab._bar_lengths = [6000.0, 5000.0, 4000.0]
    tab._bar_stock_ids = ["S1", "S2", "S3"]
    pa.placed_qty = pb.placed_qty = pc.placed_qty = 1
    return tab


def _order(tab):
    return [bar[0].corte.descripcion for bar in tab._bars]


def test_move_bar_down_reorders_visually(qapp):
    tab = _three_bar_tab()
    tab._move_bar(0, +1)            # A down → B, A, C
    assert _order(tab) == ["B", "A", "C"]
    tab._move_bar(2, -1)           # C up → B, C, A
    assert _order(tab) == ["B", "C", "A"]


def test_reorder_preserves_all_piece_and_bar_data(qapp):
    tab = _three_bar_tab()
    tab._move_bar(0, +1)            # A down → B, A, C

    # Piece A moved with its own x_offset, flip, length and stock id intact.
    a = next(pp for bar in tab._bars for pp in bar if pp.corte.descripcion == "A")
    b = next(pp for bar in tab._bars for pp in bar if pp.corte.descripcion == "B")
    assert round(a.x_offset) == 100 and a.flipped_v is False
    assert round(b.x_offset) == 200 and b.flipped_v is True
    assert tab._bar_lengths[a.bar_index] == 6000.0
    assert tab._bar_stock_ids[a.bar_index] == "S1"
    assert tab._bar_lengths[b.bar_index] == 5000.0
    assert tab._bar_stock_ids[b.bar_index] == "S2"

    # bar_index is re-stamped to match the new slot for every piece.
    assert all(pp.bar_index == i for i, bar in enumerate(tab._bars) for pp in bar)


def test_reorder_never_stacks_bars(qapp):
    tab = _three_bar_tab()
    tab._move_bar(0, +1)
    tab._move_bar(1, +1)
    # Still three independent bars, one piece each — nothing merged.
    assert len(tab._bars) == 3
    assert all(len(bar) == 1 for bar in tab._bars)


def test_move_at_ends_is_noop(qapp):
    tab = _three_bar_tab()
    before = _order(tab)
    tab._move_bar(0, -1)           # top bar up → no-op
    tab._move_bar(2, +1)          # bottom bar down → no-op
    assert _order(tab) == before


def test_reorder_is_undoable(qapp):
    tab = _three_bar_tab()
    tab._move_bar(0, +1)
    assert _order(tab) == ["B", "A", "C"]
    tab._undo()
    assert _order(tab) == ["A", "B", "C"]


def test_filter_and_expand_follow_the_bar(qapp):
    tab = _three_bar_tab()
    tab._filtered_bar = 0          # bar holding A is filtered
    tab._expanded_bars = {0}
    tab._move_bar(0, +1)           # A now at slot 1
    a_slot = next(i for i, bar in enumerate(tab._bars)
                  if bar[0].corte.descripcion == "A")
    assert tab._filtered_bar == a_slot
    assert a_slot in tab._expanded_bars
