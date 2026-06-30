"""
nestube/nestube/nestube/nesting_engine.py
Unified nesting engine.

Simple mode: pure 1D First-Fit or Best-Fit Decreasing by length.
Advanced mode: NFP (No-Fit Polygon) collision via PyClipper + Bottom-Left Fill.

Piece polygons are trapezoids derived from bevel angles.
Margin: reserved ONLY at bar START and END.
Kerf: gap between adjacent pieces — applied as polygon offset (kerf/2 per piece).
"""
from __future__ import annotations

import logging
import math
import random
import time as _time
from dataclasses import dataclass, field
from threading import Event
from typing import Callable, Dict, List, Optional, Tuple

import pyclipper
from shapely import affinity as sh_affinity
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

from .models import Corte
from .bevel_geom import (
    ORIENTATIONS,
    corte_to_bevel,
    vertices_local,
)

_log = logging.getLogger(__name__)

TOL = 0.01
INF = float("inf")
CLIPPER_SCALE = 1_000_000


# ── Parameters ───────────────────────────────────────────────────────────────

STRATEGIES = [
    "length",      # Longest Piece First
    "nfp_compact", # NFP Fitting — maximize end-to-end compaction
    "remnants",    # Remnant Priority — consolidate waste to bar end
    "symmetry",    # Pattern Matching — pair symmetric pieces
    "min_length",  # Minimize Total Length (irregular strip packing)
]

@dataclass
class NestingParams:
    bar_length: float
    profile_height: float
    kerf: float
    margin: float
    common_cut: bool = False
    priority: str = "length"


# ── Piece representation ─────────────────────────────────────────────────────

@dataclass
class NestingPiece:
    piece_id: int
    corte: Corte
    quantity: int
    color: str
    base_polygon: Polygon = field(default_factory=Polygon)
    polygons: Dict[Tuple[bool, bool], Polygon] = field(default_factory=dict)
    virtual_polygons: Dict[Tuple[bool, bool], Polygon] = field(default_factory=dict)
    orientations: List[Tuple[bool, bool]] = field(default_factory=list)

    def polygon_for(self, fh: bool, fv: bool) -> Polygon:
        return self.polygons.get((fh, fv), self.base_polygon)

    def virtual_for(self, fh: bool, fv: bool) -> Polygon:
        return self.virtual_polygons.get((fh, fv), self.polygon_for(fh, fv))


@dataclass
class PlacedPiece:
    piece: NestingPiece
    bar_index: int
    x_offset: float
    y_offset: float = 0.0
    flipped_h: bool = False
    flipped_v: bool = False
    color: str = ""

    def get_polygon(self) -> Polygon:
        base = self.piece.polygon_for(self.flipped_h, self.flipped_v)
        return sh_affinity.translate(base, self.x_offset, self.y_offset)

    def local_polygon_coords(self) -> List[Tuple[float, float]]:
        """Polygon vertices in local coords (relative to piece origin, no offset)."""
        poly = self.piece.polygon_for(self.flipped_h, self.flipped_v)
        return list(poly.exterior.coords[:-1])

    @property
    def corte(self) -> Corte:
        return self.piece.corte


@dataclass
class NestingResult:
    placed: List[PlacedPiece] = field(default_factory=list)
    bars_used: int = 0
    efficiency: float = 0.0
    total_placed: int = 0
    total_pieces: int = 0


# ── Polygon builder (rotation-safe) ─────────────────────────────────────────

def _normalize_to_origin(poly: Polygon) -> Polygon:
    bx, by = poly.bounds[0], poly.bounds[1]
    if abs(bx) < 0.001 and abs(by) < 0.001:
        return poly
    return sh_affinity.translate(poly, -bx, -by)


def _build_base_polygon(corte: Corte, profile_h: float) -> Polygon:
    L = corte.largo
    H = profile_h
    if H <= 0 or L <= 0:
        return box(0, 0, max(L, 0.1), max(H, 0.1))
    piece = corte_to_bevel(corte, flipped_h=False, flipped_v=False)
    bl, br, tr, tl = vertices_local(piece, H)
    try:
        poly = Polygon([bl, br, tr, tl])
        if not poly.is_valid:
            poly = poly.buffer(0)
            if hasattr(poly, "geoms"):
                poly = max(poly.geoms, key=lambda g: g.area)
        if poly.is_empty or poly.area < TOL:
            return box(0, 0, L, H)
        return _normalize_to_origin(poly)
    except Exception:
        return box(0, 0, L, H)


