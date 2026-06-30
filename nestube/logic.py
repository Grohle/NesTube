"""
nestube/nestube/nestube/logic.py
Pure business logic — no UI, no globals.
"""
from __future__ import annotations

import math
from typing import List

from .models import Corte, ConfigPerfil, MaterialContext, ResultadoCorte, TipoPerfil


def _expand_cuts(longitud_barra: float, cortes: List[Corte]) -> List[float]:
    return [
        corte.largo
        for corte in cortes
        for _ in range(corte.cantidad)
        if corte.es_valido() and corte.largo <= longitud_barra
    ]


def _ffd_pack(longitud_barra: float, lista: List[float]) -> List[List[float]]:
    """First-Fit Decreasing — fill each bar with largest fitting pieces.

    Sorted once up front (descending); since removing pieces preserves the
    relative order, each pass partitions the list into "placed in this bar" and
    "carried over", keeping the carry-over sorted. This is O(n²) instead of the
    O(n²·log n) of re-sorting every bar, and avoids the O(n) list.remove() calls.
    """
    remaining = sorted(lista, reverse=True)
    barras: List[List[float]] = []
    while remaining:
        barra: List[float] = []
        carry: List[float] = []
        restante = longitud_barra
        for corte in remaining:
            if corte <= restante:
                barra.append(corte)
                restante -= corte
            else:
                carry.append(corte)
        if not barra:
            # Every remaining piece is longer than (bar − gap): with a non-zero
            # gap a piece whose length is close to the full bar can't share a bar
            # with anything, yet it still fits the bar on its own (largo ≤
            # longitud_barra is guaranteed by _expand_cuts). Place the largest
            # (remaining[0], the list is sorted descending) alone instead of
            # breaking, which would silently drop that piece — and, with this
            # loop structure, every remaining piece after it.
            barras.append([remaining[0]])
            remaining = remaining[1:]
            continue
        barras.append(barra)
        remaining = carry
    return barras


def _bfd_pack(longitud_barra: float, lista: List[float]) -> List[List[float]]:
    """Best-Fit Decreasing — place each piece in the bin with least leftover.

    The remaining space per bar is tracked incrementally in ``leftovers`` rather
    than recomputed with sum(barra) for every candidate bar, turning the inner
    scan from O(bar_size) into O(1) (overall O(n³) → O(n²))."""
    barras: List[List[float]] = []
    leftovers: List[float] = []
    for corte in sorted(lista, reverse=True):
        best_idx = -1
        best_left = longitud_barra + 1
        for i, leftover in enumerate(leftovers):
            if corte <= leftover < best_left:
                best_left = leftover
                best_idx = i
        if best_idx >= 0:
            barras[best_idx].append(corte)
            leftovers[best_idx] -= corte
        else:
            barras.append([corte])
            leftovers.append(longitud_barra - corte)
    return barras


def _nfd_pack(longitud_barra: float, lista: List[float]) -> List[List[float]]:
    """Next-Fit Decreasing — fill current bar, open new when piece doesn't fit."""
    barras: List[List[float]] = []
    current: List[float] = []
    restante = longitud_barra
    for corte in sorted(lista, reverse=True):
        if corte <= restante:
            current.append(corte)
            restante -= corte
        else:
            if current:
                barras.append(current)
            current = [corte]
            restante = longitud_barra - corte
    if current:
        barras.append(current)
    return barras


def calcular_barras(
    longitud_barra: float,
    cortes: List[Corte],
    system: str = "ffd",
    gap: float = 0.0,
) -> List[List[float]]:
    """
    Bin-packing for cut lengths.
    system: 'ffd' | 'bfd' | 'nfd'
    gap: kerf + margin between pieces (mm)
    Returns a list of bars, each bar being a list of cut lengths.
    """
    lista = _expand_cuts(longitud_barra, cortes)
    if not lista:
        return []

    effective_bar = longitud_barra
    effective_cuts = [c + gap for c in lista] if gap > 0 else lista

    match system.lower():
        case "bfd":
            barras = _bfd_pack(effective_bar, effective_cuts)
        case "nfd":
            barras = _nfd_pack(effective_bar, effective_cuts)
        case _:
            barras = _ffd_pack(effective_bar, effective_cuts)

    if gap > 0:
        barras = [[c - gap for c in barra] for barra in barras]
    return barras


def eficiencia_barras(barras: List[List[float]], longitud_barra: float) -> float:
    """Material utilisation 0–100 %."""
    if not barras or longitud_barra <= 0:
        return 0.0
    total_material = sum(sum(b) for b in barras)
    total_comprado = len(barras) * longitud_barra
    return total_material / total_comprado * 100


# ── Cross-sectional area ──────────────────────────────────────────────────────

