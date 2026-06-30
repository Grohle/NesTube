"""
nestube/nestube/nestube/bevel_geom.py
Bevel/miter geometry for nesting: quadrilateral pieces, kerf perpendicular to edges.
"""
from __future__ import annotations

import copy
import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .models import ConfigPerfil, Corte, TipoPerfil

_log = logging.getLogger(__name__)

TOL = 0.01


@dataclass(frozen=True)
class BevelPiece:
    """Piece as quadrilateral: nominal length L, left/right bevel angles (degrees from vertical).

    ``flipped_v`` marks a vertical mirror of the trapezoid (top/bottom swapped).
    It is carried as a flag rather than baked into the angles because a vertical
    flip moves the full-length edge from the bottom to the top — that cannot be
    expressed by changing ``alpha_L``/``alpha_R`` alone (see ``vertices_local``).
    This mirrors the nesting engine's ``_flip_v`` so the manual-placement
    collision contour agrees with the rendered/auto-nested polygon.
    """
    L: float
    alpha_L: float = 0.0
    alpha_R: float = 0.0
    flipped_v: bool = False

    def rotated_180(self) -> "BevelPiece":
        # Horizontal flip of the trapezoid == swapping the end angles (the
        # full-length bottom edge is preserved). The vertical-flip flag is
        # orthogonal, so carry it through unchanged.
        return BevelPiece(self.L, self.alpha_R, self.alpha_L, self.flipped_v)

    @property
    def symmetric(self) -> bool:
        return abs(self.alpha_L - self.alpha_R) < 1e-9


def _tan_deg(deg: float) -> float:
    return math.tan(math.radians(deg))


def _cos_deg(deg: float) -> float:
    c = math.cos(math.radians(deg))
    return c if abs(c) > 1e-12 else 1e-12


def dx_kerf_perpendicular(alpha_deg: float, kerf: float, margin_between: float = 0.0) -> float:
    """Horizontal separation equivalent to (kerf + margin_between) perpendicular to edge at alpha."""
    total = kerf + margin_between
    return total / _cos_deg(alpha_deg)


def vertices_local(piece: BevelPiece, H: float) -> Tuple[Tuple[float, float], ...]:
    """BL, BR, TR, TL in local coords.

    Base (non-flipped) trapezoid has the full length L on the bottom edge and
    the bevels inset the top corners. A vertical flip reflects across the
    horizontal mid-line (x kept, y → H − y): the full length moves to the top
    and the bevels inset the bottom corners — identical to the engine's
    ``_flip_v``. A vertical flip never changes the x-extent, only which height
    each slanted edge leans toward, which is exactly what interlocking miters
    need for correct collision.
    """
    t_l = H * _tan_deg(piece.alpha_L)
    t_r = H * _tan_deg(piece.alpha_R)
    if piece.flipped_v:
        # Reflected trapezoid: bottom corners inset by the bevels, top edge full.
        bl = (t_l, 0.0)
        br = (piece.L - t_r, 0.0)
        tr = (piece.L, H)
        tl = (0.0, H)
    else:
        bl = (0.0, 0.0)
        br = (piece.L, 0.0)
        tr = (piece.L - t_r, H)
        tl = (t_l, H)
    return bl, br, tr, tl


def vertices_global(x: float, piece: BevelPiece, H: float) -> Tuple[Tuple[float, float], ...]:
    return tuple((px + x, py) for px, py in vertices_local(piece, H))


def min_x_extent(piece: BevelPiece, H: float) -> float:
    """Minimum x of local vertices (for left bar margin)."""
    return min(px for px, _ in vertices_local(piece, H))


def max_x_extent(piece: BevelPiece, H: float) -> float:
    """Maximum x of local vertices (for right bar margin)."""
    return max(px for px, _ in vertices_local(piece, H))


def corte_to_bevel(corte: Corte, flipped_h: bool = False, flipped_v: bool = False) -> BevelPiece:
    """Map Corte + orientation to (L, αL, αR) per nesting spec."""

    def _alpha(has: bool, direction: str, deg: float) -> float:
        if not has:
            return 0.0
        sign = 1.0 if direction == "up" else -1.0
        return sign * deg

    a_l = _alpha(corte.inglete1, corte.inglete1_dir, corte.inglete1_deg)
    a_r = _alpha(corte.inglete2, corte.inglete2_dir, corte.inglete2_deg)
    # A vertical flip is a true reflection (handled in vertices_local), NOT a
    # sign change on the angles — negating them pushed the top corners outside
    # [0, L] and made the manual-placement contour disagree with the engine.
    piece = BevelPiece(corte.largo, a_l, a_r, flipped_v=flipped_v)
    if flipped_h:
        piece = piece.rotated_180()
    return piece


