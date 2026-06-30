"""
test_profile_catalog.py — §20.4 built-in profile/tube catalogue import.

Verifies the 22-row dataset is well-formed and that ensure_catalog_profiles()
idempotently creates CustomProfileEntry records without touching the real
app config / Profiles folder (PROFILES_DIR and persistence are monkeypatched).
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from nestify import app_config, profile_catalog
from nestify.app_config import AppPreferences
from nestify.profile_geometry import GEOMETRY_TYPES


@pytest.fixture(scope="module", autouse=True)
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_catalog_rows_are_well_formed():
    assert len(profile_catalog.CATALOG_ROWS) == 22
    ids = [r.id for r in profile_catalog.CATALOG_ROWS]
    names = [r.name for r in profile_catalog.CATALOG_ROWS]
    assert len(ids) == len(set(ids))
    assert len(names) == len(set(names))
    for row in profile_catalog.CATALOG_ROWS:
        assert row.geometry_type in GEOMETRY_TYPES
        assert row.h > 0
        assert row.seccion_cm2 > 0
        assert row.peso_lineal_kg_m > 0


def test_entry_ids_are_filesystem_safe_and_unique():
    eids = [profile_catalog._entry_id(r) for r in profile_catalog.CATALOG_ROWS]
    assert len(eids) == len(set(eids))
    for eid in eids:
        assert eid.startswith("catalog-")
        assert all(c.isalnum() or c == "-" for c in eid)


def test_build_entry_canonicalizes_material_and_fills_meta():
    row = next(r for r in profile_catalog.CATALOG_ROWS if r.id == "INX-MAC-20")
    entry = profile_catalog._build_entry(row)
    assert entry.meta["material"] == "Inoxidable"  # alias, not "Acero Inoxidable"
    assert entry.meta["specific_weight"] == pytest.approx(7.90)
    assert entry.meta["geometry_type"] == "Redondo"
    assert entry.meta["macizo"] is True
    assert entry.meta["seccion_cm2"] == pytest.approx(3.14)
    assert entry.fields == ["h (mm)", "b (mm)", "tw (mm)", "tf (mm)"]
    assert entry.field_defaults["h (mm)"] == pytest.approx(20)


def test_build_entry_keeps_specific_catalog_materials_distinct():
    carbon = next(r for r in profile_catalog.CATALOG_ROWS if r.id == "AC-IPE-100")
    galv = next(r for r in profile_catalog.CATALOG_ROWS if r.id == "GALV-TC-1")
    assert profile_catalog._build_entry(carbon).meta["material"] == "Acero al Carbono"
    assert profile_catalog._build_entry(galv).meta["material"] == "Acero Galvanizado"


@pytest.fixture
def isolated_catalog_io(tmp_path, monkeypatch):
    """Redirect ensure_catalog_profiles()'s IO to a throwaway in-memory store."""
    prefs = AppPreferences()
    saved_files = []

    monkeypatch.setattr(profile_catalog, "PROFILES_DIR", str(tmp_path))
    monkeypatch.setattr(profile_catalog, "save_profile_file",
                         lambda entry: saved_files.append(entry.id))
    monkeypatch.setattr(app_config, "get", lambda: prefs)
    monkeypatch.setattr(app_config, "save", lambda p=None: True)
    return prefs, saved_files


def test_ensure_catalog_profiles_is_idempotent(isolated_catalog_io):
    prefs, saved_files = isolated_catalog_io
    added_first = profile_catalog.ensure_catalog_profiles()
    assert added_first == 22
    assert len(prefs.custom_profiles) == 22
    assert len(saved_files) == 22

    added_second = profile_catalog.ensure_catalog_profiles()
    assert added_second == 0
    assert len(prefs.custom_profiles) == 22  # no duplicates


def test_ensure_catalog_profiles_generates_thumbnails(isolated_catalog_io, tmp_path):
    profile_catalog.ensure_catalog_profiles()
    pngs = list(tmp_path.glob("catalog-*.png"))
    assert len(pngs) == 22