def area_seccion(perfil: ConfigPerfil) -> float:
    """Returns cross-sectional area in mm²."""
    d = perfil.dimensiones
    e = d.espesor

    if d.tipo is None:
        return 0.0

    if d.macizo:
        match d.tipo:
            case TipoPerfil.REDONDO:
                return math.pi * (d.diametro / 2) ** 2
            case TipoPerfil.RECTANGULAR:
                return d.lado_a * d.lado_b
            case TipoPerfil.L:
                return d.lado_a * d.lado_b
            case TipoPerfil.U:
                return (d.lado_a + d.lado_c) * d.lado_b
            case TipoPerfil.H:
                return 2 * d.lado_a * d.lado_c + d.lado_b * d.lado_c
    else:
        match d.tipo:
            case TipoPerfil.REDONDO:
                r = d.diametro / 2
                return math.pi * r ** 2 - math.pi * (r - e) ** 2
            case TipoPerfil.RECTANGULAR:
                return d.lado_a * d.lado_b - (d.lado_a - 2 * e) * (d.lado_b - 2 * e)
            case TipoPerfil.L:
                return d.lado_a * e + d.lado_b * e - e ** 2
            case TipoPerfil.U:
                return (d.lado_a + d.lado_c) * e + (d.lado_b - e) * e
            case TipoPerfil.H:
                return (
                    2 * d.lado_a * e
                    + d.lado_b * d.espesor_int_H
                    + 2 * d.lado_c * e
                )

    return 0.0


# ── Cross-sectional outer perimeter ───────────────────────────────────────────

def perimetro_seccion(perfil: ConfigPerfil) -> float:
    """Outer perimeter of the cross-section in mm.

    Used for the developed-surface area (perimeter × length) priced by
    ``precio_m2``. Exact for round (π·d), rectangular and L (2·(a+b)); for the
    U and H sections it uses the bounding 2·(a+b) as a first-order
    approximation of the outer envelope.
    """
    d = perfil.dimensiones
    if d.tipo is None:
        return 0.0
    if d.tipo == TipoPerfil.REDONDO:
        return math.pi * d.diametro
    return 2.0 * (d.lado_a + d.lado_b)


# ── Per-cut cost calculation ──────────────────────────────────────────────────

def calcular_resultado(
    corte:           Corte,
    perfil:          ConfigPerfil,
    barras:          List[List[float]],
    longitud_barra:  float,
    n_ingletes_total: int,
) -> ResultadoCorte:
    """
    Computes weight, area, material cost and labour cost for one cut line.

    n_ingletes_total is accepted for backward compatibility but no longer used:
    miter labour is now derived per-cut from the cut's own mitered ends (see
    docs/COST_REVIEW.md, F1). Callers may keep passing their job-wide count.
    """
    area = area_seccion(perfil)
    m = perfil.material
    mo = perfil.mano_obra

    if m.kg_por_m > 0:
        kg_ud = (corte.largo / 1000) * m.kg_por_m
    else:
        kg_ud = corte.largo * area * m.peso_especifico / 1_000_000
    # Developed (outer) surface area in m², priced by precio_m2 — perimeter[mm] ×
    # length[mm] / 1e6. (Previously largo·area, which is volume, not m².)
    m2_ud = perimetro_seccion(perfil) * corte.largo / 1_000_000

    precio_mat = (
        kg_ud * m.precio_kg
        + m2_ud * m.precio_m2
        + (corte.largo / 1000) * m.precio_m
    )

    if m.precio_barra > 0 and longitud_barra > 0:
        precio_mat += (corte.largo / longitud_barra) * m.precio_barra

    if m.repartir_retales and barras:
        if m.kg_por_m > 0:
            total_kg_retal = sum(
                ((longitud_barra - sum(b)) / 1000) * m.kg_por_m
                for b in barras
                if longitud_barra - sum(b) > 0.001
            )
        else:
            total_kg_retal = sum(
                (longitud_barra - sum(b)) * area * m.peso_especifico / 1_000_000
                for b in barras
                if longitud_barra - sum(b) > 0.001
            )
        total_piezas = sum(len(b) for b in barras)
        if total_piezas > 0:
            precio_mat += total_kg_retal * m.precio_kg / total_piezas

    if m.margen_beneficio > 0:
        precio_mat *= (1 + m.margen_beneficio / 100)

    # Labour: each piece takes one straight-cut time; every mitered END adds
    # porcentaje_inglete % of that time. Charged per piece (scales with the
    # line quantity and the number of mitered ends on THIS cut). The legacy
    # job-wide n_ingletes_total is no longer used — it double-counted the miter
    # premium once per line across the whole job.
    miter_ends = (1 if corte.inglete1 else 0) + (1 if corte.inglete2 else 0)
    t_per_piece_min = mo.tiempo_corte_recto * (1 + miter_ends * mo.porcentaje_inglete / 100)
    mo_ud = (t_per_piece_min / 60) * mo.coste_operario_hora

    return ResultadoCorte(
        descripcion=corte.descripcion,
        largo=corte.largo,
        cantidad=corte.cantidad,
        kg_ud=kg_ud,
        m2_ud=m2_ud,
        precio_material_ud=precio_mat,
        coste_mano_obra_ud=mo_ud,
    )


def total_cost_for_context(ctx: MaterialContext) -> float:
    """Sum line totals for all cuts in a material context."""
    from .context_sync import effective_barras

    if not ctx.cortes:
        return 0.0
    barras = effective_barras(ctx)
    n_ingletes = sum(1 for c in ctx.cortes if c.inglete1 or c.inglete2)
    total = 0.0
    for corte in ctx.cortes:
        res = calcular_resultado(
            corte, ctx.perfil, barras, ctx.longitud_barra, n_ingletes,
        )
        total += res.precio_total_linea
    return total