def profile_section_height(perfil: ConfigPerfil, default: float = 50.0) -> float:
    """Cross-section height (mm) used for miter depth along the bar axis."""
    if perfil is None:
        return default
    d = perfil.dimensiones
    if d.tipo == TipoPerfil.REDONDO and d.diametro > 0:
        return d.diametro
    h = max(d.lado_a, d.lado_b, d.lado_c, d.diametro)
    return h if h > 0 else default


def profile_section_height_known(perfil: ConfigPerfil) -> float:
    """Real cross-section height (mm) if the profile defines one, else 0.

    Unlike :func:`profile_section_height`, this never falls back to a default,
    so callers can tell "no profile height known yet" (0) from a real value and
    decide whether the bar-height field should auto-fill read-only.
    """
    if perfil is None:
        return 0.0
    d = perfil.dimensiones
    if d.tipo == TipoPerfil.REDONDO:
        return d.diametro if d.diametro > 0 else 0.0
    h = max(d.lado_a, d.lado_b, d.lado_c, d.diametro)
    return h if h > 0 else 0.0


def profile_available_heights(perfil: ConfigPerfil) -> list:
    """Return list of (label, value_mm) for each distinct nonzero profile face."""
    d = perfil.dimensiones
    heights = []
    if d.diametro > 0:
        heights.append(("⌀", d.diametro))
    if d.lado_a > 0:
        heights.append(("A", d.lado_a))
    if d.lado_b > 0 and d.lado_b != d.lado_a:
        heights.append(("B", d.lado_b))
    if d.lado_c > 0 and d.lado_c not in (d.lado_a, d.lado_b):
        heights.append(("C", d.lado_c))
    return heights


def transform_corte(corte: Corte, flipped_h: bool = False, flipped_v: bool = False) -> Corte:
    """Return a copy with horizontal (swap ends) and/or vertical (flip dirs) symmetry."""
    c = copy.copy(corte)
    if flipped_h:
        c.inglete1, c.inglete2 = c.inglete2, c.inglete1
        c.inglete1_dir, c.inglete2_dir = c.inglete2_dir, c.inglete1_dir
        c.inglete1_deg, c.inglete2_deg = c.inglete2_deg, c.inglete1_deg
    if flipped_v:
        c.inglete1_dir = "down" if c.inglete1_dir == "up" else "up"
        c.inglete2_dir = "down" if c.inglete2_dir == "up" else "up"
    return c


def _end_miter(corte: Corte, end: str) -> Tuple[bool, str, float]:
    if end == "left":
        return corte.inglete1, corte.inglete1_dir, corte.inglete1_deg
    return corte.inglete2, corte.inglete2_dir, corte.inglete2_deg


def miters_complementary(c_left: Corte, c_right: Corte) -> bool:
    """True when the right end of c_left can nest with the left end of c_right (legacy UI)."""
    r_has, r_dir, r_deg = _end_miter(c_left, "right")
    l_has, l_dir, l_deg = _end_miter(c_right, "left")
    if not (r_has and l_has):
        return False
    if r_dir == l_dir:
        return False
    return abs(r_deg - l_deg) < 0.5


