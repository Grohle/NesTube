"""
nestify/db_settings.py

Bootstrap settings that MUST live outside the SQLite store itself — the location
of the database and the backup policy. (The DB path can't be stored in the DB:
chicken-and-egg.) These are kept in a tiny JSON file next to the app so the
database can be pointed at a shared/server location and switched at will.

Fields:
  • db_path               — absolute path to the active SQLite database.
  • backup_dir            — directory where snapshots are written.
  • backup_interval_hours — 0 = on every launch, N>0 = at most once per N hours,
                            <0 = disabled.
  • last_backup_ts        — epoch seconds of the last snapshot (interval gate).
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

from .paths import app_root

_log = logging.getLogger(__name__)

# The bootstrap file lives at a FIXED location (the app root) regardless of where
# the database itself is configured to live.
_SETTINGS_FILE = os.path.join(app_root(), "nestify_db_location.json")
_DEFAULT_DB_NAME = "nestify_geometry.db"


@dataclass
class DBSettings:
    db_path: str = ""
    backup_dir: str = ""
    backup_interval_hours: float = 0.0   # 0 = every launch
    last_backup_ts: float = 0.0

    def resolved_db_path(self) -> str:
        return self.db_path or os.path.join(app_root(), _DEFAULT_DB_NAME)

    def resolved_backup_dir(self) -> str:
        if self.backup_dir:
            return self.backup_dir
        return os.path.join(os.path.dirname(self.resolved_db_path()) or ".", "backups")

    def to_dict(self) -> dict:
        return {
            "db_path": self.db_path,
            "backup_dir": self.backup_dir,
            "backup_interval_hours": self.backup_interval_hours,
            "last_backup_ts": self.last_backup_ts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DBSettings":
        return cls(
            db_path=str(d.get("db_path", "")),
            backup_dir=str(d.get("backup_dir", "")),
            backup_interval_hours=float(d.get("backup_interval_hours", 0.0)),
            last_backup_ts=float(d.get("last_backup_ts", 0.0)),
        )


_cache: Optional[DBSettings] = None


def get() -> DBSettings:
    """Load (and cache) the bootstrap settings. Never raises — falls back to
    defaults so a missing/corrupt file can't block startup."""
    global _cache
    if _cache is not None:
        return _cache
    s = DBSettings()
    try:
        if os.path.isfile(_SETTINGS_FILE):
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as fh:
                s = DBSettings.from_dict(json.load(fh))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        _log.warning("Could not read DB settings (%s) — using defaults", exc)
    _cache = s
    return s


def save(s: Optional[DBSettings] = None) -> bool:
    """Persist the bootstrap settings. Returns True on success."""
    global _cache
    if s is not None:
        _cache = s
    if _cache is None:
        _cache = DBSettings()
    try:
        with open(_SETTINGS_FILE, "w", encoding="utf-8") as fh:
            json.dump(_cache.to_dict(), fh, ensure_ascii=False, indent=2)
        return True
    except OSError as exc:
        _log.error("Could not write DB settings: %s", exc)
        return False


def settings_file() -> str:
    return _SETTINGS_FILE
