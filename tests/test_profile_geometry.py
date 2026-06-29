"""
test_profile_geometry.py — §20.3 parametric cross-section contours.

Pure-Python coverage of nestify.profile_geometry.section_contours() for every
catalogue geometry type. No Qt required (the rasteriser is exercised
separately, only under a real/offscreen QApplication).
"""
import math

import pytest

from nestify.profile_geometry import GEOMETRY_TYPES, section_contours

# Representative dimensions per type, drawn from the catalogue xlsx dataset.
SAMPLES = {
    "Viga I": dict(h=100, b=55, tw=4.1, tf=5.7),
    "Viga H": dict(h=100, b=100, tw=6, tf=10),
    "Viga U": dict(h=100, b=50, tw=5, tf=7),
    "Perfil C": dict(h=100, b=50, tw=3, tf=3),
    "Perfil Z": dict(h=100, b=50, tw=3, tf=3),
    "Angular": dict(h=50, b=50, tw=5, tf=5),
    "Cuadrado": dict(h=40, b=40, tw=3, tf=3),
    "Redondo": dict(h=60.3, tw=3),
    "Pletina": dict(h=10, b=50),
    "Ranurado": dict(h=40, b=40),
}


def _bbox(contour):
    xs = [p[0] for p in contour]
    ys = [p[1] for p in contour]
    return min(xs), min(ys), max(xs), max(ys)


@pytest.mark.parametrize("geometry_type", GEOMETRY_TYPES)
def test_every_geometry_type_produces_a_nonempty_outer(geometry_type):
    params = SAMPLES.get(geometry_type, dict(h=50, b=50, tw=3, tf=3))
    outer, holes = section_contours(geometry_type, **params)
    assert len(outer) >= 3
    assert all(isinstance(p, tuple) and len(p) == 2 for p in outer)
    for hole in holes:
        assert len(hole) >= 3


def test_redondo_hollow_has_one_hole_smaller_than_outer():
    outer, holes = section_contours("Redondo", h=60.3, tw=3, macizo=False)
    assert len(holes) == 1
    minx, miny, maxx, maxy = _bbox(outer)
    hminx, hminy, hmaxx, hmaxy = _bbox(holes[0])
    assert hmaxx - hminx < maxx - minx
    assert hmaxy - hminy < maxy - miny


def test_redondo_macizo_has_no_hole_even_with_wall_given():
    outer, holes = section_contours("Redondo", h=60.3, tw=3, macizo=True)
    assert outer
    assert holes == []


def test_redondo_wall_too_thick_collapses_to_no_hole():
    # tw >= h/2 would invert the bore; must not produce a hole.
    outer, holes = section_contours("Redondo", h=20, tw=15, macizo=False)
    assert holes == []


def test_cuadrado_hollow_vs_macizo():
    outer, holes = section_contours("Cuadrado", h=40, b=40, tw=3, tf=3, macizo=False)
    assert len(holes) == 1
    outer2, holes2 = section_contours("Cuadrado", h=40, b=40, tw=3, tf=3, macizo=True)
    assert holes2 == []
    assert outer == outer2


def test_cuadrado_defaults_to_square_when_b_missing():
    outer, _ = section_contours("Cuadrado", h=40)
    minx, miny, maxx, maxy = _bbox(outer)
    assert pytest.approx(maxx - minx) == pytest.approx(maxy - miny)


def test_pletina_is_a_flat_rectangle_with_no_holes():
    outer, holes = section_contours("Pletina", h=10, b=50)
    assert holes == []
    minx, miny, maxx, maxy = _bbox(outer)
    assert maxx - minx == pytest.approx(50)
    assert maxy - miny == pytest.approx(10)


def test_viga_i_and_h_are_doubly_symmetric_about_origin():
    for g in ("Viga I", "Viga H"):
        outer, holes = section_contours(g, **SAMPLES[g])
        assert holes == []
        for x, y in outer:
            # Every vertex must have a mirrored counterpart (doubly symmetric).
            assert any(
                math.isclose(x, -ox, abs_tol=1e-6) and math.isclose(y, -oy, abs_tol=1e-6)
                for ox, oy in outer
            )


def test_viga_u_and_perfil_c_open_on_one_side():
    for g in ("Viga U", "Perfil C"):
        outer, holes = section_contours(g, **SAMPLES[g])
        assert holes == []
        assert len(outer) == 8


def test_perfil_z_outer_only_no_holes():
    outer, holes = section_contours("Perfil Z", **SAMPLES["Perfil Z"])
    assert holes == []
    assert len(outer) == 8


def test_angular_has_six_vertices_no_holes():
    outer, holes = section_contours("Angular", **SAMPLES["Angular"])
    assert holes == []
    assert len(outer) == 6


def test_ranurado_has_a_circular_bore():
    outer, holes = section_contours("Ranurado", h=40, b=40)
    assert len(holes) == 1
    assert len(holes[0]) > 4  # circle approximation, not a square hole


def test_unknown_geometry_falls_back_to_rectangle():
    outer, holes = section_contours("No Existe", h=30, b=40)
    assert holes == []
    minx, miny, maxx, maxy = _bbox(outer)
    assert maxx - minx == pytest.approx(40)
    assert maxy - miny == pytest.approx(30)


def test_unknown_geometry_with_only_height_falls_back_to_square():
    outer, holes = section_contours("No Existe", h=30)
    minx, miny, maxx, maxy = _bbox(outer)
    assert maxx - minx == pytest.approx(30)
    assert maxy - miny == pytest.approx(30)


def test_none_dimensions_do_not_raise():
    for g in GEOMETRY_TYPES:
        outer, holes = section_contours(g, h=None, b=None, tw=None, tf=None)
        assert outer  # always produces *some* contour, never crashes


def test_contours_are_centred_on_bounding_box_origin_where_applicable():
    # Geometries that explicitly centre (Cuadrado, Viga U/Perfil C, Perfil Z,
    # Ranurado, fallback) should have their bbox centred near (0, 0).
    for g in ("Cuadrado", "Viga U", "Perfil C", "Perfil Z", "Ranurado"):
        outer, holes = section_contours(g, **SAMPLES.get(g, dict(h=40, b=40)))
        contours = [outer] + holes
        xs = [x for c in contours for x, _ in c]
        ys = [y for c in contours for _, y in c]
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        assert cx == pytest.approx(0, abs=1e-6)
        assert cy == pytest.approx(0, abs=1e-6)
