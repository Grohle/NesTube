"""
tests/test_nesting_engine.py
Rigorous tests for the nesting engine.
Tests exact coordinates, kerf gaps, rotation invariance, and NFP collision.
"""
import math
import threading
import pytest
from shapely.geometry import Polygon, box

from nestify.nesting_engine import (
    STRATEGIES,
    NestingParams,
    NestingPiece,
    NestingResult,
    PlacedPiece,
    _build_base_polygon,
    _flip_h,
    _flip_v,
    _build_all_orientations,
    _offset_polygon,
    _compute_nfp,
    _compute_ifp,
    _compute_viable_space,
    _bottom_left_fill,
    build_nesting_piece,
    build_obstacle_for_bar,
    nest_simple,
    nest_advanced_timed,
)
from nestify.models import Corte


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_corte(largo, qty=1, inglete1=False, inglete1_deg=45.0, inglete1_dir="up",
                inglete2=False, inglete2_deg=45.0, inglete2_dir="up", descripcion="cut") -> Corte:
    c = Corte()
    c.largo = largo
    c.cantidad = qty
    c.descripcion = descripcion
    c.inglete1 = inglete1
    c.inglete1_deg = inglete1_deg
    c.inglete1_dir = inglete1_dir
    c.inglete2 = inglete2
    c.inglete2_deg = inglete2_deg
    c.inglete2_dir = inglete2_dir
    return c


def _params(bar_length=6000.0, profile_height=50.0, kerf=2.0, margin=5.0,
            common_cut=False, priority="length") -> NestingParams:
    return NestingParams(
        bar_length=bar_length, profile_height=profile_height,
        kerf=kerf, margin=margin, common_cut=common_cut, priority=priority,
    )


def _placed_on_bar(result: NestingResult, bar_idx: int = 0):
    return [(pp, pp.get_polygon()) for pp in result.placed if pp.bar_index == bar_idx]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. POLYGON BUILDER — exact geometry, rotation invariance
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolygonBuilder:

    def test_straight_piece_exact_rectangle(self):
        poly = _build_base_polygon(_make_corte(1000.0), 50.0)
        b = poly.bounds
        assert abs(b[0]) < 0.01
        assert abs(b[1]) < 0.01
        assert abs(b[2] - 1000.0) < 0.01
        assert abs(b[3] - 50.0) < 0.01
        assert abs(poly.area - 50000.0) < 1.0

    def test_left_bevel_45_area(self):
        H, L = 50.0, 500.0
        poly = _build_base_polygon(
            _make_corte(L, inglete1=True, inglete1_deg=45.0, inglete1_dir="up"), H)
        expected = H * (L + (L - H)) / 2  # trapezoid
        assert abs(poly.area - expected) < 10.0

    def test_right_bevel_30_area(self):
        H, L = 50.0, 600.0
        dx = H * math.tan(math.radians(30.0))
        poly = _build_base_polygon(
            _make_corte(L, inglete2=True, inglete2_deg=30.0, inglete2_dir="up"), H)
        expected = H * (L + (L - dx)) / 2
        assert abs(poly.area - expected) < 10.0

    def test_both_bevels_45(self):
        H, L = 50.0, 800.0
        poly = _build_base_polygon(
            _make_corte(L, inglete1=True, inglete1_deg=45.0, inglete1_dir="up",
                        inglete2=True, inglete2_deg=45.0, inglete2_dir="up"), H)
        expected = H * (L + (L - 2 * H)) / 2
        assert abs(poly.area - expected) < 10.0


