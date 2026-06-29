"""
scripts/verify_manual_nfp.py — headless verification of NFP-based manual placement.

Asserts that the manual collision/snap path (now engine-NFP based) is consistent
with the auto-nest engine:
  • every engine-placed piece's own x_offset is accepted by manual _can_place
    (engine layout is collision-valid under the manual checker);
  • picking up a placed piece and re-snapping returns it to its EXACT x
    (no phantom gap) — the headline bug — for straight AND bevelled pieces;
  • flush snap beside a neighbour respects kerf exactly (gap == eff_kerf, no
    overlap), and snaps are byte-consistent with engine placement;
  • a degenerate/zero-height piece does not crash.

Run: QT_QPA_PLATFORM=offscreen PYTHONPATH=. python scripts/verify_manual_nfp.py
"""
from __future__ import annotations
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from nestify.models import AppState, Corte
from nestify.context_sync import ensure_material_contexts

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("PASS" if cond else "FAIL"), name, "-", detail)


def mk_corte(desc, largo, qty, b1deg=0.0, b2deg=0.0, d1="ext", d2="ext"):
    c = Corte(descripcion=desc, largo=largo, cantidad=qty)
    if b1deg and hasattr(c, "inglete1"):
        c.inglete1 = True
        c.inglete1_deg = b1deg
        if hasattr(c, "inglete1_dir"):
            c.inglete1_dir = d1
    if b2deg and hasattr(c, "inglete2"):
        c.inglete2 = True
        c.inglete2_deg = b2deg
        if hasattr(c, "inglete2_dir"):
            c.inglete2_dir = d2
    return c


def build_tab(cortes, kerf=3.0, margin=0.0, sh=100.0, common=False):
    app = QApplication.instance() or QApplication([])
    from nestify.ui_qt.tab_nesting import TabNesting
    state = AppState()
    state.longitud_barra = 6000.0
    state.perdida_corte = kerf
    state.margen_tubo = margin
    state.cortes = list(cortes)
    state.nesting_height_override = sh
    ensure_material_contexts(state)
    tab = TabNesting(state)
    tab.load_state(state)
    tab.refresh_from_cuts()
    tab._height_override = sh
    tab._mode_switch.setChecked(True)   # 2D bevel mode
    if common:
        tab._cb_common.setChecked(True)
    tab.ui.tb_bar_len.setText("6000")
    # Ensure at least one empty bar exists (manual placement needs a bar).
    if not tab._bars:
        tab._bars = [[]]
        tab._bar_lengths = [6000.0]
        tab._bar_stock_ids = [None]
    return app, tab


def place_via_simple_nest(tab):
    """Synchronous 1D packer → fills tab._bars without the threaded worker."""
    tab._mode_switch.setChecked(False)
    tab._run_simple_nest()
    tab._mode_switch.setChecked(True)


