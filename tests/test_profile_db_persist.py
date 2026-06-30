"""
test_profile_db_persist.py — custom profiles persist in the SQLite profiles
table (drawing/metadata + thumbnail), with safe upsert/delete semantics.
"""
import pytest


@pytest.fixture()
def db(tmp_path):
    from nestube.database import GeometryDB
    return GeometryDB(str(tmp_path / "test_geo.db"))


def test_upsert_and_get_round_trip(db):
    entry = {"id": "p1", "name": "IPE 200", "fields": ["A", "B"],
             "wkt": "POLYGON((0 0,1 0,1 1,0 0))", "meta": {"kg": 8.1}}
    db.upsert_profile(entry)
    rows = db.get_all_profiles()
    assert len(rows) == 1
    assert rows[0]["id"] == "p1"
    assert rows[0]["name"] == "IPE 200"
    assert rows[0]["meta"]["kg"] == 8.1


def test_upsert_updates_existing_row(db):
    db.upsert_profile({"id": "p1", "name": "Old"})
    db.upsert_profile({"id": "p1", "name": "New", "fields": ["X"]})
    rows = db.get_all_profiles()
    assert len(rows) == 1  # updated in place, not duplicated
    assert rows[0]["name"] == "New"


def test_image_bytes_persist_and_are_preserved_on_recordonly_upsert(db):
    png = b"\x89PNG\r\n\x1a\n-thumbnail-"
    db.upsert_profile({"id": "p1", "name": "WithImg", "image": "p1.png"}, png)
    assert db.get_profile_image("p1") == png
    # A record-only upsert (image_data=None) must keep the stored thumbnail.
    db.upsert_profile({"id": "p1", "name": "Renamed", "image": "p1.png"})
    assert db.get_profile_image("p1") == png
    assert db.get_all_profiles()[0]["name"] == "Renamed"


def test_delete_profile(db):
    db.upsert_profile({"id": "p1", "name": "A"})
    db.upsert_profile({"id": "p2", "name": "B"})
    db.delete_profile("p1")
    rows = db.get_all_profiles()
    assert [r["id"] for r in rows] == ["p2"]
    assert db.get_profile_image("p1") is None