def min_x_after_anchor(
    x_a: float,
    piece_a: BevelPiece,
    piece_b: BevelPiece,
    H: float,
    kerf: float,
    margin_between: float = 0.0,
    log_label: str = "",
) -> float:
    """Minimum x for B's BL when A is placed with BL at x_a (section 5).

    Contact coordinates are derived from vertices_local so the result is
    correct for both flipped_v=False and flipped_v=True pieces.  The old
    hard-coded formulas (a_right_y0 = x_a + L, b_left_y0 = 0, …) only
    held for the non-flipped case and gave wrong kerf clearance for
    vertically-flipped bevel pieces.
    """
    alpha_r_a = piece_a.alpha_R
    alpha_l_b = piece_b.alpha_L

    # Derive contact-face x-coordinates from the actual vertex geometry so
    # both flipped_v orientations are handled correctly.
    _, br_a, tr_a, _ = vertices_local(piece_a, H)
    bl_b, _, _, tl_b = vertices_local(piece_b, H)

    a_right_y0 = x_a + br_a[0]  # A's right face at y=0
    a_right_yh = x_a + tr_a[0]  # A's right face at y=H
    b_left_y0  = bl_b[0]         # B's left face at y=0 (local)
    b_left_yh  = tl_b[0]         # B's left face at y=H (local)

    if abs(alpha_r_a - alpha_l_b) < 1e-6:
        dx = dx_kerf_perpendicular(alpha_r_a, kerf, margin_between)
        # For parallel faces, the most constrained contact point is the
        # y-level where the faces are closest; take the max of both ends.
        x_b = max(a_right_y0 - b_left_y0, a_right_yh - b_left_yh) + dx
        if log_label:
            _log.info(
                "%s parallel α=%.2f dx_kerf=%.4f x_B=%.4f",
                log_label, alpha_r_a, dx, x_b,
            )
        return x_b

    dx_y0 = dx_kerf_perpendicular(alpha_r_a, kerf, margin_between)
    dx_yh = dx_kerf_perpendicular(alpha_r_a, kerf, margin_between)
    candidate_y0 = a_right_y0 + dx_y0 - b_left_y0
    candidate_yh = a_right_yh + dx_yh - b_left_yh
    x_b = max(candidate_y0, candidate_yh)
    if log_label:
        _log.info(
            "%s dx_kerf_y0=%.4f dx_kerf_yH=%.4f cand_y0=%.4f cand_yH=%.4f x_B=%.4f",
            log_label, dx_y0, dx_yh, candidate_y0, candidate_yh, x_b,
        )
    return x_b


def bar_used_length(
    placements: List[Tuple[float, BevelPiece]],
    H: float,
    margin: float,
) -> float:
    """Rightmost extent on bar including margin (max vertex x + margin at right)."""
    if not placements:
        return margin
    right = margin
    for x, piece in placements:
        right = max(right, x + max_x_extent(piece, H))
    return right


def fits_on_bar(
    x: float,
    piece: BevelPiece,
    bar_length: float,
    H: float,
    margin: float,
) -> bool:
    verts = vertices_global(x, piece, H)
    min_x = min(v[0] for v in verts)
    max_x = max(v[0] for v in verts)
    return min_x >= margin - TOL and max_x <= bar_length - margin + TOL


def _segments_overlap_1d(a0: float, a1: float, b0: float, b1: float, gap: float) -> bool:
    return a0 < b1 + gap - TOL and b0 < a1 + gap - TOL


def _convex_polygons_intersect(
    poly_a: Tuple[Tuple[float, float], ...],
    poly_b: Tuple[Tuple[float, float], ...],
    tol: float = TOL,
) -> bool:
    """True if two convex polygons overlap (SAT)."""
    for poly in (poly_a, poly_b):
        n = len(poly)
        for i in range(n):
            p0 = poly[i]
            p1 = poly[(i + 1) % n]
            nx = -(p1[1] - p0[1])
            ny = p1[0] - p0[0]
            min_a = max_a = poly_a[0][0] * nx + poly_a[0][1] * ny
            for p in poly_a[1:]:
                v = p[0] * nx + p[1] * ny
                min_a = min(min_a, v)
                max_a = max(max_a, v)
            min_b = max_b = poly_b[0][0] * nx + poly_b[0][1] * ny
            for p in poly_b[1:]:
                v = p[0] * nx + p[1] * ny
                min_b = min(min_b, v)
                max_b = max(max_b, v)
            if max_a < min_b - tol or max_b < min_a - tol:
                break
        else:
            continue
        return False
    return True


