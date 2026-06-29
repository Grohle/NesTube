# Guia UI — Nestify PySide6

Documento de referencia para la revision completa de la interfaz Qt.
Cubre: peticiones del usuario, estado actual, especificacion visual, interacciones,
accesibilidad y buenas practicas PySide6.

---

## 1. Resumen de peticiones del usuario (cronologico)

### Sesion 1 — Migracion PySide6 y correcciones UX

| # | Peticion (verbatim / resumida) | Estado |
|---|---|---|
| P1 | **"continua por donde lo dejaste"** — continuar la migracion PySide6 completa con paridad 1:1 respecto a CTk | Implementado |
| P2 | **Restriccion critica**: `nesting_engine.py` INTOCABLE, los 46 tests deben pasar siempre | Vigente (46/46 pass) |
| P3 | **Semantica del margen**: "el margen es como un kerf extra" — el margen se suma al gap inter-pieza, NO se resta de los extremos de la barra | Implementado |
| P4 | **Screenshot del tab Cortes** — multiples problemas reportados: | |
| P4a | Persistencia perdida entre tabs | Corregido |
| P4b | Campos demasiado cortos/cortados (fields too short/clipped) | Corregido (min-height 30px) |
| P4c | "Edit Fields" muestra "not implemented" | Corregido (inline QDialog) |
| P4d | Preview de nesting vacio tras Calculate | **Corregido** (perfil None guard + defensive paint) |
| P4e | CorteRow: falta simulador de forma, no hay toggle de direccion, falta texto "Miter", boton delete feo | Corregido |
| P4f | Nombre de cliente demasiado ancho, boton Calculate no naranja | Corregido |
| P5 | **Labels muestran nombres de codigo** en vez de texto UI (raw i18n keys) | Corregido (0 raw keys) |
| P6 | **Dibujos de perfiles** todos iguales (fallback triangulo) — deben diferir por tipo | Corregido (poligonos rellenos) |
| P7 | **Sidebars del nesting incompletos** vs version CTk | Corregido (click, swatches, context menu) |
| P8 | **Panel de remanentes** completamente ausente | Corregido (toggle, refresh, apply-to-stock) |

### Sesion 2 — Conflictos, auditoria, color y motor visual

| # | Peticion (verbatim / resumida) | Estado |
|---|---|---|
| P9 | **"hay conflictos en la pr73"** — resolver merge conflicts en PR #73 | Corregido |
| P10 | **"te has dejado algo por hacer?"** — auditoria completa de tareas pendientes | Corregido (16 keys i18n adicionales) |
| P11 | **Consistencia de color dark/light** — "no hay consistencias de color en cada modo oscuro/claro y errores de accesibilidad y legibilidad" | Corregido (live `_th.*` refs, QPalette, TEXT_DIM fix) |
| P12 | **Modo nativo PySide6** — "en pyside6 hay un modo claro/oscuro nativo y no hace falta hardcodear el color. Si es asi aplicalo" | Corregido (build_palette + apply_theme + QSS) |
| P13 | **Motor de representacion visual del nesting** — "sigue sin existir un motor de representacion visual de los nesting, definemelo por completo" | Corregido (perfil None guard, BG_CANVAS, fit_scene, sceneRect) |
| P14 | **"OJO, no te enganes, no se ve el nesting ni en modo claro ni en oscuro"** — el motor no renderiza nada | Corregido (root cause: AttributeError en profile_section_height) |

### Sesion 3 (actual) — Guia UI completa

| # | Peticion | Estado |
|---|---|---|
| P15 | Resumen de TODAS las peticiones UI + plan de integracion de cada una | Este documento |
| P16 | Plan de funcionamiento completo de la interfaz adaptado a PySide6 | Secciones 2-8 de este documento |
| P17 | Crear `guia_UI.md` como guia de revision | Este documento |
| P18 | Incluir arreglos por buenas practicas y filtros de accesibilidad | Seccion 8 |

---

## 2. Arquitectura general de la ventana

