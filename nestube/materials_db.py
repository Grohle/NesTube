"""
nestube/nestube/nestube/materials_db.py
Materials database — manages material definitions (name + quality).
Materials are separate from stock: stock bars have a material assigned.
Stored as JSON in the project root.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import List, Optional

_log = logging.getLogger(__name__)
_lock = threading.Lock()

from .paths import app_root

_ROOT = app_root()
MATERIALS_DB_PATH = os.path.join(_ROOT, "materials_db.json")


@dataclass
class Material:
    """A material definition with name, quality grade, and specific weight."""
    id: str
    name: str
    quality: str = ""
    category: str = ""
    specific_weight: float = 7.85

    @property
    def display(self) -> str:
        from .naming import format_material
        return format_material(self.name, self.quality)

    def matches(self, query: str) -> bool:
        q = query.lower()
        return (q in self.name.lower() or q in self.quality.lower()
                or q in self.display.lower())

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name,
            "quality": self.quality, "category": self.category,
            "specific_weight": self.specific_weight,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Material":
        return cls(
            id=str(d.get("id", "")),
            name=str(d.get("name", "")),
            quality=str(d.get("quality", "")),
            category=str(d.get("category", "")),
            specific_weight=float(d.get("specific_weight", 7.85)),
        )


@dataclass
class MaterialsDB:
    materials: List[Material] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"materials": [m.to_dict() for m in self.materials]}

    @classmethod
    def from_dict(cls, d: dict) -> "MaterialsDB":
        return cls(materials=[Material.from_dict(m) for m in d.get("materials", [])])


_db: Optional[MaterialsDB] = None


def load_materials() -> MaterialsDB:
    """Load materials from the SQLite store (nestube_geometry.db).

    On first run after the JSON→SQLite migration, if the DB has no materials
    but a legacy ``materials_db.json`` exists, its rows are imported once and
    the JSON file is retired (renamed to ``*.migrated``) so it is never
    re-imported. The in-memory cache and dataclasses are unchanged, so callers
    and the UI keep the same API.
    """
    global _db
    with _lock:
        from nestube.database import get_geometry_db
        db = get_geometry_db()
        rows = db.get_all_materials()
        if not rows and os.path.isfile(MATERIALS_DB_PATH):
            try:
                with open(MATERIALS_DB_PATH, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                legacy = MaterialsDB.from_dict(raw)
                if legacy.materials:
                    db.replace_all_materials([m.to_dict() for m in legacy.materials])
                    rows = db.get_all_materials()
                    _log.info("Migrated %d materials from JSON to SQLite", len(legacy.materials))
            except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
                _log.warning("Could not import legacy materials JSON: %s", exc)
            _retire_legacy_json(MATERIALS_DB_PATH)
        _db = MaterialsDB(materials=[Material.from_dict(r) for r in rows])
        return _db


def save_materials(db: Optional[MaterialsDB] = None) -> bool:
    global _db
    with _lock:
        if db is not None:
            _db = db
        if _db is None:
            _db = MaterialsDB()
        try:
            from nestube.database import get_geometry_db
            get_geometry_db().replace_all_materials([m.to_dict() for m in _db.materials])
            return True
        except Exception as exc:  # noqa: BLE001 — persistence must never crash the UI
            _log.error("Could not save materials to SQLite: %s", exc)
            return False


def _retire_legacy_json(path: str) -> None:
    """Rename a migrated legacy JSON file to ``*.migrated`` so it is kept as a
    backup but no longer re-imported. Best-effort: failures are non-fatal."""
    try:
        if os.path.isfile(path):
            os.replace(path, path + ".migrated")
    except OSError as exc:
        _log.warning("Could not retire legacy JSON %s: %s", path, exc)


def get_materials() -> MaterialsDB:
    if _db is None:
        return load_materials()
    return _db


def add_material(
    name: str, quality: str = "", category: str = "",
    specific_weight: float = 7.85,
) -> Material:
    db = get_materials()
    mid = f"{len(db.materials) + 1:04d}"
    mat = Material(id=mid, name=name, quality=quality, category=category,
                   specific_weight=specific_weight)
    db.materials.append(mat)
    save_materials()
    return mat


def update_material(
    material_id: str, name: str, quality: str = "", category: str = "",
    specific_weight: float = 7.85,
) -> bool:
    db = get_materials()
    for mat in db.materials:
        if mat.id == material_id:
            mat.name = name
            mat.quality = quality
            mat.category = category
            mat.specific_weight = specific_weight
            save_materials()
            return True
    return False


def find_duplicate(name: str, quality: str = "", exclude_id: str = "") -> Optional[Material]:
    """Find another material with the same name and quality."""
    db = get_materials()
    name_l = name.strip().lower()
    quality_l = quality.strip().lower()
    for mat in db.materials:
        if mat.id == exclude_id:
            continue
        if mat.name.strip().lower() == name_l and mat.quality.strip().lower() == quality_l:
            return mat
    return None


def remove_material(material_id: str) -> bool:
    db = get_materials()
    db.materials = [m for m in db.materials if m.id != material_id]
    save_materials()
    return True


def search_materials(query: str) -> List[Material]:
    """Search materials by partial name/quality match."""
    db = get_materials()
    if not query:
        return db.materials[:]
    return [m for m in db.materials if m.matches(query)]


def get_material_names() -> List[str]:
    """Get unique material display names for dropdowns."""
    db = get_materials()
    return [m.display for m in db.materials]


def find_material(name: str, quality: str = "") -> Optional[Material]:
    """Find a material by exact name and quality."""
    db = get_materials()
    for m in db.materials:
        if m.name.lower() == name.lower():
            if not quality or m.quality.lower() == quality.lower():
                return m
    return None
