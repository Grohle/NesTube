"""
nestify/stock_db.py
Local stock/inventory database stored as JSON in the project root.
Manages bars, profiles, and remnants (retales).
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_log = logging.getLogger(__name__)
_lock = threading.Lock()

from .paths import app_root

_ROOT = app_root()
STOCK_DB_PATH = os.path.join(_ROOT, "stock_db.json")
MIN_RETAL_LENGTH = 200.0  # mm — minimum leftover length to keep as retal


@dataclass
class StockBar:
    """A bar/tube in stock with cost parameters."""
    id: str
    profile_name: str
    material_desc: str
    length: float
    quantity: int = 1
    usage_count: int = 0
    is_retal: bool = False
    retal_length: float = 0.0
    quality: str = ""
    espesor: float = 0.0
    kg_por_m: float = 0.0
    precio_kg: float = 0.0
    precio_m: float = 0.0
    precio_barra: float = 0.0
    peso_especifico: float = 7.85
    fields: Dict[str, float] = field(default_factory=dict)
    notes: str = ""
    custom_display_name: str = ""
    creation_job_name: str = ""
    used_in_job_names: List[str] = field(default_factory=list)

    @property
    def material(self) -> str:
        """Canonical alias for the material name (stored as ``material_desc``).

        Lets the rest of the app refer to ``bar.material`` consistently with
        ``MaterialContext.material`` and ``Material.name`` without a risky
        SQLite column rename. See TODO.md §0.
        """
        return self.material_desc

    @material.setter
    def material(self, value: str) -> None:
        self.material_desc = value

    # ``blocked`` is stored inside ``fields`` (key ``_blocked``) so it round-trips
    # through the existing ``fields_json`` column without a DB schema migration.
    # A blocked bar stays in stock but cannot be picked for a nesting layout.
    @property
    def blocked(self) -> bool:
        return bool(self.fields.get("_blocked", 0.0))

    @blocked.setter
    def blocked(self, value: bool) -> None:
        if value:
            self.fields["_blocked"] = 1.0
        else:
            self.fields.pop("_blocked", None)

    @property
    def full_name(self) -> str:
        """Canonical "profile · material · quality" representation.

        Use this anywhere a bar is shown as a profile/material selection
        (selectors, tables, window titles). For the unique physical-bar code
        (e.g. ``ACERO-000001-00``) use :pyattr:`display_name` instead.
        """
        from .naming import format_full_name
        return format_full_name(self.profile_name, self.material_desc, self.quality)

    @property
    def display_name(self) -> str:
        """Unique physical-bar code: ``MATERIAL-NNNNNN-SS`` (id + usage count).

        This identifies one specific bar in stock. For the human-readable
        profile/material representation use :pyattr:`full_name`.
        """
        base = self.material_desc.upper()
        # Bars/retals get zero-padded numeric ids, but imported/legacy rows may
        # carry arbitrary string ids. Only reformat when the tail is numeric —
        # display_name is read on every stock-table render, so a ValueError here
        # would crash the whole table.
        tail = self.id[-6:]
        num = f"{int(tail):06d}" if tail.isdigit() else self.id
        suffix = f"{self.usage_count:02d}"
        return f"{base}-{num}-{suffix}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "profile_name": self.profile_name,
            "material_desc": self.material_desc,
            "length": self.length,
            "quantity": self.quantity,
            "usage_count": self.usage_count,
            "is_retal": self.is_retal,
            "retal_length": self.retal_length,
            "quality": self.quality,
            "espesor": self.espesor,
            "kg_por_m": self.kg_por_m,
            "precio_kg": self.precio_kg,
            "precio_m": self.precio_m,
            "precio_barra": self.precio_barra,
            "peso_especifico": self.peso_especifico,
            "fields": self.fields,
            "notes": self.notes,
            "custom_display_name": self.custom_display_name,
            "creation_job_name": self.creation_job_name,
            "used_in_job_names": self.used_in_job_names,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StockBar":
        return cls(
            id=str(d.get("id", "")),
            profile_name=str(d.get("profile_name", "")),
            material_desc=str(d.get("material_desc", "")),
            length=float(d.get("length", 6000)),
            quantity=int(d.get("quantity", 1)),
            usage_count=int(d.get("usage_count", 0)),
            is_retal=bool(d.get("is_retal", False)),
            retal_length=float(d.get("retal_length", 0)),
            quality=str(d.get("quality", "")),
            espesor=float(d.get("espesor", 0)),
            kg_por_m=float(d.get("kg_por_m", 0)),
            precio_kg=float(d.get("precio_kg", 0)),
            precio_m=float(d.get("precio_m", 0)),
            precio_barra=float(d.get("precio_barra", 0)),
            peso_especifico=float(d.get("peso_especifico", 7.85)),
            fields=dict(d.get("fields", {})),
            notes=str(d.get("notes", "")),
            custom_display_name=str(d.get("custom_display_name", "")),
            creation_job_name=str(d.get("creation_job_name", "")),
            used_in_job_names=list(d.get("used_in_job_names", [])),
        )


@dataclass
class StockDB:
    """Full stock database."""
    bars: List[StockBar] = field(default_factory=list)
    min_retal_length: float = 200.0

    def to_dict(self) -> dict:
        return {
            "bars": [b.to_dict() for b in self.bars],
            "min_retal_length": self.min_retal_length,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StockDB":
        return cls(
            bars=[StockBar.from_dict(b) for b in d.get("bars", [])],
            min_retal_length=float(d.get("min_retal_length", 200)),
        )


_db: Optional[StockDB] = None


_META_MIN_RETAL = "stock_min_retal_length"


def load_stock() -> StockDB:
    """Load the stock inventory from the SQLite store (nestify_geometry.db).

    One-time migration: if the DB has no stock rows but a legacy
    ``stock_db.json`` exists, its bars are imported and the JSON retired
    (renamed ``*.migrated``). The in-memory cache, dataclasses and public API
    are unchanged, so the UI is unaffected.
    """
    global _db
    with _lock:
        from nestify.database import get_geometry_db
        db = get_geometry_db()
        rows = db.get_all_stock()
        min_retal = db.get_meta(_META_MIN_RETAL)
        if not rows and os.path.isfile(STOCK_DB_PATH):
            try:
                with open(STOCK_DB_PATH, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
                legacy = StockDB.from_dict(raw)
                if legacy.bars:
                    db.replace_all_stock([b.to_dict() for b in legacy.bars])
                    rows = db.get_all_stock()
                db.set_meta(_META_MIN_RETAL, str(legacy.min_retal_length))
                min_retal = str(legacy.min_retal_length)
                _log.info("Migrated %d stock bars from JSON to SQLite", len(legacy.bars))
            except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
                _log.warning("Could not import legacy stock JSON: %s", exc)
            _retire_legacy_json(STOCK_DB_PATH)
        _db = StockDB(
            bars=[StockBar.from_dict(r) for r in rows],
            min_retal_length=float(min_retal) if min_retal else MIN_RETAL_LENGTH,
        )
        return _db


def save_stock(db: Optional[StockDB] = None) -> bool:
    """Persist the whole stock inventory to the SQLite store."""
    global _db
    with _lock:
        if db is not None:
            _db = db
        if _db is None:
            _db = StockDB()
        try:
            from nestify.database import get_geometry_db
            gdb = get_geometry_db()
            gdb.replace_all_stock([b.to_dict() for b in _db.bars])
            gdb.set_meta(_META_MIN_RETAL, str(_db.min_retal_length))
            return True
        except Exception as exc:  # noqa: BLE001 — persistence must never crash the UI
            _log.error("Could not save stock to SQLite: %s", exc)
            return False


def _retire_legacy_json(path: str) -> None:
    """Rename a migrated legacy JSON to ``*.migrated`` (kept as backup, not
    re-imported). Best-effort: failures are non-fatal."""
    try:
        if os.path.isfile(path):
            os.replace(path, path + ".migrated")
    except OSError as exc:
        _log.warning("Could not retire legacy JSON %s: %s", path, exc)


def get_stock() -> StockDB:
    """Get current stock (loads if needed)."""
    if _db is None:
        return load_stock()
    return _db


def add_bar(profile_name: str, material_desc: str, length: float,
            quantity: int = 1, fields: Optional[Dict[str, float]] = None,
            job_name: str = "",
            **kwargs) -> StockBar:
    """Add a new bar to stock."""
    db = get_stock()
    next_id = f"{max((int(b.id) for b in db.bars if b.id.isdigit()), default=0) + 1:06d}"
    bar = StockBar(
        id=next_id,
        profile_name=profile_name,
        material_desc=material_desc,
        length=length,
        quantity=quantity,
        fields=fields or {},
        creation_job_name=job_name,
        **kwargs,
    )
    db.bars.append(bar)
    save_stock()
    return bar


def update_bar(bar_id: str, **kwargs) -> bool:
    """Update an existing stock bar."""
    db = get_stock()
    for bar in db.bars:
        if bar.id == bar_id:
            for key, value in kwargs.items():
                if hasattr(bar, key):
                    setattr(bar, key, value)
            save_stock()
            return True
    return False


def remove_bar(bar_id: str) -> bool:
    """Remove a bar from stock."""
    db = get_stock()
    db.bars = [b for b in db.bars if b.id != bar_id]
    save_stock()
    return True


def _next_retal_sequence(material: str, quality: str) -> int:
    """Find next sequential number for remnants matching material/quality."""
    db = get_stock()
    prefix = f"RET-{material.upper()}-{quality.upper()}-"
    max_seq = 0
    for b in db.bars:
        name = b.custom_display_name or ""
        if name.startswith(prefix):
            try:
                seq = int(name[len(prefix):])
                max_seq = max(max_seq, seq)
            except ValueError:
                pass
    return max_seq + 1


def add_retal(profile_name: str, material_desc: str, retal_length: float,
              parent_id: str = "", quality: str = "",
              job_name: str = "") -> Optional[StockBar]:
    """Add a remnant (retal) to stock if it meets minimum length."""
    db = get_stock()
    if retal_length < db.min_retal_length:
        return None
    next_id = f"{max((int(b.id) for b in db.bars if b.id.isdigit()), default=0) + 1:06d}"
    seq = _next_retal_sequence(material_desc, quality)
    display_name = f"RET-{material_desc.upper()}-{quality.upper()}-{seq:04d}"
    bar = StockBar(
        id=next_id,
        profile_name=profile_name,
        material_desc=material_desc,
        length=retal_length,
        quantity=1,
        is_retal=True,
        retal_length=retal_length,
        quality=quality,
        custom_display_name=display_name,
        creation_job_name=job_name,
    )
    db.bars.append(bar)
    save_stock()
    return bar


def delete_retales(material_desc: str = "", quality: str = "") -> int:
    """Remove remnant (retal) bars from stock and return how many were removed.

    With no arguments, removes every remnant. When ``material_desc`` is given,
    only remnants of that material (and optional ``quality``) are removed.
    """
    db = get_stock()
    md = material_desc.strip().lower()
    ql = quality.strip().lower()

    def _match(b: StockBar) -> bool:
        if not b.is_retal:
            return False
        if md and b.material_desc.strip().lower() != md:
            return False
        if ql and (b.quality or "").strip().lower() != ql:
            return False
        return True

    before = len(db.bars)
    db.bars = [b for b in db.bars if not _match(b)]
    removed = before - len(db.bars)
    if removed:
        save_stock()
    return removed


def get_available_bars(profile_name: str = "", min_length: float = 0) -> List[StockBar]:
    """Get available bars from stock, optionally filtered."""
    db = get_stock()
    result = []
    for b in db.bars:
        if b.quantity <= 0:
            continue
        if profile_name and b.profile_name.lower() != profile_name.lower():
            continue
        effective_length = b.retal_length if b.is_retal else b.length
        if effective_length < min_length:
            continue
        result.append(b)
    return result


def deduct_bar(bar_id: str, used_length: float, generate_retal: bool = True,
               job_name: str = "") -> Optional[StockBar]:
    """Use a bar: deduct quantity, optionally generate retal."""
    db = get_stock()
    for b in db.bars:
        if b.id == bar_id and b.quantity > 0:
            b.quantity -= 1
            b.usage_count += 1
            if job_name and job_name not in b.used_in_job_names:
                b.used_in_job_names.append(job_name)
            remaining = (b.retal_length if b.is_retal else b.length) - used_length
            retal = None
            if generate_retal and remaining >= db.min_retal_length:
                retal = add_retal(b.profile_name, b.material_desc, remaining, b.id,
                                  quality=b.quality, job_name=job_name)
            save_stock()
            return retal
    return None


def restore_bar(bar_id: str, quantity: int = 1) -> None:
    """Return bars to stock (reverse a previous deduct_bar call)."""
    db = get_stock()
    for b in db.bars:
        if b.id == bar_id:
            b.quantity += quantity
            save_stock()
            return


def get_profiles_in_stock() -> List[str]:
    """Get unique profile names in stock."""
    db = get_stock()
    return list(set(b.profile_name for b in db.bars if b.quantity > 0))


def get_bars_by_creation_job(job_name: str) -> List[StockBar]:
    """Return all bars (including retales) whose creation_job_name matches job_name."""
    if not job_name:
        return []
    db = get_stock()
    return [b for b in db.bars if b.creation_job_name == job_name]