```
NestifyApp (QMainWindow, 1280x800, min 900x580)
├── QMenuBar
│   ├── File: open, save, save_as, export (excel/pdf), import, exit
│   ├── View: theme (dark/light), font_size (8-14), language (en/es), units
│   ├── Settings: calc_system, cost_mode, materials, profiles, currency, PDF, nesting
│   └── About/Help: version, donate, issues
├── Central Widget (QVBoxLayout, 0 margins)
│   └── QTabWidget
│       ├── Tab 0: Jobs Explorer
│       ├── Tab 1: Cuts (Cortes)
│       ├── Tab 2: Nesting
│       ├── Tab 3: Costs & Weight (Perfiles)
│       └── Tab 4: Stock
└── Status: geometry persistence via saveGeometry/restoreGeometry
```

### Flujo de datos entre tabs

```
AppState (compartido)
├── material_contexts[]: List[MaterialContext]
│   ├── cortes, longitud_barra, perdida_corte, margen_tubo
│   ├── barras_necesarias (resultado de Calculate)
│   └── nesting_layout (resultado de nesting manual/auto)
├── active_material_index: int
├── nesting_bar_lengths: List[float]
└── perfil: ConfigPerfil (para seccion transversal)

Tab Cortes → Calculate → apply_auto_barras(state, ctx, barras)
                       → NestingPreviewWidget.set_state(state)
Tab Nesting → auto-nest / manual → sync_to_state()
Tab Perfiles → lee barras_necesarias → calcula costes
```

### Cambio de tema

```python
_set_theme(mode):
    apply_theme(mode)           # actualiza theme_qt.ACCENT, .BG_CARD, etc.
    app.setPalette(build_palette(mode))  # QPalette nativo Qt
    app.setStyleSheet(build_stylesheet(mode))  # QSS completo
```

Los ficheros con paintEvent usan `import nestify.ui_qt.theme_qt as _th` para acceso
en tiempo real (NO copias de import-time).

---

## 3. Tab Jobs Explorer

```
TabJobsExplorer (QWidget, QHBoxLayout)
├── QSplitter (Horizontal, no collapsible, 260|600)
│   ├── LEFT: Job List (min 220, max 340, BG_CARD)
│   │   ├── Header (12×12×12×6 margins)
│   │   │   ├── QLabel "JOBS" (ACCENT, bold 13px)
│   │   │   └── QPushButton "New job" (variant=accent, h=28)
│   │   ├── Search bar (8×0×8×4 margins)
│   │   │   ├── QComboBox field selector (100×26)
│   │   │   ├── QLineEdit search (h=26, stretch)
│   │   │   ├── QPushButton "🔍" (26×26)
│   │   │   └── QPushButton "✕" clear (26×26)
│   │   └── QScrollArea
│   │       └── _JobTile items (52px h, 4px spacing)
│   │           ├── Name (bold si selected, ACCENT)
│   │           └── Client + date (TEXT_DIM, 9px)
│   └── RIGHT: Job Detail (8×8×8×8 margins)
│       ├── Placeholder: "Select a job" (TEXT_DIM, center)
│       └── Detail card (hidden initially):
│           ├── Header: name (ACCENT, bold 13px) + date (TEXT_DIM, 9px)
│           ├── Meta grid: Client, Offer, Order, Description
│           ├── Pieces table (4 cols: #, Description, Length, Qty)
│           └── Buttons: [Open] (accent) [Delete] (danger)
```

**Interacciones:**
- Click en _JobTile → selecciona, muestra detalle
- Doble-click → abre el job (carga state)
- Busqueda: campos name/client/material/description/order/offer, debounce 200ms

---

## 4. Tab Cortes (Cuts)

