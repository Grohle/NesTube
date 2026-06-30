"""
tests/test_costing.py
Cost-path tests (logic.py). The costing code had no coverage; these lock the
verified-correct formulas and the §3 fixes (F1 miter labour, F2 developed-area
m²). See docs/COST_REVIEW.md.
"""
import math

import pytest

from nestube.logic import area_seccion, perimetro_seccion, calcular_resultado
from nestube.models import (
    ConfigPerfil, PerfilDimensiones, ParametrosMaterial, ParametrosManoObra,
    Corte, TipoPerfil,
)


def _rect_perfil(**mat) -> ConfigPerfil:
    """Hollow RHS 80×40×3 with overridable material/labour params."""
    return ConfigPerfil(
        dimensiones=PerfilDimensiones(
            tipo=TipoPerfil.RECTANGULAR, lado_a=80, lado_b=40, espesor=3, macizo=False,
        ),
        material=ParametrosMaterial(**mat),
        mano_obra=ParametrosManoObra(),
    )


# ── Geometry ──────────────────────────────────────────────────────────────────

def test_area_rect_hollow():
    # 80·40 − (80−6)(40−6) = 3200 − 2516 = 684 mm²
    assert area_seccion(_rect_perfil()) == pytest.approx(684.0)


def test_perimeter_rect_and_round():
    assert perimetro_seccion(_rect_perfil()) == pytest.approx(240.0)  # 2·(80+40)
    rnd = ConfigPerfil(dimensiones=PerfilDimensiones(tipo=TipoPerfil.REDONDO, diametro=48))
    assert perimetro_seccion(rnd) == pytest.approx(math.pi * 48)


# ── Weight ──────────────────────────────────────────────────────────────────

def test_weight_from_specific_weight():
    perfil = _rect_perfil(peso_especifico=7.85)
    res = calcular_resultado(Corte(largo=1850, cantidad=4), perfil, [], 6000, 0)
    # 1850·684·7.85/1e6
    assert res.kg_ud == pytest.approx(9.9334, abs=1e-3)


def test_weight_from_kg_per_m_takes_precedence():
    perfil = _rect_perfil(kg_por_m=5.0, peso_especifico=7.85)
    res = calcular_resultado(Corte(largo=2000, cantidad=1), perfil, [], 6000, 0)
    assert res.kg_ud == pytest.approx(10.0)  # (2000/1000)·5


# ── Material pricing bases ────────────────────────────────────────────────────

def test_price_per_kg():
    perfil = _rect_perfil(peso_especifico=7.85, precio_kg=2.0)
    res = calcular_resultado(Corte(largo=1850, cantidad=1), perfil, [], 6000, 0)
    assert res.precio_material_ud == pytest.approx(9.9334 * 2.0, abs=1e-2)


def test_price_per_linear_m():
    perfil = _rect_perfil(precio_m=4.0)
    res = calcular_resultado(Corte(largo=1500, cantidad=1), perfil, [], 6000, 0)
    assert res.precio_material_ud == pytest.approx(1.5 * 4.0)  # 1.5 m · 4


def test_price_per_bar_prorated():
    perfil = _rect_perfil(precio_barra=120.0)
    res = calcular_resultado(Corte(largo=3000, cantidad=1), perfil, [], 6000, 0)
    assert res.precio_material_ud == pytest.approx(0.5 * 120.0)  # half a bar


def test_price_per_m2_uses_developed_surface():
    # F2: m² = outer perimeter (240 mm) × length / 1e6, NOT length·area.
    perfil = _rect_perfil(precio_m2=10.0)
    res = calcular_resultado(Corte(largo=1850, cantidad=1), perfil, [], 6000, 0)
    expected_m2 = 240.0 * 1850 / 1_000_000  # 0.444 m²
    assert res.m2_ud == pytest.approx(expected_m2)
    assert res.precio_material_ud == pytest.approx(expected_m2 * 10.0)


def test_profit_margin_on_material():
    perfil = _rect_perfil(precio_m=10.0, margen_beneficio=20.0)
    res = calcular_resultado(Corte(largo=1000, cantidad=1), perfil, [], 6000, 0)
    assert res.precio_material_ud == pytest.approx(10.0 * 1.20)  # 1 m · 10 · 1.2


# ── Labour (F1) ───────────────────────────────────────────────────────────────

def test_labour_straight_cut():
    # defaults: 3 min/cut, 30 €/h → 3/60·30 = 1.50 € per piece
    res = calcular_resultado(Corte(largo=1000, cantidad=1), _rect_perfil(), [], 6000, 0)
    assert res.coste_mano_obra_ud == pytest.approx(1.50)


def test_labour_scales_with_mitered_ends():
    one = calcular_resultado(
        Corte(largo=1000, cantidad=1, inglete1=True), _rect_perfil(), [], 6000, 1)
    two = calcular_resultado(
        Corte(largo=1000, cantidad=1, inglete1=True, inglete2=True), _rect_perfil(), [], 6000, 1)
    # 3·(1+0.35)/60·30 = 2.025 ; 3·(1+0.70)/60·30 = 2.55
    assert one.coste_mano_obra_ud == pytest.approx(2.025)
    assert two.coste_mano_obra_ud == pytest.approx(2.55)


def test_labour_is_per_piece_not_inflated_by_other_lines():
    # F1 regression: a line's labour must not depend on the job-wide miter count.
    perfil = _rect_perfil()
    straight = Corte(largo=1000, cantidad=1)  # no miters
    # Same cut, but pass a large job-wide n_ingletes_total (legacy arg) — must be ignored.
    res_a = calcular_resultado(straight, perfil, [], 6000, 0)
    res_b = calcular_resultado(straight, perfil, [], 6000, 99)
    assert res_a.coste_mano_obra_ud == pytest.approx(res_b.coste_mano_obra_ud) == pytest.approx(1.50)


# ── Scrap distribution ────────────────────────────────────────────────────────

def test_scrap_distribution_adds_remnant_cost():
    perfil = _rect_perfil(peso_especifico=7.85, precio_kg=2.0, repartir_retales=True)
    # one bar of 6000 with a single 2000 piece → 4000 mm leftover
    barras = [[2000.0]]
    res = calcular_resultado(Corte(largo=2000, cantidad=1), perfil, barras, 6000, 0)
    base = 2000 * 684 * 7.85 / 1e6 * 2.0          # piece material
    scrap_kg = 4000 * 684 * 7.85 / 1e6            # leftover weight
    expected = base + scrap_kg * 2.0 / 1          # +scrap value / total_piezas(=1)
    assert res.precio_material_ud == pytest.approx(expected, abs=1e-3)
