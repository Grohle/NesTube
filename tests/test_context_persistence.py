"""
test_context_persistence.py — regression for review-pass data-loss fixes.

- MaterialContext.custom_fields (per-tab extra cut columns) must survive
  to_dict/from_dict (was a dynamic attribute, lost on save/reopen).
- A user tab rename must persist: it is stored in custom_display_name, the field
  context_tab_label() honours (ctx.name alone was ignored once a profile was set).
"""
from nestify.models import MaterialContext
from nestify.naming import context_tab_label


def test_custom_fields_round_trip():
    c = MaterialContext()
    c.custom_fields = {"Peso": "12", "Lote": "A3"}
    restored = MaterialContext.from_dict(c.to_dict())
    assert restored.custom_fields == {"Peso": "12", "Lote": "A3"}


def test_custom_fields_default_empty():
    assert MaterialContext().custom_fields == {}
    assert MaterialContext.from_dict({}).custom_fields == {}


def test_rename_persists_via_custom_display_name():
    # Even with a profile/material set (which would otherwise drive the label),
    # the user's rename wins and survives a round-trip.
    c = MaterialContext(profile_name="IPE 200", material="Acero")
    c.custom_display_name = "Mi pestaña"
    assert context_tab_label(c, 0) == "Mi pestaña"
    restored = MaterialContext.from_dict(c.to_dict())
    assert context_tab_label(restored, 0) == "Mi pestaña"


def test_label_falls_back_to_derived_without_rename():
    c = MaterialContext(profile_name="IPE 200", material="Acero")
    label = context_tab_label(c, 0)
    assert "IPE 200" in label and "Acero" in label