def test_engine_layout_consistency():
    cortes = [mk_corte("B45", 1200.0, 4, b1deg=45.0, b2deg=45.0),
              mk_corte("Straight", 800.0, 4)]
    app, tab = build_tab(cortes)
    # Build a real engine layout (advanced, synchronous greedy pass) directly.
    from nestify.nesting_engine import (
        NestingParams, build_nesting_piece, _nest_advanced_greedy_pass)
    sh = tab._section_height_mm()
    _, _, eff_kerf, _, _, common = tab._placement_params()
    units = []
    for i, c in enumerate(cortes):
        np = build_nesting_piece(c, i, sh, "#888888", eff_kerf)
        for _ in range(c.cantidad):
            units.append(np)
    params = NestingParams(bar_length=6000.0, profile_height=sh, kerf=eff_kerf,
                           margin=0.0, common_cut=common, priority="length")
    res = _nest_advanced_greedy_pass(units, params)
    tab._apply_nest_result(res, 6000.0)
    total = sum(len(b) for b in tab._bars)
    check("engine_layout_has_pieces", total > 0, f"placed={total}")

    disagree = []
    for bi, bar in enumerate(tab._bars):
        for pp in bar:
            if not tab._can_place(pp.corte, bi, pp.x_offset, pp.flipped_h,
                                  pp.flipped_v, exclude=pp):
                disagree.append((bi, round(pp.x_offset, 3), pp.corte.descripcion))
    check("manual_accepts_engine_positions", not disagree,
          f"disagree={disagree[:6]}")

    # Re-place exactness via the REAL flow: pick each piece up (sets
    # _moving_original, removes it from the bar) and drop it with the cursor on
    # its old spot; _find_best_snap must return its identical x.
    from PySide6.QtCore import QPointF
    if any(tab._bars):
        bi = max(range(len(tab._bars)), key=lambda i: len(tab._bars[i]))
        worst = 0.0
        for pp in list(tab._bars[bi]):
            tab._pick_up_placed(pp)   # removes pp, sets _moving_original=pp
            bar_y = bi * (tab._section_height_mm() + 500) + tab._section_height_mm() / 2
            snap = tab._find_best_snap(QPointF(pp.x_offset, bar_y),
                                       pp.corte, pp.flipped_h, pp.flipped_v,
                                       max_dx=float("inf"))
            tab._restore_moving_piece()
            tab._moving_original = None
            tab._floating = False
            if snap is None:
                worst = 9e9
                break
            worst = max(worst, abs(snap[1] - pp.x_offset))
        check("replace_same_spot_exact", worst < 0.01, f"worst_gap={worst:.5f}mm")


def test_flush_kerf_exact():
    """Two straight pieces placed flush: real-edge gap must equal eff_kerf."""
    app, tab = build_tab([mk_corte("S", 1000.0, 2)], kerf=4.0)
    _, _, eff_kerf, _, _, _ = tab._placement_params()
    # Place first at its bar-start snap, second flush beside it.
    s1 = tab._rendered_snaps(0, tab._pieces[0].corte, False, False)
    check("snaps_nonempty_empty_bar", bool(s1), f"snaps={ [round(x,2) for x in s1][:4] }")
    x0 = min(s1)
    poly = tab._compute_poly_local(tab._pieces[0].corte, False, False)
    from nestify.ui_qt.tab_nesting import PlacedPiece
    tab._bars[0].append(PlacedPiece(corte=tab._pieces[0].corte, bar_index=0,
                                    x_offset=x0, color="#888", poly_local=poly))
    tab._viable_cache.clear()
    s2 = tab._rendered_snaps(0, tab._pieces[0].corte, False, False)
    flush = [x for x in s2 if x > x0 + 1]
    check("flush_snap_exists", bool(flush), f"snaps={[round(x,2) for x in s2][:6]}")
    if flush:
        x1 = min(flush)
        # real right edge of piece 0 = x0 + L ; real left edge of piece 1 = x1.
        L = tab._pieces[0].corte.largo
        gap = x1 - (x0 + L)
        check("flush_gap_equals_kerf", abs(gap - eff_kerf) < 0.05,
              f"gap={gap:.4f} eff_kerf={eff_kerf:.4f}")


def test_degenerate_no_crash():
    app, tab = build_tab([mk_corte("Z", 500.0, 1)], sh=0.0)
    try:
        ok = tab._can_place(tab._pieces[0].corte, 0, 10.0, False, False)
        snaps = tab._rendered_snaps(0, tab._pieces[0].corte, False, False)
        check("degenerate_no_crash", True, f"can_place={ok} nsnaps={len(snaps)}")
    except Exception as exc:
        check("degenerate_no_crash", False, f"raised {exc!r}")


def main():
    test_engine_layout_consistency()
    test_flush_kerf_exact()
    test_degenerate_no_crash()
    failed = [r for r in RESULTS if not r[1]]
    print("\n%d/%d checks passed" % (len(RESULTS) - len(failed), len(RESULTS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
