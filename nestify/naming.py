"""
nestify/naming.py
Canonical naming system for profiles, materials and stock bars.

The whole application must present a profile/material/quality selection the
same way, everywhere (Cuts, Nesting, Costs & Weight, Stock, Job Explorer,
dialogs, window titles, exported documents). This module is the single
source of truth for that representation so the format can never drift
between tabs.

Convention (TODO.md §0):
    full name  ->  "{profile_name} · {material} · {quality}"

Empty parts are dropped, so the helpers degrade gracefully:
    ("U60x60x2", "Acero", "S355J2")  -> "U60x60x2 · Acero · S355J2"
    ("",         "Acero", "S355J2")  -> "Acero · S355J2"
    ("",         "Acero", "")        -> "Acero"
"""
from __future__ import annotations

from typing import Iterable

# Separator between name parts. Centralised so it can never diverge between
# tabs. A middle dot reads cleanly and is unambiguous (unlike "-", which
# also appears inside profile names like "U60-60-2").
SEP = " · "


def _join(parts: Iterable[str]) -> str:
    """Join the non-empty, stripped parts with the canonical separator."""
    clean = [str(p).strip() for p in parts if p is not None and str(p).strip()]
    return SEP.join(clean)


def format_full_name(profile_name: str = "", material: str = "", quality: str = "") -> str:
    """Canonical full representation: profile · material · quality.

    Use this for any label, table cell, selector entry or window title that
    identifies a profile together with its material and quality.
    """
    return _join((profile_name, material, quality))


def format_material(material: str = "", quality: str = "") -> str:
    """Material-only representation: material · quality.

    Use this where there is no profile context (e.g. the Materials library,
    a material-only dropdown).
    """
    return _join((material, quality))


def context_tab_label(ctx, index: int = 0) -> str:
    """Permanent, self-healing sub-tab label for a MaterialContext.

    The label is derived from the *persisted* identity fields
    (profile · material · quality) so it survives save/reopen and never has to
    be re-selected. A user-typed custom name (``custom_display_name``) always
    wins; the legacy ``name`` field is used only as a fallback for older jobs
    that have no profile/material stored. Falls back to ``"Nesting N"``.
    """
    custom = (getattr(ctx, "custom_display_name", "") or "").strip()
    if custom:
        return custom
    derived = format_full_name(
        getattr(ctx, "profile_name", "") or "",
        getattr(ctx, "material", "") or "",
        getattr(ctx, "quality", "") or "",
    ).strip(" ·")
    if derived:
        return derived
    legacy = (getattr(ctx, "name", "") or "").strip(" ·")
    return legacy or f"Nesting {index + 1}"


# ── Built-in material localisation (TODO §6) ────────────────────────────────
# The canonical material value is its Spanish name (the historical storage
# value), so existing jobs/stock keep matching. Only the DISPLAYED label is
# localised; custom/user-defined materials pass through unchanged. Pairs of
# (canonical name, specific weight t/m³) — single source of truth for the
# built-in material presets shown in the profile/material dialogs.
BASE_MATERIALS: tuple[tuple[str, float], ...] = (
    ("Acero", 7.85),
    ("Aluminio", 2.70),
    ("Inoxidable", 7.90),
    # §20.2 catalogue materials (specific steel grades, kept alongside the
    # generic ones above so existing jobs/stock referencing "Acero"/
    # "Inoxidable" keep matching). "Acero Inoxidable" is not listed here: it
    # is the same material as "Inoxidable", just the longer Spanish phrasing
    # used in the catalogue xlsx — see _CANON_ALIASES below.
    ("Acero al Carbono", 7.85),
    ("Acero Galvanizado", 7.85),
)

_MATERIAL_I18N_KEY = {
    "acero": "material_acero",
    "aluminio": "material_aluminio",
    "inoxidable": "material_inoxidable",
    "acero al carbono": "material_acero_carbono",
    "acero galvanizado": "material_acero_galvanizado",
}
# Canonical proper-case names keyed by lowercase, for round-tripping.
_CANON_BY_LOWER = {name.lower(): name for name, _sw in BASE_MATERIALS}
# Alternate spellings that mean an existing canonical material (not a new
# one) — e.g. the catalogue xlsx's "Acero Inoxidable" is just "Inoxidable".
_CANON_ALIASES = {
    "acero inoxidable": "Inoxidable",
}
_CANON_BY_LOWER.update(_CANON_ALIASES)


def localize_material(material: str) -> str:
    """Localised display label for a built-in material; unknown → unchanged."""
    if not material:
        return material
    key = _MATERIAL_I18N_KEY.get(material.strip().lower())
    if not key:
        return material
    from .i18n import t
    return t(key)


def canonical_material(display: str) -> str:
    """Map a (possibly localised) material label back to its canonical name.

    Accepts the canonical Spanish name or any language's localised label and
    returns the canonical name so storage/matching stays language-independent.
    Custom/user materials pass through unchanged.
    """
    if not display:
        return display
    d = display.strip()
    dl = d.lower()
    if dl in _CANON_BY_LOWER:
        return _CANON_BY_LOWER[dl]
    from .i18n import _TRANSLATIONS
    for canon, key in (("Acero", "material_acero"),
                       ("Aluminio", "material_aluminio"),
                       ("Inoxidable", "material_inoxidable"),
                       ("Acero al Carbono", "material_acero_carbono"),
                       ("Acero Galvanizado", "material_acero_galvanizado")):
        for lang_map in _TRANSLATIONS.values():
            val = lang_map.get(key)
            if val and val.lower() == dl:
                return canon
    return d