```
TabCortes (QWidget, QVBoxLayout, 0 margins, 0 spacing)
├── MaterialSubTabs (has_total=False)
│   └── [Mat 1] [Mat 2] ... [+]
├── Header Card (QFrame role=card, 8×6×8×6 margins, 8px spacing)
│   ├── Row 0: MaterialAutocomplete(2col) + QLineEdit pedido + QLineEdit oferta
│   ├── Row 1: QLineEdit cliente + [+ Add Field] + [✎ Edit Fields]
│   └── Row 2: Custom fields (dynamic, hidden when empty)
├── Controls Card (QFrame role=card, 8×6×8×6 margins, 12px spacing)
│   ├── QLabel "Bar length" + QLineEdit (w=72, mono) default "6000"
│   ├── QLabel "Kerf" + QLineEdit (w=54, mono) default "2.0"
│   ├── QLabel "Margin" + QLineEdit (w=54, mono) default "0"
│   ├── [stretch]
│   ├── QLabel result (ACCENT, 11px) "N barras · XX.X%"
│   ├── QPushButton "+ Add cut" (variant=ghost, h=28)
│   └── QPushButton "⚙ Calculate" (variant=accent, h=28)
└── QSplitter (Horizontal, non-collapsible, stretch 0|1)
    ├── LEFT (min 320): Cuts List
    │   ├── QLabel "CUTS" (ACCENT, bold 11px)
    │   └── QScrollArea (no h-scroll)
    │       └── CorteRow items + stretch
    └── RIGHT (min 200): Preview
        ├── QLabel "Nesting Preview" (ACCENT, bold 11px)
        └── QScrollArea
            └── NestingPreviewWidget (QPainter custom)
```

### CorteRow (widget)

```
QFrame (h=38, 6px spacing, QGridLayout)
├── Col 0: Badge QLabel (24w, TEXT_DIM, mono 9px, border-radius 3)
├── Col 1: QLineEdit description (stretch 3, placeholder i18n)
├── Col 2: QLineEdit length (72w, mono, DoubleValidator)
├── Col 3: QLineEdit quantity (40w, mono, IntValidator)
├── Col 4: Bevel 1 group
│   ├── QLabel "Miter"
│   ├── QCheckBox enable
│   ├── _MiterToggle (28×20, painted arrow up/down)
│   └── QLineEdit degree (36w)
├── Col 5: Bevel 2 group (same structure)
├── Col 6: ShapePreview (64×32, painted polygon)
└── Col 7: QPushButton "✕" delete (28×28, variant=danger)
```

**Senales:** `changed`, `deleted(int)`, `tab_from_last(int)` (Tab→add row)

### NestingPreviewWidget (QPainter)

```
Para cada barra:
  ├── Bar label (izquierda): "Barra N" — TEXT_PRI, bold 8pt
  ├── Efficiency (derecha): "XX.X% ↩ NNmm" — TEXT_SEC, mono 7pt
  ├── Bar background: BG_CANVAS fill, BORDER stroke 1px
  ├── Piezas: rectangulos/trapezoides coloreados (_PALETTE[10])
  │   ├── Outline: "#080808" 1px
  │   ├── Label (si cw > 20px): largo en mm, blanco, centrado, mono 7pt
  │   └── Gap kerf: linea vertical "#2A2A2E"
  └── Scrap: hatching diagonal, TEXT_DIM, step=6px
```

**Defensive painting:** try/except alrededor de `compute_nesting_canvas_layout()`,
`resizeEvent` → `self.update()` para re-render en resize.

---

## 5. Tab Nesting (Interactive)

