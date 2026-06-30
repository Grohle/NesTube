"""
nestube/nestube/nestube/stock_export.py
Lightweight stock-inventory export (Excel). Kept separate from export_utils so
it doesn't pull in the PDF stack (fpdf/cryptography) — a stock export only needs
pandas/openpyxl. Pure: the caller supplies the path (Qt QFileDialog).
"""
from __future__ import annotations

from typing import List

from nestube.i18n import t


def export_stock_to_excel(filepath: str, bars: List, currency: str = "EUR") -> None:
    """Write the stock inventory to an .xlsx at ``filepath``.

    One row per stock bar: identity, dimensions, availability and pricing.
    Remnants report their offcut length. Headers are localised via t().
    """
    import pandas as pd  # local import: keeps module load light

    rows = []
    for b in bars:
        length = b.retal_length if getattr(b, "is_retal", False) else b.length
        rows.append({
            t("stock_profile"): b.profile_name,
            t("stock_material"): b.material_desc,
            t("material_quality"): b.quality,
            f"{t('stock_length')} (mm)": round(length, 1),
            t("stock_qty"): b.quantity,
            t("stock_available"): t("yes") if b.quantity > 0 else t("no"),
            t("stock_retal"): t("yes") if getattr(b, "is_retal", False) else t("no"),
            f"{t('wall_thickness')} (mm)": b.espesor or "",
            "kg/m": b.kg_por_m or "",
            f"{t('price_kg', sym=currency)}": b.precio_kg or "",
            f"{t('price_m', sym=currency)}": b.precio_m or "",
            f"{t('price_bar', sym=currency)}": b.precio_barra or "",
            t("notes"): b.notes or "",
        })
    if not rows:
        rows = [{t("stock_profile"): ""}]
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, index=False, sheet_name="Stock")
