# Critical Cost Review (roadmap §3 — Revisión Crítica de Costes)

Exhaustive technical verification of every parameter and formula in the costing
system. Scope: `nestify/logic.py` (`area_seccion`, `calcular_resultado`,
`total_cost_for_context`), `nestify/models.py` (`Material`, `ManoObra`,
`ResultadoCorte`, units) and the UI feed in `nestify/ui_qt/tab_perfiles.py`
(`_build_config`, `_barras_for_costing`, `_calcular`).

> **Note on the engine.** `logic.py` is protected and the cost path has **no
> unit tests**. The findings below that touch engine formulas are written up
> for a decision, not silently changed — several are domain calls (how miter
> labour should be charged, what "price per m²" means) that the maintainer must
> confirm before a fix lands.

Reference example used throughout: RHS **80×40×3**, cut **1850 mm × 4**,
`peso_especifico = 7.85`, `precio_kg = 1.85`.
Hollow area = `80·40 − (80−6)(40−6) = 3200 − 2516 = 684 mm²`.

---

## ✅ Verified correct

- **Weight from specific weight** (`logic.py:183`)
  `kg_ud = largo · area · peso_especifico / 1e6`.
  Units check out: `mm · mm² = mm³`; `peso_especifico` is **t/m³**, and
  `t/m³ × mm³ = (×1e3 kg/t)·(×1e-9 m³/mm³) = ×1e-6 kg`. So `/1e6` is exactly
  right. Example: `1850·684·7.85/1e6 = 9.933 kg` ✓ (matches the UI).

- **Weight from kg/m** (`:181`) `kg_ud = (largo/1000)·kg_por_m` ✓.

- **Linear price** (`:189`) `(largo/1000)·precio_m` ✓.

- **Bar-price proration** (`:192`) `(largo/longitud_barra)·precio_barra`
  per unit → ×cantidad in the line total = fraction-of-bars-used × bar price ✓.

- **Cost modes** (`tab_perfiles._barras_for_costing`) — "shared" uses the
  globally optimised bars; "individual" puts each piece on its own bar. Correct
  and engine-free ✓.

- **Scrap distribution math** (`:195–210`) — total leftover kg across all bars
  is split evenly over `total_piezas`; summed across the job it recovers the
  full scrap cost once (when `total_piezas == Σ cantidad`) ✓. (But see F4 for
  the valuation gap.)

---

## Findings

### F1 — Miter labour surcharge is mis-modelled (HIGH) — ✅ FIXED

> Fixed in `logic.py`: miter labour is now derived per-cut from the cut's own
> mitered ends (`miter_ends · porcentaje_inglete`), charged per piece, and no
> longer depends on the job-wide `n_ingletes_total` (kept as an accepted-but-
> unused arg for caller compatibility). Covered by `tests/test_costing.py`
> (`test_labour_*`).


`logic.py:215`:
```python
t_total_h = (
    mo.tiempo_corte_recto * corte.cantidad                                   # straight, per line
    + n_ingletes_total * mo.tiempo_corte_recto * mo.porcentaje_inglete / 100 # miter surcharge
) / 60
mo_ud = t_total_h * mo.coste_operario_hora / corte.cantidad
```
`n_ingletes_total` is the **job-wide count of lines that have any miter** (same
value passed to every line). Because `mo_ud` divides by `cantidad` and
`precio_total_linea` multiplies by `cantidad`, the per-line labour total is
`(A + B)/60 · rate` where `B` is that job-wide surcharge. So:

- **`B` is added to every line** → the whole-job miter surcharge is counted once
  *per line*, i.e. multiplied by the number of lines `L`. A 10-line job pays the
  miter premium ~10×.
- Within a line it does **not** scale with `cantidad` or with the number of
  mitered ends, so a single line of 100 mitered pieces gets the same miter time
  as one piece.

The model is muddled in both directions (over-counts across lines,
under-counts within a line). **Needs a decision on the intended charging
rule.** Most likely intent: a miter end costs `tiempo_corte_recto · pct/100`
extra **per mitered cut**, charged per piece, e.g.

```python
miter_ends = (1 if corte.inglete1 else 0) + (1 if corte.inglete2 else 0)
t_line_min = corte.cantidad * (
    mo.tiempo_corte_recto + miter_ends * mo.tiempo_corte_recto * mo.porcentaje_inglete / 100
)
```
(`n_ingletes_total` would then no longer be needed.)

### F2 — `m2_ud` is dimensionally volume, not area (MEDIUM) — ✅ FIXED

> Fixed in `logic.py`: `m2_ud = perimetro_seccion(perfil) · largo / 1e6`
> (developed outer surface in m², which scales with length and is the useful
> meaning for surface-priced materials). New `perimetro_seccion()` helper
> (π·d for round, 2·(a+b) for rect/L, bounding 2·(a+b) for U/H). Covered by
> `tests/test_costing.py` (`test_price_per_m2_uses_developed_surface`,
> `test_perimeter_rect_and_round`).


`logic.py:184`: `m2_ud = largo · area / 1e6`. That is `mm · mm² = mm³`, scaled
by `1e-6` — a **volume-like** quantity, not m². It is then multiplied by
`precio_m2` (price per m²), so "price per m²" actually behaves as a volumetric
price. Example shows `1850·684/1e6 = 1.2654` labelled "1.265400 m²", but the
true cross-section is `684 mm² = 0.000684 m²` and the true outer surface is
`perimeter·length`.

Two plausible intended meanings — **needs a decision**:
- **Cross-section in m²** (plate-style pricing): `m2_ud = area / 1e6` (drop the
  length).
- **Developed/outer surface in m²** (coating/painting): `m2_ud = perimeter ·
  largo / 1e6`, which needs a per-profile perimeter (not currently computed).

### F3 — Profit margin applies to material only, not labour (LOW — confirm)

`logic.py:212`: `precio_mat *= (1 + margen/100)` runs **before** labour is added
and labour is never marked up. If the margin is meant as an overall markup it
should also cover labour; if it is purely a material markup this is correct.
Confirm intent.

### F4 — Scrap is always valued at `precio_kg` (LOW)

`logic.py:210`: the distributed remnant cost uses `precio_kg` only. A user who
prices by `precio_m` or `precio_barra` and leaves `precio_kg = 0` gets **no**
scrap cost distributed, silently. Consider valuing scrap by the same method the
user actually priced with.

### F5 — The four pricing methods are summed, not exclusive (LOW)

`logic.py:186`: `precio_kg`, `precio_m2`, `precio_m` and `precio_barra` are
**added together**. They are intended as alternative methods; if a user fills
more than one they stack with no warning. Consider a UI hint or a single
"pricing basis" selector.

### F6 — `area_seccion` solid L/U (INFO — verify dimension semantics)

`logic.py:137` solid **L** returns `lado_a · lado_b` (full bounding rectangle),
and solid **U** returns `(lado_a + lado_c)·lado_b`. These only make sense for a
genuinely solid section and depend on the exact `lado_a/b/c` meaning per
profile. The **hollow** formulas (the common case) look correct. Worth a quick
confirmation of the dimension legend per profile type.

---

## Status

- **F1, F2 — fixed** behind a new `tests/test_costing.py` (13 cost tests added;
  the cost path previously had none). Engine touched only where the bug
  originated (`logic.py`), with the public API preserved.
- **F3–F6 — deferred** (low severity / domain decisions): margin on material
  only, scrap valued only at `precio_kg`, the four pricing bases summed rather
  than exclusive, and the solid L/U area semantics. These are documented here
  and can be revisited if the maintainer wants to change the intended behaviour.