```
TabNesting (QWidget, QVBoxLayout, 0 margins, 0 spacing)
├── MaterialSubTabs (has_total=False)
├── Toolbar (QFrame, h=44, BG_CARD, border-bottom)
│   └── QHBoxLayout (6×4×6×4 margins, 4px spacing)
│       ├── 💾 Save (30×30, icon)
│       ├── 🗑 Clear (30×30, icon)
│       ├── Separator (QFrame VLine, 2w)
│       ├── PillSwitch "Advanced|Simple" (140×28)
│       ├── PillSwitch "Stock|Fictional" (130×28)
│       ├── QPushButton "+ Add Bar" (h=28)
│       ├── Separator
│       ├── QLabel "profile_height" + QLineEdit (48w)
│       ├── QLabel "Kerf" + QLineEdit (40w, mono)
│       ├── QLabel "Margin" + QLineEdit (40w, mono)
│       ├── QCheckBox "Common cut"
│       ├── QCheckBox "Snap" (checked)
│       ├── Separator
│       ├── ↺ ⇕ ⇄ ↻ rotate/flip buttons (30×30 each)
│       ├── Separator
│       ├── QComboBox optimization (1-5, unlimited)
│       ├── QComboBox strategy
│       ├── [stretch]
│       └── QPushButton "⚙ Auto-nest" (variant=accent, 120×32)
├── Info bar (transparent)
│   ├── QLabel qty (ACCENT, 11px, hidden)
│   ├── [stretch]
│   └── QLabel status (TEXT_SEC, 10px) "N bars · X/Y placed · Z%"
└── QSplitter (Horizontal, collapsible, 240|1200|200)
    ├── LEFT: Pieces Panel (min 160, max 280)
    │   ├── Header (BG_CARD)
    │   │   ├── QLabel "PIECES REMAINING (n)" (ACCENT, bold 10px)
    │   │   └── Filter: [All] [Complete] [Incomplete] (h=20, 9px)
    │   └── QScrollArea
    │       └── Piece rows (dynamic)
    │           ├── Color swatch QLabel "■" (color=piece.color)
    │           ├── Description + "placed/total"
    │           ├── Click → _select_piece (comienza floating)
    │           ├── Click (si done=True) → _highlight_all_instances
    │           └── Right-click → _highlight_all_instances
    ├── CENTER: NestingView (QGraphicsView)
    │   └── NestingScene (QGraphicsScene, 1 unit = 1 mm)
    │       ├── BarBackground (QGraphicsRectItem)
    │       │   └── Fill: BG_MID, Stroke: BORDER 0.5px
    │       ├── PlacedPieceItem (QGraphicsPolygonItem)
    │       │   ├── Fill: piece.color, Stroke: "#080808" 0.3px
    │       │   ├── Selected: ACCENT stroke 1.0px
    │       │   ├── Highlighted: "#FFE500" stroke 0.8px
    │       │   └── Label: largo mm, blanco, mono 6pt (si > 8mm)
    │       ├── RemantItem (QGraphicsRectItem)
    │       │   └── Fill: "#2E7D32" alpha 80, Stroke: dashed 0.8px
    │       ├── FloatPreviewItem (QGraphicsPolygonItem)
    │       │   └── 55% opacity, ACCENT border (snap) / "#888" (free)
    │       └── Bar labels: "Bar N", TEXT_PRI, 7pt
    └── RIGHT: Bars Panel (min 140, max 260)
        ├── Header
        │   ├── QLabel "BAR LIST" (ACCENT, bold 10px)
        │   ├── QPushButton "Show all" (h=20, 9px)
        │   └── QPushButton "↩ Remnants" (h=20, 9px)
        ├── QScrollArea (bar sections)
        │   └── Bar header: "Bar N (M pieces)" → expandable
        │       └── Piece rows: [■ swatch] [desc × count]
        │           └── Click → _highlight_in_bar
        └── Remnant Panel (initially hidden)
            ├── QLabel "GENERATE REMNANTS"
            ├── QLineEdit min_length (default "1000")
            ├── QPushButton "↻ Refresh"
            ├── QPushButton "✓ Apply to stock"
            └── QLabel remnant_list (multiline)
```

### Coordenadas de escena

```
section_h = profile_section_height(perfil) or 50.0 mm
BAR_GAP_MM = 20.0 mm
bar_y[i] = i × (section_h + BAR_GAP_MM)
label_y[i] = bar_y[i] - 10
sceneRect = (-10, -14, max_bar_len + 20, last_y + 20)
```

### Interacciones del canvas

| Evento | Signal | Accion |
|--------|--------|--------|
| Click izq en pieza | `piece_pressed` | Seleccionar pieza, resaltar en sidebar |
| Click der en pieza | `piece_right_pressed` | Menu contextual: Remove, Flip H, Flip V |
| Click izq en fondo | `background_pressed` | Colocar pieza flotante o deseleccionar |
| Hover pieza | — | Cursor hand |
| Ctrl+wheel | — | Zoom (0.05x–40x, step 1.15) |
| Middle-drag / Ctrl+drag | — | Pan |
| Escape | — | Cancelar pieza flotante |
| Delete | — | Eliminar pieza seleccionada |
| Ctrl+Z / Ctrl+Y | — | Undo / Redo (stack 50) |
| Ctrl+Q / Ctrl+E | — | Rotar izq/der |
| Ctrl+S / Ctrl+A | — | Flip horizontal / vertical |

