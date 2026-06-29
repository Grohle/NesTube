"""
nestify/context_sync.py
Save/load shared AppState fields into MaterialContext sub-tabs.
"""
from __future__ import annotations

from typing import List, Optional

from .models import AppState, ConfigPerfil, Corte, MaterialContext


def _copy_cortes(cortes) -> List[Corte]:
    """Deep-copy a cut list so two contexts never share Corte instances."""
    out: List[Corte] = []
    for c in cortes:
        if hasattr(c, "to_dict") and hasattr(Corte, "from_dict"):
            out.append(Corte.from_dict(c.to_dict()))
        else:
            out.append(c)
    return out


def _copy_perfil(perfil) -> ConfigPerfil:
    """Deep-copy a profile config so contexts own independent profiles."""
    if perfil is None:
        return ConfigPerfil()
    return ConfigPerfil.from_dict(perfil.to_dict())


def _copy_layout(layout) -> list:
    """Deep-copy a manual nesting layout (list of per-bar lists of dicts)."""
    out = []
    for bar in layout or []:
        if isinstance(bar, list):
            out.append([dict(p) if isinstance(p, dict) else p for p in bar])
        else:
            out.append(bar)
    return out


def ensure_material_contexts(state: AppState) -> None:
    """Ensure at least one material context exists, synced from legacy global fields."""
    if state.material_contexts:
        if state.active_material_index >= len(state.material_contexts):
            state.active_material_index = 0
        return

    from .i18n import t

    default = MaterialContext(name=t("nesting_n", n=1))
    default.cortes = list(state.cortes)
    default.longitud_barra = state.longitud_barra
    default.perdida_corte = state.perdida_corte
    default.margen_tubo = state.margen_tubo
    default.aprovechar_inglete = state.aprovechar_inglete
    default.perfil = state.perfil
    default.nesting_layout = list(state.nesting_layout)
    default.nesting_bar_lengths = list(state.nesting_bar_lengths)
    default.barras_necesarias = list(state.barras_necesarias)
    default.material = state.descripcion
    default.quality = state.calidad
    state.material_contexts = [default]
    state.active_material_index = 0


def get_active_context(state: AppState) -> MaterialContext:
    ensure_material_contexts(state)
    return state.material_contexts[state.active_material_index]


def material_context_as_state(base: AppState, ctx: MaterialContext) -> AppState:
    """Build an AppState snapshot for exports/calcs from one material context."""
    snap = base.to_dict()
    snap["cortes"] = [c.to_dict() if hasattr(c, "to_dict") else c for c in ctx.cortes]
    snap["perfil"] = ctx.perfil.to_dict()
    snap["barras_necesarias"] = effective_barras(ctx)
    snap["longitud_barra"] = ctx.longitud_barra
    snap["perdida_corte"] = ctx.perdida_corte
    snap["margen_tubo"] = ctx.margen_tubo
    snap["aprovechar_inglete"] = ctx.aprovechar_inglete
    snap["descripcion"] = ctx.material
    snap["calidad"] = ctx.quality
    state = AppState.from_dict(snap)
    state.barras_necesarias = effective_barras(ctx)
    return state


def layout_to_barras(nesting_layout: list) -> List[List[float]]:
    """Convert manual nesting_layout to bar length lists (sorted by x_offset)."""
    barras: List[List[float]] = []
    for bar_data in nesting_layout:
        if not bar_data:
            barras.append([])
            continue
        sorted_pieces = sorted(bar_data, key=lambda p: p.get("x_offset", 0.0))
        barras.append([float(p.get("largo", 0)) for p in sorted_pieces])
    return barras


def expected_cut_pieces(cortes: List[Corte]) -> int:
    """Total piece count from cut lines (sum of quantities)."""
    return sum(c.cantidad for c in cortes if c.es_valido())


def nesting_layout_piece_count(nesting_layout: list) -> int:
    return sum(len(bar) for bar in layout_to_barras(nesting_layout))