def _flip_h(poly: Polygon) -> Polygon:
    max_x = poly.bounds[2]
    coords = [(max_x - x, y) for x, y in poly.exterior.coords]
    result = Polygon(coords)
    if not result.is_valid:
        result = result.buffer(0)
    return _normalize_to_origin(result)


def _flip_v(poly: Polygon) -> Polygon:
    max_y = poly.bounds[3]
    coords = [(x, max_y - y) for x, y in poly.exterior.coords]
    result = Polygon(coords)
    if not result.is_valid:
        result = result.buffer(0)
    return _normalize_to_origin(result)


def _build_all_orientations(base: Polygon) -> Dict[Tuple[bool, bool], Polygon]:
    return {
        (False, False): base,
        (True, False): _flip_h(base),
        (False, True): _flip_v(base),
        (True, True): _flip_h(_flip_v(base)),
    }


def _poly_fingerprint(poly: Polygon) -> tuple:
    coords = list(poly.exterior.coords[:-1])
    return tuple((round(x, 2), round(y, 2)) for x, y in coords)


# ── PyClipper offset ─────────────────────────────────────────────────────────

def _offset_polygon(polygon: Polygon, distance: float) -> Polygon:
    if distance <= 0:
        return polygon
    pco = pyclipper.PyclipperOffset()
    coords = pyclipper.scale_to_clipper(
        list(polygon.exterior.coords[:-1]), CLIPPER_SCALE
    )
    pco.AddPath(coords, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)
    result = pco.Execute(int(distance * CLIPPER_SCALE))
    if not result:
        return polygon
    outer = pyclipper.scale_from_clipper(result[0], CLIPPER_SCALE)
    if len(outer) < 3:
        return polygon
    p = Polygon(outer)
    if not p.is_valid:
        p = p.buffer(0)
    return p


def _offset_polygon_x_only(polygon: Polygon, distance: float) -> Polygon:
    """Inflate polygon only in X, preserving exact Y bounds. For tube nesting
    where kerf applies between pieces along the bar, not vertically."""
    if distance <= 0:
        return polygon
    min_y, max_y = polygon.bounds[1], polygon.bounds[3]
    buffered = _offset_polygon(polygon, distance)
    clip = box(-1e9, min_y, 1e9, max_y)
    result = buffered.intersection(clip)
    if not result.is_valid:
        result = result.buffer(0)
    if hasattr(result, "geoms"):
        result = max(result.geoms, key=lambda g: g.area)
    return result if isinstance(result, Polygon) and not result.is_empty else polygon


# ── NFP / IFP via PyClipper Minkowski Sum ────────────────────────────────────

def _compute_nfp(poly_a: Polygon, poly_b: Polygon) -> List[Polygon]:
    a_coords = pyclipper.scale_to_clipper(
        list(poly_a.exterior.coords[:-1]), CLIPPER_SCALE
    )
    b_coords = pyclipper.scale_to_clipper(
        list(poly_b.exterior.coords[:-1]), CLIPPER_SCALE
    )
    b_inv = [(-x, -y) for x, y in b_coords]
    try:
        nfp_raw = pyclipper.MinkowskiSum(a_coords, b_inv, True)
    except Exception:
        return []
    nfp_clean = pyclipper.SimplifyPolygons(nfp_raw)
    nfp_clean = pyclipper.CleanPolygons(nfp_clean)
    result = []
    for path in nfp_clean:
        desc = pyclipper.scale_from_clipper(path, CLIPPER_SCALE)
        if len(desc) >= 3:
            p = Polygon(desc)
            if not p.is_valid:
                p = p.buffer(0)
            if not p.is_empty:
                result.append(p)
    return result


def _compute_ifp(stock: Polygon, piece_virtual: Polygon) -> Polygon:
    """IFP for rectangular stock: valid ref-point positions so piece fits inside."""
    sb = stock.bounds
    pb = piece_virtual.bounds
    min_x = sb[0] - pb[0]
    max_x = sb[2] - pb[2]
    min_y = sb[1] - pb[1]
    max_y = sb[3] - pb[3]
    if max_y - min_y < 0.1:
        mid = (min_y + max_y) / 2.0
        min_y = mid - 0.05
        max_y = mid + 0.05
    if min_x > max_x or min_y > max_y:
        return Polygon()
    return box(min_x, min_y, max_x, max_y)