### fit_scene

Despues de cada `_rebuild_scene()`, se llama `QTimer.singleShot(0, self._view.fit_scene)`
para ajustar el viewport al contenido actual.

---

## 6. Tab Perfiles (Costs & Weight)

```
TabPerfiles (QWidget, QVBoxLayout, 0 margins, 0 spacing)
├── MaterialSubTabs (has_total=True) ← incluye boton "Total"
├── QSplitter (Horizontal, non-collapsible, 340|rest)
│   ├── LEFT: Config (min 260, max 420)
│   │   └── QScrollArea → QVBoxLayout (8 margins, 6 spacing)
│   │       ├── [⚙ Calculate] [Clear] buttons
│   │       ├── [Excel] [PDF] [DOCX] [Print] export buttons (h=24, 10px)
│   │       ├── Section "WEIGHT"
│   │       ├── ProfileTile favorites (hasta 5, 72×90 px each)
│   │       ├── QComboBox profile selector
│   │       ├── Dimension fields (dynamic per TipoPerfil):
│   │       │   REDONDO: diametro
│   │       │   RECTANGULAR: lado_a, lado_b
│   │       │   L: lado_a, lado_b
│   │       │   U: lado_a, lado_b, lado_c
│   │       │   H: lado_a, lado_b, lado_c, espesor_int_H
│   │       ├── Wall thickness + Solid checkbox
│   │       ├── kg/m field + specific weight (default 7.85)
│   │       ├── Section "PRICING"
│   │       ├── 5 price fields: price/kg, /m2, /m, /bar, margin%
│   │       ├── Currency combo (EUR,USD,GBP,JPY,CNY,CAD,AUD,CHF,SEK,NOK)
│   │       ├── Distribute scrap checkbox
│   │       ├── Section "LABOUR"
│   │       └── 3 fields: cut_time, miter%, operator_cost/h
│   └── RIGHT: Results (min 200)
│       ├── QLabel "Results per cut" (ACCENT, bold 11px)
│       └── QScrollArea → result cards
│           └── _ResultCard per corte:
│               ├── Accent stripe (h=3)
│               ├── Header: "desc · NNmm × qty units"
│               ├── Grid: weight, area, price_mat, price_labour, total, per_meter, line_total
│               └── Separator + "TOTAL: X,XXX.XX €"
```

### ProfileTile (widget, 72×90 px)

```
paintEvent:
  ├── Background: BG_CARD fill
  ├── Upper area (60px): shape preview o imagen
  │   ├── REDONDO: circulo hueco (fill ACCENT alpha 200, inner BG_CARD)
  │   ├── RECTANGULAR: rectangulo hueco (wall = 20% min dim)
  │   ├── L: poligono 6 puntos relleno
  │   ├── U: poligono 8 puntos relleno
  │   ├── H: 3 rectangulos (flange + web + flange)
  │   ├── FLAT: barra delgada centrada
  │   └── Unknown: rectangulo dashed
  ├── Lower area (30px): nombre (TEXT_PRI, 8pt, centrado)
  └── Border: selected → ACCENT 2px, normal → BORDER 1px, radius 4
```

---

## 7. Tab Stock (Inventory)

```
TabStock (QWidget, QVBoxLayout)
├── Toolbar (QFrame, h=88, BG_CARD, border-bottom)
│   └── QVBoxLayout (8×6×8×4 margins, 4px spacing)
│       ├── Row 0: Action + filter buttons
│       │   ├── QPushButton "+ Add" (accent, h=30)
│       │   ├── QPushButton "✎ Edit" (h=30)
│       │   ├── QPushButton "✕ Remove" (danger, h=30)
│       │   ├── QLineEdit "🔍 Material…" (200×28)
│       │   ├── QComboBox profile filter (160×28)
│       │   ├── [stretch]
│       │   └── QLabel summary (TEXT_SEC, 11px)
│       └── Row 1: Selection + range filters
│           ├── QCheckBox "Select all"
│           ├── QLineEdit min_length (70×24)
│           ├── QLineEdit max_length (70×24)
│           └── QLineEdit min_retal (70×24)
└── QTableWidget (role=card, 4 margins)
    ├── Columns:
    │   0: Checkbox (32w, Fixed)
    │   1: Status dot (24w, Fixed) ● verde/rojo/dark-green
    │   2: Profile (140w, Fixed)
    │   3: Material (Stretch)
    │   4: Length (80w, Fixed, mono, right)
    │   5: Quantity (50w, Fixed, right)
    │   6: Available toggle (70w, Fixed) ✓/✕ button
    │   7: Retal indicator (50w, Fixed, center)
    └── Row height: 28px
```

