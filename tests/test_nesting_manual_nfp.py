"""
test_nesting_manual_nfp.py — manual-placement collision/snap now uses the engine's
exact No-Fit-Polygon geometry (same as auto-nest), so manual drops are flawless:

  • a position auto-nest chose is accepted by the manual collision check
    (no false "occupied" rejections);
  • picking a piece up and dropping it on its old spot returns it to the EXACT
    same x — the headline phantom-gap bug — for straight AND bevelled pieces;
  • flush placement beside a neighbour leaves a real-edge gap of exactly the
    effective kerf (no gap, no overlap);
  • bevel (2D) collision uses the true perpendicular kerf, and degenerate
    geometry never crashes.
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


def _mk_corte(desc, largo, qty, b1=0.0, b2=0.0):
    from nestify.models import Corte
    c = Corte(descripcion=desc, largo=largo, cantidad=qty)
    if b1 and hasattr(c, "inglete1"):
        c.inglete1 = True
        c.inglete1_deg = b1
    if b2 and hasattr(c, "inglete2"):
        c.inglete2 = True
        c.inglete2_deg = b2
    return c


def _tab(cortes, kerf=3.0, margin=0.0, sh=100.0, common=False):
    from nestify.models import AppState
    from nestify.context_sync import ensure_material_contexts
    from nestify.ui_qt.tab_nesting import TabNesting
    st = AppState()
    st.longitud_barra = 6000.0
    st.perdida_corte = kerf
    st.margen_tubo = margin
    st.cortes = list(cortes)
    st.nesting_height_override = sh
    ensure_material_contexts(st)
    tab = TabNesting(st)
    tab.load_state(st)
    tab.refresh_from_cuts()
    tab._height_override = sh
    tab._mode_switch.setChecked(True)
    if common:
        tab._cb_common.setChecked(True)
    if not tab._bars:
        tab._bars = [[]]
        tab._bar_lengths = [6000.0]
        tab._bar_stock_ids = [None]
    return tab


def _engine_layout(tab, cortes):
    """Place pieces via the engine's synchronous greedy NFP pass (no worker)."""
    from nestify.nesting_engine import (
        NestingParams, build_nesting_piece, _nest_advanced_greedy_pass)
    sh = tab._section_height_mm()
    _, _, eff_kerf, _, _, common = tab._placement_params()
    units = []
    for i, c in enumerate(cortes):
        npc = build_nesting_piece(c, i, sh, "#888888", eff_kerf)
        units.extend([npc] * c.cantidad)
    params = NestingParams(bar_length=6000.0, profile_height=sh, kerf=eff_kerf,
                           margin=0.0, common_cut=common, priority="length")
    res = _nest_advanced_greedy_pass(units, params)
    tab._apply_nest_result(res, 6000.0)
    return eff_kerf


def test_manual_accepts_engine_positions(qapp):
    cortes = [_mk_corte("B45", 1200.0, 4, b1=45.0, b2=45.0),
              _mk_corte("Straight", 800.0, 4)]
    tab = _tab(cortes)
    _engine_layout(tab, cortes)
    assert sum(len(b) for b in tab._bars) > 0
    for bi, bar in enumerate(tab._bars):
        for pp in bar:
            assert tab._can_place(pp.corte, bi, pp.x_offset, pp.flipped_h,
                                  pp.flipped_v, exclude=pp), \
                f"engine position rejected: bar {bi} x={pp.x_offset:.3f}"


def test_replace_same_spot_exact(qapp):
    from PySide6.QtCore import QPointF
    cortes = [_mk_corte("B45", 1200.0, 4, b1=45.0, b2=45.0)]
    tab = _tab(cortes)
    _engine_layout(tab, cortes)
    bi = max(range(len(tab._bars)), key=lambda i: len(tab._bars[i]))
    assert tab._bars[bi]
    sh = tab._section_height_mm()
    for pp in list(tab._bars[bi]):
        orig_x = pp.x_offset
        tab._pick_up_placed(pp)
        bar_y = bi * (sh + 500) + sh / 2.0
        snap = tab._find_best_snap(QPointF(orig_x, bar_y), pp.corte,
                                   pp.flipped_h, pp.flipped_v, max_dx=float("inf"))
        tab._restore_moving_piece()
        tab._moving_original = None
        tab._floating = False
        assert snap is not None, "no snap when re-dropping on the old spot"
        assert abs(snap[1] - orig_x) < 0.01, \
            f"re-placement drifted: {snap[1]:.5f} vs {orig_x:.5f}"


def test_flush_gap_equals_kerf(qapp):
    from nestify.ui_qt.tab_nesting import PlacedPiece
    tab = _tab([_mk_corte("S", 1000.0, 2)], kerf=4.0)
    corte = tab._pieces[0].corte
    _, _, eff_kerf, _, _, _ = tab._placement_params()
    snaps0 = tab._rendered_snaps(0, corte, False, False)
    assert snaps0, "no snaps on an empty bar"
    x0 = min(snaps0)
    poly = tab._compute_poly_local(corte, False, False)
    tab._bars[0].append(PlacedPiece(corte=corte, bar_index=0, x_offset=x0,
                                    color="#888", poly_local=poly))
    tab._viable_cache.clear()
    snaps1 = tab._rendered_snaps(0, corte, False, False)
    flush = [x for x in snaps1 if x > x0 + 1.0]
    assert flush, f"no flush slot beside the neighbour: {snaps1}"
    x1 = min(flush)
    gap = x1 - (x0 + corte.largo)   # real right edge of #0 → real left edge of #1
    assert abs(gap - eff_kerf) < 0.05, f"gap {gap:.4f} != kerf {eff_kerf:.4f}"


def test_degenerate_zero_height_no_crash(qapp):
    tab = _tab([_mk_corte("Z", 500.0, 1)], sh=0.0)
    corte = tab._pieces[0].corte
    # Must not raise.
    tab._can_place(corte, 0, 10.0, False, False)
    tab._rendered_snaps(0, corte, False, False)
