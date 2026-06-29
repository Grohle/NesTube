"""
nestify/nesting_pdf.py
Render the 2D nesting layout to a PDF report.

Structure (per §3.2 of the roadmap):
  1. Header — job fields (name, order, offer, client) + date.
  2. Per bar — a scaled drawing of the bar with each placed piece in its exact
     position/orientation, colour-filled; below it a legend (swatch + cut
     description) for the pieces present in that bar.
  3. Piece table — name, profile, length, qty and a uniform-scale silhouette
     thumbnail of each distinct cut.

The drawing uses a readable fixed bar height (the on-screen "simple" mode):
horizontal scale follows length, the section height is mapped to the fixed bar
height so pieces stay visible. Geometry (which bar, x position, orientation)
is faithful; only the vertical proportion is normalised for legibility.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Sequence, Tuple

from fpdf import FPDF

from .export_utils import _register_pdf_fonts, _write_pdf_header, set_pdf_font
from .i18n import t
from .models import AppState

# A4 landscape gives long thin bars more room.
_PAGE_W = 297.0
_PAGE_H = 210.0
_MARGIN = 12.0
_DRAW_W = _PAGE_W - 2 * _MARGIN

_BAR_H = 16.0          # fixed visible bar height (mm on page)
_BAR_LABEL_H = 6.0     # space above each bar for its caption
_LEGEND_ROW_H = 5.0    # height of one legend entry
_LEGEND_SWATCH = 4.0   # legend colour swatch side
_BAR_BLOCK_GAP = 8.0   # gap between one bar block and the next


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = (hex_color or "#888888").lstrip("#")
    if len(h) != 6:
        h = "888888"
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _piece_bounds(poly: Sequence[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def export_nesting_pdf(
    filename: str,
    bars: List[List[Any]],
    bar_lengths: List[float],
    section_height_mm: float,
    state: AppState,
    *,
    profile_name: str = "",
) -> None:
    """Write a single-nesting report to ``filename`` (see module docstring)."""
    export_multi_nesting_pdf(
        filename,
        [{
            "name": profile_name,
            "bars": bars,
            "bar_lengths": bar_lengths,
            "section_height": section_height_mm,
            "profile_name": profile_name,
        }],
        state,
    )


def export_multi_nesting_pdf(
    filename: str,
    nestings: List[Dict[str, Any]],
    state: AppState,
) -> None:
    """Write a report covering one or more nestings to ``filename``.

    Each ``nestings`` entry is a dict with keys ``name``, ``bars``,
    ``bar_lengths``, ``section_height`` and ``profile_name``. Bars are lists of
    placed-piece objects with attributes ``corte`` (``.descripcion``,
    ``.largo``), ``x_offset``, ``color`` and ``poly_local``.
    """
    renderable = [n for n in nestings if any(n.get("bars") or [])]
    if not renderable:
        raise ValueError(t("no_data"))

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    _register_pdf_fonts(pdf)
    pdf.set_auto_page_break(False)
    pdf.add_page()

    _write_pdf_header(pdf, state)
    set_pdf_font(pdf, "", 8)
    today = datetime.date.today().isoformat()
    pdf.set_xy(_MARGIN, pdf.get_y())
    pdf.cell(0, 5, f"{t('date')}: {today}", 0, 1)

    y = pdf.get_y() + 2
    multi = len(renderable) > 1
    all_bars: List[List[Any]] = []

    for ni, nst in enumerate(renderable):
        bars = nst.get("bars") or []
        bar_lengths = nst.get("bar_lengths") or []
        sh_in = nst.get("section_height") or 60.0
        name = nst.get("name") or nst.get("profile_name") or ""
        all_bars.extend(b for b in bars if b)

        if multi:
            if ni > 0:
                y += 2
            if y + 12 > _PAGE_H - _MARGIN:
                pdf.add_page()
                y = _MARGIN
            set_pdf_font(pdf, "B", 11)
            pdf.set_text_color(0, 0, 0)
            pdf.set_xy(_MARGIN, y)
            pdf.cell(0, 7, name or f"Nesting {ni + 1}", 0, 1)
            y = pdf.get_y() + 1

        y = _render_nesting_bars(pdf, bars, bar_lengths, sh_in, y)

    # One combined piece table at the end across all rendered nestings.
    profile_name = renderable[0].get("profile_name", "") if not multi else ""
    _write_piece_table(pdf, all_bars,
                       renderable[0].get("section_height", 60.0) or 60.0,
                       profile_name)

    pdf.output(filename)


def _render_nesting_bars(pdf: FPDF, bars: List[List[Any]],
                         bar_lengths: List[float], section_height_mm: float,
                         y: float) -> float:
    """Draw all non-empty bars of one nesting starting at ``y``; return new y."""
    used_bars = [(i, b) for i, b in enumerate(bars) if b]
    if not used_bars:
        return y

    sh = section_height_mm if section_height_mm > 0 else 60.0
    ref_len = max((bar_lengths[i] if i < len(bar_lengths) else 6000.0)
                  for i, _ in used_bars)
    ref_len = max(ref_len, 1.0)
    px_per_mm = _DRAW_W / ref_len

    for bar_idx, bar in used_bars:
        bar_len = bar_lengths[bar_idx] if bar_idx < len(bar_lengths) else ref_len
        draw_w = bar_len * px_per_mm

        # Pieces present in this bar (for the legend), keyed by description+length.
        legend: Dict[Tuple[str, float], Dict[str, Any]] = {}
        for pp in bar:
            key = (pp.corte.descripcion, round(pp.corte.largo, 2))
            entry = legend.setdefault(key, {"color": pp.color, "qty": 0,
                                            "corte": pp.corte})
            entry["qty"] += 1
        legend_rows = len(legend)

        block_h = (_BAR_LABEL_H + _BAR_H + 2 +
                   legend_rows * _LEGEND_ROW_H + _BAR_BLOCK_GAP)
        if y + block_h > _PAGE_H - _MARGIN:
            pdf.add_page()
            y = _MARGIN

        # ── Bar caption ──────────────────────────────────────────────────────
        used_mm = sum(pp.corte.largo for pp in bar)
        usage = (used_mm / bar_len * 100.0) if bar_len > 0 else 0.0
        retal = max(0.0, bar_len - used_mm)
        set_pdf_font(pdf, "B", 9)
        pdf.set_xy(_MARGIN, y)
        pdf.cell(0, _BAR_LABEL_H, t("pdf_bar_info",
                                    n=str(bar_idx + 1),
                                    pieces=str(len(bar)),
                                    retal=f"{retal:.1f}",
                                    usage=f"{usage:.1f}"), 0, 1)
        bar_top = y + _BAR_LABEL_H

        # ── Bar outline ──────────────────────────────────────────────────────
        pdf.set_draw_color(120, 120, 124)
        pdf.set_line_width(0.3)
        pdf.rect(_MARGIN, bar_top, draw_w, _BAR_H, "D")

        # ── Placed pieces ────────────────────────────────────────────────────
        pdf.set_line_width(0.2)
        for pp in bar:
            poly = pp.poly_local or [(0, 0), (pp.corte.largo, 0),
                                     (pp.corte.largo, sh), (0, sh)]
            r, g, b = _hex_to_rgb(pp.color)
            pdf.set_fill_color(r, g, b)
            pdf.set_draw_color(60, 60, 64)
            pts = [
                (_MARGIN + (pp.x_offset + px) * px_per_mm,
                 bar_top + (py / sh) * _BAR_H)
                for (px, py) in poly
            ]
            try:
                pdf.polygon(pts, style="DF")
            except Exception:
                # Degenerate polygon — fall back to a filled rect spanning it.
                x0 = _MARGIN + pp.x_offset * px_per_mm
                pdf.rect(x0, bar_top, max(0.4, pp.corte.largo * px_per_mm),
                         _BAR_H, "DF")

            # Label inside the piece only if the text width fits.
            label = pp.corte.descripcion or f"{pp.corte.largo:.0f}"
            set_pdf_font(pdf, "", 6)
            piece_w = pp.corte.largo * px_per_mm
            if pdf.get_string_width(label) + 1.5 < piece_w:
                tr, tg, tb = _text_rgb_for_bg(r, g, b)
                pdf.set_text_color(tr, tg, tb)
                pdf.set_xy(_MARGIN + pp.x_offset * px_per_mm, bar_top + _BAR_H / 2 - 2)
                pdf.cell(piece_w, 4, label, 0, 0, "C")
                pdf.set_text_color(0, 0, 0)

        # ── Remnant hatch ────────────────────────────────────────────────────
        if retal > 0.5:
            rx = _MARGIN + (bar_len - retal) * px_per_mm
            rw = retal * px_per_mm
            pdf.set_draw_color(160, 160, 165)
            pdf.set_line_width(0.2)
            pdf.rect(rx, bar_top, rw, _BAR_H, "D")
            _hatch(pdf, rx, bar_top, rw, _BAR_H)

        # ── Legend under the bar ─────────────────────────────────────────────
        ly = bar_top + _BAR_H + 2
        set_pdf_font(pdf, "", 7)
        for (desc, largo), entry in sorted(legend.items(),
                                           key=lambda kv: -kv[1]["qty"]):
            r, g, b = _hex_to_rgb(entry["color"])
            pdf.set_fill_color(r, g, b)
            pdf.set_draw_color(90, 90, 94)
            pdf.set_line_width(0.2)
            pdf.rect(_MARGIN, ly + 0.3, _LEGEND_SWATCH, _LEGEND_SWATCH, "DF")
            pdf.set_text_color(0, 0, 0)
            pdf.set_xy(_MARGIN + _LEGEND_SWATCH + 2, ly)
            name = desc or t("pieces")
            pdf.cell(0, _LEGEND_ROW_H,
                     f"{name}   {largo:.1f} mm   x{entry['qty']}", 0, 1)
            ly += _LEGEND_ROW_H

        y = ly + _BAR_BLOCK_GAP

    return y


def _text_rgb_for_bg(r: int, g: int, b: int) -> Tuple[int, int, int]:
    """Pick black or white text for best contrast (WCAG relative luminance)."""
    def lin(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    lum = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return (0, 0, 0) if lum > 0.179 else (255, 255, 255)


def _hatch(pdf: FPDF, x: float, y: float, w: float, h: float,
           spacing: float = 2.0) -> None:
    pdf.set_draw_color(180, 180, 185)
    pdf.set_line_width(0.15)
    total = w + h
    offset = spacing
    while offset < total:
        lx0 = x + min(offset, w)
        ly0 = y + max(0.0, offset - w)
        lx1 = x + max(0.0, offset - h)
        ly1 = y + min(offset, h)
        pdf.line(lx0, ly0, lx1, ly1)
        offset += spacing


def _write_piece_table(pdf: FPDF, bars: List[List[Any]],
                       section_height_mm: float, profile_name: str) -> None:
    # Aggregate distinct cuts across all bars.
    agg: Dict[Tuple[str, float], Dict[str, Any]] = {}
    for bar in bars:
        for pp in bar:
            key = (pp.corte.descripcion, round(pp.corte.largo, 2))
            entry = agg.setdefault(key, {"qty": 0, "color": pp.color,
                                         "corte": pp.corte,
                                         "poly": pp.poly_local})
            entry["qty"] += 1
    if not agg:
        return

    pdf.add_page()
    set_pdf_font(pdf, "B", 13)
    pdf.cell(0, 10, t("pdf_piece_table_title"), 0, 1, "C")
    pdf.ln(2)

    # Column layout: name | profile | length | qty | silhouette
    col_name = 90.0
    col_prof = 60.0
    col_len = 35.0
    col_qty = 25.0
    col_sil = _DRAW_W - (col_name + col_prof + col_len + col_qty)
    row_h = 14.0

    def header() -> None:
        set_pdf_font(pdf, "B", 9)
        pdf.set_fill_color(230, 230, 233)
        pdf.set_text_color(0, 0, 0)
        pdf.set_x(_MARGIN)
        pdf.cell(col_name, 8, t("description"), 1, 0, "L", True)
        pdf.cell(col_prof, 8, t("profile_col"), 1, 0, "L", True)
        pdf.cell(col_len, 8, f"{t('length')} (mm)", 1, 0, "R", True)
        pdf.cell(col_qty, 8, t("placeholder_qty"), 1, 0, "R", True)
        pdf.cell(col_sil, 8, "", 1, 1, "C", True)

    header()
    set_pdf_font(pdf, "", 8)
    for (desc, largo), entry in sorted(agg.items(), key=lambda kv: -kv[1]["qty"]):
        if pdf.get_y() + row_h > _PAGE_H - _MARGIN:
            pdf.add_page()
            header()
            set_pdf_font(pdf, "", 8)
        x0 = _MARGIN
        ytop = pdf.get_y()
        pdf.set_x(x0)
        pdf.cell(col_name, row_h, desc or t("pieces"), 1, 0, "L")
        pdf.cell(col_prof, row_h, profile_name or "—", 1, 0, "L")
        pdf.cell(col_len, row_h, f"{largo:.1f}", 1, 0, "R")
        pdf.cell(col_qty, row_h, str(entry["qty"]), 1, 0, "R")
        pdf.cell(col_sil, row_h, "", 1, 1, "C")
        # Silhouette thumbnail, uniform scale inside the last cell.
        _draw_silhouette(pdf, entry["poly"], largo, section_height_mm,
                         x0 + col_name + col_prof + col_len + col_qty, ytop,
                         col_sil, row_h, entry["color"])


def _draw_silhouette(pdf: FPDF, poly, largo: float, sh: float,
                     cx: float, cy: float, cw: float, ch: float,
                     color: str) -> None:
    pad = 2.0
    pts = poly or [(0, 0), (largo, 0), (largo, sh or 1), (0, sh or 1)]
    minx, miny, maxx, maxy = _piece_bounds(pts)
    pw = max(maxx - minx, 0.01)
    ph = max(maxy - miny, 0.01)
    scale = min((cw - 2 * pad) / pw, (ch - 2 * pad) / ph)
    ox = cx + (cw - pw * scale) / 2.0
    oy = cy + (ch - ph * scale) / 2.0
    r, g, b = _hex_to_rgb(color)
    pdf.set_fill_color(r, g, b)
    pdf.set_draw_color(60, 60, 64)
    pdf.set_line_width(0.2)
    scaled = [(ox + (px - minx) * scale, oy + (py - miny) * scale)
              for (px, py) in pts]
    try:
        pdf.polygon(scaled, style="DF")
    except Exception:
        pass
