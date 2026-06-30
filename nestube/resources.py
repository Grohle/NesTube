"""
nestube/nestube/nestube/resources.py
Bundled assets (logo, icon) for source and PyInstaller builds.
"""
from __future__ import annotations

import os
import sys


def _package_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts: str) -> str:
    """Absolute path to a file under nestube/ or the PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", _package_dir())
    else:
        base = _package_dir()
    return os.path.join(base, *parts)


def logo_png_path() -> str:
    return resource_path("assets", "logo.png")


def icon_ico_path() -> str:
    return resource_path("assets", "icon.ico")


def icon_png_path() -> str:
    return resource_path("assets", "icon.png")
