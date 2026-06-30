"""
nestube/nestube/nestube/backup.py
Backup & restore for the single SQLite store (nestube_geometry.db).

A timestamped, consistent snapshot is taken on each app start using the
sqlite3 online-backup API (so WAL contents are included and there are no
file-copy races), with a rolling retention limit. Restore copies a chosen
snapshot back over the live DB and removes the WAL/SHM sidecars; the app must
restart afterwards so every in-memory cache (config, materials, stock) reloads
from the restored database.
"""
from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import time
from datetime import datetime
from typing import List, Optional, Tuple

import nestube.database as _database
from nestube import db_settings
from nestube.database import get_geometry_db

_log = logging.getLogger(__name__)

BACKUP_DIRNAME = "backups"
MAX_BACKUPS = 15
_PREFIX = "nestube_"
_EXT = ".db"


def _db_path() -> str:
    """Current active DB path (read dynamically so it follows a switch)."""
    return _database.DB_PATH


def backup_dir() -> str:
    """Directory holding the snapshots (configurable via DB settings)."""
    return db_settings.get().resolved_backup_dir()


def _interval_due() -> bool:
    """Whether a startup snapshot is due given the configured interval."""
    s = db_settings.get()
    hours = s.backup_interval_hours
    if hours < 0:
        return False                      # backups disabled
    if hours == 0:
        return True                       # every launch
    return (time.time() - s.last_backup_ts) >= hours * 3600.0


def create_backup(reason: str = "startup") -> Optional[str]:
    """Write a consistent snapshot of the live DB into the backup directory.

    For ``reason == "startup"`` the configured interval gates whether a snapshot
    is actually taken (disabled / every-launch / once per N hours). A manual
    "Backup now" always snapshots. Returns the snapshot path, or None if nothing
    was backed up. Never raises — backups must not block app startup.
    """
    if not os.path.isfile(_db_path()):
        return None
    if reason == "startup" and not _interval_due():
        return None
    try:
        os.makedirs(backup_dir(), exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(backup_dir(), f"{_PREFIX}{ts}{_EXT}")
        # Online backup API → consistent snapshot incl. WAL pages.
        src = get_geometry_db().connect()
        dst = sqlite3.connect(dest)
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
        _prune_backups()
        # Record the snapshot time so the interval gate works across launches.
        s = db_settings.get()
        s.last_backup_ts = time.time()
        db_settings.save(s)
        _log.info("Created %s backup: %s", reason, dest)
        return dest
    except (sqlite3.Error, OSError) as exc:
        _log.warning("Backup failed: %s", exc)
        return None


def list_backups() -> List[Tuple[str, datetime, int]]:
    """Return [(path, modified-time, size-bytes)] for each snapshot, newest first."""
    d = backup_dir()
    if not os.path.isdir(d):
        return []
    out: List[Tuple[str, datetime, int]] = []
    for name in os.listdir(d):
        if name.startswith(_PREFIX) and name.endswith(_EXT):
            p = os.path.join(d, name)
            try:
                st = os.stat(p)
            except OSError:
                continue
            out.append((p, datetime.fromtimestamp(st.st_mtime), st.st_size))
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def _prune_backups(keep: Optional[int] = None) -> None:
    """Delete the oldest snapshots beyond the retention limit (read at call
    time so MAX_BACKUPS stays overridable)."""
    if keep is None:
        keep = MAX_BACKUPS
    for path, _, _ in list_backups()[keep:]:
        try:
            os.remove(path)
        except OSError:
            pass


def restore_backup(path: str) -> bool:
    """Replace the live DB with the given snapshot.

    Closes the live connection, keeps a one-shot safety copy of the current DB
    (``*.pre_restore``), copies the snapshot over the live file and removes the
    WAL/SHM sidecars. The caller must restart the app afterwards so caches
    reload. Returns True on success.
    """
    if not os.path.isfile(path):
        return False
    try:
        get_geometry_db().close()
    except Exception:  # noqa: BLE001 — closing is best-effort
        pass
    db_path = _db_path()
    try:
        if os.path.isfile(db_path):
            shutil.copy2(db_path, db_path + ".pre_restore")
        shutil.copy2(path, db_path)
        for side in ("-wal", "-shm"):
            sidecar = db_path + side
            if os.path.isfile(sidecar):
                os.remove(sidecar)
        return True
    except OSError as exc:
        _log.error("Restore failed: %s", exc)
        return False
