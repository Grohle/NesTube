"""
nestube/nestube/nestube/nesting_viz.py
Shared nesting canvas layout: length/width scaling for preview and interactive tab.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .bevel_geom import profile_section_height
from .models import ConfigPerfil


@dataclass
class NestingBarLayout:
    """Pixel layout for one bar row on the nesting canvas."""
    bar_index: int
    label_y: float
    y_top: float
    y_bottom: float
    draw_width_px: float
    px_per_mm: float
    bar_length_mm: float
    bar_height_px: float


@dataclass
class NestingCanvasLayout:
    """Full vertical layout for drawing nesting bars."""
    bars: List[NestingBarLayout]
    ref_length_mm: float
    inner_width_px: float
    margin_px: float
    px_per_mm: float


def compute_nesting_canvas_layout(
    inner_width_px: float,
    bar_lengths_mm: List[float],
    perfil: ConfigPerfil,
    *,
    real_proportions: bool,
    fixed_bar_h_px: float = 36.0,
    label_h_px: float = 18.0,
    bar_gap_px: float = 24.0,
    margin_px: float = 20.0,
    min_bar_h_px: float = 4.0,
    max_bar_h_ratio: float = 0.45,
) -> Optional[NestingCanvasLayout]:
    """Compute bar positions and scales for nesting drawing.

    The longest bar uses the full inner canvas width; shorter bars scale
  proportionally in length. With real_proportions, bar height follows
    profile section size using the same px/mm scale; otherwise height is fixed.
    """
    if inner_width_px < 40:
        return None

    lengths = [max(length, 0.01) for length in bar_lengths_mm] if bar_lengths_mm else [6000.0]
    ref = max(lengths)
    px_per_mm = inner_width_px / ref
    section_h = profile_section_height(perfil)

    bars: List[NestingBarLayout] = []
    y = float(margin_px)
    max_bar_h = inner_width_px * max_bar_h_ratio

    for i, bar_len in enumerate(lengths):
        label_y = y
        y += label_h_px
        draw_w = bar_len * px_per_mm
        if real_proportions and section_h > 0:
            bar_h = section_h * px_per_mm
            bar_h = max(min_bar_h_px, min(bar_h, max_bar_h))
        else:
            bar_h = fixed_bar_h_px
        bars.append(NestingBarLayout(
            bar_index=i,
            label_y=label_y,
            y_top=y,
            y_bottom=y + bar_h,
            draw_width_px=draw_w,
            px_per_mm=px_per_mm,
            bar_length_mm=bar_len,
            bar_height_px=bar_h,
        ))
        y += bar_h + bar_gap_px

    return NestingCanvasLayout(
        bars=bars,
        ref_length_mm=ref,
        inner_width_px=inner_width_px,
        margin_px=margin_px,
        px_per_mm=px_per_mm,
    )


def bar_layout_at_y(layout: NestingCanvasLayout, cy: float) -> Optional[NestingBarLayout]:
    """Return the bar layout row whose vertical band contains cy."""
    for bar in layout.bars:
        if bar.y_top <= cy <= bar.y_bottom:
            return bar
    return None


def nearest_bar_layout(layout: NestingCanvasLayout, cy: float) -> Optional[NestingBarLayout]:
    """Return the bar row closest to cy (for hit-testing)."""
    if not layout.bars:
        return None
    best = layout.bars[0]
    best_dy = abs(cy - (best.y_top + best.y_bottom) / 2)
    for bar in layout.bars[1:]:
        mid = (bar.y_top + bar.y_bottom) / 2
        dy = abs(cy - mid)
        if dy < best_dy:
            best_dy = dy
            best = bar
    return best
