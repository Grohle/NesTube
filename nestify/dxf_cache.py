"""
nestify/dxf_cache.py
DXF contour bank for bevel piece geometry (Track D).

Naming convention (D2):
  dxf/{PROFILE_NAME}_{L_BEVEL_DEG}L{L_SIDE}_{R_BEVEL_DEG}R{R_SIDE}_{FLIP}.dxf

  PROFILE_NAME : uppercase, spaces stripped  e.g. "IPE 200" -> "IPE200"
  L_BEVEL_DEG  : integer degrees (0..89)
  L_SIDE       : "UP" or "DW"
  R_BEVEL_DEG  : integer degrees
  R_SIDE       : "UP" or "DW"
  FLIP         : "N"   (none)
               | "FH"  (flipped_h — piece.rotated_180())
               | "FV"  (flipped_v=True)
               | "FHV" (both)

Corte field mapping:
  left  bevel: inglete1, inglete1_dir ("up"/"down"), inglete1_deg
  right bevel: inglete2, inglete2_dir ("up"/"down"), inglete2_deg
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

# Repo-root dxf/ directory (one level above nestify/)
_DXF_DIR: Path = Path(__file__).resolve().parents[1] / "dxf"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_dxf_dir() -> Path:
    _DXF_DIR.mkdir(exist_ok=True)
    return _DXF_DIR


def _profile_slug(profile_name: str) -> str:
    """Uppercase profile name with spaces removed."""
    return profile_name.upper().replace(" ", "")


def _side_tag(has: bool, direction: str) -> str:
    """Return 'UP' or 'DW' based on direction field."""
    if not has:
        return "UP"   # 0-degree bevel — side is irrelevant; use UP as canonical
    return "UP" if direction == "up" else "DW"


def _deg_tag(has: bool, deg: float) -> int:
    """Return integer degrees; 0 if no bevel."""
    if not has:
        return 0
    return int(round(deg))


def _flip_tag(flipped_h: bool, flipped_v: bool) -> str:
    if flipped_h and flipped_v:
        return "FHV"
    if flipped_h:
        return "FH"
    if flipped_v:
        return "FV"
    return "N"


# ── Public API ────────────────────────────────────────────────────────────────

def piece_dxf_path(
    profile_name: str,
    corte,
    flipped_h: bool,
    flipped_v: bool,
) -> Path:
    """Build DXF path per D2 convention.  Returns the path regardless of existence.

    Piece length is part of the key: a 536mm piece and a 1242mm piece with the
    same bevel angles have different polygons and must not share a cached file.
    """
    slug = _profile_slug(profile_name)

    l_deg  = _deg_tag(corte.inglete1, corte.inglete1_deg)
    l_side = _side_tag(corte.inglete1, corte.inglete1_dir)
    r_deg  = _deg_tag(corte.inglete2, corte.inglete2_deg)
    r_side = _side_tag(corte.inglete2, corte.inglete2_dir)
    flip   = _flip_tag(flipped_h, flipped_v)
    length = int(round(corte.largo))

    filename = f"{slug}_{l_deg}L{l_side}_{r_deg}R{r_side}_{flip}_{length}mm.dxf"
    return _DXF_DIR / filename


def load_piece_contour(
    profile_name: str,
    corte,
    flipped_h: bool,
    flipped_v: bool,
    H: float,
) -> Optional[List[Tuple[float, float]]]:
    """Load LWPOLYLINE vertices from DXF if file exists; else return None.

    The first LWPOLYLINE entity in modelspace is used.  The H parameter is
    accepted for API symmetry but is not needed for loading (vertices are
    stored as absolute coordinates).
    """
    path = piece_dxf_path(profile_name, corte, flipped_h, flipped_v)
    if not path.exists():
        return None
    try:
        import ezdxf
        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()
        for entity in msp.query("LWPOLYLINE"):
            pts = [(x, y) for x, y, *_ in entity.get_points()]
            if pts:
                return pts
    except Exception:
        return None
    return None


def save_piece_contour(
    poly_coords: List[Tuple[float, float]],
    profile_name: str,
    corte,
    flipped_h: bool,
    flipped_v: bool,
) -> Path:
    """Write polygon as LWPOLYLINE in a new DXF file (R2010).  Returns the path."""
    import ezdxf

    _ensure_dxf_dir()
    path = piece_dxf_path(profile_name, corte, flipped_h, flipped_v)
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline(poly_coords, close=True)
    doc.saveas(str(path))
    return path


def write_piece_dxf_from_corte(corte, H: float, path: str) -> None:
    """Compute piece polygon from corte+H and write to the given DXF path."""
    from nestify.bevel_geom import corte_to_bevel, vertices_local
    import ezdxf
    piece = corte_to_bevel(corte)
    verts = list(vertices_local(piece, H))
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline(verts, close=True)
    doc.saveas(str(path))


def auto_generate_and_save(
    profile_name: str,
    corte,
    flipped_h: bool,
    flipped_v: bool,
    H: float,
) -> List[Tuple[float, float]]:
    """Compute vertices from bevel_geom, save to DXF, return vertices.

    Uses corte_to_bevel() so the geometry matches the nesting engine exactly.
    """
    from nestify.bevel_geom import corte_to_bevel, vertices_local

    piece = corte_to_bevel(corte, flipped_h=flipped_h, flipped_v=flipped_v)
    verts = list(vertices_local(piece, H))
    save_piece_contour(verts, profile_name, corte, flipped_h, flipped_v)
    return verts
