"""
tests/test_packing.py
1D bin-packing tests (logic.calcular_barras). Locks the FFD/BFD/NFD behaviour
and the regression where a full-length piece was silently dropped when a
non-zero gap (kerf + margin) pushed its effective length past the bar.
"""
import pytest

from nestube.logic import calcular_barras, eficiencia_barras
from nestube.models import Corte


def _corte(largo: float, cantidad: int = 1, desc: str = "") -> Corte:
    c = Corte()
    c.descripcion = desc or f"c{largo}"
    c.largo = float(largo)
    c.cantidad = cantidad
    return c


def _all_placed(barras) -> int:
    return sum(len(b) for b in barras)


@pytest.mark.parametrize("system", ["ffd", "bfd", "nfd"])
def test_no_gap_basic(system):
    barras = calcular_barras(6000.0, [_corte(2000, 6)], system=system, gap=0.0)
    assert _all_placed(barras) == 6
    # 6 × 2000 = 12000 → exactly two 6000 bars.
    assert len(barras) == 2


@pytest.mark.parametrize("system", ["ffd", "bfd", "nfd"])
def test_full_length_piece_with_gap_not_dropped(system):
    """Regression: a piece whose length equals the bar must not be dropped
    when gap > 0 (its effective length largo + gap exceeds the bar)."""
    cortes = [_corte(6000, 1, "full"), _corte(2000, 3, "small")]
    barras = calcular_barras(6000.0, cortes, system=system, gap=53.0)
    assert _all_placed(barras) == 4, f"{system} dropped a piece: {barras}"
    # The full-length piece must occupy a bar on its own.
    assert any(b == [6000.0] for b in barras), barras


@pytest.mark.parametrize("system", ["ffd", "bfd", "nfd"])
def test_multiple_full_length_pieces_with_gap(system):
    cortes = [_corte(6000, 3, "full")]
    barras = calcular_barras(6000.0, cortes, system=system, gap=53.0)
    assert _all_placed(barras) == 3
    assert all(b == [6000.0] for b in barras), barras


def test_pieces_longer_than_bar_are_excluded():
    barras = calcular_barras(6000.0, [_corte(7000, 2)], system="ffd", gap=0.0)
    assert barras == []


@pytest.mark.parametrize("system", ["ffd", "bfd", "nfd"])
def test_gap_round_trips_to_true_lengths(system):
    """The returned cut lengths must be the true piece sizes, not inflated by
    the gap used internally for packing."""
    cortes = [_corte(1500, 4)]
    barras = calcular_barras(6000.0, cortes, system=system, gap=100.0)
    for bar in barras:
        for piece in bar:
            assert piece == 1500.0


def test_efficiency_within_bounds():
    cortes = [_corte(2000, 6), _corte(6000, 1)]
    barras = calcular_barras(6000.0, cortes, system="ffd", gap=53.0)
    eff = eficiencia_barras(barras, 6000.0)
    assert 0.0 <= eff <= 100.0