def _compute_viable_space(
    stock: Polygon,
    placed_virtual: List[Polygon],
    piece_virtual: Polygon,
) -> Polygon:
    ifp = _compute_ifp(stock, piece_virtual)
    if ifp.is_empty:
        return Polygon()
    if not placed_virtual:
        return ifp
    forbidden = []
    for pv in placed_virtual:
        nfps = _compute_nfp(pv, piece_virtual)
        forbidden.extend(nfps)
    if not forbidden:
        return ifp
    forbidden_union = unary_union(forbidden)
    viable = ifp.difference(forbidden_union)
    if not viable.is_valid:
        viable = viable.buffer(0)
    return viable


# ── Bottom-Left Fill ─────────────────────────────────────────────────────────

def _bottom_left_fill(viable_space) -> Optional[Tuple[float, float]]:
    if viable_space.is_empty:
        return None
    eps = 1e-3
    best_cost = INF
    best_pos = None
    candidates = []
    if viable_space.geom_type == "Polygon":
        candidates.extend(viable_space.exterior.coords[:-1])
        for interior in viable_space.interiors:
            candidates.extend(interior.coords[:-1])
    elif viable_space.geom_type == "MultiPolygon":
        for geom in viable_space.geoms:
            candidates.extend(geom.exterior.coords[:-1])
            for interior in geom.interiors:
                candidates.extend(interior.coords[:-1])
    elif viable_space.geom_type == "GeometryCollection":
        for geom in viable_space.geoms:
            if hasattr(geom, "exterior"):
                candidates.extend(geom.exterior.coords[:-1])

    for x, y in candidates:
        pt = Point(x, y)
        if viable_space.contains(pt) or viable_space.boundary.distance(pt) < 0.1:
            cost = x + eps * y
            if cost < best_cost:
                best_cost = cost
                best_pos = (x, y)
    return best_pos


# ── Piece builder ────────────────────────────────────────────────────────────

def build_nesting_piece(
    corte: Corte,
    piece_id: int,
    profile_h: float,
    color: str,
    kerf: float = 0.0,
) -> NestingPiece:
    base = _build_base_polygon(corte, profile_h)
    all_polys = _build_all_orientations(base)

    d = kerf / 2.0
    virtual = {}
    for orient, poly in all_polys.items():
        virtual[orient] = _offset_polygon_x_only(poly, d) if d > 0 else poly

    seen: List[tuple] = []
    unique: List[Tuple[bool, bool]] = []
    for orient, poly in all_polys.items():
        fp = _poly_fingerprint(poly)
        if fp not in seen:
            seen.append(fp)
            unique.append(orient)

    return NestingPiece(
        piece_id=piece_id,
        corte=corte,
        quantity=corte.cantidad,
        color=color,
        base_polygon=base,
        polygons=all_polys,
        virtual_polygons=virtual,
        orientations=unique,
    )


# ── Score ────────────────────────────────────────────────────────────────────

def _bar_extents(result: NestingResult) -> List[float]:
    """Per-bar occupied length (rightmost piece end ≈ x_offset + nominal largo)."""
    ends: dict = {}
    for pp in result.placed:
        end = pp.x_offset + pp.piece.corte.largo
        if end > ends.get(pp.bar_index, 0.0):
            ends[pp.bar_index] = end
    return list(ends.values())


def _score(result: NestingResult, params: NestingParams) -> Tuple[int, float]:
    """Quality score (lower is better) — the *secondary* term depends on the
    chosen strategy so each priority optimises a genuinely different goal while
    they all keep ``bars_used`` as the primary (fewest bars wins first).

    - length / min_length / default → minimise total waste (historical behaviour).
    - remnants  → maximise the single largest offcut (consolidate the leftover
      into one reusable remnant) ⇒ minimise its negative.
    - nfp_compact → minimise the summed per-bar extent (pack as tight/left as
      possible).
    - symmetry → minimise the spread of per-bar fill (balance the bars).
    """
    used = sum(pp.piece.corte.largo for pp in result.placed)
    waste = result.bars_used * params.bar_length - used
    pr = params.priority
    if pr == "remnants":
        extents = _bar_extents(result)
        largest_remnant = max((params.bar_length - e for e in extents), default=0.0)
        secondary = -largest_remnant
    elif pr == "nfp_compact":
        secondary = sum(_bar_extents(result))
    elif pr == "symmetry":
        extents = _bar_extents(result)
        if extents:
            mean = sum(extents) / len(extents)
            secondary = sum((e - mean) ** 2 for e in extents) / len(extents)
        else:
            secondary = 0.0
    else:  # length / min_length / default — unchanged
        secondary = waste
    return (result.bars_used, secondary)


