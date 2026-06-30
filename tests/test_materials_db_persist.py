"""
test_materials_db_persist.py — specific_weight DB round-trip (Fix 21).

Verifies that:
  1. specific_weight is stored and retrieved correctly via get_all_materials /
     replace_all_materials.
  2. Rows inserted without a specific_weight key default to 7.85.
  3. A pre-migration DB (column absent) gets the column added automatically and
     existing rows get the default value 7.85.
"""
import sqlite3
import pytest


@pytest.fixture()
def db(tmp_path):
    from nestify.database import GeometryDB
    return GeometryDB(str(tmp_path / "test_geo.db"))


def test_specific_weight_round_trips(db):
    materials = [
        {"id": "0001", "name": "Acero", "quality": "S275", "category": "",
         "specific_weight": 7.85},
        {"id": "0002", "name": "Aluminio", "quality": "6082", "category": "",
         "specific_weight": 2.70},
    ]
    db.replace_all_materials(materials)
    rows = db.get_all_materials()
    assert len(rows) == 2
    assert abs(rows[0]["specific_weight"] - 7.85) < 1e-9
    assert abs(rows[1]["specific_weight"] - 2.70) < 1e-9


def test_missing_specific_weight_key_defaults_to_7_85(db):
    """Dict without 'specific_weight' key should default to 7.85 on insert."""
    db.replace_all_materials([
        {"id": "0001", "name": "Custom", "quality": "", "category": ""},
    ])
    rows = db.get_all_materials()
    assert abs(rows[0]["specific_weight"] - 7.85) < 1e-9


def test_migration_adds_column_to_existing_db(tmp_path):
    """Simulate a pre-migration DB (column absent) and verify migration fills it."""
    db_path = str(tmp_path / "legacy.db")

    # Create a schema without the specific_weight column.
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE materials (
            id       TEXT PRIMARY KEY,
            name     TEXT NOT NULL DEFAULT '',
            quality  TEXT DEFAULT '',
            category TEXT DEFAULT ''
        )
    """)
    conn.execute(
        "INSERT INTO materials (id, name, quality, category) VALUES (?, ?, ?, ?)",
        ("0001", "Acero", "S235", ""),
    )
    conn.commit()
    conn.close()

    # Open via GeometryDB — _migrate_materials_table should add the column.
    from nestify.database import GeometryDB
    db = GeometryDB(db_path)
    rows = db.get_all_materials()
    assert len(rows) == 1
    assert rows[0]["name"] == "Acero"
    # Existing row gets SQL DEFAULT (7.85) when the column is added via ALTER TABLE.
    assert abs(rows[0]["specific_weight"] - 7.85) < 1e-9
