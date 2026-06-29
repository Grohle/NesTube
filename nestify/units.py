"""
nestify/units.py
Unit system support — metric (mm, kg) vs imperial (in, lb).
Provides label strings and conversion functions.
"""
from __future__ import annotations

_system: str = "metric"

# Conversion factors (metric base → imperial)
MM_TO_IN = 1 / 25.4
KG_TO_LB = 2.20462
M2_TO_FT2 = 10.7639
T_M3_TO_LB_FT3 = 62.428


def set_unit_system(system: str) -> None:
    global _system
    _system = system.lower() if system.lower() in ("metric", "imperial") else "metric"


def get_unit_system() -> str:
    return _system


def is_metric() -> bool:
    return _system == "metric"


# ── Unit label strings ────────────────────────────────────────────────────────

def u_len() -> str:
    """Length unit: mm or in."""
    return "mm" if is_metric() else "in"


def u_len_long() -> str:
    """Length unit long: metros or feet."""
    return "m" if is_metric() else "ft"


def u_weight() -> str:
    """Weight unit: kg or lb."""
    return "kg" if is_metric() else "lb"


def u_area() -> str:
    """Area unit: m² or ft²."""
    return "m²" if is_metric() else "ft²"


def u_density() -> str:
    """Density unit: t/m³ or lb/ft³."""
    return "t/m³" if is_metric() else "lb/ft³"


def u_linear_weight() -> str:
    """Linear weight: kg/m or lb/ft."""
    return "kg/m" if is_metric() else "lb/ft"


# ── Conversion to display (internal metric → display) ─────────────────────────

def to_display_length(mm: float) -> float:
    """Convert mm to display units."""
    return mm if is_metric() else mm * MM_TO_IN


def to_display_weight(kg: float) -> float:
    """Convert kg to display units."""
    return kg if is_metric() else kg * KG_TO_LB


def to_display_area(m2: float) -> float:
    """Convert m² to display units."""
    return m2 if is_metric() else m2 * M2_TO_FT2


def to_display_density(t_m3: float) -> float:
    """Convert t/m³ to display units."""
    return t_m3 if is_metric() else t_m3 * T_M3_TO_LB_FT3


def to_display_linear_weight(kg_m: float) -> float:
    """Convert kg/m to display units (lb/ft)."""
    if is_metric():
        return kg_m
    return kg_m * KG_TO_LB / 3.28084  # kg/m → lb/ft


# ── Conversion from display (display → internal metric) ───────────────────────

def from_display_length(value: float) -> float:
    """Convert display length to mm."""
    return value if is_metric() else value / MM_TO_IN


def from_display_weight(value: float) -> float:
    """Convert display weight to kg."""
    return value if is_metric() else value / KG_TO_LB


def from_display_density(value: float) -> float:
    """Convert display density to t/m³."""
    return value if is_metric() else value / T_M3_TO_LB_FT3


def from_display_linear_weight(value: float) -> float:
    """Convert display linear weight to kg/m."""
    if is_metric():
        return value
    return value / (KG_TO_LB / 3.28084)