def layout_covers_all_cuts(ctx: MaterialContext) -> bool:
    """True when manual nesting includes every piece from the cut list."""
    if not ctx.nesting_layout or not ctx.cortes:
        return False
    return nesting_layout_piece_count(ctx.nesting_layout) >= expected_cut_pieces(ctx.cortes)


def apply_auto_barras(
    state: AppState,
    ctx: MaterialContext,
    barras: List[List[float]],
) -> None:
    """Store FFD/BFD/NFD result and drop stale partial manual layouts."""
    state.barras_necesarias = barras
    state.nesting_layout = []
    ctx.barras_necesarias = list(barras)
    ctx.nesting_layout = []


def effective_barras(ctx: MaterialContext) -> List[List[float]]:
    """Barras for preview/costs: full manual layout wins; else auto-calc."""
    if ctx.nesting_layout and layout_covers_all_cuts(ctx):
        return layout_to_barras(ctx.nesting_layout)
    if ctx.barras_necesarias:
        return list(ctx.barras_necesarias)
    if ctx.nesting_layout:
        return layout_to_barras(ctx.nesting_layout)
    return []


def recompute_auto_barras(ctx: MaterialContext, calc_system: str = "ffd") -> List[List[float]]:
    """Run bin-packing for a material context and clear incomplete manual layout."""
    from .logic import calcular_barras

    gap = ctx.perdida_corte + ctx.margen_tubo
    barras = calcular_barras(
        ctx.longitud_barra, list(ctx.cortes), system=calc_system, gap=gap,
    )
    ctx.barras_necesarias = barras
    ctx.nesting_layout = []
    return barras


def save_state_to_context(state: AppState, index: Optional[int] = None) -> None:
    """Persist current global AppState fields into a material context."""
    ensure_material_contexts(state)
    idx = state.active_material_index if index is None else index
    if idx < 0 or idx >= len(state.material_contexts):
        return
    ctx = state.material_contexts[idx]
    ctx.cortes = _copy_cortes(state.cortes)
    ctx.longitud_barra = state.longitud_barra
    ctx.perdida_corte = state.perdida_corte
    ctx.margen_tubo = state.margen_tubo
    ctx.aprovechar_inglete = state.aprovechar_inglete
    ctx.perfil = _copy_perfil(state.perfil)
    ctx.nesting_layout = _copy_layout(state.nesting_layout)
    ctx.nesting_bar_lengths = list(state.nesting_bar_lengths)
    ctx.barras_necesarias = list(state.barras_necesarias)
    if state.descripcion:
        ctx.material = state.descripcion
    if state.calidad:
        ctx.quality = state.calidad
    if hasattr(state, "nesting_height_override"):
        ctx.nesting_height_override = state.nesting_height_override
    if hasattr(state, "nesting_mode"):
        ctx.nesting_mode = state.nesting_mode
    if hasattr(state, "nesting_strategy"):
        ctx.nesting_strategy = state.nesting_strategy


def load_context_to_state(state: AppState, index: int) -> None:
    """Load a material context into global AppState (shared by all tabs)."""
    ensure_material_contexts(state)
    if index < 0 or index >= len(state.material_contexts):
        return
    state.active_material_index = index
    ctx = state.material_contexts[index]
    state.cortes = _copy_cortes(ctx.cortes)
    state.longitud_barra = ctx.longitud_barra
    state.perdida_corte = ctx.perdida_corte
    state.margen_tubo = ctx.margen_tubo
    state.aprovechar_inglete = ctx.aprovechar_inglete
    state.perfil = _copy_perfil(ctx.perfil)
    state.nesting_layout = _copy_layout(ctx.nesting_layout)
    state.nesting_bar_lengths = list(ctx.nesting_bar_lengths)
    state.barras_necesarias = effective_barras(ctx)
    state.descripcion = ctx.material
    state.calidad = ctx.quality
    if hasattr(state, "nesting_height_override"):
        state.nesting_height_override = ctx.nesting_height_override
    if hasattr(state, "nesting_mode"):
        state.nesting_mode = ctx.nesting_mode
    if hasattr(state, "nesting_strategy"):
        state.nesting_strategy = ctx.nesting_strategy


