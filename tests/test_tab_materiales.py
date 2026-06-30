"""
test_tab_materiales.py — §20.5 / §21.1 "Profiles & Tubes" tab (search + list/grid views).

Builds the widget against an isolated AppPreferences (no real app config /
Profiles folder touched) and exercises the default list (detail/table) view,
the grid (icon) view toggle, search filtering and selection -> detail panel.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from nestube import app_config, profile_catalog
from nestube.app_config import AppPreferences, CustomProfileEntry
from nestube.naming import localize_material
from nestube.ui_qt.tab_materiales import TabMateriales


@pytest.fixture(scope="module", autouse=True)
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def isolated_profiles(tmp_path, monkeypatch):
    prefs = AppPreferences()
    prefs.custom_profiles = [
        CustomProfileEntry(
            id="t1", name="Test IPE 100",
            meta={
                "material": "Acero al Carbono",
                "h": 100, "b": 55, "tw": 4.1, "tf": 5.7,
                "seccion_cm2": 10.3, "peso_lineal_kg_m": 8.1,
            },
        ),
        CustomProfileEntry(
            id="t2", name="Test Tubo Aluminio",
            meta={
                "material": "Aluminio",
                "h": 50, "b": 50, "tw": 2.0, "tf": 0,
                "seccion_cm2": 3.0, "peso_lineal_kg_m": 1.0,
            },
        ),
    ]
    monkeypatch.setattr(app_config, "get", lambda: prefs)
    monkeypatch.setattr(app_config, "save", lambda p=None: True)
    monkeypatch.setattr(app_config, "PROFILES_DIR", str(tmp_path))
    # Don't pull the real 22-row catalogue into the isolated prefs.
    monkeypatch.setattr(profile_catalog, "ensure_catalog_profiles", lambda: 0)
    return prefs


def test_table_view_is_default_and_lists_all_entries(isolated_profiles):
    w = TabMateriales()
    assert w._stack.currentWidget() is w._table
    assert w._btn_view_list.isChecked()
    assert w._table.rowCount() == 2
    # Grid view is populated too, just not shown.
    assert w._list.count() == 2


def test_search_filters_both_views(isolated_profiles):
    w = TabMateriales()
    w._search.setText("tubo")  # matches entry name, language-independent
    assert w._table.rowCount() == 1
    assert w._list.count() == 1

    w._search.setText("")
    assert w._table.rowCount() == 2


def test_selecting_row_enables_edit_and_shows_detail(isolated_profiles):
    w = TabMateriales()
    assert not w._btn_edit.isEnabled()

    w._table.selectRow(0)
    assert w._btn_edit.isEnabled()
    entry = w._selected_entry()
    assert entry.id == "t1"
    assert localize_material("Acero al Carbono") in w._detail.text()
    assert "10.3" in w._detail.text()


def test_switching_to_grid_view_keeps_selection_logic(isolated_profiles):
    w = TabMateriales()
    w._btn_view_grid.setChecked(True)
    assert w._stack.currentWidget() is w._list

    w._list.setCurrentRow(1)
    entry = w._selected_entry()
    assert entry.id == "t2"
