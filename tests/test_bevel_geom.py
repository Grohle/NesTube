"""
tests/test_bevel_geom.py — §21.3 bevel/miter collision geometry.

The manual-placement collision path (nestube/bevel_geom.py) and the rendered /
auto-nested polygon (nestube/nesting_engine.py) must describe the SAME contour
for every orientation. The historical bug: corte_to_bevel negated the miter
angles for flipped_v instead of mirroring the trapezoid, so a vertically
flipped beveled piece's collision shape spilled outside [0, L] and disagreed
with the engine. These tests pin the two geometries together.
"""
import pytest

from nestube.models import Corte
from nestube.nesting_engine import _build_base_polygon, _build_all_orientations
from nestube.bevel_geom import (
    BevelPiece, corte_to_bevel, vertices_local, min_x_extent, max_x_extent,
    min_x_after_anchor, contour_polygons_collide, snap_positions_after_pieces,
)

H = 50.0  # section height (miter depth along the bar axis)


def _make(largo, i1=False, i1d="up", i1deg=45.0, i2=False, i2d="up", i2deg=45.0):
    c = Corte()
    c.largo = largo
    c.cantidad = 1
    c.inglete1, c.inglete1_dir, c.inglete1_deg = i1, i1d, i1deg
    c.inglete2, c.inglete2_dir, c.inglete2_deg = i2, i2d, i2deg
    return c


def _norm(verts):
    """Normalize a vertex set to the origin and return it sorted (order-free)."""
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    mnx, mny = min(xs), min(ys)
    return sorted((round(x - mnx, 3), round(y - mny, 3)) for x, y in verts)


def _engine_contour(corte, fh, fv):
    base = _build_base_polygon(corte, H)
    poly = _build_all_orientations(base)[(fh, fv)]
    return _norm(list(poly.exterior.coords[:-1]))


def _ui_contour(corte, fh, fv):
    piece = corte_to_bevel(corte, fh, fv)
    return _norm(vertices_local(piece, H))


_CORTES = [
    _make(1000),                                            # no miter
    _make(1000, i1=True),                                   # left 45 up
    _make(1000, i2=True),                                   # right 45 up
    _make(1000, i1=True, i2=True),                          # symmetric 45 up
    _make(1000, i1=True, i1d="down", i2=True, i2d="down"),  # both down
    _make(1000, i1=True, i1deg=30, i2=True, i2deg=60),      # asymmetric angles
    _make(1000, i1=True, i1d="up", i2=True, i2d="down"),    # mixed directions
]


@pytest.mark.parametrize("fv", [False, True])
@pytest.mark.parametrize("fh", [False, True])
@pytest.mark.parametrize("corte", _CORTES, ids=lambda c: f"L{c.largo}_{c.inglete1_dir}{c.inglete1_deg if c.inglete1 else '-'}_{c.inglete2_dir}{c.inglete2_deg if c.inglete2 else '-'}")
def test_ui_collision_contour_matches_engine(corte, fh, fv):
    assert _ui_contour(corte, fh, fv) == _engine_contour(corte, fh, fv)


def test_flipped_v_symmetric_stays_within_bar_length():
    # The exact regression: 1000mm, 45°/45°, flipped vertically. The collision
    # contour must stay within [0, 1000] — the old code produced [-50, 1050].
    corte = _make(1000, i1=True, i2=True)
    piece = corte_to_bevel(corte, flipped_h=False, flipped_v=True)
    assert min_x_extent(piece, H) == pytest.approx(0.0)
    assert max_x_extent(piece, H) == pytest.approx(1000.0)


def test_vertical_flip_preserves_x_extent():
    # A vertical flip mirrors top<->bottom; it never changes the x-extent.
    corte = _make(800, i1=True, i1deg=40, i2=True, i2d="down", i2deg=20)
    base = corte_to_bevel(corte, flipped_h=False, flipped_v=False)
    flipped = corte_to_bevel(corte, flipped_h=False, flipped_v=True)
    assert min_x_extent(flipped, H) == pytest.approx(min_x_extent(base, H))
    assert max_x_extent(flipped, H) == pytest.approx(max_x_extent(base, H))


def test_base_orientation_unchanged():
    # The non-flipped trapezoid must be exactly the historical shape: full
    # length on the bottom, bevels inset the top corners.
    piece = BevelPiece(1000.0, 45.0, 45.0, flipped_v=False)
    bl, br, tr, tl = vertices_local(piece, H)
    assert bl == pytest.approx((0.0, 0.0))
    assert br == pytest.approx((1000.0, 0.0))
    assert tr == pytest.approx((1000.0 - H, H))
    assert tl == pytest.approx((H, H))


