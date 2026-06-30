"""
test_backup.py — §15 database backup & restore.

Verifies the SQLite snapshot system used at app startup (main.py calls
backup.create_backup("startup")) and from the Backups dialog: create a
consistent snapshot, list it, and restore it over a mutated live DB.
"""
import sqlite3

import pytest


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point database + backup at an isolated temp DB and reset the singleton."""
    import nestube.database as db
    import nestube.backup as bk
    import nestube.db_settings as ds
    path = str(tmp_path / "nestube_geometry.db")
    # Drive both the DB path and the backup dir through db_settings (the real
    # source) and keep database.DB_PATH in sync; avoid writing the real settings
    # file by stubbing save().
    s = ds.DBSettings(db_path=path, backup_dir=str(tmp_path / "backups"),
                      backup_interval_hours=0.0)
    monkeypatch.setattr(ds, "_cache", s, raising=False)
    monkeypatch.setattr(ds, "save", lambda *_a, **_k: True)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "_db", None, raising=False)
    g = db.GeometryDB(path)
    monkeypatch.setattr(db, "_db", g, raising=False)
    g.connect().execute("CREATE TABLE t (x INTEGER)")
    g.connect().commit()
    return db, bk, g


def test_create_list_restore_round_trip(temp_db):
    db, bk, g = temp_db
    g.connect().execute("INSERT INTO t VALUES (42)")
    g.connect().commit()

    snap = bk.create_backup("test")
    assert snap is not None
    assert any(p == snap for p, _, _ in bk.list_backups())

    # Mutate the live DB, then restore the snapshot over it.
    g.connect().execute("INSERT INTO t VALUES (99)")
    g.connect().commit()
    assert bk.restore_backup(snap) is True

    # Re-open and confirm the restored content (99 gone, 42 kept).
    fresh = db.GeometryDB(db.DB_PATH)
    rows = sorted(r[0] for r in fresh.connect().execute("SELECT x FROM t"))
    assert rows == [42]
    fresh.close()


def test_create_backup_no_db_returns_none(tmp_path, monkeypatch):
    import nestube.backup as bk
    import nestube.database as db
    missing = str(tmp_path / "does_not_exist.db")
    monkeypatch.setattr(db, "DB_PATH", missing)
    assert bk.create_backup("test") is None


def test_startup_interval_gate(temp_db, monkeypatch):
    db, bk, g = temp_db
    import nestube.db_settings as ds
    g.connect().execute("INSERT INTO t VALUES (1)")
    g.connect().commit()
    s = ds.get()
    # Disabled → no startup snapshot, but a manual one still works.
    s.backup_interval_hours = -1
    assert bk.create_backup("startup") is None
    assert bk.create_backup("manual") is not None
    # Interval not yet elapsed → startup skipped.
    s.backup_interval_hours = 24
    import time
    s.last_backup_ts = time.time()
    assert bk.create_backup("startup") is None
    # Elapsed → startup runs.
    s.last_backup_ts = time.time() - 25 * 3600
    assert bk.create_backup("startup") is not None


def test_retention_prunes_old_backups(temp_db, monkeypatch):
    db, bk, g = temp_db
    g.connect().execute("INSERT INTO t VALUES (1)")
    g.connect().commit()
    monkeypatch.setattr(bk, "MAX_BACKUPS", 3)
    # Distinct mtimes so newest-first ordering and pruning are deterministic.
    import os, time
    for _ in range(5):
        p = bk.create_backup("test")
        assert p is not None
        os.utime(p, (time.time(), time.time() + _))
    bk._prune_backups()
    assert len(bk.list_backups()) <= 3