**Filtrado:** texto + perfil + rango longitud, debounce 200ms

---

## 8. Sistema de temas y accesibilidad

### Paleta de colores

| Token | Dark | Light | Uso |
|-------|------|-------|-----|
| BG_APP | `#161618` | `#F5F5F7` | Fondo ventana |
| BG_MID | `#1E1E20` | `#EBEBED` | Fondo medio (toolbars) |
| BG_CARD | `#27272A` | `#FFFFFF` | Tarjetas, paneles |
| BG_CANVAS | `#111113` | `#E8E8EA` | Fondo canvas/preview |
| BG_HOVER | `#333336` | `#E0E0E3` | Hover |
| ACCENT | `#F05A22` | `#E8521A` | Naranja principal |
| TEXT_PRI | `#F2F2F2` | `#1C1C1E` | Texto principal |
| TEXT_SEC | `#8A8A8E` | `#636366` | Texto secundario |
| TEXT_DIM | `#48484C` | `#86868B` | Texto terciario/placeholder |
| SUCCESS | `#34C759` | `#28A745` | Verde exito |
| DANGER | `#FF3B30` | `#DC3545` | Rojo peligro |
| BORDER | `#3A3A3C` | `#D1D1D6` | Bordes |

### QPalette mapping

```python
Window          → BG_APP
WindowText      → TEXT_PRI
Base            → BG_CARD
AlternateBase   → BG_MID
Text            → TEXT_PRI
Button          → BG_MID
ButtonText      → TEXT_PRI
Highlight       → ACCENT
HighlightedText → #FFFFFF
Link            → ACCENT
PlaceholderText → TEXT_DIM
ToolTipBase     → BG_CARD
ToolTipText     → TEXT_PRI
```

### Colores de seleccion (nesting)

```
COLOR_SELECT_SINGLE  = #00FFFF  (cian)
COLOR_SELECT_MULTI   = #FF00FF  (magenta)
COLOR_HIGHLIGHT      = #FFE500  (amarillo)
```

### Accesibilidad — WCAG AA

| Requisito | Estado |
|-----------|--------|
| TEXT_DIM light sobre blanco ≥ 3:1 | Corregido: `#86868B` = 3.5:1 (era `#AEAEB2` = 2.3:1) |
| TEXT_PRI sobre BG_CARD ≥ 4.5:1 | OK: dark `#F2F2F2/#27272A` = 11.7:1, light `#1C1C1E/#FFFFFF` = 17.4:1 |
| TEXT_SEC sobre BG_CARD ≥ 3:1 | OK: dark `#8A8A8E/#27272A` = 3.3:1, light `#636366/#FFFFFF` = 5.7:1 |
| ACCENT sobre BG_CARD ≥ 3:1 | OK: dark `#F05A22/#27272A` = 3.8:1, light `#E8521A/#FFFFFF` = 3.9:1 |
| Texto blanco en piezas ≥ 3:1 | OK: todas las 10 paleta tienen contrast ≥ 3:1 con blanco |

### Buenas practicas PySide6

| Practica | Implementacion |
|----------|---------------|
| **Live theme colors** | `import theme_qt as _th` + `_th.BG_CARD` en paintEvent (no copies) |
| **QPalette nativo** | `build_palette()` aplicado en `_set_theme()` |
| **QSS centralizado** | `build_stylesheet()` unico, QSS por-widget solo para layout |
| **No hardcodear colores** | Eliminar `#1A1A1E` → usar `_th.BG_CANVAS` |
| **setMinimumHeight** fuera de paintEvent | Usar `updateGeometry()` + `sizeHint()` |
| **Defensive painting** | try/except en `paintEvent`, None guards |
| **resizeEvent** | Re-trigger `update()` en widgets con custom paint |

