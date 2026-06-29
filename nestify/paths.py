"""
nestify/paths.py
Install / project root for config, Profiles/, and local JSON databases.
"""
from __future__ import annotations

import os
import sys


def app_root() -> str:
    """Directory for user-writable config and data (exe folder when frozen)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
