"""
nestify/nesting_export.py
Reconstruct export-ready nesting data from a stored MaterialContext.

The Nesting tab keeps the *active* nesting live (with computed piece polygons),
but other material sub-tabs only persist a serialised ``nesting_layout``. To
export any nesting (active or not) we rebuild lightweight piece objects that the
PDF/DXF writers can consume: each carries its ``corte`` (for description and
length), ``x_offset`` along the bar, ``color`` and the local 2D ``poly_local``
contour (recomputed from the cut + the context's section height, so bevel
geometry is preserved).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from .bevel_geom import profile_section_height
from .models import Corte, MaterialContext
from .nesting_engine import _build_all_orientations, _build_base_polygon


@dataclass
class ExportPiece:
    corte: Corte
    x_offset: float
    color: str
    poly_local: Optional[List[Tuple[float, float]]] = field(default=None, repr=False)


def _poly_local(corte: Corte, sh: float, fh: bool, fv: bool) -> List[Tuple[float, float]]:
    try:
        base = _build_base_polygon(corte, sh)
        orients = _build_all_orientations(base)
        poly = orients.get((fh, fv), base)
        return list(poly.exterior.coords[:-1])
    except Exception:
        return [(0, 0), (corte.largo, 0), (corte.largo, sh), (0, sh)]


def context_section_height(ctx: MaterialContext) -> float:
    if ctx.nesting_height_override:
        return ctx.nesting_height_override
    h = profile_section_height(ctx.perfil)
    return h if h > 0 else 60.0


def _as_corte(item: Any) -> Corte:
    if isinstance(item, Corte):
        return item
    if isinstance(item, dict):
        return Corte.from_dict(item)
    return Corte()


def build_context_export_data(
    ctx: MaterialContext,
) -> Tuple[List[List[ExportPiece]], List[float], float, str]:
    """Return ``(bars, bar_lengths, section_height, display_name)`` for ``ctx``.

    ``bars`` is a list of bars (each a list of :class:`ExportPiece`) rebuilt from
    the context's serialised ``nesting_layout``.
    """
    sh = context_section_height(ctx)
    cortes = [_as_corte(c) for c in (ctx.cortes or [])]

    def match(desc: str, largo: float) -> Corte:
        for c in cortes:
            if c.descripcion == desc and abs(c.largo - largo) < 1e-6:
                return c
        return Corte(descripcion=desc, largo=largo, cantidad=1)

    bars: List[List[ExportPiece]] = []
    for bar_snap in (ctx.nesting_layout or []):
        bar: List[ExportPiece] = []
        for item in bar_snap:
            if isinstance(item, dict):
                desc = item.get("descripcion", "")
                largo = float(item.get("largo", 0.0))
                x_off = float(item.get("x_offset", 0.0))
                fh = bool(item.get("flipped_h", False))
                fv = bool(item.get("flipped_v", False))
                color = item.get("color", "")
            else:
                (desc, largo, x_off, _rot, fh, fv, color, _bi) = item
            corte = match(desc, largo)
            bar.append(ExportPiece(
                corte=corte, x_offset=x_off, color=color,
                poly_local=_poly_local(corte, sh, fh, fv),
            ))
        bars.append(bar)

    return bars, list(ctx.nesting_bar_lengths or []), sh, ctx.full_name
