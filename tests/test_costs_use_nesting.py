"""
test_costs_use_nesting.py — costs must reflect the real Nesting-tab layout.

When a material context has a nesting layout that covers every cut, the cost
calculation must use that layout's actual bars (its yield and remnants), not a
fresh quick FFD/BFD/NFD estimate — and it must not destroy the layout. When the
layout is incomplete (or absent), it falls back to the quick estimate.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from nestify import app_config
from nestify.app_config import AppPreferences
from nestify.models import AppState, Corte, MaterialContext
from nestify.ui_qt.tab_perfiles import TabPerfiles


@pytest.fixture(scope="module", autouse=True)
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def shared_mode(tmp_path, monkeypatch):
    prefs = AppPreferences()  # cost_mode defaults to "shared"
    monkeypatch.setattr(app_config, "get", lambda: prefs)
    monkeypatch.setattr(app_config, "save", lambda p=None: True)
    monkeypatch.setattr(app_config, "PROFILES_DIR", str(tmp_path))
    return prefs


def _ctx_with_layout(layout):
    """A material context: two 1000 mm pieces in a 6000 mm bar, plus the given
    manual nesting layout."""
    ctx = MaterialContext()
    ctx.longitud_barra = 6000.0
    ctx.cortes = [Corte(descripcion="p", largo=1000.0, cantidad=2)]
    ctx.nesting_layout = layout
    return ctx


def _tab(shared_mode):
    # Build the tab with an empty state (the constructor stays passive); the
    # context is passed straight into _barras_for_costing.
    tab = TabPerfiles(state=AppState())
    tab._state.calc_system = "ffd"
    return tab


def test_full_layout_drives_costs_and_is_preserved(shared_mode):
    # Layout spreads the two pieces across two separate bars (unlike the quick
    # FFD estimate, which would pack both into a single bar).
    layout = [
        [{"x_offset": 0.0, "largo": 1000.0}],
        [{"x_offset": 0.0, "largo": 1000.0}],
    ]
    ctx = _ctx_with_layout(layout)
    tab = _tab(shared_mode)

    bars = tab._barras_for_costing(ctx)

    # Two bars, one piece each — the nesting layout, not the 1-bar quick estimate.
    assert bars == [[1000.0], [1000.0]]
    # The layout must survive the cost calculation (regression: it used to be
    # wiped by recompute_auto_barras).
    assert len(ctx.nesting_layout) == 2


def test_incomplete_layout_falls_back_to_quick_estimate(shared_mode):
    # Only one of the two pieces is placed → layout does not cover all cuts.
    layout = [[{"x_offset": 0.0, "largo": 1000.0}]]
    ctx = _ctx_with_layout(layout)
    tab = _tab(shared_mode)

    bars = tab._barras_for_costing(ctx)

    # Quick FFD packs both 1000 mm pieces into a single 6000 mm bar.
    assert bars == [[1000.0, 1000.0]]
