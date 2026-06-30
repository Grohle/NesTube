"""
test_material_i18n.py — §6 built-in material name localisation.

Built-in materials display a localised label but store their canonical (Spanish)
name, so existing jobs/stock keep matching across a language switch. Custom
materials pass through unchanged.
"""
import pytest

from nestube import i18n
from nestube.naming import BASE_MATERIALS, canonical_material, localize_material


@pytest.fixture(autouse=True)
def _restore_lang():
    prev = i18n.get_language()
    yield
    i18n.set_language(prev)


def test_localized_labels_per_language():
    i18n.set_language("en")
    assert localize_material("Acero") == "Steel"
    assert localize_material("Aluminio") == "Aluminium"
    assert localize_material("Inoxidable") == "Stainless steel"
    i18n.set_language("es")
    assert localize_material("Acero") == "Acero"
    assert localize_material("Aluminio") == "Aluminio"


def test_canonical_storage_is_language_independent():
    # Whatever the display language, the stored value is the canonical name.
    i18n.set_language("en")
    assert canonical_material("Steel") == "Acero"
    assert canonical_material("Aluminium") == "Aluminio"
    assert canonical_material("Stainless steel") == "Inoxidable"
    # Canonical or other-language labels resolve regardless of current language.
    i18n.set_language("es")
    assert canonical_material("Steel") == "Acero"      # EN label while in ES
    assert canonical_material("Acero") == "Acero"


def test_custom_material_passthrough():
    i18n.set_language("en")
    assert localize_material("Titanio especial") == "Titanio especial"
    assert canonical_material("Titanio especial") == "Titanio especial"
    assert localize_material("") == ""
    assert canonical_material("") == ""


def test_round_trip_every_base_material_every_language():
    for lang in ("en", "es"):
        i18n.set_language(lang)
        for canon, _sw in BASE_MATERIALS:
            label = localize_material(canon)
            assert canonical_material(label) == canon, (lang, canon, label)


def test_catalogue_materials_localized_per_language():
    # §20.2: catalogue-specific steel grades, added alongside the generic 3.
    i18n.set_language("en")
    assert localize_material("Acero al Carbono") == "Carbon steel"
    assert localize_material("Acero Galvanizado") == "Galvanized steel"
    i18n.set_language("es")
    assert localize_material("Acero al Carbono") == "Acero al Carbono"
    assert localize_material("Acero Galvanizado") == "Acero Galvanizado"


def test_acero_inoxidable_is_an_alias_for_inoxidable():
    # The catalogue xlsx spells stainless steel "Acero Inoxidable"; it is the
    # same material as the pre-existing generic "Inoxidable", not a new one.
    assert canonical_material("Acero Inoxidable") == "Inoxidable"
    i18n.set_language("en")
    assert canonical_material("Stainless steel") == "Inoxidable"
