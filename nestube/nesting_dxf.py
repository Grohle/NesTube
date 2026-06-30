"""
nestube/nestube/nestube/nesting_dxf.py
Export the 2D nesting layout to a DXF file.

Each placed piece becomes a closed LWPOLYLINE at its exact scene coordinates
(x_offset along the bar, local section geometry vertically). Each bar is a
separate DXF layer (``BAR_1``, ``BAR_2``, …) plus a ``BAR_OUTLINE`` rectangle,
so the consumer can toggle bars independently.

Coordinates are in millimetres, matching the engine's working units. The
piece polygons already embed kerf/margin offsets (they come straight from the
placement polygons used on screen), so inter-piece spacing and the contour are
preserved as-is.
"""
from __future__ import annotations

from typing import Any, Dict, List

import ezdxf

# DXF y-axis points up, the scene's points down. Flip y so the exported file
# reads naturally in a CAD viewer (bar resting on the x-axis).


def export_nesting_dxf(
    filename: str,
    bars: List[List[Any]],
    bar_lengths: List[float],
    section_height_mm: float,
    *,
    bar_gap_mm: float = 500.0,
) -> None:
    """Write a single nesting to ``filename`` as a DXF document.

    ``bars`` is a list of bars; each bar is a list of placed-piece objects with
    ``corte`` (``.largo``), ``x_offset`` and ``poly_local`` (local ``(x, y)``
    mm vertices). ``section_height_mm`` is the bar's vertical extent.
    """
    export_multi_nesting_dxf(
        filename,
        [{"bars": bars, "bar_lengths": bar_lengths,
          "section_height": section_height_mm}],
        bar_gap_mm=bar_gap_mm,
    )


def export_multi_nesting_dxf(
    filename: str,
    nestings: List[Dict[str, Any]],
    *,
    bar_gap_mm: float = 500.0,
    nesting_gap_mm: float = 1500.0,
) -> None:
    """Write one or more nestings to ``filename`` as a single DXF document.

    Each ``nestings`` entry is a dict with keys ``bars``, ``bar_lengths`` and
    ``section_height``. Nestings are stacked vertically; each gets its own layer
    prefix (``N1_BAR_1``, ``N2_BAR_1``, …) so they can be toggled independently.
    """
    renderable = [n for n in nestings if any(n.get("bars") or [])]
    if not renderable:
        raise ValueError("no data")

    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()
    doc.layers.add("BAR_OUTLINE", color=8)  # grey

    multi = len(renderable) > 1
    cursor_y = 0.0  # top of the next nesting block (we build downward)

    # Pre-compute total height so the first nesting sits at the top.
    def block_height(nst: Dict[str, Any]) -> float:
        used = [b for b in (nst.get("bars") or []) if b]
        sh = nst.get("section_height") or 60.0
        return len(used) * (sh + bar_gap_mm)

    total_h = sum(block_height(n) for n in renderable) + \
        nesting_gap_mm * (len(renderable) - 1)
    top = total_h

    for ni, nst in enumerate(renderable):
        bars = nst.get("bars") or []
        bar_lengths = nst.get("bar_lengths") or []
        sh = nst.get("section_height") or 60.0
        prefix = f"N{ni + 1}_" if multi else ""

        used = [(i, b) for i, b in enumerate(bars) if b]
        block_pitch = sh + bar_gap_mm
        n_bars = len(used)
        block_top = top
        for slot, (bar_idx, bar) in enumerate(used):
            bar_len = bar_lengths[bar_idx] if bar_idx < len(bar_lengths) else max(
                (pp.x_offset + pp.corte.largo for pp in bar), default=0.0)
            base_y = block_top - (slot + 1) * block_pitch + bar_gap_mm
            layer = f"{prefix}BAR_{bar_idx + 1}"
            if layer not in doc.layers:
                doc.layers.add(layer, color=(slot % 6) + 1)

            msp.add_lwpolyline(
                [(0.0, base_y), (bar_len, base_y),
                 (bar_len, base_y + sh), (0.0, base_y + sh)],
                close=True,
                dxfattribs={"layer": "BAR_OUTLINE"},
            )
            for pp in bar:
                poly = pp.poly_local or [
                    (0, 0), (pp.corte.largo, 0),
                    (pp.corte.largo, sh), (0, sh),
                ]
                pts = [(pp.x_offset + px, base_y + py) for (px, py) in poly]
                msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})

        top -= n_bars * block_pitch + nesting_gap_mm

    doc.saveas(filename)