# ── Simple nesting (1D) ─────────────────────────────────────────────────────

def nest_simple(
    pieces: List[NestingPiece],
    params: NestingParams,
) -> NestingResult:
    units: List[NestingPiece] = []
    for p in pieces:
        for _ in range(max(1, p.quantity)):
            units.append(p)
    units.sort(key=lambda p: p.corte.largo, reverse=True)

    bars: List[List[PlacedPiece]] = []
    cursors: List[float] = []
    placed: List[PlacedPiece] = []
    usable_end = params.bar_length - params.margin

    for piece in units:
        length = piece.corte.largo
        if length <= 0:
            continue
        gap = 0.0 if params.common_cut else params.kerf
        found = False

        use_bestfit = params.priority in ("remnants", "nfp_compact", "min_length")
        if use_bestfit and bars:
            bar_order = sorted(range(len(bars)), key=lambda i: usable_end - cursors[i])
            for i in bar_order:
                if cursors[i] + length <= usable_end:
                    pp = PlacedPiece(piece=piece, bar_index=i, x_offset=cursors[i], color=piece.color)
                    bars[i].append(pp)
                    placed.append(pp)
                    cursors[i] += length + gap
                    found = True
                    break
        else:
            for i in range(len(bars)):
                if cursors[i] + length <= usable_end:
                    pp = PlacedPiece(piece=piece, bar_index=i, x_offset=cursors[i], color=piece.color)
                    bars[i].append(pp)
                    placed.append(pp)
                    cursors[i] += length + gap
                    found = True
                    break

        if not found:
            i = len(bars)
            bars.append([])
            cursors.append(params.margin)
            pp = PlacedPiece(piece=piece, bar_index=i, x_offset=params.margin, color=piece.color)
            bars[i].append(pp)
            placed.append(pp)
            cursors[i] += length + gap

    bars_used = len([b for b in bars if b])
    used_length = sum(pp.piece.corte.largo for pp in placed)
    total_bar = bars_used * params.bar_length
    return NestingResult(
        placed=placed,
        bars_used=bars_used,
        efficiency=used_length / total_bar if total_bar > 0 else 0.0,
        total_placed=len(placed),
        total_pieces=sum(p.quantity for p in pieces),
    )


# ── Advanced nesting (NFP + BLF) ────────────────────────────────────────────

def _remaining_length(bar_placed: List[PlacedPiece], params: NestingParams) -> float:
    if not bar_placed:
        return params.bar_length
    max_x = max(pp.get_polygon().bounds[2] for pp in bar_placed)
    return params.bar_length - max_x


