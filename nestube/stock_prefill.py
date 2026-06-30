"""
nestube/nestube/nestube/stock_prefill.py
Match stock bars to material/quality and prefill cost profile parameters.
"""
from __future__ import annotations

from typing import Optional

from .models import ConfigPerfil, MaterialContext, AppState, TipoPerfil
from .stock_db import StockBar, get_stock


# Catalogue/custom-profile geometry_type → builtin TipoPerfil. Kept here (a
# non-UI module) so Cuts/Nesting/Costs can all map a chosen profile name onto
# the dimension slots without importing the Qt tabs. Mirrors the mapping in
# nestube/ui_qt/tab_perfiles.py::_GEOMETRY_TO_TIPO.
_GEOMETRY_TO_TIPO = {
    "redondo": TipoPerfil.REDONDO,
    "cuadrado": TipoPerfil.RECTANGULAR,
    "rectangular": TipoPerfil.RECTANGULAR,
    "pletina": TipoPerfil.RECTANGULAR,
    "ranurado": TipoPerfil.RECTANGULAR,
    "perfil z": TipoPerfil.RECTANGULAR,
    "angular": TipoPerfil.L,
    "viga u": TipoPerfil.U,
    "perfil c": TipoPerfil.U,
    "viga i": TipoPerfil.H,
    "viga h": TipoPerfil.H,
}


def find_profile_entry(profile_name: str):
    """Return the saved custom/catalogue profile entry matching ``profile_name``.

    Looks up by exact (case-insensitive) name in ``app_config.custom_profiles``.
    Returns ``None`` if there is no match or config can't be read.
    """
    if not profile_name:
        return None
    try:
        from . import app_config
        profiles = getattr(app_config.get(), "custom_profiles", [])
    except Exception:
        return None
    pn = profile_name.strip().lower()
    for cp in profiles:
        if (cp.name or "").strip().lower() == pn:
            return cp
    return None


def apply_profile_entry_to_perfil(perfil: ConfigPerfil, entry) -> bool:
    """Apply a catalogue/custom profile entry's geometry to ``perfil``.

    Populates the dimension slots (so the cross-section height is derivable) and
    the linear weight / specific weight when present. Returns True when a real
    height was applied.
    """
    meta = getattr(entry, "meta", None) or {}
    geometry = (meta.get("geometry_type") or "").strip().lower()
    h = float(meta.get("h", 0) or 0)
    b = float(meta.get("b", 0) or 0)
    tw = float(meta.get("tw", 0) or 0)
    tf = float(meta.get("tf", 0) or 0)
    if h <= 0:
        return False
    tipo = _GEOMETRY_TO_TIPO.get(geometry, TipoPerfil.RECTANGULAR)
    d = perfil.dimensiones
    d.tipo = tipo
    if tipo == TipoPerfil.REDONDO:
        d.diametro, d.lado_a, d.lado_b, d.lado_c = h, 0.0, 0.0, 0.0
    else:
        d.diametro, d.lado_a, d.lado_b, d.lado_c = 0.0, h, b, tf
    if tw > 0:
        d.espesor = tw
        d.espesor_int_H = tw
    d.macizo = bool(meta.get("macizo", False))
    m = perfil.material
    kg_m = float(meta.get("peso_lineal_kg_m", 0) or 0)
    if kg_m > 0:
        m.kg_por_m = kg_m
    sw = float(meta.get("specific_weight", 0) or 0)
    if sw > 0:
        m.peso_especifico = sw
    return True


def find_best_stock_bar(material: str, quality: str = "") -> Optional[StockBar]:
    """Best available stock row for material (+ optional quality)."""
    material = material.strip()
    if not material:
        return None
    quality_l = quality.strip().lower()
    material_l = material.lower()
    db = get_stock()
    candidates: list = []
    for bar in db.bars:
        if bar.quantity <= 0:
            continue
        md = bar.material_desc.lower()
        ql = (bar.quality or "").lower()
        if material_l not in md and md not in material_l:
            continue
        if quality_l and quality_l not in ql and quality_l not in md:
            continue
        candidates.append(bar)
    if not candidates:
        return None
    candidates.sort(key=lambda b: (-(b.precio_kg or 0), -(b.length or 0)))
    return candidates[0]


def apply_stock_bar_to_perfil(perfil: ConfigPerfil, bar: StockBar) -> None:
    """Copy pricing/weight fields from a stock bar into profile cost params."""
    m = perfil.material
    if bar.peso_especifico > 0:
        m.peso_especifico = bar.peso_especifico
    if bar.precio_kg > 0:
        m.precio_kg = bar.precio_kg
    if bar.precio_m > 0:
        m.precio_m = bar.precio_m
    if bar.kg_por_m > 0:
        m.kg_por_m = bar.kg_por_m
    if bar.precio_barra > 0:
        m.precio_barra = bar.precio_barra
    if bar.espesor > 0:
        perfil.dimensiones.espesor = bar.espesor
    for dim_key in ("lado_a", "lado_b", "lado_c", "diametro"):
        val = bar.fields.get(dim_key, 0)
        if val and val > 0:
            setattr(perfil.dimensiones, dim_key, float(val))


def prefill_material_context_from_stock(ctx: MaterialContext) -> Optional[StockBar]:
    """Apply stock pricing to a material context; returns matched bar or None."""
    bar = find_best_stock_bar(ctx.material, ctx.quality)
    if bar is None:
        return None
    apply_stock_bar_to_perfil(ctx.perfil, bar)
    return bar


def prefill_active_material_from_stock(state: AppState) -> Optional[StockBar]:
    """Prefill the active material context from stock."""
    from .context_sync import ensure_material_contexts, get_active_context

    ensure_material_contexts(state)
    ctx = get_active_context(state)
    bar = prefill_material_context_from_stock(ctx)
    if bar is not None:
        state.perfil = ConfigPerfil.from_dict(ctx.perfil.to_dict())
    return bar
