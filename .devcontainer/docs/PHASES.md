# Nestify 2.0 — Fases de implementación

> **⚠️ Motor de nesting — invariante absoluto**: `use_bevel=OFF` → 1D largo nominal. `use_bevel=ON` → 2D contorno SAT, NUNCA largo nominal. Condición flush-fit: `alpha_R + alpha_L ≈ 0` (signos opuestos). Ver `TODO.md` y `AGENTS.md`.

Estado: **Fases A, B y C completadas** (sin entregas parciales).

## Fase A — Fundamentos

| Entrega | Estado |
|---------|--------|
| PDF multi-material + diálogo traducido | Hecho |
| Exportar solo barra visible / contexto activo | Hecho |
| Sincronía kerf/margen Cortes ↔ Anidado en vivo | Hecho |
| Tiempos de optimización (1–5) en Ajustes + persistencia | Hecho |
| Claves i18n (snap, opt times, cancel, etc.) | Hecho |
| Tests `tests/test_phase_a.py` | Hecho |

## Fase B — Motor de anidado

| Entrega | Estado |
|---------|--------|
| Colocación por colisión de contornos (polilíneas reales; sin `x = L`) | Hecho |
| `can_place_on_bar`, snap con kerf/bevel/corte común | Hecho |
| Rotación manual siempre (Ctrl+Q/E) | Hecho |
| Auto-anidar usa motor de colocación | Hecho |
| Snap por zonas (cerca = snap, lejos = libre en barra) | Hecho |
| Snap antes/después de piezas (borde contrario) | Hecho |
| Preview ghost en posición de snap (opaco en barra) | Hecho |
| Zona snap configurable (mm) en Ajustes | Hecho |
| Tests `tests/test_phase_b.py` | Hecho |

## Fase C — Paneles y material

| Entrega | Estado |
|---------|--------|
| Paneles ocultables ◧/◨ + persistencia | Hecho |
| Redimensionado (PanedWindow doble sash) | Hecho |
| Arrastrar paneles (⋮⋮) a izq/der con iluminación de borde | Hecho |
| Apilamiento vertical si ambos paneles al mismo lado | Hecho |
| Ajustes → Anidado — paneles y snap | Hecho |
| Autocomplete material + lupa | Hecho |
| Crear/cambiar sub-tab al elegir material | Hecho |
| Sub-tab inicial «Anidado 1» (`ensure_material_contexts`) | Hecho |
| Filtro sidebar Completas/Pendientes | Hecho |
| Árbol barras colapsable + filtro por barra | Hecho |
| Esc cancela pieza flotante | Hecho |
| Tests `tests/test_roadmap_phase_c.py`, `tests/test_phases_complete.py` | Hecho |

## Verificación

```bash
python3 -m pytest tests/ -q
python3 -m flake8 --max-line-length=120 nestify/ main.py
```

## Fuera de estas fases (roadmap `TODO.md`)

Anidado avanzado (retales, selección múltiple), Profile Creator, SQLite stock, export Excel multi-hoja, etc.