def contour_polygons_collide(
    x_a: float,
    piece_a: BevelPiece,
    x_b: float,
    piece_b: BevelPiece,
    H: float,
    kerf: float,
    margin_between: float = 0.0,
    profile_name_a=None,
    corte_a=None,
    flipped_h_a: bool = False,
    flipped_v_a: bool = False,
    profile_name_b=None,
    corte_b=None,
    flipped_h_b: bool = False,
    flipped_v_b: bool = False,
) -> bool:
    """True if 2D contours overlap or violate kerf clearance (never nominal largo).

    When profile_name_* and corte_* are provided the function tries to load a
    DXF contour for that piece and uses those vertices instead of the trapezoid
    approximation.  All extra keyword args default to None/False so existing
    callers work unchanged.
    """
    if x_a > x_b:
        x_a, piece_a, x_b, piece_b = x_b, piece_b, x_a, piece_a
        # swap optional DXF args too
        profile_name_a, corte_a, flipped_h_a, flipped_v_a, \
        profile_name_b, corte_b, flipped_h_b, flipped_v_b = \
            profile_name_b, corte_b, flipped_h_b, flipped_v_b, \
            profile_name_a, corte_a, flipped_h_a, flipped_v_a

    # Try loading DXF contours (lazy import to avoid circular deps)
    va: Tuple[Tuple[float, float], ...]
    vb: Tuple[Tuple[float, float], ...]

    if profile_name_a is not None and corte_a is not None:
        try:
            from nestube.dxf_cache import load_piece_contour as _lpc
            local_a = _lpc(profile_name_a, corte_a, flipped_h_a, flipped_v_a, H)
            if local_a is not None:
                va = tuple((px + x_a, py) for px, py in local_a)
            else:
                va = vertices_global(x_a, piece_a, H)
        except Exception:
            va = vertices_global(x_a, piece_a, H)
    else:
        va = vertices_global(x_a, piece_a, H)

    if profile_name_b is not None and corte_b is not None:
        try:
            from nestube.dxf_cache import load_piece_contour as _lpc
            local_b = _lpc(profile_name_b, corte_b, flipped_h_b, flipped_v_b, H)
            if local_b is not None:
                vb = tuple((px + x_b, py) for px, py in local_b)
            else:
                vb = vertices_global(x_b, piece_b, H)
        except Exception:
            vb = vertices_global(x_b, piece_b, H)
    else:
        vb = vertices_global(x_b, piece_b, H)

    if _convex_polygons_intersect(va, vb, tol=TOL):
        return True
    min_sep = min_x_after_anchor(x_a, piece_a, piece_b, H, kerf, margin_between)
    return x_b < min_sep - TOL


def resolve_contact_x(
    x_a: float,
    piece_a: BevelPiece,
    piece_b: BevelPiece,
    H: float,
    kerf: float,
    margin_between: float = 0.0,
    use_bevel: bool = True,
) -> float:
    """Leftmost x for B's BL with no contour overlap (kerf via min_x_after_anchor)."""
    if use_bevel:
        x = min_x_after_anchor(x_a, piece_a, piece_b, H, kerf, margin_between)
    else:
        x = x_a + max_x_extent(piece_a, H) + kerf
    step = 0.05
    for _ in range(40000):
        if not contour_polygons_collide(x_a, piece_a, x, piece_b, H, kerf, margin_between):
            return x
        x += step
    return x


def _piece_x_interval_at_y(x: float, piece: BevelPiece, H: float, y: float) -> Tuple[float, float]:
    """Occupied x interval of piece at height y (0..H)."""
    bl, br, tr, tl = vertices_global(x, piece, H)
    if y <= TOL:
        return min(bl[0], br[0]), max(bl[0], br[0])
    if y >= H - TOL:
        return min(tl[0], tr[0]), max(tl[0], tr[0])
    # Linear interpolation along left and right edges
    t = y / H if H > 0 else 0.0
    left_x = bl[0] + t * (tl[0] - bl[0])
    right_x = br[0] + t * (tr[0] - br[0])
    return min(left_x, right_x), max(left_x, right_x)


def pieces_overlap(
    x_a: float,
    piece_a: BevelPiece,
    x_b: float,
    piece_b: BevelPiece,
    H: float,
    kerf: float,
    margin_between: float = 0.0,
) -> bool:
    """True if contours collide (polygon intersection + kerf clearance)."""
    return contour_polygons_collide(
        x_a, piece_a, x_b, piece_b, H, kerf, margin_between,
    )




