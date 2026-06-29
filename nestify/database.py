"""
nestify/database.py
SQLite-backed persistence for irregular piece geometries.
Stores polygons as WKT (Well-Known Text) via Shapely.
No temporary DXF files — geometry lives natively as WKT in the DB.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from shapely import wkt as shapely_wkt
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid

from .paths import app_root
from . import db_settings

_log = logging.getLogger(__name__)

DB_FILENAME = "nestify_geometry.db"
# The active database location comes from the bootstrap settings (so it can live
# on a shared server and be switched), falling back to the app-root default.
DB_PATH = db_settings.get().resolved_db_path()

_SCHEMA_VERSION = 1


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class GeometryRecord:
    """A unique geometry stored once and referenced by many pieces."""
    id: int = 0
    wkt: str = ""
    wkt_hash: str = ""
    bounds_min_x: float = 0.0
    bounds_min_y: float = 0.0
    bounds_max_x: float = 0.0
    bounds_max_y: float = 0.0
    area: float = 0.0
    created_at: str = ""

    def to_polygon(self) -> Polygon:
        return shapely_wkt.loads(self.wkt)


@dataclass
class PieceRecord:
    """A piece definition referencing a geometry."""
    id: int = 0
    geometry_id: int = 0
    name: str = ""
    description: str = ""
    material: str = ""
    quality: str = ""
    thickness: float = 0.0
    quantity: int = 1
    created_at: str = ""


@dataclass
class JobRecord:
    """A nesting job."""
    id: int = 0
    name: str = ""
    bar_length: float = 6000.0
    tube_circumference: float = 0.0
    kerf: float = 3.0
    margin: float = 5.0
    created_at: str = ""
    state_json: str = ""
    description: str = ""
    client: str = ""
    offer: str = ""
    order_ref: str = ""
    file_path: str = ""
    updated_at: str = ""


@dataclass
class PlacementRecord:
    """A piece placed on a bar within a job."""
    id: int = 0
    job_id: int = 0
    piece_id: int = 0
    bar_index: int = 0
    x_offset: float = 0.0
    y_offset: float = 0.0
    rotation_deg: float = 0.0
    flipped_h: bool = False
    flipped_v: bool = False


@dataclass
class StockBarRecord:
    """A bar in stock (tubes available for nesting)."""
    id: int = 0
    profile_name: str = ""
    material: str = ""
    quality: str = ""
    length: float = 6000.0
    circumference: float = 0.0
    quantity: int = 1
    is_remnant: bool = False
    cost_per_unit: float = 0.0
    notes: str = ""


# ── Database connection ──────────────────────────────────────────────────────

class GeometryDB:
    """SQLite database for geometry persistence with WKT deduplication."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            os.makedirs(os.path.dirname(self._db_path) or ".", exist_ok=True)
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._init_schema()
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _init_schema(self) -> None:
        c = self.connect()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS geometries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                wkt         TEXT NOT NULL,
                wkt_hash    TEXT NOT NULL UNIQUE,
                bounds_min_x REAL DEFAULT 0,
                bounds_min_y REAL DEFAULT 0,
                bounds_max_x REAL DEFAULT 0,
                bounds_max_y REAL DEFAULT 0,
                area        REAL DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS pieces (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                geometry_id INTEGER NOT NULL REFERENCES geometries(id),
                name        TEXT NOT NULL DEFAULT '',
                description TEXT DEFAULT '',
                material    TEXT DEFAULT '',
                quality     TEXT DEFAULT '',
                thickness   REAL DEFAULT 0,
                quantity    INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT NOT NULL DEFAULT '',
                bar_length          REAL DEFAULT 6000,
                tube_circumference  REAL DEFAULT 0,
                kerf                REAL DEFAULT 3,
                margin              REAL DEFAULT 5,
                created_at          TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS placements (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                piece_id    INTEGER NOT NULL REFERENCES pieces(id),
                bar_index   INTEGER DEFAULT 0,
                x_offset    REAL DEFAULT 0,
                y_offset    REAL DEFAULT 0,
                rotation_deg REAL DEFAULT 0,
                flipped_h   INTEGER DEFAULT 0,
                flipped_v   INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS stock_bars (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name    TEXT DEFAULT '',
                material        TEXT DEFAULT '',
                quality         TEXT DEFAULT '',
                length          REAL DEFAULT 6000,
                circumference   REAL DEFAULT 0,
                quantity        INTEGER DEFAULT 1,
                is_remnant      INTEGER DEFAULT 0,
                cost_per_unit   REAL DEFAULT 0,
                notes           TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS materials (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL DEFAULT '',
                quality         TEXT DEFAULT '',
                category        TEXT DEFAULT '',
                specific_weight REAL DEFAULT 7.85
            );

            CREATE TABLE IF NOT EXISTS stock (
                id                  TEXT PRIMARY KEY,
                profile_name        TEXT DEFAULT '',
                material_desc       TEXT DEFAULT '',
                length              REAL DEFAULT 6000,
                quantity            INTEGER DEFAULT 1,
                usage_count         INTEGER DEFAULT 0,
                is_retal            INTEGER DEFAULT 0,
                retal_length        REAL DEFAULT 0,
                quality             TEXT DEFAULT '',
                espesor             REAL DEFAULT 0,
                kg_por_m            REAL DEFAULT 0,
                precio_kg           REAL DEFAULT 0,
                precio_m            REAL DEFAULT 0,
                precio_barra        REAL DEFAULT 0,
                peso_especifico     REAL DEFAULT 7.85,
                fields_json         TEXT DEFAULT '{}',
                notes               TEXT DEFAULT '',
                custom_display_name TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS profiles (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL DEFAULT '',
                data        TEXT NOT NULL DEFAULT '{}',
                image_data  BLOB
            );

            CREATE TABLE IF NOT EXISTS app_meta (
                key     TEXT PRIMARY KEY,
                value   TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_geometries_hash ON geometries(wkt_hash);
            CREATE INDEX IF NOT EXISTS idx_pieces_geom ON pieces(geometry_id);
            CREATE INDEX IF NOT EXISTS idx_placements_job ON placements(job_id);
            CREATE INDEX IF NOT EXISTS idx_stock_material ON stock_bars(material, quality);
        """)
        c.commit()
        self._migrate_jobs_table(c)
        self._migrate_materials_table(c)

    # Allowlist of valid column names for DDL migrations (prevents f-string SQLi if list ever grows)
    _SAFE_COL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def _migrate_jobs_table(self, c: sqlite3.Connection) -> None:
        """Add new columns to jobs table if they don't exist (safe migration)."""
        existing = {row[1] for row in c.execute("PRAGMA table_info(jobs)").fetchall()}
        migrations = [
            ("state_json",  "TEXT DEFAULT ''"),
            ("description", "TEXT DEFAULT ''"),
            ("client",      "TEXT DEFAULT ''"),
            ("offer",       "TEXT DEFAULT ''"),
            ("order_ref",   "TEXT DEFAULT ''"),
            ("file_path",   "TEXT DEFAULT ''"),
            ("updated_at",  "TEXT DEFAULT (datetime('now'))"),
        ]
        try:
            for col, typedef in migrations:
                if not self._SAFE_COL_RE.match(col):
                    raise ValueError(f"Invalid migration column name: {col!r}")
                if col not in existing:
                    c.execute(f"ALTER TABLE jobs ADD COLUMN {col} {typedef}")
            c.commit()
        except Exception:
            c.rollback()
            raise

    def _migrate_materials_table(self, c: sqlite3.Connection) -> None:
        """Add new columns to the materials table if they don't exist.

        ``specific_weight`` was added after the original schema shipped; without
        this migration density edits were silently dropped on reload because the
        column did not exist for existing databases.
        """
        existing = {row[1] for row in c.execute("PRAGMA table_info(materials)").fetchall()}
        migrations = [
            ("specific_weight", "REAL DEFAULT 7.85"),
        ]
        try:
            for col, typedef in migrations:
                if not self._SAFE_COL_RE.match(col):
                    raise ValueError(f"Invalid migration column name: {col!r}")
                if col not in existing:
                    c.execute(f"ALTER TABLE materials ADD COLUMN {col} {typedef}")
            c.commit()
        except Exception:
            c.rollback()
            raise

    # ── Geometry CRUD ────────────────────────────────────────────────────────

    @staticmethod
    def _wkt_hash(wkt_str: str) -> str:
        normalized = " ".join(wkt_str.split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def store_geometry(self, polygon: Polygon) -> int:
        """Store a polygon, deduplicating by WKT hash. Returns geometry ID."""
        polygon = make_valid(polygon)
        if isinstance(polygon, MultiPolygon):
            polygon = max(polygon.geoms, key=lambda g: g.area)

        wkt_str = polygon.wkt
        h = self._wkt_hash(wkt_str)

        c = self.connect()
        row = c.execute(
            "SELECT id FROM geometries WHERE wkt_hash = ?", (h,)
        ).fetchone()
        if row:
            return row["id"]

        bounds = polygon.bounds
        c.execute(
            """INSERT INTO geometries
               (wkt, wkt_hash, bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y, area)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (wkt_str, h, bounds[0], bounds[1], bounds[2], bounds[3], polygon.area),
        )
        c.commit()
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_geometry(self, geometry_id: int) -> Optional[GeometryRecord]:
        c = self.connect()
        row = c.execute("SELECT * FROM geometries WHERE id = ?", (geometry_id,)).fetchone()
        if not row:
            return None
        return GeometryRecord(
            id=row["id"], wkt=row["wkt"], wkt_hash=row["wkt_hash"],
            bounds_min_x=row["bounds_min_x"], bounds_min_y=row["bounds_min_y"],
            bounds_max_x=row["bounds_max_x"], bounds_max_y=row["bounds_max_y"],
            area=row["area"], created_at=row["created_at"],
        )

    def get_polygon(self, geometry_id: int) -> Optional[Polygon]:
        rec = self.get_geometry(geometry_id)
        return rec.to_polygon() if rec else None

    def find_geometry_by_wkt(self, wkt_str: str) -> Optional[int]:
        h = self._wkt_hash(wkt_str)
        c = self.connect()
        row = c.execute("SELECT id FROM geometries WHERE wkt_hash = ?", (h,)).fetchone()
        return row["id"] if row else None

    # ── Piece CRUD ───────────────────────────────────────────────────────────

    def add_piece(self, geometry_id: int, name: str = "", quantity: int = 1,
                  material: str = "", quality: str = "", thickness: float = 0.0,
                  description: str = "") -> int:
        c = self.connect()
        c.execute(
            """INSERT INTO pieces
               (geometry_id, name, description, material, quality, thickness, quantity)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (geometry_id, name, description, material, quality, thickness, quantity),
        )
        c.commit()
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_pieces(self, material: str = "", quality: str = "") -> List[PieceRecord]:
        c = self.connect()
        query = "SELECT * FROM pieces WHERE 1=1"
        params: list = []
        if material:
            query += " AND material = ?"
            params.append(material)
        if quality:
            query += " AND quality = ?"
            params.append(quality)
        rows = c.execute(query, params).fetchall()
        return [PieceRecord(
            id=r["id"], geometry_id=r["geometry_id"], name=r["name"],
            description=r["description"], material=r["material"],
            quality=r["quality"], thickness=r["thickness"],
            quantity=r["quantity"], created_at=r["created_at"],
        ) for r in rows]

    def delete_piece(self, piece_id: int) -> None:
        c = self.connect()
        c.execute("DELETE FROM pieces WHERE id = ?", (piece_id,))
        c.commit()

    # ── Job CRUD ─────────────────────────────────────────────────────────────

    def create_job(self, name: str, bar_length: float = 6000.0,
                   tube_circumference: float = 0.0,
                   kerf: float = 3.0, margin: float = 5.0) -> int:
        c = self.connect()
        c.execute(
            """INSERT INTO jobs (name, bar_length, tube_circumference, kerf, margin)
               VALUES (?, ?, ?, ?, ?)""",
            (name, bar_length, tube_circumference, kerf, margin),
        )
        c.commit()
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_job(self, job_id: int) -> Optional[JobRecord]:
        c = self.connect()
        row = c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        keys = {col[1] for col in c.execute("PRAGMA table_info(jobs)").fetchall()}
        return JobRecord(
            id=row["id"], name=row["name"],
            bar_length=row["bar_length"],
            tube_circumference=row["tube_circumference"],
            kerf=row["kerf"], margin=row["margin"],
            created_at=row["created_at"],
            state_json=row["state_json"] if "state_json" in keys else "",
            description=row["description"] if "description" in keys else "",
            client=row["client"] if "client" in keys else "",
            offer=row["offer"] if "offer" in keys else "",
            order_ref=row["order_ref"] if "order_ref" in keys else "",
            file_path=row["file_path"] if "file_path" in keys else "",
            updated_at=row["updated_at"] if "updated_at" in keys else "",
        )

    def list_jobs(self) -> List[JobRecord]:
        c = self.connect()
        rows = c.execute("SELECT * FROM jobs ORDER BY updated_at DESC, created_at DESC").fetchall()
        keys = {col[1] for col in c.execute("PRAGMA table_info(jobs)").fetchall()}
        return [JobRecord(
            id=r["id"], name=r["name"],
            bar_length=r["bar_length"],
            tube_circumference=r["tube_circumference"],
            kerf=r["kerf"], margin=r["margin"],
            created_at=r["created_at"],
            state_json=r["state_json"] if "state_json" in keys else "",
            description=r["description"] if "description" in keys else "",
            client=r["client"] if "client" in keys else "",
            offer=r["offer"] if "offer" in keys else "",
            order_ref=r["order_ref"] if "order_ref" in keys else "",
            file_path=r["file_path"] if "file_path" in keys else "",
            updated_at=r["updated_at"] if "updated_at" in keys else "",
        ) for r in rows]

    def delete_job(self, job_id: int) -> None:
        c = self.connect()
        c.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        c.commit()

    def upsert_job(
        self,
        name: str,
        state_json: str = "",
        description: str = "",
        client: str = "",
        offer: str = "",
        order_ref: str = "",
        file_path: str = "",
        job_id: Optional[int] = None,
    ) -> int:
        """Insert or update a job record.

        If *job_id* is supplied the row is always updated by primary key (the
        fastest and most reliable path when the user opened a DB job and
        Ctrl-S's back into it). Otherwise falls back to matching by file_path
        then by name, and inserts a new row only when nothing matches.
        """
        c = self.connect()
        if job_id is not None:
            c.execute(
                """UPDATE jobs SET name=?, state_json=?, description=?, client=?,
                   offer=?, order_ref=?, file_path=?, updated_at=datetime('now')
                   WHERE id=?""",
                (name, state_json, description, client, offer, order_ref, file_path, job_id),
            )
            c.commit()
            return job_id
        existing = None
        if file_path:
            existing = c.execute(
                "SELECT id FROM jobs WHERE file_path = ?", (file_path,)
            ).fetchone()
        if existing is None:
            existing = c.execute(
                "SELECT id FROM jobs WHERE name = ? AND file_path = ''", (name,)
            ).fetchone()
        if existing:
            eid = existing["id"]
            c.execute(
                """UPDATE jobs SET name=?, state_json=?, description=?, client=?,
                   offer=?, order_ref=?, file_path=?, updated_at=datetime('now')
                   WHERE id=?""",
                (name, state_json, description, client, offer, order_ref, file_path, eid),
            )
            c.commit()
            return eid
        c.execute(
            """INSERT INTO jobs
               (name, state_json, description, client, offer, order_ref, file_path)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, state_json, description, client, offer, order_ref, file_path),
        )
        c.commit()
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_job_meta(self, job_id: int, name: Optional[str] = None,
                        description: Optional[str] = None, client: Optional[str] = None,
                        offer: Optional[str] = None, order_ref: Optional[str] = None) -> None:
        """Update a job's metadata in place (does not touch state_json).

        Only the provided fields change. Column names are hardcoded literals
        (no injection); values are parameterised."""
        sets, params = [], []
        for col, val in (("name", name), ("description", description),
                         ("client", client), ("offer", offer), ("order_ref", order_ref)):
            if val is not None:
                sets.append(f"{col}=?")
                params.append(val)
        if not sets:
            return
        params.append(job_id)
        c = self.connect()
        c.execute(
            f"UPDATE jobs SET {', '.join(sets)}, updated_at=datetime('now') WHERE id=?",
            params,
        )
        c.commit()

    def get_job_state(self, job_id: int) -> Optional[dict]:
        """Return the stored AppState dict for a job, or None."""
        import json
        c = self.connect()
        row = c.execute("SELECT state_json FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row or not row["state_json"]:
            return None
        try:
            return json.loads(row["state_json"])
        except Exception:
            return None

    def list_jobs_summary(self) -> List[dict]:
        """Return lightweight job summaries (no state_json blob).

        Includes profile_name and mat_name extracted from state_json via
        json_extract (SQLite 3.9+) so the Jobs Explorer can filter by
        profile/material without loading the full state blob.
        """
        c = self.connect()
        rows = c.execute(
            """SELECT id, name, description, client, offer, order_ref,
               file_path, created_at, updated_at,
               json_extract(state_json, '$.material_contexts[0].profile_name') AS profile_name,
               json_extract(state_json, '$.material_contexts[0].material') AS mat_name
               FROM jobs ORDER BY updated_at DESC, created_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Placement CRUD ───────────────────────────────────────────────────────

    def add_placement(self, job_id: int, piece_id: int, bar_index: int = 0,
                      x_offset: float = 0.0, y_offset: float = 0.0,
                      rotation_deg: float = 0.0,
                      flipped_h: bool = False, flipped_v: bool = False) -> int:
        c = self.connect()
        c.execute(
            """INSERT INTO placements
               (job_id, piece_id, bar_index, x_offset, y_offset,
                rotation_deg, flipped_h, flipped_v)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, piece_id, bar_index, x_offset, y_offset,
             rotation_deg, int(flipped_h), int(flipped_v)),
        )
        c.commit()
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_placements(self, job_id: int) -> List[PlacementRecord]:
        c = self.connect()
        rows = c.execute(
            "SELECT * FROM placements WHERE job_id = ? ORDER BY bar_index, x_offset",
            (job_id,),
        ).fetchall()
        return [PlacementRecord(
            id=r["id"], job_id=r["job_id"], piece_id=r["piece_id"],
            bar_index=r["bar_index"], x_offset=r["x_offset"],
            y_offset=r["y_offset"], rotation_deg=r["rotation_deg"],
            flipped_h=bool(r["flipped_h"]), flipped_v=bool(r["flipped_v"]),
        ) for r in rows]

    def clear_placements(self, job_id: int) -> None:
        c = self.connect()
        c.execute("DELETE FROM placements WHERE job_id = ?", (job_id,))
        c.commit()

    # ── Stock bars ───────────────────────────────────────────────────────────

    def add_stock_bar(self, profile_name: str, material: str, quality: str,
                      length: float, circumference: float = 0.0,
                      quantity: int = 1, cost_per_unit: float = 0.0,
                      notes: str = "") -> int:
        c = self.connect()
        c.execute(
            """INSERT INTO stock_bars
               (profile_name, material, quality, length, circumference,
                quantity, cost_per_unit, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (profile_name, material, quality, length, circumference,
             quantity, cost_per_unit, notes),
        )
        c.commit()
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_stock_bars(self, material: str = "", quality: str = "",
                       min_length: float = 0.0) -> List[StockBarRecord]:
        c = self.connect()
        query = "SELECT * FROM stock_bars WHERE quantity > 0"
        params: list = []
        if material:
            query += " AND material = ?"
            params.append(material)
        if quality:
            query += " AND quality = ?"
            params.append(quality)
        if min_length > 0:
            query += " AND length >= ?"
            params.append(min_length)
        rows = c.execute(query, params).fetchall()
        return [StockBarRecord(
            id=r["id"], profile_name=r["profile_name"],
            material=r["material"], quality=r["quality"],
            length=r["length"], circumference=r["circumference"],
            quantity=r["quantity"], is_remnant=bool(r["is_remnant"]),
            cost_per_unit=r["cost_per_unit"], notes=r["notes"],
        ) for r in rows]

    # ── Materials (definitions: id/name/quality/category) ──────────────────

    def get_all_materials(self) -> List[dict]:
        """Return every material definition as a plain dict, insertion order."""
        c = self.connect()
        rows = c.execute(
            "SELECT id, name, quality, category, specific_weight "
            "FROM materials ORDER BY rowid"
        ).fetchall()
        return [
            {"id": r["id"], "name": r["name"],
             "quality": r["quality"], "category": r["category"],
             "specific_weight": r["specific_weight"]}
            for r in rows
        ]

    def replace_all_materials(self, materials: List[dict]) -> None:
        """Replace the whole materials set in one transaction (matches the
        JSON 'save the whole file' semantics the callers expect)."""
        c = self.connect()
        c.execute("DELETE FROM materials")
        c.executemany(
            "INSERT INTO materials (id, name, quality, category, specific_weight) "
            "VALUES (?, ?, ?, ?, ?)",
            [(str(m.get("id", "")), str(m.get("name", "")),
              str(m.get("quality", "")), str(m.get("category", "")),
              float(m.get("specific_weight", 7.85) or 7.85))
             for m in materials],
        )
        c.commit()

    # ── Stock inventory (full-fidelity StockBar rows) ──────────────────────

    def get_all_stock(self) -> List[dict]:
        """Return every stock bar as a StockBar.to_dict()-shaped dict.

        The dynamic per-profile dimensions live in fields_json and are parsed
        back into the ``fields`` dict so callers get exactly the JSON shape."""
        c = self.connect()
        rows = c.execute("SELECT * FROM stock ORDER BY rowid").fetchall()
        out: List[dict] = []
        for r in rows:
            try:
                fields = json.loads(r["fields_json"] or "{}")
            except (ValueError, TypeError):
                fields = {}
            out.append({
                "id": r["id"], "profile_name": r["profile_name"],
                "material_desc": r["material_desc"], "length": r["length"],
                "quantity": r["quantity"], "usage_count": r["usage_count"],
                "is_retal": bool(r["is_retal"]), "retal_length": r["retal_length"],
                "quality": r["quality"], "espesor": r["espesor"],
                "kg_por_m": r["kg_por_m"], "precio_kg": r["precio_kg"],
                "precio_m": r["precio_m"], "precio_barra": r["precio_barra"],
                "peso_especifico": r["peso_especifico"], "fields": fields,
                "notes": r["notes"], "custom_display_name": r["custom_display_name"],
            })
        return out

    def replace_all_stock(self, bars: List[dict]) -> None:
        """Replace the whole stock inventory in one transaction."""
        c = self.connect()
        c.execute("DELETE FROM stock")
        c.executemany(
            """INSERT INTO stock
               (id, profile_name, material_desc, length, quantity, usage_count,
                is_retal, retal_length, quality, espesor, kg_por_m, precio_kg,
                precio_m, precio_barra, peso_especifico, fields_json, notes,
                custom_display_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(
                str(b.get("id", "")), str(b.get("profile_name", "")),
                str(b.get("material_desc", "")), float(b.get("length", 6000)),
                int(b.get("quantity", 1)), int(b.get("usage_count", 0)),
                1 if b.get("is_retal") else 0, float(b.get("retal_length", 0)),
                str(b.get("quality", "")), float(b.get("espesor", 0)),
                float(b.get("kg_por_m", 0)), float(b.get("precio_kg", 0)),
                float(b.get("precio_m", 0)), float(b.get("precio_barra", 0)),
                float(b.get("peso_especifico", 7.85)),
                json.dumps(b.get("fields", {}) or {}, ensure_ascii=False),
                str(b.get("notes", "")), str(b.get("custom_display_name", "")),
            ) for b in bars],
        )
        c.commit()

    # ── Custom profiles (full-fidelity CustomProfileEntry rows) ────────────

    def get_all_profiles(self) -> List[dict]:
        """Return every custom profile as a CustomProfileEntry.to_dict()-shaped
        dict, in insertion order. The drawing/metadata live in the ``data``
        JSON column; the thumbnail bytes are fetched separately."""
        c = self.connect()
        rows = c.execute("SELECT data FROM profiles ORDER BY rowid").fetchall()
        out: List[dict] = []
        for r in rows:
            try:
                out.append(json.loads(r["data"] or "{}"))
            except (ValueError, TypeError):
                continue
        return out

    def get_profile_image(self, profile_id: str) -> Optional[bytes]:
        """Return the stored PNG thumbnail bytes for a profile, or None."""
        c = self.connect()
        row = c.execute(
            "SELECT image_data FROM profiles WHERE id = ?", (str(profile_id),)
        ).fetchone()
        return row["image_data"] if row and row["image_data"] is not None else None

    def upsert_profile(self, entry: dict, image_data: Optional[bytes] = None) -> None:
        """Insert or update one custom profile. ``entry`` is a
        CustomProfileEntry.to_dict(); ``image_data`` are the PNG thumbnail bytes,
        kept so the profile travels with the database and lands in backups.
        When ``image_data`` is None any previously stored image is preserved."""
        c = self.connect()
        pid = str(entry.get("id", ""))
        payload = json.dumps(entry, ensure_ascii=False)
        name = str(entry.get("name", ""))
        if image_data is None:
            c.execute(
                "INSERT INTO profiles (id, name, data) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, data=excluded.data",
                (pid, name, payload),
            )
        else:
            c.execute(
                "INSERT INTO profiles (id, name, data, image_data) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
                "name=excluded.name, data=excluded.data, image_data=excluded.image_data",
                (pid, name, payload, sqlite3.Binary(image_data)),
            )
        c.commit()

    def delete_profile(self, profile_id: str) -> None:
        c = self.connect()
        c.execute("DELETE FROM profiles WHERE id = ?", (str(profile_id),))
        c.commit()

    # ── Generic key/value app metadata ─────────────────────────────────────

    def get_meta(self, key: str, default: Optional[str] = None) -> Optional[str]:
        c = self.connect()
        row = c.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row is not None else default

    def set_meta(self, key: str, value: str) -> None:
        c = self.connect()
        c.execute(
            "INSERT INTO app_meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        c.commit()


# ── DXF Import (one-time read → Shapely → WKT → SQLite) ────────────────────

def import_dxf_to_db(
    filepath: str,
    db: GeometryDB,
    material: str = "",
    quality: str = "",
) -> List[int]:
    """
    Import all closed entities from a DXF file into the geometry database.
    Each unique polygon is stored once (deduplicated by WKT hash).
    Returns list of piece IDs created.
    """
    import ezdxf
    from shapely.geometry import Polygon, LineString

    doc = ezdxf.readfile(filepath)
    msp = doc.modelspace()
    piece_ids: List[int] = []

    for entity in msp:
        polygon = _dxf_entity_to_polygon(entity)
        if polygon is None or polygon.is_empty:
            continue

        geometry_id = db.store_geometry(polygon)
        name = getattr(entity, "dxf", None)
        layer = name.layer if name else "default"

        piece_id = db.add_piece(
            geometry_id=geometry_id,
            name=layer,
            material=material,
            quality=quality,
        )
        piece_ids.append(piece_id)

    return piece_ids


def _dxf_entity_to_polygon(entity) -> Optional[Polygon]:
    """Convert a single DXF entity to a Shapely Polygon."""
    from shapely.geometry import Polygon, LineString, Point
    import math

    dxftype = entity.dxftype()

    if dxftype == "LWPOLYLINE":
        points = list(entity.get_points(format="xy"))
        if len(points) < 3:
            return None
        if entity.closed or (
            abs(points[0][0] - points[-1][0]) < 0.01
            and abs(points[0][1] - points[-1][1]) < 0.01
        ):
            return Polygon(points)
        return None

    elif dxftype == "POLYLINE":
        points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
        if len(points) < 3:
            return None
        if entity.is_closed or (
            abs(points[0][0] - points[-1][0]) < 0.01
            and abs(points[0][1] - points[-1][1]) < 0.01
        ):
            return Polygon(points)
        return None

    elif dxftype == "CIRCLE":
        cx, cy = entity.dxf.center.x, entity.dxf.center.y
        r = entity.dxf.radius
        pts = [
            (cx + r * math.cos(2 * math.pi * i / 64),
             cy + r * math.sin(2 * math.pi * i / 64))
            for i in range(64)
        ]
        return Polygon(pts)

    elif dxftype == "ELLIPSE":
        cx, cy = entity.dxf.center.x, entity.dxf.center.y
        mx, my = entity.dxf.major_axis.x, entity.dxf.major_axis.y
        ratio = entity.dxf.ratio
        a = math.hypot(mx, my)
        b = a * ratio
        angle = math.atan2(my, mx)
        pts = []
        for i in range(64):
            t = 2 * math.pi * i / 64
            px = a * math.cos(t)
            py = b * math.sin(t)
            rx = px * math.cos(angle) - py * math.sin(angle) + cx
            ry = px * math.sin(angle) + py * math.cos(angle) + cy
            pts.append((rx, ry))
        return Polygon(pts)

    elif dxftype == "SPLINE":
        try:
            points = list(entity.flattening(0.5))
            xy = [(p.x, p.y) for p in points]
            if len(xy) < 3:
                return None
            if abs(xy[0][0] - xy[-1][0]) < 0.1 and abs(xy[0][1] - xy[-1][1]) < 0.1:
                return Polygon(xy)
        except Exception:
            pass
        return None

    elif dxftype == "HATCH":
        try:
            paths = entity.paths
            if paths:
                all_pts = []
                for path in paths:
                    if hasattr(path, "vertices"):
                        all_pts.extend((v.x, v.y) for v in path.vertices)
                if len(all_pts) >= 3:
                    return Polygon(all_pts)
        except Exception:
            pass
        return None

    return None


# ── Module-level singleton ───────────────────────────────────────────────────

_db: Optional[GeometryDB] = None


def get_geometry_db() -> GeometryDB:
    global _db
    if _db is None:
        _db = GeometryDB()
        _db.connect()
    return _db