---

## 9. Widgets reutilizables

### MaterialSubTabs

```
QWidget (QHBoxLayout, 0 margins, 4 spacing)
├── QPushButton tabs (h=28, clickable, double-click → rename)
├── QPushButton "+" add (28×28)
└── QPushButton "Total" (optional, h=28)
Signals: tab_changed(int), before_switch(from,to), tab_renamed(idx,name)
```

### PillSwitch

```
QWidget (fixed size, animated)
├── Track: rounded rect (SUCCESS if on, BG_CARD if off)
├── Border: ACCENT if on, BORDER if off
├── Labels: off_text (left), on_text (right)
├── Knob: white circle, animated 150ms InOutQuad
Signal: toggled(value_str)
```

### MaterialAutocomplete

```
QWidget (QHBoxLayout)
├── SimpleAutocomplete material (stretch, debounce 180ms)
├── SimpleAutocomplete quality (stretch)
└── QPushButton "🔍" picker (variant=icon)
Signal: picked(material, quality)
```

---

## 10. Dimensiones de referencia

### Margenes estandar (L,T,R,B)

| Contexto | Margenes | Spacing |
|----------|----------|---------|
| Card/Panel | 8,6,8,6 | 6-8 |
| Toolbar | 6,4,6,4 | 4 |
| Dialog | 12,12,12,12 o 20,20,20,20 | 8-12 |
| Container snug | 4,4,4,4 | 2-4 |
| Header | 12,12,12,6 | — |

### Tamanos fijos

| Elemento | Tamano | Notas |
|----------|--------|-------|
| Icon button | 28×28 o 30×30 | variant=icon |
| Small button | h=20-22, 9px font | filter, show-all |
| Standard button | h=28-30 | ghost, accent |
| Title button | h=32-34 | auto-nest |
| QLineEdit min | h=30 (via QSS) | padding 4px 8px |
| ProfileTile | 72×90 | fixed |
| ShapePreview | 64×32 | fixed |
| CorteRow | h=38 | row height |
| Table row | h=28 | stock table |
| _JobTile | h=52 | job list |

### Fuentes

| Nombre | Familia | Tamano | Uso |
|--------|---------|--------|-----|
| F_TITLE | IBM Plex Sans | 15px bold | Titulos de dialogo |
| F_BOLD | IBM Plex Sans | 12px bold | Headers de seccion |
| F_BODY | IBM Plex Sans | 12px | Texto general |
| F_SMALL | IBM Plex Sans | 10px | Labels secundarios |
| F_CAPTION | IBM Plex Sans | 9px | Captions, badges |
| F_NUM | DejaVu Sans Mono | 11px | Valores numericos |
| F_NUM_SM | DejaVu Sans Mono | 10px | Valores compactos |
| F_BADGE | DejaVu Sans Mono | 9px | Badge numbers |

Todas ajustables via `font_size_offset` (-2 a +4).

---

## 11. Flujos de usuario criticos

### Calcular barras (Tab Cortes)

1. Usuario rellena: longitud barra, kerf, margen, cortes (desc + largo + qty)
2. Click "⚙ Calculate"
3. `_calcular()` → `calcular_barras(bar_len, cortes, gap=kerf+margin)`
4. `apply_auto_barras(state, ctx, barras)` → actualiza `ctx.barras_necesarias`
5. `NestingPreviewWidget.set_state(state)` → trigger `paintEvent`
6. Preview renderiza barras con piezas coloreadas

### Auto-nesting (Tab Nesting)

1. Usuario configura cortes en Tab Cortes, cambia a Tab Nesting
2. `load_state()` → `_rebuild_pieces()` + `_restore_from_state()` + `_rebuild_scene()`
3. Click "⚙ Auto-nest"
4. `_AutoNestWorker` en QThreadPool (no bloquea UI)
5. Progress: boton muestra "■ Stop XX%", live_result cada 250ms
6. `_apply_nest_result()` → crea PlacedPiece para cada resultado
7. `_rebuild_scene()` → `fit_scene()` → viewport ajusta al contenido

