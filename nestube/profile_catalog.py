"""
nestube/nestube/nestube/profile_catalog.py
Built-in profile/tube catalogue (TODO §20). The 22 profiles/tubes below come
verbatim from the shop's multimaterial spreadsheet (sheet
``Base_de_Datos_Maestra_IA``). Importing is idempotent: each row gets a
stable id, so re-running :func:`ensure_catalog_profiles` never duplicates
entries, and a profile the user has since edited or deleted is left alone.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple

from .app_config import CustomProfileEntry, PROFILES_DIR, save_profile_file
from .naming import BASE_MATERIALS, canonical_material


@dataclass(frozen=True)
class _CatalogRow:
    id: str
    material: str
    geometry_type: str
    name: str
    h: float
    b: float = 0.0
    tw: float = 0.0
    tf: float = 0.0
    seccion_cm2: float = 0.0
    peso_lineal_kg_m: float = 0.0
    macizo: bool = False


# id, material, geometry_type, designacion, h, b, tw, tf, seccion_cm2, peso_lineal_kg_m, macizo
CATALOG_ROWS: Tuple[_CatalogRow, ...] = (
    _CatalogRow("AC-IPE-100", "Acero al Carbono", "Viga I", "IPE 100", 100, 55, 4.1, 5.7, 10.3, 8.1),
    _CatalogRow("AC-IPE-200", "Acero al Carbono", "Viga I", "IPE 200", 200, 100, 5.6, 8.5, 28.5, 22.4),
    _CatalogRow("AC-HEA-140", "Acero al Carbono", "Viga H", "HEA 140", 133, 140, 5.5, 8.5, 31.4, 24.7),
    _CatalogRow("AC-UPN-100", "Acero al Carbono", "Viga U", "UPN 100", 100, 50, 6, 8.5, 13.5, 10.6),
    _CatalogRow("AC-ANG-50", "Acero al Carbono", "Angular", "L 50x50x5", 50, 50, 5, 5, 4.8, 3.77),
    _CatalogRow("AC-TUB-C40", "Acero al Carbono", "Cuadrado", "TC 40x40x3", 40, 40, 3, 3, 4.2, 3.3),
    _CatalogRow("AC-TUB-R60", "Acero al Carbono", "Redondo", "TR Ø60.3x3", 60.3, 0, 3, 0, 5.4, 4.24),
    _CatalogRow("GALV-TC-1/2", "Acero Galvanizado", "Redondo", 'Tubo ISO Ø21.3x2.6 (1/2")', 21.3, 0, 2.6, 0, 1.53, 1.22),
    _CatalogRow("GALV-TC-1", "Acero Galvanizado", "Redondo", 'Tubo ISO Ø33.7x3.2 (1")', 33.7, 0, 3.2, 0, 3.07, 2.44),
    _CatalogRow("GALV-COR-C125", "Acero Galvanizado", "Perfil C", "Correa C 125x50x2", 125, 50, 2, 2, 4.5, 3.65),
    _CatalogRow("GALV-COR-Z150", "Acero Galvanizado", "Perfil Z", "Correa Z 150x50x2", 150, 50, 2, 2, 5, 4.05),
    _CatalogRow("INX-TR-42", "Acero Inoxidable", "Redondo", "Tubo Inox Ø42.4x1.5", 42.4, 0, 1.5, 0, 1.93, 1.54),
    _CatalogRow("INX-TR-50", "Acero Inoxidable", "Redondo", "Tubo Inox Ø50.8x1.5", 50.8, 0, 1.5, 0, 2.32, 1.85),
    _CatalogRow("INX-TC-40", "Acero Inoxidable", "Cuadrado", "Tubo Inox 40x40x1.5", 40, 40, 1.5, 1.5, 2.27, 1.81),
    _CatalogRow("INX-MAC-20", "Acero Inoxidable", "Redondo", "Macizo Inox Ø20", 20, 0, 0, 0, 3.14, 2.49, macizo=True),
    _CatalogRow("INX-PLE-50", "Acero Inoxidable", "Pletina", "Pletina Inox 50x5", 50, 5, 0, 0, 2.5, 1.98, macizo=True),
    _CatalogRow("ALU-RAN-20", "Aluminio", "Ranurado", "Perfil Ranurado 20x20", 20, 20, 0, 0, 1.66, 0.45),
    _CatalogRow("ALU-RAN-40", "Aluminio", "Ranurado", "Perfil Ranurado 40x40", 40, 40, 0, 0, 5.37, 1.45),
    _CatalogRow("ALU-RAN-45", "Aluminio", "Ranurado", "Perfil Ranurado 45x45", 45, 45, 0, 0, 5.55, 1.5),
    _CatalogRow("ALU-RAN-4080", "Aluminio", "Ranurado", "Perfil Ranurado 40x80", 80, 40, 0, 0, 9.63, 2.6),
    _CatalogRow("ALU-TUB-R50", "Aluminio", "Redondo", "Tubo Al Ø50x2", 50, 0, 2, 0, 3.01, 0.81),
    _CatalogRow("ALU-ANG-30", "Aluminio", "Angular", "L Aluminio 30x30x3", 30, 30, 3, 3, 1.71, 0.46),
)

_SPECIFIC_WEIGHT_BY_MATERIAL = {name: sw for name, sw in BASE_MATERIALS}


def _entry_id(row: _CatalogRow) -> str:
    safe = "".join(c if c.isalnum() else "-" for c in row.id).strip("-").lower()
    return f"catalog-{safe}"


def _build_entry(row: _CatalogRow) -> CustomProfileEntry:
    from .profile_geometry import render_section_pixmap

    material = canonical_material(row.material)
    specific_weight = _SPECIFIC_WEIGHT_BY_MATERIAL.get(material, 7.85)

    entry = CustomProfileEntry(
        id=_entry_id(row),
        name=row.name,
        fields=["h (mm)", "b (mm)", "tw (mm)", "tf (mm)"],
        field_defaults={"h (mm)": row.h, "b (mm)": row.b, "tw (mm)": row.tw, "tf (mm)": row.tf},
        meta={
            "material": material,
            "specific_weight": specific_weight,
            "geometry_type": row.geometry_type,
            "h": row.h,
            "b": row.b,
            "tw": row.tw,
            "tf": row.tf,
            "seccion_cm2": row.seccion_cm2,
            "peso_lineal_kg_m": row.peso_lineal_kg_m,
            "macizo": row.macizo,
        },
    )

    pixmap = render_section_pixmap(
        row.geometry_type, row.h, row.b, row.tw, row.tf, macizo=row.macizo, size=128,
    )
    if not pixmap.isNull():
        os.makedirs(PROFILES_DIR, exist_ok=True)
        image_name = f"{entry.id}.png"
        pixmap.save(os.path.join(PROFILES_DIR, image_name))
        entry.image = image_name

    return entry


def ensure_catalog_profiles() -> int:
    """Create any catalogue profile that doesn't exist yet. Returns count added.

    Requires a running ``QApplication`` (thumbnails are rendered with Qt).
    Safe to call repeatedly: existing ids (and any the user has since
    deleted) are left untouched.
    """
    from . import app_config

    prefs = app_config.get()
    existing_ids = {p.id for p in prefs.custom_profiles}
    added = 0
    for row in CATALOG_ROWS:
        entry_id = _entry_id(row)
        if entry_id in existing_ids:
            continue
        entry = _build_entry(row)
        prefs.custom_profiles.append(entry)
        save_profile_file(entry)
        added += 1
    if added:
        app_config.save(prefs)
    return added
