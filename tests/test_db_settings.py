"""
test_db_settings.py — bootstrap DB-location / backup settings (§15).

These live OUTSIDE the SQLite store (chicken-and-egg) so the database can be
pointed at a shared/server path and switched. Verifies round-trip and the
default resolution for db path and backup directory.
"""
import os

import pytest


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    import nestube.db_settings as ds
    monkeypatch.setattr(ds, "_SETTINGS_FILE", str(tmp_path / "loc.json"))
    monkeypatch.setattr(ds, "_cache", None, raising=False)
    return ds


def test_round_trip(isolated_settings, tmp_path):
    ds = isolated_settings
    s = ds.get()
    s.db_path = str(tmp_path / "shared.db")
    s.backup_dir = str(tmp_path / "bk")
    s.backup_interval_hours = 24.0
    s.last_backup_ts = 123.0
    assert ds.save(s) is True
    ds._cache = None
    s2 = ds.get()
    assert s2.db_path == str(tmp_path / "shared.db")
    assert s2.backup_dir == str(tmp_path / "bk")
    assert s2.backup_interval_hours == 24.0
    assert s2.last_backup_ts == 123.0


def test_defaults_when_unset(isolated_settings):
    ds = isolated_settings
    s = ds.get()
    # No file yet → empty fields resolve to app-root defaults.
    assert s.resolved_db_path().endswith("nestube_geometry.db")
    assert os.path.basename(s.resolved_backup_dir()) == "backups"


def test_backup_dir_follows_db_path(isolated_settings):
    ds = isolated_settings
    s = ds.DBSettings(db_path="/srv/share/nestube.db")
    assert s.resolved_backup_dir() == os.path.join("/srv/share", "backups")


def test_corrupt_file_falls_back(isolated_settings):
    ds = isolated_settings
    with open(ds._SETTINGS_FILE, "w") as fh:
        fh.write("{ not json")
    ds._cache = None
    s = ds.get()                      # must not raise
    assert s.resolved_db_path().endswith("nestube_geometry.db")