def save_cuts_tab_to_context(
    state: AppState,
    index: int,
    cortes: List[Corte],
) -> None:
    """Save Cortes-tab fields into a material context without touching nesting layout."""
    ensure_material_contexts(state)
    if index < 0 or index >= len(state.material_contexts):
        return
    ctx = state.material_contexts[index]
    ctx.cortes = _copy_cortes(cortes)
    ctx.longitud_barra = state.longitud_barra
    ctx.perdida_corte = state.perdida_corte
    ctx.margen_tubo = state.margen_tubo
    ctx.aprovechar_inglete = state.aprovechar_inglete
    if state.descripcion:
        ctx.material = state.descripcion
    if state.calidad:
        ctx.quality = state.calidad
    if hasattr(state, "nesting_height_override"):
        ctx.nesting_height_override = state.nesting_height_override
    if state.barras_necesarias:
        ctx.barras_necesarias = list(state.barras_necesarias)


def find_context_index_for_material(
    state: AppState, material: str, quality: str = "",
) -> Optional[int]:
    """Index of a sub-tab matching material + quality, or None."""
    ensure_material_contexts(state)
    m = material.strip().lower()
    q = quality.strip().lower()
    for i, ctx in enumerate(state.material_contexts):
        if ctx.material.strip().lower() == m and ctx.quality.strip().lower() == q:
            return i
    return None


def effective_cutting_height(state: AppState) -> float:
    """Cutting height (mm) to display for the active profile.

    Order: the user's remembered per-profile choice (app prefs) → a single
    known face → an explicit override → the max known face → 0 (unknown).
    """
    from .bevel_geom import profile_available_heights, profile_section_height_known
    perfil = state.perfil
    if perfil is None:
        return 0.0
    heights = profile_available_heights(perfil)
    if not heights:
        return profile_section_height_known(perfil)
    ensure_material_contexts(state)
    ctx = state.material_contexts[state.active_material_index]
    name = (ctx.profile_name or ctx.material or "").strip()
    try:
        from . import app_config
        choices = app_config.get().cutting_height_choices
    except Exception:
        choices = {}
    if name and name in choices:
        return float(choices[name])
    if len(heights) == 1:
        return float(heights[0][1])
    ov = getattr(state, "nesting_height_override", None)
    if ov:
        return float(ov)
    return profile_section_height_known(perfil)


def set_material_selection(
    state: AppState, profile_name: str, material: str, quality: str,
) -> None:
    """Write material/quality/profile_name to both state fields and active context.

    Call this from any tab's material-selection handler so all three tabs stay
    consistent — state.descripcion/calidad mirror the active context and are
    never stale when save_state_to_context() is called later.
    """
    state.descripcion = material
    state.calidad = quality
    ensure_material_contexts(state)
    ctx = state.material_contexts[state.active_material_index]
    ctx.profile_name = profile_name
    ctx.material = material
    ctx.quality = quality
    # Populate the profile's cross-section geometry from the catalogue entry so
    # the bar-height field can auto-fill (Cuts/Nesting/Costs all read perfil).
    from .stock_prefill import find_profile_entry, apply_profile_entry_to_perfil
    entry = find_profile_entry(profile_name)
    if entry is not None and apply_profile_entry_to_perfil(ctx.perfil, entry):
        state.perfil = _copy_perfil(ctx.perfil)


def find_or_create_context_for_material(
    state: AppState, material: str, quality: str = "",
) -> int:
    """Switch to existing material tab or create a new one; returns context index."""
    idx = find_context_index_for_material(state, material, quality)
    if idx is not None:
        return idx
    from .i18n import t

    ensure_material_contexts(state)
    n = len(state.material_contexts) + 1
    ctx = MaterialContext(
        name=t("nesting_n", n=n),
        material=material.strip(),
        quality=quality.strip(),
        longitud_barra=state.longitud_barra,
        perdida_corte=state.perdida_corte,
        margen_tubo=state.margen_tubo,
        aprovechar_inglete=state.aprovechar_inglete,
        cortes=[],
    )
    state.material_contexts.append(ctx)
    return len(state.material_contexts) - 1
