"""Visual proof: auto-nest bevelled pieces, then pick up the last one and drop it
back on its spot — screenshot before/after to show no phantom gap appears."""
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF

from nestify.models import AppState, Corte
from nestify.context_sync import ensure_material_contexts
import nestify.ui_qt.theme_qt as _th


def mkc(d, l, q, b1=0.0, b2=0.0):
    c = Corte(descripcion=d, largo=l, cantidad=q)
    if b1:
        c.inglete1 = True; c.inglete1_deg = b1
    if b2:
        c.inglete2 = True; c.inglete2_deg = b2
    return c


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/nestify_shots"
    os.makedirs(outdir, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    from nestify.ui_qt.tab_nesting import TabNesting
    from nestify.nesting_engine import (
        NestingParams, build_nesting_piece, _nest_advanced_greedy_pass)

    for theme in ("dark", "light"):
        _th.apply_theme(theme)
        st = AppState()
        st.longitud_barra = 6000.0
        st.perdida_corte = 3.0
        st.cortes = [mkc("B45", 1300.0, 4, 45.0, 45.0)]
        st.nesting_height_override = 120.0
        ensure_material_contexts(st)
        tab = TabNesting(st)
        tab.load_state(st)
        tab.refresh_from_cuts()
        tab._height_override = 120.0
        tab._mode_switch.setChecked(True)
        tab.resize(1200, 360)

        sh = tab._section_height_mm()
        _, _, ek, _, _, common = tab._placement_params()
        npc = build_nesting_piece(st.cortes[0], 0, sh, "#4E79A7", ek)
        params = NestingParams(bar_length=6000.0, profile_height=sh, kerf=ek,
                               margin=0.0, common_cut=common, priority="length")
        res = _nest_advanced_greedy_pass([npc] * 4, params)
        tab._apply_nest_result(res, 6000.0)
        tab._view.fit_scene()
        app.processEvents()
        tab.grab().save(os.path.join(outdir, f"replace_before_{theme}.png"))

        # Pick up the last piece and drop it back on its exact spot.
        bi = max(range(len(tab._bars)), key=lambda i: len(tab._bars[i]))
        pp = tab._bars[bi][-1]
        orig_x = pp.x_offset
        tab._pick_up_placed(pp)
        bar_y = bi * (sh + 500) + sh / 2.0
        snap = tab._find_best_snap(QPointF(orig_x, bar_y), pp.corte,
                                   pp.flipped_h, pp.flipped_v, max_dx=float("inf"))
        # Place it where the snap says (the real drop path).
        if snap is not None:
            from nestify.ui_qt.tab_nesting import PlacedPiece
            poly = tab._compute_poly_local(pp.corte, pp.flipped_h, pp.flipped_v)
            tab._bars[snap[0]].append(PlacedPiece(
                corte=pp.corte, bar_index=snap[0], x_offset=snap[1],
                flipped_h=pp.flipped_h, flipped_v=pp.flipped_v,
                color=pp.color, poly_local=poly))
        tab._moving_original = None
        tab._floating = False
        tab._rebuild_scene()
        app.processEvents()
        tab.grab().save(os.path.join(outdir, f"replace_after_{theme}.png"))
        drift = abs(snap[1] - orig_x) if snap else 9e9
        print(f"{theme}: orig_x={orig_x:.4f} snap={snap[1] if snap else None} "
              f"drift={drift:.6f}mm")


if __name__ == "__main__":
    main()
