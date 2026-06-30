"""
test_tab_perfiles_catalog.py — §21.2 catalogue profiles in the Costs selector.

Selecting a catalogue ("custom:<name>") profile must:
  • resolve a valid tipo (so the cost calc runs instead of bailing early),
  • show a read-only summary + a single "Edit material" button (no editable
    geometry fields),
  • feed weight/section from entry.meta so pricing produces a non-zero cost.
The pricing path (calcular_resultado) is reused verbatim — no engine change.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets")

from nestube import app_config
from nestube.app_config import AppPreferences, CustomProfileEntry
from nestube.models import AppState, TipoPerfil
from nestube.ui_qt.tab_perfiles import TabPerfiles, _tipo_for_geometry


@pytest.fixture(scope="module", autouse=True)
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    prefs = AppPreferences()
    prefs.custom_profiles = [
        CustomProfileEntry(
            id="catalog-ipe-100", name="IPE 100",
            meta={
                "material": "Acero al Carbono",
                "specific_weight": 7.85,
                "geometry_type": "Viga I",
                "h": 100, "b": 55, "tw": 4.1, "tf": 5.7,
                "seccion_cm2": 10.3, "peso_lineal_kg_m": 8.1,
                "macizo": False,
            },
        ),
    ]
    monkeypatch.setattr(app_config, "get", lambda: prefs)
    monkeypatch.setattr(app_config, "save", lambda p=None: True)
    monkeypatch.setattr(app_config, "PROFILES_DIR", str(tmp_path))
    return prefs


def test_geometry_to_tipo_mapping():
    assert _tipo_for_geometry("Redondo") == TipoPerfil.REDONDO
    assert _tipo_for_geometry("Viga I") == TipoPerfil.H
    assert _tipo_for_geometry("Viga U") == TipoPerfil.U
    assert _tipo_for_geometry("Angular") == TipoPerfil.L
    assert _tipo_for_geometry("Cuadrado") == TipoPerfil.RECTANGULAR
    assert _tipo_for_geometry("nonexistent") == TipoPerfil.RECTANGULAR


def test_selecting_catalog_profile_resolves_tipo_and_hides_geometry(isolated):
    tab = TabPerfiles(state=AppState())
    tab._select_profile("custom:IPE 100")

    # tipo resolved (Viga I → H) so the cost calc won't bail out
    assert tab._tipo == TipoPerfil.H
    assert tab._catalog_entry is not None
    assert tab._catalog_entry.name == "IPE 100"

    # Editable geometry inputs are gone; wall-thickness / macizo hidden.
    assert tab._dim_entries == {}
    assert tab.ui.field_espesor.isHidden()
    assert tab.ui.cb_macizo.isHidden()

    # Weight auto-filled from meta so costing has a basis.
    assert tab.ui.e_kg_m.text() == "8.1"


def test_catalog_config_prices_from_meta(isolated):
    tab = TabPerfiles(state=AppState())
    tab._select_profile("custom:IPE 100")
    tab.ui.e_precio_kg.setText("2.0")  # €/kg

    perfil = tab._build_config()
    assert perfil is not None
    assert perfil.dimensiones.tipo == TipoPerfil.H
    # kg/m carried from meta → weight basis for pricing.
    assert perfil.material.kg_por_m == pytest.approx(8.1)
    assert perfil.material.precio_kg == pytest.approx(2.0)

    # Reuse the real cost path: a 1000 mm cut weighs 8.1 kg → 16.2 € material.
    from nestube.logic import calcular_resultado
    from nestube.models import Corte
    corte = Corte(descripcion="t", largo=1000, cantidad=1)
    res = calcular_resultado(corte, perfil, [[1000]], 6000, 0)
    assert res.kg_ud == pytest.approx(8.1, rel=1e-3)
    assert res.precio_material_ud == pytest.approx(16.2, rel=1e-3)


def test_switching_back_to_builtin_restores_geometry_fields(isolated):
    tab = TabPerfiles(state=AppState())
    tab._select_profile("custom:IPE 100")
    assert tab._catalog_entry is not None

    tab._select_profile("builtin:rectangular")
    assert tab._catalog_entry is None
    assert tab._tipo == TipoPerfil.RECTANGULAR
    # Editable dimension fields are back.
    assert set(tab._dim_entries.keys()) == {"lado_a", "lado_b"}
    assert not tab.ui.field_espesor.isHidden()
