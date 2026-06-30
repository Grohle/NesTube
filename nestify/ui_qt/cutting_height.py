"""
nestify/ui_qt/cutting_height.py

Shared helper to resolve the "cutting height" for the active profile, asking the
user once (with a clickable dialog) and remembering the choice per profile name
in app preferences. Used by Cuts, Nesting and Costs so a material selection in
any of them prompts for / applies the cutting height consistently.
"""
from __future__ import annotations

from typing import Optional

from nestify import app_config
from nestify.bevel_geom import profile_available_heights
from nestify.context_sync import ensure_material_contexts


def resolve_cutting_height(parent, state, force_ask: bool = False) -> Optional[float]:
    """Determine + apply the cutting height for the active profile.

    - 0 candidate faces → returns None (nothing to choose).
    - 1 face → uses it silently.
    - >1 faces with a remembered choice (and not ``force_ask``) → uses it.
    - >1 faces, no choice (or ``force_ask``) → opens the clickable dialog and
      remembers the pick per profile name.

    The chosen height is written to ``state.nesting_height_override`` and the
    active context, then returned (or None if the user cancelled).
    """
    perfil = getattr(state, "perfil", None)
    if perfil is None:
        return None
    heights = profile_available_heights(perfil)
    if not heights:
        return None

    ensure_material_contexts(state)
    ctx = state.material_contexts[state.active_material_index]
    name = (ctx.profile_name or ctx.material or "").strip()
    prefs = app_config.get()
    choices = prefs.cutting_height_choices

    chosen: Optional[float]
    if len(heights) == 1:
        chosen = float(heights[0][1])
    elif name and name in choices and not force_ask:
        chosen = float(choices[name])
    else:
        from nestify.ui_qt.dialogs.profile_height_dialog import ProfileHeightDialog
        dlg = ProfileHeightDialog(heights, parent)
        if not dlg.exec():
            return None
        chosen = dlg.chosen_height()
        if name and chosen:
            choices[name] = float(chosen)
            app_config.save(prefs)

    if chosen:
        state.nesting_height_override = float(chosen)
        ctx.nesting_height_override = float(chosen)
    return chosen
