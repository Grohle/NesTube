"""
conftest.py — stub GUI modules so nesting logic tests run headlessly.
Tkinter and customtkinter are not available in the CI container.
"""
import sys
import types
from unittest.mock import MagicMock


def _stub(name: str) -> None:
    if name not in sys.modules:
        sys.modules[name] = MagicMock()


# Tkinter and all sub-modules
_stub("tkinter")
_stub("tkinter.filedialog")
_stub("tkinter.messagebox")
_stub("tkinter.ttk")
_stub("customtkinter")

# GUI-only third-party libs that aren't installed headlessly
_stub("fpdf")
_stub("fpdf2")
_stub("pandas")
_stub("openpyxl")
_stub("docx")
# ezdxf is a real installed dependency (required by dxf_cache.py) — do NOT stub it
_stub("PIL")
_stub("PIL.Image")
