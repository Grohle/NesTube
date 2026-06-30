"""Tests for nestube.dxf_cache (D7)."""
import pytest
from pathlib import Path
from nestube.models import Corte
from nestube.dxf_cache import piece_dxf_path, load_piece_contour, save_piece_contour, auto_generate_and_save


def _make_corte(**kwargs) -> Corte:
    """Build a minimal valid Corte for testing.

    Corte fields: descripcion, largo, cantidad,
                  inglete1 (bool), inglete1_dir, inglete1_deg,
                  inglete2 (bool), inglete2_dir, inglete2_deg
    """
    defaults = dict(
        descripcion="Test",
        largo=1000.0,
        cantidad=1,
        inglete1=False,
        inglete1_dir="up",
        inglete1_deg=0.0,
        inglete2=False,
        inglete2_dir="up",
        inglete2_deg=0.0,
    )
    defaults.update(kwargs)
    return Corte(**defaults)


def test_piece_dxf_path_naming():
    """D2 naming: 45-degree left/down bevel, no right bevel, no flip, 1000mm piece."""
    c = _make_corte(
        inglete1=True,
        inglete1_deg=45,
        inglete1_dir="down",
        inglete2=False,
        inglete2_deg=0,
        inglete2_dir="up",
    )
    p = piece_dxf_path("IPE 200", c, flipped_h=False, flipped_v=False)
    assert p.name == "IPE200_45LDW_0RUP_N_1000mm.dxf"


def test_piece_dxf_path_naming_no_bevel():
    """No bevels -> both sides are 0 with UP tag, length encoded."""
    c = _make_corte()
    p = piece_dxf_path("REC 60X40", c, flipped_h=False, flipped_v=False)
    assert p.name == "REC60X40_0LUP_0RUP_N_1000mm.dxf"


def test_piece_dxf_path_flip_tags():
    """Flip tags appear before the length suffix."""
    c = _make_corte()
    assert piece_dxf_path("X", c, True, False).name.endswith("_FH_1000mm.dxf")
    assert piece_dxf_path("X", c, False, True).name.endswith("_FV_1000mm.dxf")
    assert piece_dxf_path("X", c, True, True).name.endswith("_FHV_1000mm.dxf")
    assert piece_dxf_path("X", c, False, False).name.endswith("_N_1000mm.dxf")


def test_round_trip_save_load(tmp_path):
    """Save then load returns the same vertex coordinates."""
    import nestube.dxf_cache as dc
    orig = dc._DXF_DIR
    dc._DXF_DIR = tmp_path / "dxf"
    dc._DXF_DIR.mkdir()
    try:
        coords = [(0.0, 0.0), (100.0, 0.0), (100.0, 50.0), (0.0, 50.0)]
        c = _make_corte()
        save_piece_contour(coords, "IPE 200", c, False, False)
        loaded = load_piece_contour("IPE 200", c, False, False, H=50.0)
        assert loaded is not None
        assert len(loaded) == 4
        for (lx, ly), (ox, oy) in zip(loaded, coords):
            assert abs(lx - ox) < 1e-6
            assert abs(ly - oy) < 1e-6
    finally:
        dc._DXF_DIR = orig


def test_load_returns_none_when_file_absent():
    """Loading a DXF for a nonexistent profile returns None."""
    c = _make_corte()
    result = load_piece_contour("NONEXISTENT_PROFILE_ZZZZZ", c, False, False, H=100.0)
    assert result is None


def test_auto_generate_returns_4_vertices(tmp_path):
    """auto_generate_and_save returns 4 trapezoid vertices from bevel_geom."""
    import nestube.dxf_cache as dc
    orig = dc._DXF_DIR
    dc._DXF_DIR = tmp_path / "dxf"
    dc._DXF_DIR.mkdir()
    try:
        c = _make_corte(
            inglete1=True, inglete1_deg=30.0, inglete1_dir="up",
            inglete2=True, inglete2_deg=15.0, inglete2_dir="up",
            largo=500.0,
        )
        coords = auto_generate_and_save("UPN 100", c, False, False, H=100.0)
        assert len(coords) == 4
    finally:
        dc._DXF_DIR = orig


def test_auto_generate_writes_file(tmp_path):
    """auto_generate_and_save actually creates the DXF file on disk."""
    import nestube.dxf_cache as dc
    orig = dc._DXF_DIR
    dc._DXF_DIR = tmp_path / "dxf"
    dc._DXF_DIR.mkdir()
    try:
        c = _make_corte(largo=300.0)
        auto_generate_and_save("HEB 200", c, False, False, H=200.0)
        path = piece_dxf_path("HEB 200", c, False, False)
        assert path.exists()
    finally:
        dc._DXF_DIR = orig


def test_round_trip_with_flips(tmp_path):
    """Round-trip save/load works for all four flip combinations."""
    import nestube.dxf_cache as dc
    orig = dc._DXF_DIR
    dc._DXF_DIR = tmp_path / "dxf"
    dc._DXF_DIR.mkdir()
    try:
        coords = [(10.0, 0.0), (90.0, 0.0), (80.0, 50.0), (20.0, 50.0)]
        c = _make_corte(inglete1=True, inglete1_deg=10.0, inglete1_dir="up")
        for fh, fv in [(False, False), (True, False), (False, True), (True, True)]:
            save_piece_contour(coords, "IPE 100", c, fh, fv)
            loaded = load_piece_contour("IPE 100", c, fh, fv, H=50.0)
            assert loaded is not None, f"load failed for fh={fh} fv={fv}"
            assert len(loaded) == 4, f"wrong vertex count for fh={fh} fv={fv}"
    finally:
        dc._DXF_DIR = orig