def gap_between_pieces(
    left: Corte,
    right: Corte,
    kerf: float,
    section_height: float,
    use_bevel: bool,
    common_cut: bool = False,
) -> float:
    """Minimum gap (mm) between two adjacent pieces along the bar."""
    if not use_bevel:
        if common_cut:
            r_has, _, _ = _end_miter(left, "right")
            l_has, _, _ = _end_miter(right, "left")
            if not r_has and not l_has:
                return 0.0
        return kerf

    H = section_height
    pa = corte_to_bevel(left)
    pb = corte_to_bevel(right)
    if common_cut and abs(pa.alpha_R - pb.alpha_L) < 1e-6 and pa.alpha_R != 0:
        return 0.0
    x_after = min_x_after_anchor(0.0, pa, pb, H, kerf, 0.0)
    return x_after - pa.L


def bevel_depth_mm(corte: Corte, end: str, section_height: float) -> float:
    """Legacy helper for visuals — axial inset at one end."""
    has, direction, deg = _end_miter(corte, end)
    if not has or section_height <= 0:
        return 0.0
    piece = BevelPiece(corte.largo, 0.0, 0.0)
    if end == "left":
        piece = BevelPiece(corte.largo, _alpha_signed(has, direction, deg), 0.0)
    else:
        piece = BevelPiece(corte.largo, 0.0, _alpha_signed(has, direction, deg))
    verts = vertices_local(piece, section_height)
    _, br, tr, tl = verts
    if end == "right":
        return abs(br[0] - tr[0])
    return abs(verts[0][0] - tl[0])


def _alpha_signed(has: bool, direction: str, deg: float) -> float:
    if not has:
        return 0.0
    return deg if direction == "up" else -deg


def bar_axis_used(
    pieces: List[Tuple[float, Corte, bool, bool]],
    section_height: float,
    margin: float,
) -> float:
    placements = [
        (x_off, corte_to_bevel(corte, fh, fv))
        for x_off, corte, fh, fv in pieces
    ]
    return bar_used_length(placements, section_height, margin)


def max_start_x_for_piece(
    corte: Corte,
    bar_length: float,
    margin: float,
    section_height: float,
    flipped_h: bool = False,
    flipped_v: bool = False,
    use_bevel: bool = False,
) -> float:
    """Maximum x for BL — always uses bevel polygon extent (never nominal largo alone)."""
    piece = corte_to_bevel(corte, flipped_h, flipped_v)
    ext = max_x_extent(piece, section_height)
    return max(margin, bar_length - margin - ext)


def can_place_on_bar(
    x_mm: float,
    corte: Corte,
    flipped_h: bool,
    flipped_v: bool,
    neighbors: List[Tuple[float, Corte, bool, bool]],
    bar_length: float,
    margin: float,
    kerf: float,
    section_height: float,
    use_bevel: bool,
    common_cut: bool = False,
    profile_name: Optional[str] = None,
) -> bool:
    """
    Placement by 2D bevel polygon collision (nestube.mdc R5).
    Never uses nominal largo intervals — use_bevel only affects gap/common-cut rules.
    When profile_name is provided, loads DXF contours for true polygon collision.
    """
    H = section_height
    piece_b = corte_to_bevel(corte, flipped_h, flipped_v)
    if not fits_on_bar(x_mm, piece_b, bar_length, H, margin):
        return False
    mb = 0.0
    gap_kerf = 0.0 if common_cut else kerf
    for ox, oc, ofh, ofv in neighbors:
        piece_a = corte_to_bevel(oc, ofh, ofv)
        if contour_polygons_collide(
            ox, piece_a, x_mm, piece_b, H, gap_kerf, mb,
            profile_name_a=profile_name, corte_a=oc,
            flipped_h_a=ofh, flipped_v_a=ofv,
            profile_name_b=profile_name, corte_b=corte,
            flipped_h_b=flipped_h, flipped_v_b=flipped_v,
        ):
            return False
    return True