def _nest_advanced_greedy_pass(
    units: List[NestingPiece],
    params: NestingParams,
    stop_event: Optional[Event] = None,
) -> NestingResult:
    bars: List[List[PlacedPiece]] = []
    bars_virtual: List[List[Polygon]] = []
    all_placed: List[PlacedPiece] = []

    stock = box(params.margin, 0, params.bar_length - params.margin, params.profile_height)

    for piece in units:
        if stop_event and stop_event.is_set():
            break

        bar_indices = list(range(len(bars)))
        if params.priority in ("remnants", "min_length") and bar_indices:
            bar_indices.sort(key=lambda i: _remaining_length(bars[i], params))
        bar_indices.append(len(bars))

        best_pos: Optional[Tuple[float, float]] = None
        best_orient = (False, False)
        best_bar = -1
        best_cost = INF

        for bar_idx in bar_indices:
            if bar_idx == len(bars):
                placed_v = []
            else:
                placed_v = bars_virtual[bar_idx]

            for fh, fv in piece.orientations:
                pv = piece.virtual_for(fh, fv)
                viable = _compute_viable_space(stock, placed_v, pv)
                pos = _bottom_left_fill(viable)
                if pos is not None:
                    cost = pos[0] + 1e-3 * pos[1]
                    if cost < best_cost:
                        best_cost = cost
                        best_pos = pos
                        best_orient = (fh, fv)
                        best_bar = bar_idx

            if best_pos is not None and best_bar == bar_idx:
                break

        if best_pos is not None:
            while len(bars) <= best_bar:
                bars.append([])
                bars_virtual.append([])

            fh, fv = best_orient
            pp = PlacedPiece(
                piece=piece,
                bar_index=best_bar,
                x_offset=best_pos[0],
                y_offset=best_pos[1],
                flipped_h=fh,
                flipped_v=fv,
                color=piece.color,
            )
            bars[best_bar].append(pp)
            all_placed.append(pp)
            placed_poly = sh_affinity.translate(
                piece.virtual_for(fh, fv), best_pos[0], best_pos[1]
            )
            bars_virtual[best_bar].append(placed_poly)

    bars_used = len([b for b in bars if b])
    used = sum(pp.piece.corte.largo for pp in all_placed)
    total_bar = bars_used * params.bar_length
    return NestingResult(
        placed=all_placed,
        bars_used=bars_used,
        efficiency=used / total_bar if total_bar > 0 else 0.0,
        total_placed=len(all_placed),
        total_pieces=sum(p.quantity for p in units),
    )


# ── Ordering strategies ─────────────────────────────────────────────────────

def _order_by_length(units: List[NestingPiece]) -> List[NestingPiece]:
    return sorted(units, key=lambda p: p.corte.largo, reverse=True)


def _order_by_area(units: List[NestingPiece]) -> List[NestingPiece]:
    return sorted(units, key=lambda p: p.base_polygon.area, reverse=True)


def _order_by_perimeter(units: List[NestingPiece]) -> List[NestingPiece]:
    return sorted(units, key=lambda p: p.base_polygon.length, reverse=True)


def _order_symmetry_pairs(units: List[NestingPiece]) -> List[NestingPiece]:
    """Pair pieces with complementary bevels so flipped copies sit together,
    forming near-rectangular blocks that pack tightly."""
    used = [False] * len(units)
    result: List[NestingPiece] = []

    def _bevel_sig(p: NestingPiece) -> tuple:
        c = p.corte
        return (c.inglete1, c.inglete1_dir, c.inglete1_deg,
                c.inglete2, c.inglete2_dir, c.inglete2_deg)

    def _complement(sig: tuple) -> tuple:
        i1, d1, g1, i2, d2, g2 = sig
        flip_d = lambda d: "down" if d == "up" else "up"
        return (i2, flip_d(d2) if i2 else d2, g2,
                i1, flip_d(d1) if i1 else d1, g1)

    indexed = sorted(enumerate(units), key=lambda x: x[1].corte.largo, reverse=True)
    for idx, p in indexed:
        if used[idx]:
            continue
        used[idx] = True
        result.append(p)
        sig = _bevel_sig(p)
        comp = _complement(sig)
        for idx2, p2 in indexed:
            if used[idx2]:
                continue
            if _bevel_sig(p2) == comp and abs(p2.corte.largo - p.corte.largo) < 1.0:
                used[idx2] = True
                result.append(p2)
                break
    return result


def _shuffled(units: List[NestingPiece], seed: int) -> List[NestingPiece]:
    result = list(units)
    random.Random(seed).shuffle(result)
    return result


def _get_strategy_orderings(strategy: str) -> List[Callable]:
    """Return a list of deterministic ordering functions for the given strategy."""
    if strategy == "remnants":
        return [_order_by_length, _order_by_area]
    if strategy == "symmetry":
        return [_order_symmetry_pairs, _order_by_length, _order_by_area]
    if strategy == "nfp_compact":
        return [_order_by_area, _order_by_perimeter, _order_by_length]
    if strategy == "min_length":
        return [_order_by_length, _order_by_area, _order_by_perimeter]
    return [_order_by_length, _order_by_area, _order_by_perimeter]


# ── Timed auto-nest ──────────────────────────────────────────────────────────