class TestRotationInvariance:

    def test_flip_h_preserves_area(self):
        poly = _build_base_polygon(
            _make_corte(500.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up"), 50.0)
        assert abs(_flip_h(poly).area - poly.area) < 0.01

    def test_flip_v_preserves_area(self):
        poly = _build_base_polygon(
            _make_corte(500.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up"), 50.0)
        assert abs(_flip_v(poly).area - poly.area) < 0.01

    def test_flip_h_preserves_bbox(self):
        poly = _build_base_polygon(
            _make_corte(500.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up",
                        inglete2=True, inglete2_deg=30.0, inglete2_dir="down"), 60.0)
        flipped = _flip_h(poly)
        assert abs((poly.bounds[2] - poly.bounds[0]) - (flipped.bounds[2] - flipped.bounds[0])) < 0.01
        assert abs((poly.bounds[3] - poly.bounds[1]) - (flipped.bounds[3] - flipped.bounds[1])) < 0.01

    def test_flip_v_preserves_bbox(self):
        poly = _build_base_polygon(
            _make_corte(500.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up",
                        inglete2=True, inglete2_deg=30.0, inglete2_dir="down"), 60.0)
        flipped = _flip_v(poly)
        assert abs((poly.bounds[2] - poly.bounds[0]) - (flipped.bounds[2] - flipped.bounds[0])) < 0.01
        assert abs((poly.bounds[3] - poly.bounds[1]) - (flipped.bounds[3] - flipped.bounds[1])) < 0.01

    def test_all_four_orientations_identical_area_and_bbox(self):
        poly = _build_base_polygon(
            _make_corte(700.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up",
                        inglete2=True, inglete2_deg=30.0, inglete2_dir="down"), 50.0)
        orients = _build_all_orientations(poly)
        ref_area = poly.area
        ref_w = poly.bounds[2] - poly.bounds[0]
        ref_h = poly.bounds[3] - poly.bounds[1]
        for key, p in orients.items():
            assert abs(p.area - ref_area) < 0.1, f"Area differs for {key}: {p.area} vs {ref_area}"
            w = p.bounds[2] - p.bounds[0]
            h = p.bounds[3] - p.bounds[1]
            assert abs(w - ref_w) < 0.1, f"Width differs for {key}: {w} vs {ref_w}"
            assert abs(h - ref_h) < 0.1, f"Height differs for {key}: {h} vs {ref_h}"

    def test_placed_piece_same_area_all_orientations(self):
        corte = _make_corte(500.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up",
                            inglete2=True, inglete2_deg=30.0, inglete2_dir="down")
        piece = build_nesting_piece(corte, 0, 50.0, "#ff0000", kerf=2.0)
        areas = []
        for fh, fv in [(False, False), (True, False), (False, True), (True, True)]:
            pp = PlacedPiece(piece=piece, bar_index=0, x_offset=100.0,
                             flipped_h=fh, flipped_v=fv, color="#ff0000")
            areas.append(pp.get_polygon().area)
        for a in areas[1:]:
            assert abs(a - areas[0]) < 0.1, f"Areas differ: {areas}"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PyClipper OFFSET
# ═══════════════════════════════════════════════════════════════════════════════

class TestOffset:

    def test_offset_increases_area(self):
        poly = box(0, 0, 100, 50)
        inflated = _offset_polygon(poly, 2.0)
        assert inflated.area > poly.area

    def test_zero_offset_unchanged(self):
        poly = box(0, 0, 100, 50)
        same = _offset_polygon(poly, 0.0)
        assert abs(same.area - poly.area) < 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. NFP / IFP
# ═══════════════════════════════════════════════════════════════════════════════

class TestNFP:

    def test_nfp_two_rects(self):
        a = box(0, 0, 100, 50)
        b = box(0, 0, 80, 50)
        nfps = _compute_nfp(a, b)
        assert len(nfps) >= 1
        nfp_union = nfps[0] if len(nfps) == 1 else nfps[0].union(nfps[-1])
        assert nfp_union.area > 0

    def test_nfp_point_outside_means_no_collision(self):
        a = box(0, 0, 100, 50)
        b = box(0, 0, 50, 50)
        nfps = _compute_nfp(a, b)
        nfp = nfps[0] if nfps else Polygon()
        from shapely.geometry import Point
        test_point = Point(200, 0)
        assert not nfp.contains(test_point)


class TestIFP:

    def test_ifp_rect_in_rect(self):
        stock = box(0, 0, 6000, 50)
        piece = box(0, 0, 100, 50)
        ifp = _compute_ifp(stock, piece)
        assert not ifp.is_empty
        b = ifp.bounds
        assert b[2] - b[0] > 5000


class TestViableSpace:

    def test_viable_space_empty_bar(self):
        stock = box(5, 0, 5995, 50)
        piece = box(0, 0, 500, 50)
        viable = _compute_viable_space(stock, [], piece)
        assert not viable.is_empty

    def test_viable_space_shrinks_with_placed(self):
        stock = box(5, 0, 5995, 50)
        piece = box(0, 0, 500, 50)
        viable_empty = _compute_viable_space(stock, [], piece)
        from shapely.affinity import translate
        placed_v = [translate(box(0, 0, 500, 50), 5, 0)]
        viable_one = _compute_viable_space(stock, placed_v, piece)
        assert viable_one.area < viable_empty.area


class TestBLF:

    def test_blf_picks_leftmost(self):
        viable = box(10, 0, 5000, 50)
        pos = _bottom_left_fill(viable)
        assert pos is not None
        assert abs(pos[0] - 10.0) < 1.0

    def test_blf_empty_returns_none(self):
        pos = _bottom_left_fill(Polygon())
        assert pos is None


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SIMPLE NESTING — margin and kerf
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimple:

    def test_first_piece_at_margin(self):
        piece = build_nesting_piece(_make_corte(500.0), 0, 50.0, "#f00", 2.0)
        result = nest_simple([piece], _params(margin=10.0))
        assert abs(result.placed[0].x_offset - 10.0) < 0.01

    def test_kerf_gap(self):
        pieces = [build_nesting_piece(_make_corte(500.0), i, 50.0, "#f00", 3.0) for i in range(2)]
        result = nest_simple(pieces, _params(kerf=3.0, margin=5.0))
        assert result.total_placed == 2
        assert abs(result.placed[1].x_offset - (5.0 + 500.0 + 3.0)) < 0.01

    def test_common_cut_zero_gap(self):
        pieces = [build_nesting_piece(_make_corte(500.0), i, 50.0, "#f00", 3.0) for i in range(3)]
        result = nest_simple(pieces, _params(kerf=3.0, margin=5.0, common_cut=True))
        assert abs(result.placed[1].x_offset - (5.0 + 500.0)) < 0.01
        assert abs(result.placed[2].x_offset - (5.0 + 1000.0)) < 0.01

    def test_end_margin_respected(self):
        piece = build_nesting_piece(_make_corte(900.0), 0, 50.0, "#f00", 0.0)
        result = nest_simple([piece], _params(bar_length=1000.0, margin=50.0, common_cut=True))
        pp = result.placed[0]
        assert pp.x_offset + 900.0 <= 1000.0 - 50.0 + 0.01

    def test_five_pieces_one_bar(self):
        pieces = [build_nesting_piece(_make_corte(500.0), i, 50.0, "#f00", 2.0) for i in range(5)]
        result = nest_simple(pieces, _params(bar_length=6000.0, kerf=2.0, margin=5.0))
        assert result.bars_used == 1
        assert result.total_placed == 5

    def test_overflow_opens_new_bar(self):
        pieces = [build_nesting_piece(_make_corte(1100.0), i, 50.0, "#f00", 2.0) for i in range(6)]
        result = nest_simple(pieces, _params(bar_length=6000.0, kerf=2.0, margin=5.0))
        assert result.bars_used >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ADVANCED NESTING — NFP-based, no overlaps
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdvanced:

    def test_first_piece_at_margin(self):
        piece = build_nesting_piece(_make_corte(500.0), 0, 50.0, "#f00", 2.0)
        stop = threading.Event()
        result = nest_advanced_timed([piece], _params(margin=10.0), time_limit_sec=1.0, stop_event=stop)
        assert result.total_placed == 1
        assert result.placed[0].x_offset >= 10.0 - 1.0

    def test_two_pieces_no_overlap(self):
        pieces = [build_nesting_piece(_make_corte(float(l)), i, 50.0, "#f00", 2.0)
                  for i, l in enumerate([500, 400])]
        stop = threading.Event()
        result = nest_advanced_timed(pieces, _params(kerf=3.0, margin=5.0, profile_height=50.0),
                                     time_limit_sec=2.0, stop_event=stop)
        assert result.total_placed == 2
        bar0 = _placed_on_bar(result, 0)
        if len(bar0) >= 2:
            inter = bar0[0][1].intersection(bar0[1][1])
            assert inter.area < 0.1

    def test_ten_pieces_no_overlap(self):
        cortes = [_make_corte(float(l)) for l in [500, 400, 300, 600, 200, 350, 450, 550, 250, 150]]
        pieces = [build_nesting_piece(c, i, 50.0, "#f00", 2.0) for i, c in enumerate(cortes)]
        stop = threading.Event()
        result = nest_advanced_timed(pieces, _params(profile_height=50.0),
                                     time_limit_sec=3.0, stop_event=stop)
        for bar_idx in range(result.bars_used):
            polys = _placed_on_bar(result, bar_idx)
            for i in range(len(polys)):
                for j in range(i + 1, len(polys)):
                    inter = polys[i][1].intersection(polys[j][1])
                    assert inter.area < 0.5, \
                        f"Bar {bar_idx}: pieces {i} and {j} overlap, area={inter.area:.2f}"

    def test_bevel_pieces_no_overlap(self):
        cortes = [
            _make_corte(500.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up"),
            _make_corte(400.0, inglete2=True, inglete2_deg=30.0, inglete2_dir="down"),
            _make_corte(600.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up",
                        inglete2=True, inglete2_deg=45.0, inglete2_dir="up"),
            _make_corte(300.0),
        ]
        pieces = [build_nesting_piece(c, i, 50.0, "#f00", 2.0) for i, c in enumerate(cortes)]
        stop = threading.Event()
        result = nest_advanced_timed(pieces, _params(profile_height=50.0),
                                     time_limit_sec=2.0, stop_event=stop)
        for bar_idx in range(result.bars_used):
            polys = _placed_on_bar(result, bar_idx)
            for i in range(len(polys)):
                for j in range(i + 1, len(polys)):
                    inter = polys[i][1].intersection(polys[j][1])
                    assert inter.area < 0.5

    def test_pieces_within_bar_bounds(self):
        cortes = [_make_corte(float(l)) for l in [800, 1200, 600, 900, 700]]
        pieces = [build_nesting_piece(c, i, 50.0, "#f00", 2.0) for i, c in enumerate(cortes)]
        margin = 15.0
        p = _params(bar_length=6000.0, margin=margin, profile_height=50.0)
        stop = threading.Event()
        result = nest_advanced_timed(pieces, p, time_limit_sec=2.0, stop_event=stop)
        for pp in result.placed:
            poly = pp.get_polygon()
            b = poly.bounds
            assert b[0] >= margin - 1.0, f"Piece starts at {b[0]}, before margin={margin}"
            assert b[2] <= 6000.0 - margin + 1.0, f"Piece ends at {b[2]}, past {6000.0-margin}"

    def test_stop_event(self):
        cortes = [_make_corte(float(l)) for l in range(200, 1200, 100)]
        pieces = [build_nesting_piece(c, i, 50.0, "#f00", 2.0) for i, c in enumerate(cortes)]
        stop = threading.Event()
        import time
        def _stop():
            time.sleep(0.1)
            stop.set()
        t = threading.Thread(target=_stop, daemon=True)
        t.start()
        result = nest_advanced_timed(pieces, _params(), time_limit_sec=None, stop_event=stop)
        t.join(timeout=2.0)
        assert isinstance(result, NestingResult)
        assert result.bars_used >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 6. OBSTACLE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuildObstacle:

    def test_excludes_dragged_piece(self):
        piece = build_nesting_piece(_make_corte(500.0), 0, 50.0, "#f00", 0.0)
        pp1 = PlacedPiece(piece=piece, bar_index=0, x_offset=5.0, color="#f00")
        pp2 = PlacedPiece(piece=piece, bar_index=0, x_offset=550.0, color="#f00")
        assert build_obstacle_for_bar([pp1, pp2]).area > build_obstacle_for_bar([pp1, pp2], exclude=pp1).area

    def test_empty_bar(self):
        assert build_obstacle_for_bar([]).is_empty


# ═══════════════════════════════════════════════════════════════════════════════
# 7. COLOR SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class TestColorSystem:

    def test_retal_color(self):
        from nestify.export_utils import get_retal_color, RETAL_COLOR
        assert get_retal_color() == "#39FF14"

    def test_cut_color_never_retal(self):
        from nestify.export_utils import get_cut_color, _is_too_close_to_retal
        for i in range(100):
            color = get_cut_color((f"cut_{i}", float(i * 10)))
            assert not _is_too_close_to_retal(color), f"Color {color} too close to neon green"

    def test_same_key_same_color(self):
        from nestify.export_utils import get_cut_color
        assert get_cut_color(("X", 100.0)) == get_cut_color(("X", 100.0))

    def test_different_desc_different_color(self):
        from nestify.export_utils import get_cut_color, clear_color_cache
        clear_color_cache()
        assert get_cut_color(("A", 500.0)) != get_cut_color(("B", 500.0))


# ═══════════════════════════════════════════════════════════════════════════════
# 8. STRATEGIES — all 5 strategies produce valid results
# ═══════════════════════════════════════════════════════════════════════════════

class TestStrategies:

    def _run_strategy(self, strategy):
        cortes = [
            _make_corte(500.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up"),
            _make_corte(400.0, inglete2=True, inglete2_deg=30.0, inglete2_dir="down"),
            _make_corte(600.0),
            _make_corte(300.0, inglete1=True, inglete1_deg=20.0, inglete1_dir="up",
                        inglete2=True, inglete2_deg=20.0, inglete2_dir="down"),
        ]
        pieces = [build_nesting_piece(c, i, 50.0, "#f00", 2.0) for i, c in enumerate(cortes)]
        params = _params(profile_height=50.0, priority=strategy)
        stop = threading.Event()
        result = nest_advanced_timed(pieces, params, time_limit_sec=2.0, stop_event=stop)
        assert result.total_placed == 4
        for bar_idx in range(result.bars_used):
            polys = _placed_on_bar(result, bar_idx)
            for i in range(len(polys)):
                for j in range(i + 1, len(polys)):
                    inter = polys[i][1].intersection(polys[j][1])
                    assert inter.area < 0.5, \
                        f"Strategy {strategy}: bar {bar_idx} pieces {i},{j} overlap"
        return result

    def test_strategy_length(self):
        self._run_strategy("length")

    def test_strategy_nfp_compact(self):
        self._run_strategy("nfp_compact")

    def test_strategy_remnants(self):
        self._run_strategy("remnants")

    def test_strategy_symmetry(self):
        self._run_strategy("symmetry")

    def test_strategy_min_length(self):
        self._run_strategy("min_length")

    def test_all_strategies_exist(self):
        assert set(STRATEGIES) == {"length", "nfp_compact", "remnants", "symmetry", "min_length"}


# ═══════════════════════════════════════════════════════════════════════════════
# 9. POLY LOCAL — engine polygon coords for rendering
# ═══════════════════════════════════════════════════════════════════════════════

class TestPolyLocal:

    def test_local_polygon_coords_returns_vertices(self):
        piece = build_nesting_piece(_make_corte(500.0), 0, 50.0, "#f00", 0.0)
        pp = PlacedPiece(piece=piece, bar_index=0, x_offset=10.0, color="#f00")
        coords = pp.local_polygon_coords()
        assert len(coords) >= 3
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        assert min(xs) >= -0.01
        assert max(xs) <= 500.01
        assert min(ys) >= -0.01
        assert max(ys) <= 50.01

    def test_flipped_v_poly_local_same_bbox(self):
        corte = _make_corte(500.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up")
        piece = build_nesting_piece(corte, 0, 50.0, "#f00", 0.0)
        pp_ff = PlacedPiece(piece=piece, bar_index=0, x_offset=0.0, color="#f00")
        pp_fv = PlacedPiece(piece=piece, bar_index=0, x_offset=0.0,
                            flipped_v=True, color="#f00")
        coords_ff = pp_ff.local_polygon_coords()
        coords_fv = pp_fv.local_polygon_coords()
        w_ff = max(c[0] for c in coords_ff) - min(c[0] for c in coords_ff)
        w_fv = max(c[0] for c in coords_fv) - min(c[0] for c in coords_fv)
        assert abs(w_ff - w_fv) < 0.01, \
            f"flip_v changed width: {w_ff} vs {w_fv}"

    def test_poly_local_area_preserved(self):
        corte = _make_corte(500.0, inglete1=True, inglete1_deg=45.0, inglete1_dir="up",
                            inglete2=True, inglete2_deg=30.0, inglete2_dir="down")
        piece = build_nesting_piece(corte, 0, 50.0, "#f00", 0.0)
        for fh, fv in piece.orientations:
            pp = PlacedPiece(piece=piece, bar_index=0, x_offset=0.0,
                             flipped_h=fh, flipped_v=fv, color="#f00")
            poly = Polygon(pp.local_polygon_coords())
            assert abs(poly.area - piece.base_polygon.area) < 0.1
