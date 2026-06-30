"""
nestify/ui_qt/fonts_qt.py
Font registration and factory functions for the Qt UI.
"""
from __future__ import annotations

import os

from PySide6.QtGui import QFont, QFontDatabase

from nestify import app_config

_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts")

_IBM_FAMILY = "IBM Plex Sans"
_MONO_FAMILY = "DejaVu Sans Mono"

_registered = False


def register_bundled_fonts() -> None:
    global _registered
    if _registered:
        return
    ttfs = [
        "IBMPlexSans-Regular.ttf",
        "IBMPlexSans-Bold.ttf",
        "IBMPlexSans-Italic.ttf",
        "IBMPlexSans-Medium.ttf",
        # Mono variant backs F_NUM/F_NUM_SM/F_BADGE. Must be bundled —
        # clean Windows builds have no "DejaVu Sans Mono".
        "DejaVuSansMono.ttf",
        "DejaVuSansMono-Bold.ttf",
    ]
    for name in ttfs:
        path = os.path.join(_FONTS_DIR, name)
        if os.path.isfile(path):
            QFontDatabase.addApplicationFont(path)
    _registered = True


def _offset() -> int:
    return app_config.get().font_size_offset


def font(family: str = _IBM_FAMILY, size: int = 12, bold: bool = False,
         italic: bool = False) -> QFont:
    # Never let a large negative font-size offset drive the point size to 0 or
    # below (Qt warns "QFont::setPointSize: Point size <= 0").
    pt = max(1, size + _offset())
    f = QFont(family, pt)
    if bold:
        f.setWeight(QFont.Weight.Bold)
    if italic:
        f.setItalic(True)
    return f


def F_TITLE() -> QFont:   return font(size=15, bold=True)
def F_BOLD() -> QFont:    return font(size=12, bold=True)
def F_BODY() -> QFont:    return font(size=12)
def F_SMALL() -> QFont:   return font(size=10)
def F_CAPTION() -> QFont: return font(size=9)
def F_NUM() -> QFont:     return font(_MONO_FAMILY, size=11)
def F_NUM_SM() -> QFont:  return font(_MONO_FAMILY, size=10)
def F_BADGE() -> QFont:   return font(_MONO_FAMILY, size=9)