def nest_advanced_timed(
    pieces: List[NestingPiece],
    params: NestingParams,
    *,
    time_limit_sec: Optional[float] = None,
    stop_event: Optional[Event] = None,
    progress_cb: Optional[Callable[[NestingResult], None]] = None,
) -> NestingResult:
    if stop_event is None:
        stop_event = Event()

    units: List[NestingPiece] = []
    for p in pieces:
        for _ in range(max(1, p.quantity)):
            units.append(p)
    if not units:
        return NestingResult()

    unlimited = time_limit_sec is None or time_limit_sec <= 0
    deadline = None if unlimited else _time.monotonic() + float(time_limit_sec)

    best: Optional[NestingResult] = None
    best_score = (INF, INF)
    best_order: Optional[List[NestingPiece]] = None

    orderings = _get_strategy_orderings(params.priority)

    # After the deterministic orderings, the loop runs an ITERATED LOCAL SEARCH:
    # it perturbs the best-known ordering (swap / segment-reverse / move / restart)
    # and keeps any improvement. This actually uses the optimisation-time budget —
    # more time finds tighter packings — where the old pure-random shuffle almost
    # never beat the sorted seed, so longer times appeared to "do nothing".
    no_improve = 0
    # Scale the patience with the available time: a longer user-selected budget
    # should keep searching, not bail out early after a fixed plateau.
    base_patience = max(200, 60 * len(orderings))
    no_improve_limit = base_patience if not unlimited else base_patience * 4

    def _perturb(order: List[NestingPiece], it: int) -> List[NestingPiece]:
        rng = random.Random((it * 2654435761) & 0xFFFFFFFF)
        out = list(order)
        n = len(out)
        if n < 2:
            return out
        kind = it % 4
        if kind == 0:                                   # swap two units
            i, j = rng.randrange(n), rng.randrange(n)
            out[i], out[j] = out[j], out[i]
        elif kind == 1:                                 # reverse a segment
            i, j = sorted((rng.randrange(n), rng.randrange(n)))
            out[i:j + 1] = out[i:j + 1][::-1]
        elif kind == 2:                                 # relocate one unit
            x = out.pop(rng.randrange(n))
            out.insert(rng.randrange(n + 1), x)
        else:                                           # occasional full restart
            rng.shuffle(out)
        return out

    iteration = 0
    while not stop_event.is_set():
        if not unlimited and _time.monotonic() >= deadline:
            break
        if iteration < len(orderings):
            ordered = orderings[iteration](list(units))
        elif best_order is not None:
            ordered = _perturb(best_order, iteration)
        else:
            ordered = _shuffled(list(units), seed=iteration)

        result = _nest_advanced_greedy_pass(ordered, params, stop_event)
        sc = _score(result, params)
        if best is None or sc < best_score:
            best_score = sc
            best = result
            best_order = ordered
            no_improve = 0
            if progress_cb:
                progress_cb(best)
        else:
            no_improve += 1

        iteration += 1
        # Only allow the early stop once every strategy ordering has been tried.
        if iteration > len(orderings) and no_improve >= no_improve_limit:
            break
        if not unlimited and _time.monotonic() >= deadline:
            break

    return best if best is not None else NestingResult()


# ── Obstacle builder for interactive drag ────────────────────────────────────

def build_obstacle_for_bar(
    placed_on_bar: List[PlacedPiece],
    exclude: Optional[PlacedPiece] = None,
) -> Polygon:
    polys = []
    for pp in placed_on_bar:
        if pp is exclude:
            continue
        polys.append(pp.get_polygon())
    if not polys:
        return Polygon()
    return unary_union(polys)


# ── Legacy compatibility ─────────────────────────────────────────────────────

def legacy_layout_to_result(
    layout: list,
    pieces: List[NestingPiece],
    bar_length: float,
) -> NestingResult:
    piece_map = {id(p.corte): p for p in pieces}
    placed = []
    bars_used = 0
    for bar_idx, bar_data in enumerate(layout):
        if bar_data:
            bars_used += 1
        for x_mm, corte, fh, fv in bar_data:
            np_ = piece_map.get(id(corte))
            if np_ is None:
                continue
            pp = PlacedPiece(
                piece=np_, bar_index=bar_idx, x_offset=x_mm,
                flipped_h=fh, flipped_v=fv, color=np_.color,
            )
            placed.append(pp)
    used = sum(pp.piece.corte.largo for pp in placed)
    total = bars_used * bar_length
    return NestingResult(
        placed=placed, bars_used=bars_used,
        efficiency=used / total if total > 0 else 0.0,
        total_placed=len(placed),
        total_pieces=sum(p.quantity for p in pieces),
    )
