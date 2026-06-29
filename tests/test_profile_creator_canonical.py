"""
test_profile_creator_canonical.py — §21.5 ProfileCreator canonical fields.

Verifies:
  • a catalogue profile (drawing_shapes=[], meta has geometry_type) seeds
    editable ProfileShapes from section_contours instead of a blank canvas,
  • _save_profile emits canonical field_defaults keyed by "<token> (mm)".
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from nestify.ui_qt.dialogs.profile_creator import ProfileCreator


@pytest.fixture(scope="module", autouse=True)
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_catalogue_meta_seeds_editable_shapes():
    meta = {
        "geometry_type": "Viga I", "h": 100, "b": 55, "tw": 4.1, "tf": 5.7,
        "macizo": False,
    }
    creator = ProfileCreator(None, initial_shapes=[], initial_meta=meta)
    # An I-beam outer contour must produce at least one editable polygon.
    assert creator._shapes, "catalogue profile opened with a blank canvas"
    assert any(s.shape_type == "polygon" for s in creator._shapes)


def test_save_emits_canonical_field_defaults():
    meta = {
        "geometry_type": "Viga I", "h": 100, "b": 55, "tw": 4.1, "tf": 5.7,
    }
    captured = {}
    creator = ProfileCreator(None, on_save=lambda d: captured.update(d),
                             initial_shapes=[], initial_meta=meta)
    # Fill the canonical numeric inputs the way the user would.
    creator._meta["h"].setText("100")
    creator._meta["b"].setText("55")
    creator._meta["tw"].setText("4.1")
    creator._meta["tf"].setText("5.7")
    creator._meta["seccion_cm2"].setText("10.3")
    creator._meta["peso_lineal_kg_m"].setText("8.1")
    creator._save_profile()

    fd = captured.get("field_defaults", {})
    assert fd.get("h (mm)") == pytest.approx(100.0)
    assert fd.get("tf (mm)") == pytest.approx(5.7)
    # Canonical numeric meta is coerced to floats and geometry_type carried.
    m = captured.get("meta", {})
    assert m.get("seccion_cm2") == pytest.approx(10.3)
    assert m.get("peso_lineal_kg_m") == pytest.approx(8.1)
    assert m.get("geometry_type") == "Viga I"
    # The canonical labels are present in fields too.
    assert "h (mm)" in captured.get("fields", [])
