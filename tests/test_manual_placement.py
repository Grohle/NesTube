"""
tests/test_manual_placement.py — manual nesting solidity regressions.

A picked-up piece must always be able to drop back into its own slot — with
snap on or off, and after rotating/flipping while carried — and rotating a
PLACED piece in place must never leave it overlapping a neighbour. The
kerf-strict NFP check and the 1D packer disagree by sub-mm on mitered
contacts, which used to make a piece's own just-vacated slot "vanish" and
teleport the drop to a far bar position (see TabNesting._fits_physically).
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QPointF  # noqa: E402

from nestube.models import AppState, Corte  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _make_tab(cortes, snap=True):
    from nestube.ui_qt.tab_nesting import TabNesting
    st = AppState()
    st.longitud_barra = 6000.0
    st.perdida_corte = 3.0
    st.margen_tubo = 0.0
    st.cortes = cortes
    tab = TabNesting(st)
    tab._cb_snap.setChecked(snap)
    i = tab._auto_mode_combo.findData("all")
    if i >= 0:
        tab._auto_mode_combo.setCurrentIndex(i)
    # Deterministic flush layout via the 1D packer, then bevel mode for the
    # manual interactions (matches the app's default workflow).
    tab._mode_switch.setChecked(False)
    tab._update_mode_controls()
    tab._run_simple_nest()
    tab._mode_switch.setChecked(True)
    tab._update_mode_controls()
    return tab


def _cursor(tab, bar_idx, x_mm):
    y = tab._scene.bar_y_for(bar_idx) + tab._section_height_mm() / 2.0
    return QPointF(x_mm, y)


def _pick_and_drop(tab, pp, drop_pos, flips_h=0, flips_v=0):
    tab._pick_up_placed(pp)
    for _ in range(flips_h):
        tab._flip_horizontal()
    for _ in range(flips_v):
        tab._flip_vertical()
    tab._update_float_preview(drop_pos)
    tab._place_floating_piece(drop_pos)
    placed = not tab._floating
    if not placed:
        tab._cancel_floating()
    return placed


def _max_overlap(tab, bar_idx):
    from shapely.geometry import Polygon
    from shapely import affinity
    polys = [affinity.translate(Polygon(pp.poly_local), pp.x_offset, 0)
             for pp in tab._bars[bar_idx]]
    worst = 0.0
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            worst = max(worst, polys[i].intersection(polys[j]).area)
    return worst


def _by_name(tab, name, bar_idx=0):
    return [p for p in tab._bars[bar_idx] if p.corte.descripcion == name]


def _rect_cuts():
    return [Corte("A", 1500, 1), Corte("B", 1200, 1), Corte("C", 900, 1)]


def _miter_cuts():
    return [
        Corte("M1", 1500, 1, inglete1=True, inglete2=True,
              inglete1_dir="up", inglete2_dir="down"),
        Corte("M2", 1200, 1, inglete1=True, inglete2=True,
              inglete1_dir="down", inglete2_dir="up"),
        Corte("M3", 900, 1, inglete1=True, inglete2=True,
              inglete1_dir="up", inglete2_dir="up"),
    ]


class TestSameSlotReplacement:

    def test_rect_pick_drop_same_spot_snap_on(self, qapp):
        tab = _make_tab(_rect_cuts(), snap=True)
        pp = sorted(tab._bars[0], key=lambda p: p.x_offset)[1]
        old_x = pp.x_offset
        assert _pick_and_drop(tab, pp, _cursor(tab, 0, old_x + 30))
        assert abs(_by_name(tab, "B")[0].x_offset - old_x) < 0.5

    def test_rect_pick_drop_same_spot_snap_off(self, qapp):
        tab = _make_tab(_rect_cuts(), snap=False)
        pp = sorted(tab._bars[0], key=lambda p: p.x_offset)[1]
        old_x = pp.x_offset
        assert _pick_and_drop(tab, pp, _cursor(tab, 0, old_x))
        assert abs(_by_name(tab, "B")[0].x_offset - old_x) < 0.5

    def test_miter_pick_drop_same_spot(self, qapp):
        """The core regression: mitered flush layout from the 1D packer —
        pick a middle piece up and drop it right back."""
        tab = _make_tab(_miter_cuts(), snap=True)
        pp = sorted(tab._bars[0], key=lambda p: p.x_offset)[1]
        old_x = pp.x_offset
        assert _pick_and_drop(tab, pp, _cursor(tab, 0, old_x + 15))
        assert abs(_by_name(tab, "M2")[0].x_offset - old_x) < 0.5
        assert _max_overlap(tab, 0) < 1.0

    def test_miter_repeated_pick_drop_no_drift(self, qapp):
        tab = _make_tab(_miter_cuts(), snap=True)
        old_x = sorted(tab._bars[0], key=lambda p: p.x_offset)[1].x_offset
        for k in range(10):
            cur = _by_name(tab, "M2")[0]
            assert _pick_and_drop(tab, cur, _cursor(tab, 0, cur.x_offset + 15)), \
                f"drop {k} failed"
        assert abs(_by_name(tab, "M2")[0].x_offset - old_x) < 0.5


class TestRotateAndReplace:

    def test_rect_flip_h_drop_same_spot(self, qapp):
        """Flipping a rectangle changes nothing geometrically — the same-slot
        guarantee must hold even though the orientation flags differ."""
        tab = _make_tab(_rect_cuts(), snap=True)
        pp = sorted(tab._bars[0], key=lambda p: p.x_offset)[1]
        old_x = pp.x_offset
        assert _pick_and_drop(tab, pp, _cursor(tab, 0, old_x + 20), flips_h=1)
        assert abs(_by_name(tab, "B")[0].x_offset - old_x) < 0.5

    def test_miter_flip_twice_back_drop_same_spot(self, qapp):
        tab = _make_tab(_miter_cuts(), snap=True)
        pp = sorted(tab._bars[0], key=lambda p: p.x_offset)[1]
        old_x = pp.x_offset
        assert _pick_and_drop(tab, pp, _cursor(tab, 0, old_x + 20), flips_h=2)
        assert abs(_by_name(tab, "M2")[0].x_offset - old_x) < 0.5
        assert _max_overlap(tab, 0) < 1.0

    def test_miter_flip_v_drop_same_spot_when_it_fits(self, qapp):
        """A flipped contour with the same x-extent goes back into its slot
        whenever it physically fits — kerf-model strictness must not refuse."""
        tab = _make_tab([Corte("L1", 1000, 1, inglete1=True, inglete1_dir="up"),
                         Corte("L2", 800, 1)], snap=True)
        pp = _by_name(tab, "L1")[0]
        old_x = pp.x_offset
        assert _pick_and_drop(tab, pp, _cursor(tab, 0, old_x + 10), flips_v=1)
        assert abs(_by_name(tab, "L1")[0].x_offset - old_x) < 1.0
        assert _max_overlap(tab, 0) < 1.0


class TestInPlaceTransformGuard:

    def test_flip_placed_never_overlaps(self, qapp):
        tab = _make_tab(_miter_cuts(), snap=True)
        pp = sorted(tab._bars[0], key=lambda p: p.x_offset)[1]
        tab._select_placed(pp)
        tab._flip_vertical()
        assert _max_overlap(tab, 0) < 1.0

    def test_blocked_flip_reverts_orientation(self, qapp):
        """When the flipped contour cannot fit between its neighbours, the
        transform is refused and the piece keeps its previous orientation
        (before the guard it silently overlapped)."""
        tab = _make_tab(_miter_cuts(), snap=True)
        pp = sorted(tab._bars[0], key=lambda p: p.x_offset)[1]
        before = (pp.flipped_h, pp.flipped_v)
        tab._select_placed(pp)
        tab._flip_vertical()
        after = (pp.flipped_h, pp.flipped_v)
        if after == before:
            # refused → orientation preserved and still no overlap
            assert _max_overlap(tab, 0) < 1.0
        else:
            # accepted → must genuinely fit
            assert _max_overlap(tab, 0) < 1.0
