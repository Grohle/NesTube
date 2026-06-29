"""
nestify/app_config.py
Persistent application preferences — nestify_config.json at project root.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_log = logging.getLogger(__name__)
_lock = threading.Lock()

# Project root (parent of nestify package)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILENAME = "nestify_config.json"
CONFIG_PATH = os.path.join(_ROOT, CONFIG_FILENAME)
ASSETS_PROFILES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "profiles")
PROFILES_DIR = os.path.join(_ROOT, "Profiles")


@dataclass
class CustomProfileEntry:
    """User-defined profile type with optional PNG illustration."""
    id: str
    name: str
    image: str = ""
    quality: str = ""
    notes: str = ""
    fields: List[str] = field(default_factory=lambda: ["A (mm)", "B (mm)"])
    drawing_shapes: List = field(default_factory=list)
    wkt: str = ""
    # Full material data sheet captured in the drawing module (profile_name,
    # material, kg_por_m, precio_kg, precio_m, peso_especifico, …) so editing a
    # profile recovers every parameter, not just the drawing.
    meta: dict = field(default_factory=dict)
    manual_sides: List = field(default_factory=list)
    # Default numeric values for each dimension field (field_name → default).
    # Used to pre-populate StockAddDialog when this profile type is selected.
    field_defaults: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "image": self.image,
            "quality": self.quality,
            "notes": self.notes,
            "fields": self.fields,
            "drawing_shapes": self.drawing_shapes,
            "wkt": self.wkt,
            "meta": self.meta,
            "manual_sides": self.manual_sides,
            "field_defaults": self.field_defaults,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CustomProfileEntry":
        return cls(
            id=str(d.get("id", "")),
            name=str(d.get("name", "")),
            image=str(d.get("image", "")),
            quality=str(d.get("quality", "")),
            notes=str(d.get("notes", "")),
            fields=list(d.get("fields", ["A (mm)", "B (mm)"])),
            drawing_shapes=list(d.get("drawing_shapes", [])),
            wkt=str(d.get("wkt", "")),
            meta=dict(d.get("meta", {})),
            manual_sides=list(d.get("manual_sides", [])),
            field_defaults=dict(d.get("field_defaults", {})),
        )


@dataclass
class AppPreferences:
    language: str = "en"
    theme: str = "dark"
    font_size_offset: int = 0
    ui_font_family: str = ""
    ui_mono_family: str = "DejaVu Sans Mono"
    calc_system: str = "ffd"
    cost_mode: str = "shared"
    confirm_costs: bool = True   # ask to confirm cost config before calculating
    currency: str = "EUR"
    unit_system: str = "metric"
    window_geometry: str = ""
    split_cortes: int = 560
    split_costes: int = 420
    split_nesting: int = 240
    split_nesting_right: int = 0
    nesting_show_left: bool = True
    nesting_show_right: bool = True
    nesting_pieces_side: str = "left"
    nesting_bars_side: str = "right"
    nesting_snap_zone_mm: float = 25.0
    opt_time_level_1: float = 1.0
    opt_time_level_2: float = 5.0
    opt_time_level_3: float = 10.0
    opt_time_level_4: float = 20.0
    opt_time_level_5: float = 30.0
    opt_time_level_6: float = 0.0
    nesting_real_proportions: bool = True
    nesting_use_cut_colors: bool = True
    # Legacy-only (CTk UI). The Qt UI no longer has an on-canvas zoom overlay or
    # its toggle — kept so the legacy nestify/ui dialog and saved configs keep
    # round-tripping without errors.
    nesting_show_zoom_overlay: bool = True
    pdf_font_regular: str = ""
    pdf_font_bold: str = ""
    pdf_template_path: str = ""
    pdf_template_layout_path: str = ""
    pdf_fastreport_path: str = ""
    pdf_cuts_layout_path: str = ""
    pdf_cuts_fastreport_path: str = ""
    donation_url: str = "https://paypal.me/artbertomiranda"
    paypal_url: str = "https://paypal.me/artbertomiranda"
    buymeacoffee_url: str = "https://buymeacoffee.com/grohle"
    github_url: str = "https://example.com/github"
    profile_usage: Dict[str, int] = field(default_factory=dict)
    custom_profiles: List[CustomProfileEntry] = field(default_factory=list)
    last_profile_key: str = ""
    job_name_prefix: str = "JOB"
    remnant_name_prefix: str = "RET"
    show_about_on_startup: bool = True
    # Remembered cutting-height (mm) per profile name, so the user is asked only
    # the first time a profile with several candidate faces is selected.
    cutting_height_choices: Dict[str, float] = field(default_factory=dict)
    # Global cost defaults (§24) — the profile-INDEPENDENT cost parameters used
    # to seed a brand-new job/material context. Set via Settings > Cost defaults.
    default_operator_cost: float = 30.0   # €/h
    default_cut_time: float = 3.0         # min (straight cut)
    default_miter_pct: float = 35.0       # % extra for mitred cuts
    default_profit_margin: float = 0.0    # % profit margin

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "theme": self.theme,
            "font_size_offset": self.font_size_offset,
            "ui_font_family": self.ui_font_family,
            "ui_mono_family": self.ui_mono_family,
            "calc_system": self.calc_system,
            "cost_mode": self.cost_mode,
            "confirm_costs": self.confirm_costs,
            "currency": self.currency,
            "unit_system": self.unit_system,
            "window_geometry": self.window_geometry,
            "split_cortes": self.split_cortes,
            "split_costes": self.split_costes,
            "split_nesting": self.split_nesting,
            "split_nesting_right": self.split_nesting_right,
            "nesting_show_left": self.nesting_show_left,
            "nesting_show_right": self.nesting_show_right,
            "nesting_pieces_side": self.nesting_pieces_side,
            "nesting_bars_side": self.nesting_bars_side,
            "nesting_snap_zone_mm": self.nesting_snap_zone_mm,
            "opt_time_level_1": self.opt_time_level_1,
            "opt_time_level_2": self.opt_time_level_2,
            "opt_time_level_3": self.opt_time_level_3,
            "opt_time_level_4": self.opt_time_level_4,
            "opt_time_level_5": self.opt_time_level_5,
            "opt_time_level_6": self.opt_time_level_6,
            "nesting_real_proportions": self.nesting_real_proportions,
            "nesting_use_cut_colors": self.nesting_use_cut_colors,
            "nesting_show_zoom_overlay": self.nesting_show_zoom_overlay,  # legacy-only
            "pdf_font_regular": self.pdf_font_regular,
            "pdf_font_bold": self.pdf_font_bold,
            "pdf_template_path": self.pdf_template_path,
            "pdf_template_layout_path": self.pdf_template_layout_path,
            "pdf_fastreport_path": self.pdf_fastreport_path,
            "pdf_cuts_layout_path": self.pdf_cuts_layout_path,
            "pdf_cuts_fastreport_path": self.pdf_cuts_fastreport_path,
            "donation_url": self.donation_url,
            "paypal_url": self.paypal_url,
            "buymeacoffee_url": self.buymeacoffee_url,
            "github_url": self.github_url,
            "profile_usage": self.profile_usage,
            "custom_profiles": [p.to_dict() for p in self.custom_profiles],
            "last_profile_key": self.last_profile_key,
            "job_name_prefix": self.job_name_prefix,
            "remnant_name_prefix": self.remnant_name_prefix,
            "show_about_on_startup": self.show_about_on_startup,
            "cutting_height_choices": self.cutting_height_choices,
            "default_operator_cost": self.default_operator_cost,
            "default_cut_time": self.default_cut_time,
            "default_miter_pct": self.default_miter_pct,
            "default_profit_margin": self.default_profit_margin,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AppPreferences":
        return cls(
            language=str(d.get("language", "en")),
            theme=str(d.get("theme", "dark")),
            font_size_offset=int(d.get("font_size_offset", 0)),
            ui_font_family=str(d.get("ui_font_family", "")),
            ui_mono_family=str(d.get("ui_mono_family", "DejaVu Sans Mono")),
            calc_system=str(d.get("calc_system", "ffd")),
            cost_mode=str(d.get("cost_mode", "shared")),
            confirm_costs=bool(d.get("confirm_costs", True)),
            currency=str(d.get("currency", "EUR")),
            unit_system=str(d.get("unit_system", "metric")),
            window_geometry=str(d.get("window_geometry", "")),
            split_cortes=int(d.get("split_cortes", 560)),
            split_costes=int(d.get("split_costes", 420)),
            split_nesting=int(d.get("split_nesting", 240)),
            split_nesting_right=int(d.get("split_nesting_right", 0)),
            nesting_show_left=bool(d.get("nesting_show_left", True)),
            nesting_show_right=bool(d.get("nesting_show_right", True)),
            nesting_pieces_side=str(d.get("nesting_pieces_side", "left")),
            nesting_bars_side=str(d.get("nesting_bars_side", "right")),
            nesting_snap_zone_mm=float(d.get("nesting_snap_zone_mm", 25.0)),
            opt_time_level_1=float(d.get("opt_time_level_1", 1.0)),
            opt_time_level_2=float(d.get("opt_time_level_2", 5.0)),
            opt_time_level_3=float(d.get("opt_time_level_3", 10.0)),
            opt_time_level_4=float(d.get("opt_time_level_4", 20.0)),
            opt_time_level_5=float(d.get("opt_time_level_5", 30.0)),
            opt_time_level_6=float(d.get("opt_time_level_6", 0.0)),
            nesting_real_proportions=bool(d.get("nesting_real_proportions", True)),
            nesting_use_cut_colors=bool(d.get("nesting_use_cut_colors", True)),
            nesting_show_zoom_overlay=bool(d.get("nesting_show_zoom_overlay", True)),  # legacy-only
            pdf_font_regular=str(d.get("pdf_font_regular", "")),
            pdf_font_bold=str(d.get("pdf_font_bold", "")),
            pdf_template_path=str(d.get("pdf_template_path", "")),
            pdf_template_layout_path=str(d.get("pdf_template_layout_path", "")),
            pdf_fastreport_path=str(d.get("pdf_fastreport_path", "")),
            pdf_cuts_layout_path=str(d.get("pdf_cuts_layout_path", "")),
            pdf_cuts_fastreport_path=str(d.get("pdf_cuts_fastreport_path", "")),
            donation_url=str(d.get("donation_url", "https://paypal.me/artbertomiranda")),
            paypal_url=str(d.get("paypal_url", "https://paypal.me/artbertomiranda")),
            buymeacoffee_url=str(d.get("buymeacoffee_url", "https://buymeacoffee.com/grohle")),
            github_url=str(d.get("github_url", "https://example.com/github")),
            profile_usage=dict(d.get("profile_usage", {})),
            custom_profiles=[
                CustomProfileEntry.from_dict(p)
                for p in d.get("custom_profiles", [])
            ],
            last_profile_key=str(d.get("last_profile_key", "")),
            job_name_prefix=str(d.get("job_name_prefix", "JOB")),
            remnant_name_prefix=str(d.get("remnant_name_prefix", "RET")),
            show_about_on_startup=bool(d.get("show_about_on_startup", True)),
            cutting_height_choices={
                str(k): float(v)
                for k, v in dict(d.get("cutting_height_choices", {})).items()
            },
            default_operator_cost=float(d.get("default_operator_cost", 30.0)),
            default_cut_time=float(d.get("default_cut_time", 3.0)),
            default_miter_pct=float(d.get("default_miter_pct", 35.0)),
            default_profit_margin=float(d.get("default_profit_margin", 0.0)),
        )


_prefs: Optional[AppPreferences] = None


def get_opt_time_limits() -> dict:
    """Return optimization level (1–6) → max seconds; level 6 is 0 (unlimited)."""
    p = get()
    defaults = (1.0, 5.0, 10.0, 20.0, 30.0, 0.0)
    out = {
        i: max(0.1, float(getattr(p, f"opt_time_level_{i}", defaults[i - 1])))
        for i in range(1, 6)
    }
    out[6] = 0.0
    return out


def get_config_path() -> str:
    return CONFIG_PATH


_META_CONFIG = "app_config"


def load() -> AppPreferences:
    """Load preferences from the SQLite store (app_meta['app_config']).

    Preferences are stored as a single JSON document in the relational DB — a
    document is the right shape for ~40 heterogeneous settings (and keeps the
    bootstrap, which runs before Qt, simple and fast). One-time migration: if
    the DB has no config but a legacy nestify_config.json exists, it is imported
    and retired (*.migrated). Profiles dropped into the Profiles/ folder are
    still merged in afterwards, unchanged.
    """
    global _prefs
    os.makedirs(ASSETS_PROFILES, exist_ok=True)
    os.makedirs(PROFILES_DIR, exist_ok=True)
    with _lock:
        from nestify.database import get_geometry_db
        db = get_geometry_db()
        raw_json = db.get_meta(_META_CONFIG)
        if raw_json is None and os.path.isfile(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                    raw_json = fh.read()
                db.set_meta(_META_CONFIG, raw_json)
                _log.info("Migrated app config from JSON to SQLite")
            except OSError as exc:
                _log.warning("Could not import legacy config JSON: %s", exc)
                raw_json = None
            _retire_legacy_json(CONFIG_PATH)

        if raw_json:
            try:
                _prefs = AppPreferences.from_dict(json.loads(raw_json))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                _log.warning("Could not parse stored config: %s — using defaults", exc)
                _prefs = AppPreferences()
                _apply_default_pdf_fonts(_prefs)
        else:
            _prefs = AppPreferences()
            _apply_default_pdf_fonts(_prefs)

        _sync_profiles_from_folder(_prefs)
        return _prefs


def _sync_profiles_from_folder(prefs: AppPreferences) -> None:
    """Merge profiles from Profiles/ folder into prefs."""
    folder_profiles = load_profiles_from_folder()
    existing_ids = {p.id for p in prefs.custom_profiles}
    for fp in folder_profiles:
        if fp.id not in existing_ids:
            prefs.custom_profiles.append(fp)


def save(prefs: Optional[AppPreferences] = None) -> bool:
    """Persist preferences to the SQLite store (app_meta['app_config'])."""
    global _prefs
    with _lock:
        if prefs is not None:
            _prefs = prefs
        if _prefs is None:
            _prefs = AppPreferences()
        try:
            from nestify.database import get_geometry_db
            get_geometry_db().set_meta(
                _META_CONFIG, json.dumps(_prefs.to_dict(), ensure_ascii=False))
            return True
        except Exception as exc:  # noqa: BLE001 — persistence must never crash the UI
            _log.error("Could not save config to SQLite: %s", exc)
            return False


def _retire_legacy_json(path: str) -> None:
    """Rename a migrated legacy JSON to ``*.migrated`` (kept as backup, not
    re-imported). Best-effort: failures are non-fatal."""
    try:
        if os.path.isfile(path):
            os.replace(path, path + ".migrated")
    except OSError as exc:
        _log.warning("Could not retire legacy JSON %s: %s", path, exc)


def get() -> AppPreferences:
    if _prefs is None:
        return load()
    return _prefs


def apply_cost_defaults(perfil) -> None:
    """Seed a ConfigPerfil's profile-INDEPENDENT cost fields from the saved
    global defaults (§24): operator cost, straight-cut time, mitre %, profit
    margin. Mutates ``perfil`` in place. Duck-typed (no models import → no
    circular dependency); the per-material prices (€/kg, kg/m…) are untouched
    because those come from the chosen profile/material, not these defaults."""
    prefs = get()
    mo = perfil.mano_obra
    mo.coste_operario_hora = prefs.default_operator_cost
    mo.tiempo_corte_recto = prefs.default_cut_time
    mo.porcentaje_inglete = prefs.default_miter_pct
    perfil.material.margen_beneficio = prefs.default_profit_margin


def record_profile_use(profile_key: str) -> None:
    """Increment usage counter for built-in or custom profile."""
    prefs = get()
    prefs.profile_usage[profile_key] = prefs.profile_usage.get(profile_key, 0) + 1
    prefs.last_profile_key = profile_key
    save()


def top_profiles(n: int = 5) -> List[str]:
    """Return up to n most-used profile keys, most recent first on ties."""
    prefs = get()
    items = sorted(
        prefs.profile_usage.items(),
        key=lambda x: (-x[1], x[0]),
    )
    return [k for k, _ in items[:n]]


# ── Profile file management (Profiles/ folder) ───────────────────────────────

def save_profile_file(entry: CustomProfileEntry) -> str:
    """Save a profile as a JSON file in the Profiles/ folder. Returns the file path."""
    os.makedirs(PROFILES_DIR, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in entry.name).strip()
    filepath = os.path.join(PROFILES_DIR, f"{safe_name}.json")
    data = entry.to_dict()
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return filepath


def load_profiles_from_folder() -> List[CustomProfileEntry]:
    """Load all profiles from the Profiles/ folder."""
    if not os.path.isdir(PROFILES_DIR):
        return []
    profiles = []
    for filename in sorted(os.listdir(PROFILES_DIR)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(PROFILES_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            profiles.append(CustomProfileEntry.from_dict(data))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return profiles


def delete_profile_file(entry: CustomProfileEntry) -> bool:
    """Delete a profile JSON (and its image if any) from the Profiles/ folder."""
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in entry.name).strip()
    filepath = os.path.join(PROFILES_DIR, f"{safe_name}.json")
    try:
        if os.path.isfile(filepath):
            os.remove(filepath)
        if entry.image:
            img_path = os.path.join(PROFILES_DIR, entry.image)
            if os.path.isfile(img_path):
                os.remove(img_path)
        return True
    except OSError:
        return False


def _apply_default_pdf_fonts(prefs: AppPreferences) -> None:
    if prefs.pdf_font_regular:
        return
    for path in _discover_pdf_font_paths():
        prefs.pdf_font_regular = path
        bold = path.replace(".ttf", "bd.ttf").replace("Regular", "Bold")
        if not os.path.isfile(bold):
            bold = path.replace("arial.ttf", "arialbd.ttf")
        if os.path.isfile(bold):
            prefs.pdf_font_bold = bold
        else:
            prefs.pdf_font_bold = path
        break


def _discover_pdf_font_paths() -> List[str]:
    """Search bundled and system paths for Unicode-capable TTF fonts."""
    pkg_fonts = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    candidates = [
        os.path.join(pkg_fonts, "DejaVuSans.ttf"),
        os.path.join(pkg_fonts, "DejaVuSans-Bold.ttf"),
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    return [p for p in candidates if os.path.isfile(p)]
