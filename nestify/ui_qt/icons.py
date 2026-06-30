"""
nestify/ui_qt/icons.py
Themed monochrome SVG icons loaded from ``nestify/assets/icons``.

Why this exists: text emojis (🔍 💾 🗑 🖨 🖼) render inconsistently on Linux
— they fall back to colour-emoji fonts or show as tofu boxes depending on the
installed font set. These are replaced by single-colour SVGs shipped in the
assets directory, rasterised here into crisp QIcons.

Each SVG is authored with a ``__C__`` placeholder for its stroke/fill colour,
so the same file serves every theme: the loader substitutes the requested
colour (defaulting to the live ``_th.TEXT_PRI``) before rendering. Icons must
be re-fetched from ``refresh_theme()`` so the glyph follows dark/light switches
— a QIcon is a baked pixmap and does not re-tint on its own.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from nestify.resources import resource_path
import nestify.ui_qt.theme_qt as _th

# (name, colour, size) → QIcon. Keyed by colour so a theme switch produces a
# fresh entry instead of returning a stale-coloured icon.
_CACHE: dict = {}


def themed_icon(name: str, color: Optional[str] = None, size: int = 18) -> QIcon:
    """Return a QIcon for ``assets/icons/<name>.svg`` tinted to ``color``.

    ``color`` defaults to the current theme's primary text colour so icons read
    correctly in both dark and light mode. Pass an explicit colour (e.g.
    ``_th.ACCENT``) for accented controls. Returns an empty QIcon if the asset
    is missing rather than raising, so a typo never crashes the UI.
    """
    col = color or _th.TEXT_PRI
    key = (name, col, size)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    path = resource_path("assets", "icons", f"{name}.svg")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            svg = fh.read()
    except OSError:
        return QIcon()

    svg = svg.replace("__C__", col)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pm = QPixmap(QSize(size, size))
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()

    icon = QIcon(pm)
    _CACHE[key] = icon
    return icon
