"""
nestube/nestube/nestube/geometry_engine.py
Vectorized 2D irregular nesting engine using Shapely 2.0 + NumPy.

Key concepts:
- Pieces are Shapely Polygons (imported from DXF, stored as WKT)
- Tube surface = flat rectangle (X = length axis, Y = circumference)
- Cylindrical wrapping: periodic boundary condition on Y axis
- Anisotropic margins: offset ONLY in X (kerf + margin), never in Y
- Solid-wall collision: vectorial blocking during manual drag

INVARIANT: Y dimension represents the tube circumference and must NEVER
be altered by buffer/margin operations. Only X-axis expansion is allowed.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from shapely import affinity as sh_affinity
from shapely.geometry import Polygon, MultiPolygon, box, LineString, Point
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.validation import make_valid

_log = logging.getLogger(__name__)


# ── Piece wrapper ────────────────────────────────────────────────────────────

@dataclass
class IrregularPiece:
    """An irregular 2D piece for tube nesting."""
    piece_id: int
    polygon: Polygon
    name: str = ""
    quantity: int = 1
    placed_qty: int = 0
    color: str = "#4A6FA5"
    thickness: float = 0.0

    @property
    def remaining(self) -> int:
        return max(0, self.quantity - self.placed_qty)

    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        return self.polygon.bounds

    @property
    def width(self) -> float:
        b = self.bounds
        return b[2] - b[0]

    @property
    def height(self) -> float:
        b = self.bounds
        return b[3] - b[1]

    @property
    def area(self) -> float:
        return self.polygon.area

    def translated(self, dx: float, dy: float) -> Polygon:
        return sh_affinity.translate(self.polygon, xoff=dx, yoff=dy)

    def rotated(self, angle_deg: float, origin: str = "centroid") -> Polygon:
        return sh_affinity.rotate(self.polygon, angle_deg, origin=origin)

    def flipped_h(self) -> Polygon:
        cx = (self.bounds[0] + self.bounds[2]) / 2
        return sh_affinity.scale(self.polygon, xfact=-1, yfact=1, origin=(cx, 0))

    def flipped_v(self) -> Polygon:
        cy = (self.bounds[1] + self.bounds[3]) / 2
        return sh_affinity.scale(self.polygon, xfact=1, yfact=-1, origin=(0, cy))


@dataclass
class PlacedIrregularPiece:
    """A piece placed at a specific position on a bar."""
    piece: IrregularPiece
    bar_index: int
    x_offset: float
    y_offset: float
    rotation_deg: float = 0.0
    flipped_h: bool = False
    flipped_v: bool = False

    def get_placed_polygon(self) -> Polygon:
        """Get the polygon in its placed position (transformed)."""
        poly = self.piece.polygon
        if self.flipped_h:
            cx = (poly.bounds[0] + poly.bounds[2]) / 2
            poly = sh_affinity.scale(poly, xfact=-1, yfact=1, origin=(cx, 0))
        if self.flipped_v:
            cy = (poly.bounds[1] + poly.bounds[3]) / 2
            poly = sh_affinity.scale(poly, xfact=1, yfact=-1, origin=(0, cy))
        if abs(self.rotation_deg) > 0.01:
            poly = sh_affinity.rotate(poly, self.rotation_deg, origin="centroid")
        return sh_affinity.translate(poly, xoff=self.x_offset, yoff=self.y_offset)


# ── Anisotropic offset (X-only margin) ──────────────────────────────────────

def anisotropic_x_offset(polygon: Polygon, offset_mm: float) -> Polygon:
    """
    Apply margin ONLY along X axis, preserving Y (circumference) exactly.

    Algorithm:
    1. Buffer the polygon isotropically (expands all directions)
    2. Clip the result to the original Y bounds (removes Y expansion)

    This adds offset_mm to left and right sides in X while keeping
    the exact Y height of the polygon unchanged — critical because
    Y represents the tube circumference and must not be altered.
    """
    if offset_mm <= 0:
        return polygon

    min_y = polygon.bounds[1]
    max_y = polygon.bounds[3]

    buffered = polygon.buffer(offset_mm, join_style="mitre", mitre_limit=5.0)

    clip = box(-1e9, min_y, 1e9, max_y)
    result = buffered.intersection(clip)

    result = make_valid(result)
    if isinstance(result, MultiPolygon):
        result = max(result.geoms, key=lambda g: g.area)

    return result if isinstance(result, Polygon) else polygon


def compute_total_x_offset(kerf: float, margin: float,
                           bevel_extra: float = 0.0) -> float:
    """Total X offset = kerf/2 + margin + bevel extra."""
    return kerf / 2.0 + margin + bevel_extra


# ── Cylindrical boundary (periodic Y) ───────────────────────────────────────

def cylindrical_copies(
    polygon: Polygon,
    tube_circumference: float,
) -> List[Polygon]:
    """
    Generate the polygon plus its periodic Y-boundary ghosts.

    If the piece is near the top edge (Y → circumference), it wraps
    around and reappears at the bottom (Y ← 0), and vice versa.
    Returns 1–3 polygons: the original + up to 2 ghost copies.
    """
    if tube_circumference <= 0:
        return [polygon]

    copies = [polygon]
    min_y, max_y = polygon.bounds[1], polygon.bounds[3]
    circ = tube_circumference

    if max_y > circ:
        copies.append(sh_affinity.translate(polygon, yoff=-circ))
    elif max_y > circ * 0.0:
        pass

    if min_y < 0:
        copies.append(sh_affinity.translate(polygon, yoff=circ))

    if max_y > circ:
        copies.append(sh_affinity.translate(polygon, yoff=-circ))
    if min_y < 0:
        copies.append(sh_affinity.translate(polygon, yoff=circ))

    return copies


def cylindrical_union(
    placed_polygons: List[Polygon],
    tube_circumference: float,
) -> Polygon:
    """
    Build the union of all placed polygons + their cylindrical ghosts.
    Used as the obstacle geometry for collision checks.
    """
    if not placed_polygons:
        return Polygon()

    all_polys: List[Polygon] = []
    for poly in placed_polygons:
        all_polys.extend(cylindrical_copies(poly, tube_circumference))

    return unary_union(all_polys)


# ── Collision detection ──────────────────────────────────────────────────────

def check_collision(
    piece_poly: Polygon,
    obstacles: Polygon,
    bar_length: float,
    tube_circumference: float,
) -> bool:
    """
    Check if a piece polygon collides with obstacles or exceeds bar bounds.
    Returns True if collision detected (placement invalid).

    Checks:
    1. Piece within bar X bounds [0, bar_length]
    2. Piece within tube Y bounds [0, circumference] — with wrapping
    3. No intersection with obstacle union (including cylindrical ghosts)
    """
    bounds = piece_poly.bounds
    if bounds[0] < -0.01 or bounds[2] > bar_length + 0.01:
        return True

    if tube_circumference > 0:
        copies = cylindrical_copies(piece_poly, tube_circumference)
        for copy in copies:
            if not obstacles.is_empty and obstacles.intersects(copy):
                return True
    else:
        if bounds[1] < -0.01 or bounds[3] > tube_circumference + 0.01 if tube_circumference > 0 else False:
            return True
        if not obstacles.is_empty and obstacles.intersects(piece_poly):
            return True

    return False


def check_collision_fast(
    piece_poly: Polygon,
    prepared_obstacles,
    bar_length: float,
    tube_circumference: float,
) -> bool:
    """
    Fast collision check using Shapely prepared geometry.
    prepared_obstacles should be prep(obstacles_union).
    """
    bounds = piece_poly.bounds
    if bounds[0] < -0.01 or bounds[2] > bar_length + 0.01:
        return True

    if tube_circumference > 0:
        for copy in cylindrical_copies(piece_poly, tube_circumference):
            if prepared_obstacles.intersects(copy):
                return True
    else:
        if prepared_obstacles.intersects(piece_poly):
            return True

    return False


# ── Solid-wall manual drag ───────────────────────────────────────────────────

def solid_wall_move(
    piece_poly: Polygon,
    dx: float,
    dy: float,
    obstacles: Polygon,
    bar_length: float,
    tube_circumference: float,
    resolution: float = 0.5,
) -> Tuple[float, float]:
    """
    Compute the maximum allowed (dx, dy) displacement that doesn't
    cause collision. The piece "slides" along obstacles.

    Strategy: binary search on each axis independently.
    If full displacement collides, halve until we find the max safe distance.
    """
    if obstacles.is_empty and tube_circumference <= 0:
        candidate = sh_affinity.translate(piece_poly, xoff=dx, yoff=dy)
        if candidate.bounds[0] >= 0 and candidate.bounds[2] <= bar_length:
            return dx, dy

    def _can_move(ddx: float, ddy: float) -> bool:
        candidate = sh_affinity.translate(piece_poly, xoff=ddx, yoff=ddy)
        return not check_collision(
            candidate, obstacles, bar_length, tube_circumference
        )

    # Try full displacement first
    if _can_move(dx, dy):
        return dx, dy

    # Binary search on X axis with fixed Y=0
    safe_dx = _binary_search_axis(
        piece_poly, "x", dx, obstacles, bar_length, tube_circumference, resolution
    )

    # Binary search on Y axis with safe X
    moved_x = sh_affinity.translate(piece_poly, xoff=safe_dx)
    safe_dy = _binary_search_axis(
        moved_x, "y", dy, obstacles, bar_length, tube_circumference, resolution
    )

    return safe_dx, safe_dy


def _binary_search_axis(
    piece_poly: Polygon,
    axis: str,
    target: float,
    obstacles: Polygon,
    bar_length: float,
    tube_circumference: float,
    resolution: float,
) -> float:
    """Binary search for max safe displacement along one axis."""
    if abs(target) < resolution:
        return 0.0

    sign = 1.0 if target > 0 else -1.0
    lo, hi = 0.0, abs(target)

    for _ in range(20):
        if hi - lo < resolution:
            break
        mid = (lo + hi) / 2.0
        ddx = sign * mid if axis == "x" else 0.0
        ddy = sign * mid if axis == "y" else 0.0
        candidate = sh_affinity.translate(piece_poly, xoff=ddx, yoff=ddy)
        if not check_collision(candidate, obstacles, bar_length, tube_circumference):
            lo = mid
        else:
            hi = mid

    return sign * lo


@dataclass
class NestResult:
    """Result of an auto-nest operation."""
    placements: List[PlacedIrregularPiece] = field(default_factory=list)
    bars_used: int = 0
    efficiency: float = 0.0
    total_bar_length: float = 0.0
    total_piece_area: float = 0.0



# ── Utility: normalize polygon to origin ─────────────────────────────────────

def normalize_to_origin(polygon: Polygon) -> Polygon:
    """Translate polygon so its bounding box starts at (0, 0)."""
    bx, by = polygon.bounds[0], polygon.bounds[1]
    return sh_affinity.translate(polygon, xoff=-bx, yoff=-by)


def polygon_from_profile_shapes(shapes: list) -> Optional[Polygon]:
    """
    Convert a list of ProfileShape dicts (from profile_creator) to a Shapely Polygon.
    Takes the union of all material shapes minus void shapes.
    """
    from shapely.ops import unary_union

    material_polys: List[Polygon] = []
    void_polys: List[Polygon] = []

    for shape_dict in shapes:
        stype = shape_dict.get("shape_type", "")
        points = shape_dict.get("points", [])
        is_void = shape_dict.get("is_void", False)

        poly = _shape_dict_to_polygon(stype, points)
        if poly is None or poly.is_empty:
            continue

        if is_void:
            void_polys.append(poly)
        else:
            material_polys.append(poly)

    if not material_polys:
        return None

    result = unary_union(material_polys)
    for vp in void_polys:
        result = result.difference(vp)

    result = make_valid(result)
    if isinstance(result, MultiPolygon):
        result = max(result.geoms, key=lambda g: g.area)

    return result if isinstance(result, Polygon) and not result.is_empty else None


def _shape_dict_to_polygon(shape_type: str, points: list) -> Optional[Polygon]:
    """Convert a single ProfileShape to a Shapely Polygon."""
    if shape_type == "rect" and len(points) >= 2:
        x0, y0 = points[0]
        x1, y1 = points[1]
        return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))

    elif shape_type == "circle" and len(points) >= 2:
        cx, cy = points[0]
        rx = abs(points[1][0] - cx)
        ry = abs(points[1][1] - cy) if len(points[1]) > 1 else rx
        r = max(rx, ry)
        if r < 0.01:
            return None
        return Point(cx, cy).buffer(r, resolution=32)

    elif shape_type in ("polygon", "line") and len(points) >= 3:
        return Polygon(points)

    elif shape_type == "arc" and len(points) >= 3:
        if len(points) >= 4:
            return Polygon(points)
        return None

    return None