def snap_positions_after_pieces(
    neighbors: List[Tuple[float, Corte, bool, bool]],
    corte: Corte,
    flipped_h: bool,
    flipped_v: bool,
    bar_length: float,
    margin: float,
    kerf: float,
    section_height: float,
    use_bevel: bool,
    common_cut: bool = False,
    profile_name: Optional[str] = None,
) -> List[float]:
    def _fits(x_mm: float) -> bool:
        return can_place_on_bar(
            x_mm, corte, flipped_h, flipped_v, neighbors,
            bar_length, margin, kerf, section_height, use_bevel, common_cut,
            profile_name=profile_name,
        )

    candidates: List[float] = []

    H = section_height
    piece_b = corte_to_bevel(corte, flipped_h, flipped_v)

    # Bar-start snap: for pieces with a bevel overhang past x=0 (min_x < 0,
    # e.g. a "down" miter on the left end), the minimum valid x_offset is
    # -min_x_extent, not margin.  Try both so that left-edge placement is
    # always offered regardless of bevel orientation.
    bar_start = margin - min_x_extent(piece_b, H)
    if _fits(margin):
        candidates.append(margin)
    if abs(bar_start - margin) > TOL and _fits(bar_start):
        candidates.append(bar_start)
    for ox, oc, ofh, ofv in sorted(neighbors, key=lambda t: t[0]):
        piece_a = corte_to_bevel(oc, ofh, ofv)
        after = resolve_contact_x(ox, piece_a, piece_b, H, kerf, 0.0, use_bevel)
        if _fits(after):
            candidates.append(after)

    piece = corte_to_bevel(corte, flipped_h, flipped_v)
    right = bar_length - margin - max_x_extent(piece, section_height)
    if _fits(right):
        candidates.append(right)

    unique: List[float] = []
    for x in sorted(candidates):
        if not unique or abs(x - unique[-1]) > 0.05:
            unique.append(x)
    return unique


def bevel_polygon_points(
    x0: float, y0: float, x1: float, y1: float, corte: Corte,
) -> Optional[List[float]]:
    """Canvas polygon [x,y,...] using spec quadrilateral (y0=bottom, y1=top)."""
    h = y1 - y0
    w = x1 - x0
    if w <= 0 or h <= 0:
        return None
    if not corte.inglete1 and not corte.inglete2:
        return None
    scale = w / corte.largo if corte.largo > 0 else 1.0
    piece = corte_to_bevel(corte)
    bl, br, tr, tl = vertices_local(piece, h)
    pts = [
        (x0 + tl[0] * scale, y0 + (h - tl[1])),
        (x0 + tr[0] * scale, y0 + (h - tr[1])),
        (x0 + br[0] * scale, y0 + (h - br[1])),
        (x0 + bl[0] * scale, y0 + (h - bl[1])),
    ]
    return [coord for pt in pts for coord in pt]


# Orientation cycle for Ctrl+Q / Ctrl+E (4 states)
ORIENTATIONS: Tuple[Tuple[bool, bool], ...] = (
    (False, False),
    (True, False),
    (True, True),
    (False, True),
)


def orientation_index(flipped_h: bool, flipped_v: bool) -> int:
    for i, pair in enumerate(ORIENTATIONS):
        if pair == (flipped_h, flipped_v):
            return i
    return 0


def cycle_orientation(flipped_h: bool, flipped_v: bool, delta: int) -> Tuple[bool, bool]:
    idx = (orientation_index(flipped_h, flipped_v) + delta) % len(ORIENTATIONS)
    return ORIENTATIONS[idx]


def bevel_bar_used_after_place(
    neighbors: List[Tuple[float, Corte, bool, bool]],
    x_mm: float,
    corte: Corte,
    flipped_h: bool,
    flipped_v: bool,
    section_height: float,
    margin: float,
    use_bevel: bool,
) -> float:
    """Rightmost mm used on bar after placing corte at x_mm (polygon extent)."""
    placements = [
        (ox, corte_to_bevel(oc, fh, fv))
        for ox, oc, fh, fv in neighbors
    ]
    placements.append((x_mm, corte_to_bevel(corte, flipped_h, flipped_v)))
    return bar_used_length(placements, section_height, margin)




def log_placement_vertices(
    label: str,
    x: float,
    piece: BevelPiece,
    H: float,
) -> None:
    verts = vertices_global(x, piece, H)
    _log.info(
        "%s x=%.4f BL=%s BR=%s TR=%s TL=%s",
        label, x,
        tuple(round(v, 2) for v in verts[0]),
        tuple(round(v, 2) for v in verts[1]),
        tuple(round(v, 2) for v in verts[2]),
        tuple(round(v, 2) for v in verts[3]),
    )
