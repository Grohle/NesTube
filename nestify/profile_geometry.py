"""
nestify/profile_geometry.py
Parametric cross-section geometry for the multi-material profile/tube catalogue
(TODO §20.3). Given a geometry type and the canonical dimensions
(h, b, tw, tf) it builds the 2D cross-section contour(s) to scale, so the same
description drives both the catalogue thumbnail and any future section drawing.

Dimensions (millimetres), matching the master spreadsheet columns:
    h   — height / outer diameter      (h_Alto_Diámetro_mm)
    b   — width                        (b_Ancho_mm)
    tw  — web thickness / wall         (tw_Espesor_Alma_mm)
    tf  — flange thickness             (tf_Espesor_Alas_mm)

The contour generator is pure (no Qt) so it is unit-testable on its own. The Qt
rasteriser lives in :func:`render_section_pixmap` for thumbnails.

A section is returned as ``(outer, holes)`` where ``outer`` is a list of
``(x, y)`` points (millimetres, origin centred, y up) and ``holes`` is a list of
inner contours to subtract (e.g. the bore of a tube).
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

Point = Tuple[float, float]
Contour = List[Point]

# Canonical geometry types (the spreadsheet's Tipo_Geometria). Hidden from the
# user — it only selects which parametric drawing a profile gets.
GEOMETRY_TYPES = (
    "Viga I", "Viga H", "Viga U", "Perfil C", "Perfil Z",
    "Angular", "Cuadrado", "Redondo", "Pletina", "Ranurado",
)


def _f(v: Optional[float]) -> float:
    """Coerce a possibly-None numeric to a float (None/blank → 0.0)."""
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _center(contours: List[Contour]) -> None:
    """Shift every contour in place so the bounding box is centred on origin."""
    xs = [x for c in contours for x, _ in c]
    ys = [y for c in contours for _, y in c]
    if not xs:
        return
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    for c in contours:
        for i, (x, y) in enumerate(c):
            c[i] = (x - cx, y - cy)


def _circle(cx: float, cy: float, r: float, segs: int = 64) -> Contour:
    return [(cx + r * math.cos(2 * math.pi * i / segs),
             cy + r * math.sin(2 * math.pi * i / segs)) for i in range(segs)]


def section_contours(
    geometry_type: str,
    h: Optional[float] = 0.0,
    b: Optional[float] = 0.0,
    tw: Optional[float] = 0.0,
    tf: Optional[float] = 0.0,
    macizo: bool = False,
) -> Tuple[Contour, List[Contour]]:
    """Build the cross-section for ``geometry_type`` → ``(outer, holes)`` in mm.

    Falls back to a plain rectangle/square for unknown types so a thumbnail is
    always produced. Thicknesses that are missing (None/0) collapse the shape to
    solid where that makes sense (e.g. a round bar vs a tube).
    """
    g = (geometry_type or "").strip().lower()
    h, b, tw, tf = _f(h), _f(b), _f(tw), _f(tf)

    if g == "redondo":
        outer = _circle(0, 0, h / 2.0)
        holes: List[Contour] = []
        if not macizo and tw > 0 and tw < h / 2.0:
            holes.append(_circle(0, 0, h / 2.0 - tw))
        return outer, holes

    if g in ("cuadrado",):
        w = b or h
        outer = [(0, 0), (w, 0), (w, h), (0, h)]
        holes = []
        wall = tw or tf
        if not macizo and wall > 0 and w - 2 * wall > 0 and h - 2 * wall > 0:
            holes = [[(wall, wall), (w - wall, wall),
                      (w - wall, h - wall), (wall, h - wall)]]
        cs = [outer] + holes
        _center(cs)
        return cs[0], cs[1:]

    if g == "pletina":
        w = b or 1.0
        outer = [(0, 0), (w, 0), (w, h), (0, h)]
        _center([outer])
        return outer, []

    if g == "angular":
        t = tw or tf or max(h, b) * 0.1
        outer = [(0, 0), (b, 0), (b, t), (t, t), (t, h), (0, h)]
        _center([outer])
        return outer, []

    if g in ("viga i", "viga h"):
        # Doubly-symmetric I/H section: flange width b, height h, web tw, flange tf.
        bw = b or h
        web = tw or bw * 0.1
        fl = tf or h * 0.1
        x0 = -bw / 2.0
        xw = web / 2.0
        y0 = -h / 2.0
        yf = y0 + fl
        outer = [
            (x0, y0), (-x0, y0), (-x0, yf), (xw, yf), (xw, -yf),
            (-x0, -yf), (-x0, -y0), (x0, -y0), (x0, -yf), (-xw, -yf),
            (-xw, yf), (x0, yf),
        ]
        return outer, []

    if g in ("viga u", "perfil c"):
        # Channel opening to the right: back web on the left.
        bw = b or h * 0.5
        web = tw or bw * 0.2
        fl = tf or h * 0.1
        outer = [
            (0, 0), (bw, 0), (bw, fl), (web, fl),
            (web, h - fl), (bw, h - fl), (bw, h), (0, h),
        ]
        _center([outer])
        return outer, []

    if g == "perfil z":
        bw = b or h * 0.5
        t = tw or tf or h * 0.08
        outer = [
            (0, 0), (bw, 0), (bw, t), (t, t),
            (t, h), (-bw + t, h), (-bw + t, h - t), (0, h - t),
        ]
        _center([outer])
        return outer, []

    if g == "ranurado":
        # T-slot extrusion: square shell with a central bore (approximation).
        w = b or h
        outer = [(0, 0), (w, 0), (w, h), (0, h)]
        holes = []
        bore = min(w, h) * 0.28
        if bore > 0:
            holes = [_circle(w / 2.0, h / 2.0, bore)]
        cs = [outer] + holes
        _center(cs)
        return cs[0], cs[1:]

    # Fallback: a plain rectangle (or square if b missing).
    w = b or h or 1.0
    hh = h or w
    outer = [(0, 0), (w, 0), (w, hh), (0, hh)]
    _center([outer])
    return outer, []


def render_section_pixmap(
    geometry_type: str,
    h: Optional[float] = 0.0,
    b: Optional[float] = 0.0,
    tw: Optional[float] = 0.0,
    tf: Optional[float] = 0.0,
    macizo: bool = False,
    size: int = 128,
    fg: str = "#C8C8D2",
    outline: str = "#5A5A66",
    bg: Optional[str] = None,
):
    """Rasterise the parametric section to a ``size``×``size`` ``QPixmap``.

    Holes are punched with an odd-even fill path. Colours default to a neutral
    grey fill so the icon reads in both themes; pass theme colours for accents.
    Requires a running ``QApplication`` (import kept local so the pure contour
    generator above stays Qt-free and testable headless).
    """
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPixmap

    outer, holes = section_contours(geometry_type, h, b, tw, tf, macizo)
    if not outer:
        return QPixmap(size, size)

    xs = [x for x, _ in outer] + [x for hole in holes for x, _ in hole]
    ys = [y for _, y in outer] + [y for hole in holes for _, y in hole]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w_mm = max(maxx - minx, 1e-6)
    h_mm = max(maxy - miny, 1e-6)

    pad = size * 0.12
    scale = min((size - 2 * pad) / w_mm, (size - 2 * pad) / h_mm)
    ox = (size - w_mm * scale) / 2.0
    oy = (size - h_mm * scale) / 2.0

    def to_px(p: Point) -> QPointF:
        # Flip y so the section is drawn upright in image coordinates.
        return QPointF(ox + (p[0] - minx) * scale,
                       oy + (maxy - p[1]) * scale)

    pm = QPixmap(size, size)
    pm.fill(QColor(bg) if bg else Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    path = QPainterPath()
    path.setFillRule(Qt.FillRule.OddEvenFill)

    def add(contour: Contour) -> None:
        path.moveTo(to_px(contour[0]))
        for p in contour[1:]:
            path.lineTo(to_px(p))
        path.closeSubpath()

    add(outer)
    for hole in holes:
        add(hole)

    painter.setBrush(QBrush(QColor(fg)))
    painter.setPen(QPen(QColor(outline), max(1.0, size / 96.0)))
    painter.drawPath(path)
    painter.end()
    return pm