### Colocar pieza manual (Tab Nesting)

1. Click en pieza del sidebar izquierdo → `_select_piece(pi)` → floating=True
2. Mover raton sobre canvas → `FloatPreviewItem` sigue cursor
3. Snap automatico si esta cerca de borde existente
4. Click en barra → `_place_floating_piece()` → crea PlacedPiece
5. `_rebuild_scene()` → actualiza canvas + sidebars

---

## 12. Dialogs

| Dialog | Tamano | Proposito |
|--------|--------|-----------|
| `about_dialog` | 400×300 | Version, update check, links |
| `material_picker_dialog` | 420×360 | Buscar/seleccionar material de DB |
| `stock_add_dialog` | — | Formulario agregar barra al stock |
| `profile_creator` | 800×600 | Canvas editor de perfiles custom |
| `profile_manager` | — | Gestionar perfiles guardados |
| `profile_save_dialog` | — | Guardar perfil con metadatos |
| `materials_manager` | — | Gestionar base de datos materiales |
| `nesting_layout_dialog` | — | Configurar opciones de nesting layout |
| `pdf_template_editor` | — | Editar plantilla PDF |
| `add_bar_dialog` | — | Quick add bar |
| `retal_dialog` | — | Gestion de retales |

---

## 13. Funciones del CTk no portadas (pendientes de evaluar)

| Feature | Prioridad | Notas |
|---------|-----------|-------|
| Sidebar toggle buttons (◧/◨) | Baja | Collapse sidebars desde canvas edge |
| Zoom overlay (top-right) | Media | Muestra zoom %, modo zoom/scroll, centrar |
| Multi-select (Ctrl+click) | Media | Seleccion multiple con magenta highlight |
| Real proportions mode | Baja | Bar height dinamico segun seccion transversal |
| Scroll/zoom mode toggle | Baja | Alterna entre zoom-wheel y scroll-wheel |

---

## 14. Checklist de revision

- [x] Todos los labels usan `t(key)` con keys existentes (0 raw keys)
- [x] Todos los paintEvent usan `_th.*` para colores (no stale imports)
- [x] Cambiar dark↔light actualiza TODOS los widgets painted
- [x] NestingPreviewWidget renderiza barras tras Calculate
- [x] NestingScene muestra barras y piezas tras auto-nest
- [x] ProfileTile dibuja formas correctas para cada TipoPerfil
- [x] PillSwitch animacion funciona y muestra labels correctos
- [x] CorteRow: todos los campos visibles sin clipping (margins 6×2×6×2)
- [x] Tab switching preserva estado (contexts synced) — `_flush_main_tab`/`_refresh_main_tab` vuelcan y repueblan; verificado end-to-end (jobs incl. `active_tab`).
- [x] Keyboard shortcuts funcionan en Tab Nesting — acotados a `WidgetWithChildrenShortcut` (ya no fugan a otras tabs) + foco al canvas en `showEvent`; verificado con QTest.
- [x] TEXT_DIM legible en ambos temas (≥ 3:1 contrast)
- [x] Fonts bundled cargan correctamente (IBM Plex Sans, DejaVu) — añadidas `DejaVuSansMono(.ttf/-Bold)` al bundle y al registro; antes el mono usado por F_NUM/F_NUM_SM/F_BADGE dependía de la fuente del sistema (rompía en builds limpios de Windows).
- [x] 46 engine tests pasan (`python -m pytest tests/ -q`)
- [x] QT_QPA_PLATFORM=offscreen import OK
- [x] Sin colores hardcoded en setStyleSheet (usar tokens de theme_qt)
- [x] Campos de tab_perfiles h=30 (no 26)
- [x] Pieza completa usa SUCCESS_BG (no #143314)
- [x] Bar header usa BG_MID (no #2A2A2E)
- [x] Gap line en preview usa BG_HOVER (no #2A2A2E)
- [x] Sidebar header margins alineados: 8×6×8×6
- [x] Filter buttons con color TEXT_SEC