def test_flipped_v_insets_bottom_corners():
    # Vertical flip: full length now on top, bevels inset the bottom corners.
    piece = BevelPiece(1000.0, 45.0, 45.0, flipped_v=True)
    bl, br, tr, tl = vertices_local(piece, H)
    assert bl == pytest.approx((H, 0.0))
    assert br == pytest.approx((1000.0 - H, 0.0))
    assert tr == pytest.approx((1000.0, H))
    assert tl == pytest.approx((0.0, H))


# ── §21.3 kerf-contact tests (min_x_after_anchor correctness) ────────────────

def test_kerf_flipped_v_parallel_pieces():
    # Two identical flipped_v 45°/45° up/up pieces placed adjacent.
    # Before the fix: min_x_after_anchor gave 950 (old hard-coded formula),
    # so kerf was only enforced by the polygon-intersection fallback loop,
    # resulting in pieces accepted with ~0 mm kerf instead of 3/cos(45°).
    kerf = 3.0
    piece = BevelPiece(1000.0, 45.0, 45.0, flipped_v=True)
    # At y=H: piece_a TR=(1000, H), piece_b TL=(x_b, H).
    # Horizontal separation = kerf / cos(45°) = kerf * sqrt(2).
    dx_expected = kerf * (2 ** 0.5)  # kerf / cos(45°)
    x_b_min = min_x_after_anchor(0.0, piece, piece, H, kerf)
    assert x_b_min == pytest.approx(1000.0 + dx_expected, rel=1e-4)


def test_kerf_flipped_v_interlocking_pieces():
    # Interlocking: left piece alpha_R=+45 (up), right piece alpha_L=-45 (down),
    # both flipped_v=True.  The formula should still give the same result as
    # for non-flipped interlocking pieces.
    kerf = 3.0
    piece_a = BevelPiece(1000.0, 45.0, 45.0, flipped_v=True)
    piece_b = BevelPiece(1000.0, -45.0, -45.0, flipped_v=True)
    x_b = min_x_after_anchor(0.0, piece_a, piece_b, H, kerf)
    # Must be > 1000 (pieces don't overlap) and exactly enforce kerf.
    assert x_b > 1000.0
    assert not contour_polygons_collide(0.0, piece_a, x_b, piece_b, H, kerf)
    # One step before should be colliding (kerf not satisfied).
    assert contour_polygons_collide(0.0, piece_a, x_b - 0.1, piece_b, H, kerf)


def test_kerf_non_flipped_parallel_same_direction():
    # Two non-flipped 45°/45° pieces placed in the same direction (not
    # interlocking) — parallel check triggers.  Before the fix the formula
    # returned 950+dx instead of 1000+dx, so the kerf check in
    # contour_polygons_collide would accept placements with insufficient kerf.
    kerf = 3.0
    piece = BevelPiece(1000.0, 45.0, 45.0, flipped_v=False)
    dx_expected = kerf * (2 ** 0.5)  # kerf / cos(45°)
    x_b_min = min_x_after_anchor(0.0, piece, piece, H, kerf)
    assert x_b_min == pytest.approx(1000.0 + dx_expected, rel=1e-4)


# ── §21.3 bar-start snap tests ────────────────────────────────────────────────

def test_snap_bar_start_no_bevel():
    # Plain rectangular piece: bar-start snap = margin (0).
    corte = _make(1000)
    snaps = snap_positions_after_pieces([], corte, False, False, 3000, 0.0, 3.0, H, False)
    assert 0.0 in snaps


def test_snap_bar_start_down_miter_flipped_v():
    # A flipped_v down/down piece has min_x_extent < 0.
    # The bar-start snap must be -min_x_extent, NOT 0 (which would put part
    # of the piece past the bar edge and fail fits_on_bar).
    corte = _make(1000, i1=True, i1d="down", i2=True, i2d="down")
    piece = corte_to_bevel(corte, flipped_h=False, flipped_v=True)
    lo = -min_x_extent(piece, H)
    assert lo > 0.0, "down/down flipped_v piece must have min_x_extent < 0"
    snaps = snap_positions_after_pieces([], corte, False, True, 3000, 0.0, 3.0, H, True)
    # bar_start (lo) must be among the candidates
    assert any(abs(s - lo) < 0.1 for s in snaps), f"bar-start snap {lo} missing from {snaps}"
