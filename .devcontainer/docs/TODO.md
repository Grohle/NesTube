# Nestify — Plan de Desarrollo y Roadmap

Este documento es la fuente de verdad del proyecto. Cada ítem va marcado
con la fase en que debe estar resuelto **antes** del initial release, y con
`[LEGACY]` cuando es parte de la limpieza posterior.

---

## ⚠️ Invariante del motor (LEER ANTES DE TOCAR NADA)

```
El motor de nesting es INTOCABLE salvo que el bug nazca ahí dentro:
  • nestify/nesting_engine.py, nestify/logic.py, nestify/bevel_geom.py
  • Los 46 tests deben pasar SIEMPRE: python -m pytest tests/ -q
  • use_bevel=OFF → 1D largo nominal (solo kerf+margin).
  • use_bevel=ON  → contorno 2D SAT, nunca largo nominal.
  • Flush-fit (corte compartido): alpha_R + alpha_L ≈ 0 (signos opuestos).
  • El margen es un "kerf extra": se suma al gap inter-pieza, NO se resta
    de los extremos de la barra.
```

---

## 0. Sistema de nombres (afecta a TODO)

> Antes de tocar cualquier otro ítem, definir y aplicar el nuevo convenio
> de nomenclatura a toda la app (tabs, diálogos, modelos, base de datos,
> exportaciones, ventanas extra, autocompletado).

- [x] **Nombre de perfil/tubo** — campo `profile_name` (p.ej. `U60x60x2`)
- [x] **Material** — campo `material` (p.ej. `Acero`, `Aluminio`, `Inoxidable`). En `StockBar` se expone como alias `material` sobre el almacenamiento `material_desc` (sin renombrar columna SQLite, para no romper la migración reciente).
- [x] **Calidad** — campo `quality` (p.ej. `S355J2`, `6061-T6`)
- [x] **Representación completa** — helper canónico único `nestify/naming.py` (`format_full_name`, `format_material`) con separador ` · `. Todos los modelos lo usan: `Material.display`, `MaterialContext.display_name`, `StockBar.full_name`. `StockBar.display_name` se mantiene como código físico único de barra (`MATERIAL-NNNNNN-SS`).
- [~] Aplicar la representación completa en cada pestaña: ya consistente vía las propiedades de modelo (material picker, subtabs, autocompletado). Los puntos específicos de cada tab (Cuts search, columnas de Stock, Job Explorer, PDF exportado) se conectan al canónico dentro de su fase correspondiente.
- [ ] (Opcional, fase futura) Renombrar la columna SQLite `material_desc` → `material` con migración; por ahora resuelto mediante alias de propiedad.

---

## 1. Menú File

- [x] **Eliminar** entradas `Export Excel`, `Export PDF`, `Import Excel` y `Template` del menú File. Estas acciones se ubican ahora en las pestañas correspondientes.
- [x] Mantener: `Open`, `Save`, `Save As`, `Save program configuration`, `Load program configuration`, `Backups`, `Exit`.

---

## 2. Pestaña Cuts

### 2.1 Acciones de importación/exportación

- [x] **Botón "Download XLSX Template"** — a la izquierda del selector de tipo de optimización. Descarga la plantilla de Excel con columnas: Name, Length (mm), Qty, Bevel 1, Bevel 2, Direction 1, Direction 2, Angles.
- [x] **Botón "Import XLSX Cut List"** — junto al anterior, a la izquierda del selector. Abre explorador de archivos y carga lista de cortes desde xlsx.
- [x] **Botón "Export PDF"** — exporta la lista de cortes y resultados de bin packing a PDF (usa de momento el flujo multi-material existente; el selector de nestings de §10 lo refinará).
- [x] Verificado E2E con librerías reales: plantilla XLSX (`save_template`, 9 columnas), import XLSX (`import_cuts_from_excel`, round-trip OK), PDF de nesting (`_write_pdf`) y PDF de presupuesto (`_write_presupuesto_pdf`) → todos archivos válidos. Render a imagen confirmado. **Bug corregido**: la cabecera de la columna de longitud en el PDF/DOCX de presupuesto y en el Excel de costes mostraba el literal `{u}` (faltaba el kwarg `u=units.u_len()` en `t("placeholder_length")`/`t("bar_length")`); corregido en `export_utils.py`. Regresión en `tests/test_export_headers.py`.

### 2.2 Selector de material (reemplaza el buscador actual)

- [x] **Quitar** el widget de búsqueda de material actual desde Cuts (`MaterialAutocomplete` reemplazado por `StockMaterialSearchBar`).
- [x] **Añadir barra de búsqueda de stock/material ficticio** en su lugar:
  - Campo de texto: al escribir, despliega lista de sugerencias en tiempo real (stock + materiales de la DB).
  - Seleccionar sugerencia → selecciona directamente; lupa o Enter → abre la ventana de búsqueda ampliada (§2.3) pre-filtrada por el texto.
  - Si ya hay un material seleccionado, muestra `{profile_name} · {material} · {quality}` en el campo.
- [x] La ventana de búsqueda (§2.3) permite seleccionar tanto barras de stock existentes como materiales ficticios de la base de datos.
- [x] La selección queda propagada al estado compartido (`AppState` + `MaterialContext`): material/calidad/perfil y, para barras de stock, prefill completo de costes/peso y largo de barra (`state.perfil`). El reflejo visual concreto en las pestañas Nesting/Costs se completa en §3.4/§4.

### 2.3 Ventana de búsqueda de stock/material

- [x] Ventana modal con dos modos (botones toggle): **Material ficticio** (BD, por defecto) / **Stock** (barras reales); modo activo resaltado en acento.
- [x] Panel de filtros: texto libre (busca en perfil/material/calidad) + longitud mínima (solo en modo stock). _Filtros adicionales por dropdown (tipo perfil/material/calidad) quedan como mejora futura._
- [x] Lista de resultados: nombre completo canónico; en modo stock añade largo efectivo + cantidad.
- [x] Búsqueda en tiempo real (debounce) tanto en la barra de Cuts (completer) como en la ventana modal.
- [x] Al confirmar la selección, `AppState`/`MaterialContext` se actualizan (display visual completo en Nesting/Costs en §3.4/§4).

---

## 3. Pestaña Nesting

### 3.1 Botón Export (reemplaza icono imagen)

- [x] Sustituir el botón con símbolo de imagen por un botón etiquetado **"Export"** con menú desplegable:
  - **Export PDF** — genera informe de nesting (ver §3.2)
  - **Export DXF** — genera archivo con piezas encajadas (ver §3.3)
  - **Export PNG** — captura de la escena (flujo previo conservado).
- [x] Al activar cualquier opción, mostrar primero el selector de nestings (ver §10). Implementado `NestingSelectorDialog`.

### 3.2 Export PDF de nesting

Estructura del PDF por nesting seleccionado:

1. **Cabecera** — campos del job: nombre, fecha, operario, referencia, observaciones.
2. **Por cada barra** — dibujo de la barra con las piezas encajadas en su posición y orientación exactas, debajo la leyenda con swatch de color + descripción de cada pieza presente en esa barra.
3. **Tabla de piezas** al final — columnas: nombre, perfil, longitud, cantidad, y una celda con un dibujo en miniatura de la silueta de la pieza (escala uniforme).
4. Paginación automática. Fuente configurable (existente en PDF Configuration).
- [x] Implementado `nestify/nesting_pdf.py` (`export_nesting_pdf`): cabecera con campos del job + fecha, una barra por bloque con piezas coloreadas en su posición/orientación, leyenda por barra (swatch + descripción + cantidad), y tabla de piezas final con miniatura de silueta a escala uniforme. Paginación automática y fuente del PDF Config reutilizada.
- [x] Verificado que el PDF se genera correctamente (prueba E2E con datos sintéticos, renderizado a imagen).
- [x] El botón **Imprimir** — "Imprimir…" en el menú Export. Genera PDF temporal y lo envía al sistema de impresión del OS (os.startfile/lpr/lp). Temp file auto-cleanup 5 s. Implementado en `_print_nesting()`.

### 3.3 Export DXF de nesting

- [x] Implementado `nestify/nesting_dxf.py` (`export_nesting_dxf`): genera un DXF con todas las piezas en sus coordenadas exactas (x_offset + geometría local con kerf/margen ya embebidos en los polígonos de colocación).
- [x] Cada pieza representada como polilínea cerrada (LWPOLYLINE, contorno 2D).
- [x] Cada barra como capa DXF separada (`BAR_1`, `BAR_2`, …) + capa `BAR_OUTLINE` con el rectángulo de barra.
- [x] Verificado con `ezdxf.readfile` que el archivo es válido y contiene las polilíneas/capas esperadas (pendiente verificación en un visor CAD gráfico).

### 3.4 Sincronización de material

- [x] Si hay un material seleccionado en Cuts (stock o ficticio), Nesting lo hereda automáticamente al abrir la pestaña (compartido vía `MaterialContext`; `_load_from_context` lo refleja al cambiar de tab).
- [x] **Botón "Use Stock"** — toggle pill conectado a `StockMaterialSearchDialog`(stock mode). Muestra el bar seleccionado en un chip al lado; click en el chip desvincula. Estado persiste en `MaterialContext.use_stock` + `linked_stock_bar_id` + `linked_stock_bar_name`.
- [x] **Auto Nest sin material seleccionado** — si no hay perfil ni stock asignado al iniciar Auto Nest, se muestra diálogo con `Seleccionar material` / `Continuar sin material` / `Cancelar`.
- [~] Solo el stock seleccionado **desde la pestaña Nesting** (mediante "Use Stock") tiene impacto sobre el inventario real. La vinculación se persiste; el decremento efectivo de stock se realizará en §3.5.

### 3.5 Impacto sobre stock al guardar

- [x] Al **guardar un nesting** (`Ctrl+S` o menú), decrementar en stock las barras consumidas: `_deduct_stock_bars()` compara `nesting_bars_deducted` (persistido en `MaterialContext`) con el número actual de barras activas y llama a `deduct_bar(bar_id, used_length)` por cada barra nueva. `_bar_used_length(i)` = `max(pp.x_offset + pp.corte.largo) + margin`.
- [x] Al **borrar un nesting y guardar**, liberar las barras que estaban vinculadas: cuando `n_now < n_prev`, `_deduct_stock_bars()` llama a `restore_bar(bar_id, n_prev - n_now)` (nueva función en `stock_db.py` que incrementa `quantity`). `nesting_bars_deducted` se actualiza a `n_now`.
- [x] Al **salir de la pestaña Nesting** por cualquier causa (cambio de tab, cierre de app), si hay cambios sin guardar, mostrar diálogo: `_nesting_dirty` flag en `TabNesting` (puesto en `_push_undo`, borrado en `_save_nesting`/`_load_from_context`); diálogo Save/Discard/Cancel en `_on_main_tab_changed` en app.py con Cancel restaurando el tab activo sin re-disparar la señal.
- [x] `Ctrl+S` guarda simultáneamente el nesting activo y el job. `TabNesting.save_requested` emite señal que la app conecta a `_guardar()`; shortcut Ctrl+H ahora para flip horizontal.

### 3.6 Nesting Layout (reordenar barras en el panel)

> El reordenamiento de barras no existía en la versión Qt (el legacy tenía un
> "drag-to-dock" que se eliminó). Implementado de cero como **botones ▲/▼ en la
> cabecera de cada barra del panel derecho** (`_move_bar`/`_swap_bars` en
> `tab_nesting.py`), una operación puramente visual. Botones extremos
> deshabilitados; reordenamiento deshacible (Ctrl+Z) y marcado como dirty.
> Glifos con contraste WCAG sobre cabecera de acento. Verificado en dark/light.
> Regresión en `tests/test_nesting_reorder.py`.

- [x] **Corrección de cambio de lado**: al mover una barra solo se intercambian las entradas de barra completas; cada pieza conserva su `x_offset`, flips (`flipped_h/v`), polígono y contenido. Solo se re-sella `bar_index` al nuevo slot. La barra nunca cambia de lado ni de orientación.
- [x] **Sin apilamiento**: el reordenamiento intercambia slots; cada barra sigue siendo una entrada independiente de la lista (nunca se fusionan ni se solapan). Verificado con test.
- [x] Al reordenar barras en el panel no se modifica ningún dato de nesting: longitudes de barra y `_bar_stock_ids` se mueven junto con su barra; posiciones de piezas y vínculos de stock intactos.

---

## 4. Pestaña Costs & Weight

- [x] **Eliminar campo €/m²** — quitado del formulario (.ui recompilado) y de todas las referencias; `precio_m2=0.0` en `_build_config` (el motor `logic.py` queda intacto y el término se anula). Campo del modelo conservado por compatibilidad con datos guardados.
- [x] **Añadir tab "Nesting 1"** (y siguientes) sincronizada: `sync_subtabs_bar` reconstruye la barra de subtabs de Costs desde los contextos compartidos (mismos nombres/orden + índice activo), y se llama al entrar a la pestaña Costs. Si estás en Nesting 1, al cambiar a Costs aparece Nesting 1.
- [~] Sincronización Nesting↔Costs: el índice/nombres y el contexto activo ya se reflejan al cambiar de pestaña. La sincronización *bidireccional en vivo* de material/perfil se afina junto con §3.4.
- [x] Si ya hay material/perfil en el estado compartido, Costs lo muestra (vía `_apply_context_to_ui` con el contexto activo).

---

## 5. Creación y edición de perfiles

### 5.1 Campos del formulario (profile_save_dialog.py / profile_creator.py)

- [x] **Profile/Tube Name** — campo `e_name` ya existe. Autocompletado implementado en `_setup_name_completer()`: `QCompleter` sobre `QStringListModel` con los nombres de `custom_profiles`, case-insensitive, modo `MatchContains`.
- [x] **Material** — combo con Acero/Aluminio/Inoxidable base + materiales del DB. Al seleccionar, muestra el Specific Weight automáticamente.
- [x] **Quality** — campo de texto libre ya existente.
- [x] Material y specific_weight se guardan en `CustomProfileEntry.meta`.

### 5.2 Cálculo automático de campos

- [~] **kg/m** — requiere geometría 2D del perfil; pendiente para cuando el perfil tenga área de sección definida.
- [x] **€/kg** — si se conocen €/m y kg/m, se calcula €/kg automáticamente (editingFinished en StockAddDialog).
- [x] **€/m** — si se conocen €/kg y kg/m, se calcula €/m automáticamente.
- [x] **Precio por barra** — se calcula como €/m × longitud_m cuando se conocen ambos.
- [x] Los campos calculados se actualizan al salir del campo fuente (editingFinished).

### 5.3 Longitud de barra en Stock

- [x] Campo `length` ya existe en StockAddDialog (dimensiones card, default 6000 mm).
- [x] Se usa para calcular precio por barra automáticamente.
- [x] Bar Length como campo obligatorio al añadir nuevo stock: `_confirm()` valida que `length > 0` antes de guardar; muestra `stock_length_required` y enfoca el campo.

---

## 6. Settings — Manage Materials

- [x] Simplificado `MaterialsManagerDialog` a tres campos: Material name, Quality, Specific Weight (t/m³).
- [x] Campo `category` eliminado de la UI (se mantiene en el modelo por compatibilidad de datos).
- [x] Acciones crear/editar/borrar funcionando con `specific_weight`.
- [x] Los materiales del DB aparecen en el combo de material del ProfileSaveDialog (§5.1).
- [x] **Materiales base traducidos por idioma** (Acero/Aluminio/Inoxidable → Steel/Aluminium/Stainless steel, etc.). Helpers `localize_material`/`canonical_material` + `BASE_MATERIALS` en `naming.py`; claves i18n `material_acero/aluminio/inoxidable` (es/en + fr/de/zh por ahora). Los combos de material base (`profile_save_dialog`, `profile_manager`) **muestran** la etiqueta localizada pero **almacenan el nombre canónico** (español) para que jobs/stock existentes sigan coincidiendo entre idiomas; los materiales personalizados pasan intactos. Tests en `tests/test_material_i18n.py`. _Pendiente (post, opcional): aplicar la localización de display también en el buscador/autocompletado de Cuts y en columnas de Stock._

---

## 7. Settings — Edit Templates

- [x] Añadir entrada `Edit Templates` en el menú Settings (bajo "PDF Config").
- [x] Al abrir, mostrar ventana con **pestañas por tipo de template**: `EditTemplatesDialog` en `pdf_template_editor.py` con `QTabWidget` — tab "Nesting PDF" (`pdf_fastreport_path`) + tab "Cuts / Quote PDF" (`pdf_cuts_fastreport_path`); ampliable añadiendo tabs.
- [x] Cada tab muestra un **editor de plantilla propio** (`PdfTemplatePane`) dentro de la app: previsualización del layout, campos arrastrables.
- [x] Botón **"Open in FastReport"** en cada tab: abre el `.frx` en el designer asociado al SO (`os.startfile` / `xdg-open`).
- [x] Si FastReport no está instalado, ofrecer instalarlo directamente desde la app: al fallar la apertura muestra `QMessageBox` con botón **"Download FastReport"** que abre `QDesktopServices.openUrl` al enlace oficial.
- [x] Botón **"Browse…"** (Import FastReport Template) en cada tab: `QFileDialog` para importar `.frx`/`.fr3` y persiste la ruta por clave de preferencia.
- [x] **README**: sección "FastReport integration" añadida con pasos de configuración, enlace de descarga y nota de que FastReport es opcional.

---

## 8. Name Assignment

- [x] **Una sola ventana** para toda la asignación de nombres (`NamingDialog` en `dialogs/naming_dialog.py`).
- [x] Organizar por **tabs dentro de la ventana**: tab Jobs con prefijos de job y retal. (Ampliar con más tabs si se añaden más prefijos.)
- [x] Botón **Save** único que guarda todos los cambios.
- [x] Única entrada en Settings → Name Assignment; no hay otras entradas dispersas de esta función.

---

## 9. Menú View — UI Font

- [x] **Eliminar la opción "UI Font Family"** del menú View.
- [x] La app Qt usa IBM Plex Sans como fuente principal; DejaVu Sans (no-mono) no aparece en ningún stylesheet ni QFont del código Qt. DejaVu Sans **Mono** se usa intencionalmente para inputs numéricos y etiquetas de medida (bundled en assets/fonts).

---

## 10. Selector de exportación (todos los formatos)

- [x] Antes de cualquier exportación (PDF nesting, DXF), mostrar `NestingSelectorDialog`: lista de nestings activos con checkbox por cada uno, opción "Seleccionar todos", botones `Exportar seleccionados` / `Cancelar`. Implementado en `dialogs/nesting_selector_dialog.py`.
- [x] El diálogo aplica a Export PDF (nesting) y Export DXF. PDF de cortes: `app.py._exportar_pdf` actualizado — muestra `NestingSelectorDialog` si hay varios contextos con datos, luego diálogo Qt de fichero, llama `exportar_pdf(filename=path)`. Excel de presupuesto: `tab_perfiles._export_excel` usa diálogo Qt de fichero + `exportar_excel(filename=path)`.
- [x] **Botón Imprimir** — "Imprimir…" en el menú Export. Muestra el selector de nestings, genera PDF temporal y lo envía al sistema de impresión del OS (os.startfile/lpr/lp). Temp file auto-cleanup 5 s.

---

## 11. Job Explorer

- [x] Mostrar por job: stock utilizado (barras, material, cantidad): implementado como sección "Stock consumido" en el panel de detalle del Job Explorer (lee `nesting_bars_deducted` + `linked_stock_bar_name` del `state_json`). Retales generados: implementado en `_populate_retal_info(job_name)` usando `get_bars_by_creation_job()` de `stock_db.py`; muestra sección "Retales generados" con perfil y longitud de cada retal.
- [x] En la pestaña **Stock**, añadir:
  - [x] Columna **"Creation Job"** — nombre del job donde se creó esa barra. Guardado en `StockBar.creation_job_name` (pasado desde `add_bar`/`add_retal`/`deduct_bar` via parámetro `job_name`). `_deduct_stock_bars()` pasa `job_name=self._state.descripcion`. Columna visible en la tabla con ancho 130px.
  - [x] Columna **"Used In Jobs"** — lista compacta (coma-separada) de jobs donde se ha consumido esta barra. Guardado en `StockBar.used_in_job_names` (lista de strings). `deduct_bar()` añade el nombre si no está ya en la lista. Tooltip con lista completa si hay múltiples.
  - [x] Pendiente: comportamiento clickable (abrir Job Explorer con el job seleccionado / filtrado). Implementado: `TabStock.open_job_requested(str)` signal; `_on_cell_clicked` la emite al hacer clic en cols 8-9 (solo si hay texto); `app._navigate_to_job()` cambia de tab y llama `TabJobsExplorer.select_job_by_name()`. Las celdas con contenido se muestran en ACCENT como vínculo; tooltip indica la acción.
- [x] Asegurar que borrar el filtro en Job Explorer devuelve la vista completa sin perder el estado anterior. Ya implementado: `_clear_search()` llama `_render_job_list(self._jobs)` que recrea los tiles con `selected=(job["id"] == self._selected_job_id)`, preservando la selección y el panel de detalle.

---

## 12. Menú Help

- [x] **Eliminar entrada "Donate"** del menú Help — ya está en la ventana About.
- [x] Mantener: `GitHub Issues` (o equivalente de soporte). Implementado: `help_menu.addAction(t("github_issues"), self._open_github)`.

---

## 13. Ventana About

- [x] **Mostrar al iniciar la aplicación** (una vez por sesión). Checkbox "No mostrar de nuevo" persiste en `prefs.show_about_on_startup`. Implementado en `app.py._show_about_startup()`.
- [x] **Botón PayPal** — estilo `#003087`/`#009cde` hover, `setFixedHeight(32)`. Oculto si URL vacía.
- [x] **Botón BuyMeACoffee** — estilo `#FFDD00`, texto negro, `setFixedHeight(32)`. Mismo tamaño que PayPal. Oculto si URL vacía.
- [ ] ⚠️ **AVISO PRE-RELEASE**: Antes del initial release, insertar las URLs reales de PayPal y BuyMeACoffee del propietario del proyecto. Actualmente son placeholders.

---

## 14. Documentación y limpieza general

- [ ] **Comentado exhaustivo de UI** — documentar los widgets clave de cada tab para facilitar futuras modificaciones de layout.
- [~] **Reducción de deuda técnica visual** — corregir elementos solapados, cortados o con alturas inconsistentes. Resolver visibilidad en modo light del diálogo "Add Profile": botones de herramienta y ortho en `profile_creator.py` usaban `color: white` hardcodeado sobre `ACCENT`; en light mode el ratio era ~2.2:1 (fallo WCAG). Sustituido por `_text_color_for_bg(_th.ACCENT)`. Igual para la etiqueta de dimensión sobre el canvas. Corregido WCAG en `theme_qt.py`: `_contrast_color(bg_hex)` añadida; `QPushButton[variant="accent"]`, icon hover, selection colors en QLineEdit/QComboBox/QMenu/QTableWidget ahora usan color de texto calculado en lugar de `#FFFFFF` hardcodeado. Revisión a anchos estrechos (1000–1100px) de las 6 pestañas: el único recorte real era la barra de herramientas densa de Cuts/Nesting → resuelto (§21.6, scroll horizontal). Costs/Stock/Profiles/Jobs sin recortes ni solapes en la revisión.
- [x] **Sustitución de emojis** — los emojis de color (🔍 🖨 💾 🗑 🖼), que en Linux/Windows sin fuente de emoji salen como tofu/colores inconsistentes, ya están migrados a SVG monocromos temáticos en `assets/icons/` vía `icons.py` (`themed_icon()`), usados en Stock (búsqueda), Costs (imprimir), Nesting (save/clear) y el material picker. Las ocurrencias restantes de 🔍/🖨 son solo comentarios. El resto de glifos del UI (─ → ↺ ↻ ⇕ ⇄ ▲ ▼ ▾ ▸ ■ ⚙ …) son símbolos monocromos que renderizan con las fuentes incluidas (IBM Plex / DejaVu); la flecha del combobox se dibuja con bordes CSS (sin glifo). Verificado.
- [x] **README Global (EN + ES)** — README bilíngüe: sección English + sección Español con índices separados; enlace a `docs/USER_GUIDE.md` (EN) y `docs/GUIA_USUARIO.md` (ES, creada); características, instalación, privacidad e idiomas en ambas lenguas. Capturas actualizadas con modo oscuro.
- [x] **Actualizar capturas de pantalla** (`docs/img/`) — regeneradas con el script offscreen (5 tabs × modo oscuro) tras los cambios de UI de §21.6–21.8.

---

## 15. Datos, idioma y divisa

- [x] **Migración a SQLite** — completada: config (`app_config`→`app_meta`), jobs, stock (`stock_db`), materiales (`materials_db`) y perfiles residen en `nestify_geometry.db`; los antiguos `*.json` solo sirven de migración única (se renombran a `*.migrated`). Además, la **ubicación de la BD es configurable** (módulo bootstrap `db_settings.py`, fuera de la propia BD por el problema del huevo-y-la-gallina): la BD puede vivir en una ruta de servidor compartido y conmutarse. Nuevo **File → Database management** (`database_management_dialog.py`): ruta de la BD (Cambiar ubicación / Cargar base de datos), carpeta de copias, frecuencia de copia (cada arranque / diaria / semanal / desactivada), "Crear copia ahora", última copia y "Gestionar copias…". `backup.py` respeta la frecuencia y la carpeta configuradas. Cambiar/cargar BD pide reinicio (recarga limpia de cachés). Tests en `tests/test_db_settings.py` y `tests/test_backup.py` (round-trip, gate por intervalo, retención).
- [x] **Sistema de Backups** — implementado y verificado: `nestify/backup.py` toma un snapshot consistente del SQLite (API online de sqlite3, incluye WAL) en cada arranque (`main.py` → `create_backup("startup")`) con retención rodante (15). Diálogo `Settings/File → Backups` (`backup_dialog.py`): "Crear copia ahora", lista de copias, "Restaurar seleccionada" y "Restaurar desde archivo…"; `restore_backup` guarda una copia de seguridad `*.pre_restore` antes de sobrescribir. Round-trip create/list/restore + retención cubiertos en `tests/test_backup.py`.
- [ ] **Sincronización en tiempo real** — cambios de idioma y divisa sin reinicios de sesión.
- [x] **Reducir idiomas a Español e Inglés** — eliminados los bloques `fr`/`zh`/`de` de `i18n.py` y de todos los dicts suplementarios; `available_languages()` devuelve solo `["es", "en"]`. El selector de idioma en el menú View refleja automáticamente el cambio. Tests `test_material_i18n.py` actualizados para los 2 idiomas soportados. 157 tests pasan.

---

## 16. Optimización y motor de nesting

- [x] Respetar estrictamente los tiempos y tipos de optimización seleccionados. Verificado: `NestingParams.priority` se toma de `strategy_combo.currentData()`; `time_limit` se toma de `app_config.get_opt_time_limits()` indexado por `opt_combo.currentIndex()+1` y se pasa a `nest_advanced_timed`. El flujo completo ya estaba implementado.
- [x] Corregir nomenclatura en el desplegable de Symmetry: renombrado a "Simetría (emparejamiento)" / "Symmetry (pairing)" para describir el comportamiento real del motor (empareja piezas simétricas/complementarias).
- [x] Selector "Only Remaining vs Nest All" implementado: `_auto_mode_combo` junto al botón Auto-Nest (modo "Todo" recalcula todo; "Solo pendientes" conserva piezas colocadas y añade pendientes en barras nuevas).
- [x] Persistencia de piezas colocadas manualmente durante el modo Only Remaining. Bug encontrado y corregido: al cambiar de subtab de material (Nesting 1↔Nesting 2) sin pulsar Ctrl+S, las piezas colocadas a mano se perdían. `_on_before_subtab` no volcaba `_bars`→`state.nesting_layout` antes de `save_state_to_context` (faltaba `sync_to_state()`), y `_load_from_context` no cargaba `ctx.nesting_layout`→`state` antes de `_restore_from_state` (mostraba el layout del contexto anterior). Además `_restore_from_state` no restauraba `_bar_lengths`. Corregidos los tres; cada contexto ahora conserva su layout, longitudes de barra y orientación de forma aislada. Verificado en modo Only Remaining (1D y 2D) y en round-trip save/load. Regresión cubierta en `tests/test_nesting_persistence.py`.
- [x] `isDirty` flag: validar cambios pendientes antes de Calculate, cambiar de pestaña o cerrar la app. Cubierto: `closeEvent` emite warning al cerrar (Save/Discard/Cancel); `_on_main_tab_changed` emite warning al salir de la pestaña Nesting (§3.5). Warning al Calculate si hay piezas colocadas (modo 'Todo'): `_run_auto_nest()` comprueba `any(self._bars)` antes de continuar y muestra `auto_nest_clear_title/msg`.
- [x] Slider "Auto" al lado de "use stock" (manual/automático), por defecto OFF. En modo manual, Auto-Nest sin barras pide añadirlas. "Add bar" con "use stock" abre `StockBarPickerDialog`: listado de barras en stock con detalles + dibujo a escala de la barra seleccionada (útil para retales, muestra % útil). Doble clic o "Select" añade **una** barra. La ventana **muestra solo el material que se está anidando** si ya hay uno seleccionado (filtra por profile · material · quality); si no hay ninguno, al elegir una barra se **fija ese material en toda la app** (contexto + estado compartido, prefill de costes/peso, renombrado del subtab) vía `_adopt_material_from_bar`. Tests en `tests/test_stock_bar_picker.py`.

---

## 17. Estabilidad y UX

- [x] **Job Explorer** — habilitar edición directa de parámetros desde la tabla. Ya implementado: `editingFinished.connect(self._save_detail_meta)` en campos nombre, cliente, oferta, pedido, descripción. También añadida sección "Stock consumido" (§11 parcial): muestra barras de stock usadas por nesting con `nesting_bars_deducted > 0`.
- [x] **Verificar exportaciones**: verificado E2E con librerías reales (fpdf2, openpyxl, pandas, python-docx, ezdxf): XLSX plantilla + import + Excel de stock, PDF nesting + PDF/multi nesting + PDF presupuesto, DOCX presupuesto y DXF nesting → todos producen archivos válidos (validados re-parseando con openpyxl/python-docx/ezdxf y renderizando PDF a imagen). Corregido el bug de cabecera `{u}` sin sustituir (ver §2.1). Regresión en `tests/test_export_headers.py`.
- [x] **Revisión crítica de costes** *(prioridad alta)* — verificado: parámetros (€/kg, €/m, kg/m, peso_especifico, tiempo_corte, inglete, coste_operario) se pasan correctamente desde tab_perfiles.py a logic.py sin pérdida. Fórmula de peso: `kg = largo(mm) × area(mm²) × peso_especifico(t/m³) / 1,000,000` es dimensionalmente correcta (7.85 t/m³ acero → 0.785 kg para 100mm²×1000mm ✓). Margen de beneficio y distribución de retales OK. Sin errores de unidades ni de lógica encontrados.

---

## 19. Eliminación del Legacy (después del initial release)

> La rama `legacy` se conserva como archivo histórico; no se toca ni borra.

- [x] Auditoría de código legacy — identificar módulos exclusivos de Tkinter/CTk.
- [x] Verificar paridad completa — confirmar que cada funcionalidad legacy tiene su contraparte Qt.
- [x] Eliminar `nestify/ui/`, `nestify/ui_tk/` y módulos CTk residuales. Eliminados: `nestify/ui/` (26 ficheros), `nestify/theme.py`, `nestify/scroll_util.py`, `nestify/profile_draw.py`, `nestify/canvas_ui.py`, `nestify/config_manager.py`, `main_ctk.py`.
- [x] Limpiar `requirements.txt`, `pyproject.toml` y `setup.py` de referencias a `customtkinter`/`tkinter`. `requirements.txt` ya no tenía customtkinter; `export_utils.py` migrado: funciones ahora aceptan `filename` param y el caller Qt provee el diálogo de fichero.
- [x] Actualizar `main.py` para que solo arranque `NestifyApp` (Qt). Ya lo hacía.
- [x] Pasar los 46 tests tras la limpieza. 157 tests pasan.

---

## 20. Catálogo de perfiles/tubos y pestaña "Materiales" (base de datos multimaterial)

> Origen: xlsx `Base_Datos_Multimaterial_Perfiles_Corregida` (hoja
> `Base_de_Datos_Maestra_IA`, 22 perfiles/tubos). Decisiones del propietario:
> thumbnails **paramétricos a escala**; los 4 materiales tal cual; el pricing
> **no cambia** (la pestaña Costes sigue calculando costes igual); todos los
> parámetros editables se agrupan bajo un botón **"Editar material"** que abre
> la ventana de edición de parámetros existente, sincronizada y coherente.

### 20.1 Esquema de parámetros del perfil/tubo

- [x] **Medidas** = etiquetas canónicas en toda la UI: `_tipo_dims` en `tab_perfiles.py` renombrado — REDONDO→`h`, RECTANGULAR/L/U/H→`h`,`b`,`tf`,`tw` en lugar de "Diámetro","Lado A","Ala","Alma",etc. Los campos internos de `PerfilDimensiones` en `models.py` no se renombran (logic.py los usa directamente y es intocable), pero el usuario solo ve las etiquetas canónicas. Catálogo (§20.4) y ProfileCreator ya usaban h/b/tw/tf en `meta` y `field_defaults`.
- [x] **Mantener** los campos existentes que NO cambian: `macizo` (hollow/solid), `extra_dims`, calidad, notas. Solo se renombran etiquetas.
- [x] **Eliminar** la columna `Familia` — no existe en el modelo actual (nunca se importó).
- [x] **`geometry_type`** — campo oculto al usuario en todo el código Qt; solo asocia el thumbnail. No aparece en ninguna vista de usuario.
- [x] **Pricing**: sin cambios de lógica. `seccion_cm2` y `peso_lineal_kg_m` siguen tomándose de `entry.meta` para perfiles de catálogo.

### 20.2 Materiales

- [x] Usar los **4 materiales tal cual** del xlsx como valores: `Acero al Carbono`, `Acero Galvanizado`, `Acero Inoxidable`, `Aluminio` (traducidos ES/EN/FR/DE/ZH vía i18n, almacenamiento canónico — ampliado `naming.BASE_MATERIALS` con `Acero al Carbono` y `Acero Galvanizado`; `Acero Inoxidable` es un alias de la `Inoxidable` ya existente — mismo material, sólo grafía distinta del xlsx — y `Aluminio` ya existía). 6 tests nuevos/actualizados en `tests/test_material_i18n.py`.

### 20.3 Thumbnails paramétricos

- [x] Renderizador **paramétrico a escala** por `geometry_type`: genera la sección 2D real a partir de `h/b/tw/tf` (+ `macizo`). Tipos: Viga I/H (doble T), Viga U / Perfil C (canal), Perfil Z, Angular (L), Cuadrado (tubo rect. hueco), Redondo (círculo o anillo), Pletina (rectángulo macizo), Ranurado (T-slot). Implementado en `nestify/profile_geometry.py` (`section_contours()` puro sin Qt + `render_section_pixmap()` rasterizador Qt), con tests en `tests/test_profile_geometry.py` (25 tests) y verificación visual offscreen en ambos temas.
- [x] Generar y guardar el thumbnail de cada perfil del catálogo al importarlo. Implementado en `profile_catalog._build_entry()` (renderiza con `render_section_pixmap()` y lo guarda junto al `CustomProfileEntry` vía `save_profile_file()`); cubierto por `tests/test_profile_catalog.py`.

### 20.4 Import del dataset

- [x] Importar los **22 perfiles/tubos** del xlsx a la base de datos (custom profiles / materiales), con nombre = `Designacion_Normalizada`, material, medidas, sección, peso lineal, `geometry_type` y thumbnail generado. Implementado en `nestify/profile_catalog.py` (`CATALOG_ROWS` con los 22 registros embebidos verbatim del xlsx + `ensure_catalog_profiles()` idempotente que crea cada `CustomProfileEntry` con su thumbnail paramétrico). 6 tests en `tests/test_profile_catalog.py`. Pendiente: invocar `ensure_catalog_profiles()` al arrancar la app (§20.5).

### 20.5 Pestaña "Materiales" (buscador + editor)

- [x] Nueva pestaña **"Materiales"** entre "Costs and Weight" y "Stock": buscador del catálogo de perfiles/tubos + crear/editar **reutilizando** las herramientas existentes (`ProfileCreator` / `ProfileManager`). Implementado en `nestify/ui_qt/tab_materiales.py`, conectado en `app.py` (`_build_tabs`, `_refresh_main_tab`, `_set_theme`). Vista **por defecto = lista de detalle** (`QTableWidget`: miniatura a la izquierda + columnas Nombre/Material/h/b/tw/tf/Sección/Peso lineal), con un toggle "Lista"/"Cuadrícula" para alternar a la vista de iconos anterior. `ProfileManager` aceptado un `initial_select_id` opcional para abrir ya seleccionado el perfil elegido en la pestaña. Verificado offscreen en ambos temas (capturas de ambas vistas, selección y detalle).
- [x] Botón **"Editar material"** que abre la ventana de edición de parámetros existente (`MaterialsManagerDialog`) con todos los parámetros, sincronizada y coherente con el resto de la app.
- [x] **No** anula las herramientas de Settings (crear/editar perfiles, gestionar materiales) — coexisten sin cambios (`_manage_materials`/`_open_profile_manager`/`_open_profile_creator` siguen intactos en el menú Settings).

---

## 21. Pulido post-catálogo: UX, geometría de ingletes y consistencia visual

> Origen: feedback del propietario (2026-06-16) tras probar la build con el
> catálogo §20 integrado. **Investigado a fondo** (no superficial): cada punto
> referencia el archivo/línea reales y la causa raíz. Reglas vigentes de
> `CLAUDE.md`: motor (`nesting_engine.py`/`logic.py`) intocable salvo que el
> bug nazca ahí; `_th.*` por atributo de módulo; verificación con capturas en
> ambos temas; los 114 tests deben seguir pasando.

### 21.1 Renombrar pestaña "Materiales" → "Profiles & Tubes" y separar "Materials"

- [x] Renombrar la pestaña `TabMateriales` a **"Profiles & Tubes"** (nueva clave i18n, p.ej. `tab_profiles_tubes`; ES "Perfiles y Tubos" / EN "Profiles & Tubes"). La palabra **"Materials"** pasa a referirse SOLO a `Settings > Materials` (`MaterialsManagerDialog`). Tab construida en `app.py:201-205` (`t("tab_materials")`).
- [x] Barra superior de la pestaña con **dos grupos visualmente separados**:
  - Grupo **Perfiles/Tubos**: botón **"Add profile/tube"** que abre el **módulo de dibujo** (`ProfileCreator`, vía `_open_profile_creator`) + "Edit" (ya existe) sobre la fila seleccionada.
  - Grupo **Materials** (separado, p.ej. tras un separador/spacer): **"Add material"** y/o **"Edit materials"** que abren `MaterialsManagerDialog` (mismo que `Settings > Materials`, `app.py:147`). Sustituye al actual botón único "Editar material" en `tab_materiales.py`.
- [x] Mantener `Settings > Materials` y `Settings > Profile types` intactos (coexisten con la pestaña).

### 21.2 Selector de perfiles de Costs incluye los del catálogo + "Editar material"

- [x] En `TabPerfiles` (`tab_perfiles.py`): el dropdown `profile_combo` (`_rebuild_profile_combo`, líneas 397-411) **ya añade** los `custom_profiles` por nombre, PERO al seleccionarlos `_select_profile` (413-433) deja `_tipo=None` (sólo resuelve builtins), así que `_rebuild_dim_fields` (445-454) sale temprano: **no se muestran parámetros y no se puede costear** un perfil del catálogo. Hay que soportar perfiles de catálogo en el selector (tiles + combo). → `_select_profile` resuelve `custom:<name>` a `CustomProfileEntry`, mapea `geometry_type`→`TipoPerfil` (`_GEOMETRY_TO_TIPO`).
- [x] Para perfiles del catálogo/BD, la **parte de abajo NO muestra campos de parámetros editables**; en su lugar un único botón **"Editar material"** (abre el editor consolidado). Los parámetros (`h/b/tw/tf/seccion_cm2/peso_lineal_kg_m`) salen de `entry.meta`. → `_show_catalog_panel` muestra resumen read-only + botón "Edit material" (abre `ProfileManager`); oculta wall-thickness/macizo.
- [x] **Pricing sin cambios de lógica**: alimentar el cálculo de coste/peso desde `meta` (`seccion_cm2`, `peso_lineal_kg_m`) reutilizando las rutas de cálculo actuales. NO tocar motor; verificar que coste/peso se calculan correctamente al seleccionar un perfil de catálogo. → `_build_config_from_catalog` alimenta `kg_por_m` desde `peso_lineal_kg_m`; verificado (IPE 100: 8.1 kg/m → 19.44 €/ud a 2 €/kg).

### 21.3 Bug de colisión de ingletes (bevel) en colocación manual y a veces auto-nesting

- [x] **Causa raíz**: `bevel_geom.corte_to_bevel` trataba `flipped_v` **negando los ángulos** (`a_l, a_r = -a_l, -a_r`) en vez de **reflejar** la pieza. El render y el auto-nesting usan el polígono del motor (`nesting_engine._flip_v`, **correcto**); la colisión manual usa `bevel_geom` (incorrecto). Resultado: para piezas con `flipped_v=True` el contorno de colisión divergía del dibujado (~`H·tan(α)` extra por extremo) → bloqueaba colocaciones válidas / solapaba mal. Verificado: pieza 1000mm 45°/45° → motor x∈[0,1000], bevel_geom antiguo x∈[−50,1050].
- [x] **Fix** en `bevel_geom.py` (módulo de soporte UI, NO el algoritmo protegido del motor): `BevelPiece` gana un flag `flipped_v` y `vertices_local` aplica una reflexión vertical real (x igual, y→H−y) que reproduce `_flip_v` del motor; `corte_to_bevel` ya no niega ángulos. Motor intacto. Probado contra el polígono del motor en las 4 orientaciones (`tests/test_bevel_geom.py`, 32 tests).
- [x] **Bug secundario**: `tab_nesting.py` llamaba `cycle_orientation(corte, fh, fv, direction)` (4 args) pero `bevel_geom.cycle_orientation` toma 3 → `TypeError` tragado por `except Exception: pass` → el ciclo de orientación Ctrl+Q/Ctrl+E **no hacía nada**. Corregida la aridad.
- [x] **Menor**: `_clamp_free_x` usaba `corte.largo` (nominal); ahora usa la extensión x real del bevel (`min_x_extent`/`max_x_extent`) para que piezas biseladas/volteadas queden enteras dentro de la barra.
- [x] Tests de geometría: `tests/test_bevel_geom.py` compara el contorno de colisión vs el polígono del motor en las 4 orientaciones + regresión del caso `flipped_v` (x dentro de [0,L]). 32 tests; suite completa 146 pasando.

### 21.4 "Manage profiles": miniaturas reales, recorte de campos y "default_value"

- [x] **"Cosa negra" + icono genérico**: `profile_manager.py:175-177` usa `themed_icon("image", _th.TEXT_PRI)` para TODAS las filas (en tema claro el glifo tintado se ve como cuadrado negro) y **nunca** carga el PNG real (`entry.image` en `PROFILES_DIR`) ni `render_section_pixmap`. El panel de detalle SÍ carga el PNG real (302-314) — replicar eso en la lista: mini-thumbnail real por perfil (fallback a `render_section_pixmap` desde `meta`).
- [x] **Cabecera "default_value" literal**: `profile_manager.py:261` hace `t("default_value")` pero **no existe esa clave** en `i18n.py` → `t()` devuelve la propia clave → la columna muestra el texto crudo "default_value". Añadir clave i18n real (ES "Valor por defecto" / EN "Default value") o literal.
- [x] **Celdas de valor vacías/erróneas**: `profile_manager.py:277-279` lee SOLO `entry.field_defaults` (keyed por etiqueta), vacío en perfiles creados con el `ProfileCreator` e ignora los valores canónicos de `entry.meta` (`h/b/tw/tf`). Mostrar el valor real (reconciliar `field_defaults` ↔ `meta`).
- [x] **Recorte bajo la fila "tf (mm)" / sin aire antes de "+ Edit fields"**: grid con `setSpacing(3)` y sin margen inferior (`profile_manager.py:268-284`), botón × a 26px vs line edits a 28px (332-354). Igualar alturas (28/30px), aumentar spacing y añadir margen/spacer antes de "+ Edit fields".

### 21.5 Módulo de dibujo (ProfileCreator): valores canónicos + edición completa

- [x] El botón **"Add new profile/tube"** abre el módulo de dibujo (`ProfileCreator`) — ya cableado en `Settings > Add new profile` (`app.py:153`) y como `on_add_profile` de la pestaña; asegurar el botón en la barra de "Profiles & Tubes" (§21.1).
- [x] **Adaptar el panel de valores de la derecha a los valores nuevos**: la hoja `self._meta` (`profile_creator.py:661-677`) usa claves `profile_name/material/quality/kg_por_m/precio_kg/precio_m/peso_especifico` — **faltan** `h/b/tw/tf/seccion_cm2/peso_lineal_kg_m` (y `geometry_type` oculto). Añadir inputs y emitirlos en `_save_profile` (línea ~1622) a `meta` y/o `field_defaults`.
- [x] **Editar un perfil por completo desde el módulo**: existe `ProfileManager._edit_drawing` (461-520, vía botón "✎ creator tools") que abre `ProfileCreator` pre-rellenado — pero los 22 del catálogo tienen `drawing_shapes:[]` → abren **lienzo en blanco**. Convertir la geometría paramétrica (`section_contours()` desde `meta`+`geometry_type`) a `ProfileShape`s editables. Exponer la opción de edición **al final de Manage profiles**.
- [x] **Reconciliar `field_defaults`**: ni `app.py:_open_profile_creator` (506-513) ni `_edit_drawing` (478-507) escriben `field_defaults` → perfiles creados muestran columna de valores vacía. Poblar `field_defaults` (y/o unificar fuente de verdad con `meta`) en el guardado.

### 21.6 Cuts: solapamientos, texto completo, mover métricas y centrar "Calculate"

- [x] **Mover métricas de la barra**: result_lbl movido junto a preview_hdr en QHBoxLayout.
- [x] **Texto completo de cada botón**: las barras de herramientas densas de Cuts (`controls_card`) y Nesting (`toolbar_frame`) se envuelven ahora en un `QScrollArea` horizontal (estira en ventana ancha, scrollea en estrecha) → ningún botón/etiqueta se recorta a 1000px (Calculate, Auto-nest, Advanced, Use stock, Common cut, combos…). Verificado con capturas a 1000px y 1400px en ambos anchos.
- [x] **Centrar "Calculate" en altura**: accent min-height corregido 34→30px.

### 21.7 Iconos SVG en botones + eliminar TODOS los emojis + flechas de desplegable

- [x] **Iconos SVG por botón**: gear, plus, pencil, x, undo, rotate-ccw/cw, check, chevron-down/up, arrow-up/down, circle, excel, pdf, export, cursor creados en `assets/icons/`.
- [x] **Ningún emoji en la UI**: eliminados en tab_cortes, tab_nesting, tab_stock, tab_perfiles, dialogs (profile_manager, profile_creator, stock_bar_picker, add_bar), i18n.py.
- [x] **Flecha de desplegable**: QComboBox::down-arrow/on usa SVG chevron temp-file generado por tema en build_stylesheet().

### 21.8 Consistencia global de tamaños de casillas y tipografía

- [x] **Igualar la altura de TODAS las casillas**: QPushButton 28→30, accent 34→30, danger/ghost 28→30, QSpinBox 28→30. setFixedHeight(28) corregidos a 30 en tab_materiales, tab_nesting (zoom_btn), profile_manager (search), material_subtabs, stock_bar_picker, change_values_dialog.
- [x] **Tipografía unificada en IBM Plex Sans**: el QSS global usa IBM Plex Sans en toda la app; los overrides restantes son intencionales (campos numéricos con DejaVu Sans Mono y filas compactas de diálogos). Sin tipografías inconsistentes detectadas en la revisión visual.
- [x] Verificado con capturas en ambos temas (Cuts y Nesting tabs).

---

## 22. Elegir anidado para costes

- [x] Los costes ahora no sabemos si se sacan con el anidado de cuts o de nesting. Para evitar errores, si no hay anidado en nesting para sacar los cálculos avisar, o si de desea, hacer el cálculo con el nesting rápido de cuts. → Implementado: etiqueta `_nesting_src_lbl` en la pestaña Costs; cuando el layout del Nesting cubre todas las piezas muestra "Basado en el anidado completado (pestaña Nesting)" en acento; en caso contrario "Cálculo rápido — sin anidado completado en Nesting" en texto secundario. Se actualiza en `_calcular()` y en `_apply_context_to_ui()` via `layout_covers_all_cuts(ctx)`. Claves i18n `costs_using_nesting` / `costs_using_quick_calc`.

---

## 23. Jobs Explorer

- [x] La pestaña de Job Explorer no filtra por Perfil o Tubo dentro de los filtros de búsqueda. → `_SEARCH_FIELD_MAP` amplíado con clave `"profile"` → `"profile_name"` y `"material"` → `"mat_name"`; `list_jobs_summary()` en `database.py` expone ambos via `json_extract(state_json, '$.material_contexts[0].profile_name')` y `json_extract(state_json, '$.material_contexts[0].material')`.
- [x] La Description de Job explorer, es, en realidad, el Profile/Tube + Quality + Material. → `_show_detail()` extrae `ctx0 = material_contexts[0]` y construye la etiqueta con `format_full_name(profile_name, material, quality)`; campo read-only; cabecera renombrada a `t("profile_tube_label")` ("Perfil/Tubo").
- [x] Debe tener una fecha de creación no editable el job, visible en job explorer. → `detail_date_lbl` muestra `t("created"): YYYY-MM-DD` desde `job["created_at"]`; es un `QLabel` (read-only por diseño).
- [x] El panel completo del job al clickarlo aparece fijado abajo, y ha de quedar fijado arriba con mousescroll si crece hacia debajo. → `detail_card` reordenado a posición 0 de `detail_outer_layout` (arriba); el espaciador expansible queda debajo; scroll natural de la columna derecha.
- [x] Al borrar un job, permanece su info en el panel derecho, esta info solo ha de ser visible con el job seleccionado. → `_delete_selected()` llama `_hide_detail()` inmediatamente tras confirmación antes de `refresh_list()`.
- [x] Añade justo encima de la barra de búsqueda un botón que sea "Create new job". → `_create_job_btn` (variante accent, alto 30px, icono plus) insertado en `list_panel_layout` en posición 1 (tras cabecera, antes de search_row); conectado a `_new_job`.

---

## 24. Costs

- [x] Todos los campos que se rellenen en costs en cada subtab han de ser guardados en el Job. → **Bug encontrado y corregido**: `_save_active_perfil` llamaba `_build_config(quiet=True)` y, si `self._tipo` era `None` (material ficticio o precios introducidos antes de elegir perfil), devolvía `None` y **descartaba en silencio TODOS los campos de coste/mano de obra** que el usuario había rellenado. Ahora, cuando no hay geometría de perfil resuelta, `_save_active_perfil` conserva las dimensiones existentes del contexto y persiste los campos de precio/peso/mano de obra leídos del formulario (`_read_cost_fields`) sobre `ctx.perfil`. Nuevo helper `_read_cost_fields()` reutilizado por `_build_config` para una única fuente de verdad. Cada subtab se vuelca al cambiar de subtab (`_on_before_subtab`) y al guardar el job (`_flush_main_tab(3)` → `_save_active_perfil`). Verificado headless: precio/kg, coste operario, tiempo de corte, inglete y margen persisten en `MaterialContext` sin perfil seleccionado.
- [x] Quiero un campo en Settings>Costs preferences> Abrir una ventana con todas las casillas de costes no específicas de un perfil con los campos que quedarán por defecto. → Nueva entrada **Settings → "Valores de coste por defecto"** (`_configure_cost_defaults`) que abre `CostDefaultsDialog` (`dialogs/cost_defaults_dialog.py`, mismo patrón que `OptimizationTimesDialog`). Edita los 4 parámetros de coste **no específicos de un perfil**: coste operario (/h), tiempo de corte recto (min), extra por inglete (%) y margen de beneficio (%). Persisten en `AppPreferences.default_operator_cost / default_cut_time / default_miter_pct / default_profit_margin` (con `to_dict`/`from_dict`). `app_config.apply_cost_defaults(perfil)` (duck-typed, sin import de models → sin circular) siembra estos valores en los contextos de cada job nuevo (`tab_jobs._new_job`). Los precios por material (€/kg, kg/m…) NO se tocan — vienen del perfil/material elegido. Claves i18n `cost_defaults` / `cost_defaults_hint` / `cost_defaults_saved` / `operator_cost_plain`. Verificado headless (round-trip de prefs + siembra) y capturas en ambos temas.

---

## 25. Nesting

- [x] El largo de las barras en nesting, tanto si viene de stock como sino, no afecta al anidado. No tiene en cuenta el largo del mismo. → **Dos bugs encontrados y corregidos** en `tab_nesting.py`: (1) el campo de la barra de herramientas `tb_bar_len` solo escribía `state.longitud_barra` en `editingFinished`, así que pulsar **Auto-nest** directamente (sin Enter/Tab) descartaba el valor recién tecleado; (2) `_run_auto_nest`/`_run_simple_nest` leían `_bar_len_for(0)`, que prioriza un `_bar_lengths[0]` **obsoleto** de un anidado anterior por encima del largo global, haciendo que el campo pareciera inerte. Nuevo helper `_auto_nest_bar_len()`: confirma primero el campo del toolbar (`_on_toolbar_params_changed`) y, en modo "all" (recálculo completo), devuelve el largo **global** de `state.longitud_barra` — que ya refleja el largo de la barra de stock vinculada cuando Use-Stock está activo (cubre "venga de stock o no"). En modo "remaining" las barras existentes conservan su largo. Verificado headless: con `_bar_lengths[0]=6000` obsoleto + 3000 tecleado sin commit → resuelve 3000; integración 1D: 4×1500 mm → 2 barras a 6000 mm vs 4 barras a 3000 mm.

---

## 26. Colocación manual con NFP (rotaciones, recolocación, simetrías sin espacios fantasma)

- [x] Solucionar por completo las rotaciones de las piezas y la recolocación manual (mismo sitio, otros sitios, rotando, simetrías) garantizando que NO se crean espacios fantasma, el bevel sigue funcionando y se usa el NFP — experiencia flawless. → **Reescritura completa del sistema de colisión/snap manual en `tab_nesting.py` para usar la geometría NFP EXACTA del motor** (la misma que el auto-nest, que ya funcionaba perfecto). Causa raíz: la colocación manual usaba un sistema propio (SAT + inflado de kerf por desplazamiento del punto medio + barrido `_slide_to_valid`) que **divergía** del motor: (a) inflaba solo la pieza móvil por kerf completo con un desplazamiento en X geométricamente incorrecto para caras inclinadas (bevel), dando `kerf·cosθ` de holgura perpendicular en vez de `kerf`; (b) la primera pieza caía en `margin` mientras el motor la pone en `kerf/2` → al recoger una pieza auto-anidada y soltarla aparecía un hueco. **Solución**: nuevos helpers `_engine_piece` (cachea el `NestingPiece` del motor: contorno real + virtual inflado kerf/2 por orientación), `_bar_free_intervals` (calcula, por vecino, el intervalo de X prohibido vía `_compute_nfp(virtual_vecino, virtual_móvil)` cortado en la base y=0 — captura el ACOPLE de bevels complementarios exactamente), `_x_allowed`/`_can_place` (membresía en intervalos libres con tolerancia `_COLLIDE_TOL_MM=0.25` que absorbe el margen de 0.1mm del propio bottom-left-fill del motor), `_rendered_snaps` (candidatos = bordes de cada intervalo libre, sin barrido por fuerza bruta), y `_clamp_free_x` (a los límites del virtual). **Recolocación exacta**: `_find_best_snap` inyecta la X original exacta de la pieza recogida (`_moving_original.x_offset`) como candidato preferido → vuelve a su sitio idéntico (drift 0.000000 mm). El contorno DIBUJADO/exportado (`_compute_poly_local`) queda intacto (el kerf solo vive en la colisión). Caché `_viable_cache` por (barra, orientación, kerf, alto, largo, huella de vecinos), limpiada en `_rebuild_scene` → el NFP de PyClipper se calcula una vez por arrastre, no por movimiento de ratón (perf: 11 ms de calentamiento + 0.16 ms/movimiento con 30 piezas). Eliminado código muerto: `_polys_overlap`, `_inflate_poly_x`, `_neighbor_polys`, `_bar_neighbors`, `_slide_to_valid`. Tests nuevos en `tests/test_nesting_manual_nfp.py` (4): el motor y la colocación manual coinciden, recolocación exacta a 0.00 mm, hueco flush == kerf exacto, sin crash en geometría degenerada. Verificado visualmente: 4 bevels a 45° acoplan flush (caras mating), sin huecos ni solapes. 186 tests pasan.

---

## 27. QA batch (post-NFP): subtabs, costs defaults, jobs, drawing module, exports, fonts

> Lote de errores reportados tras probar la build. Cada ítem referencia archivo/causa
> al resolverse. Motor intocable; verificación con tests + capturas de salidas reales.

- [x] **Subtab fantasma**: causa raíz = `MaterialSubTabs.remove_tab` no decrementaba `_active` al borrar una subtab ANTERIOR a la activa → quedaba apuntando una posición a la derecha y se cargaba el `MaterialContext` equivocado (piezas/cortes de otra subtab). Corregido el índice en el widget; además los `_on_tab_removed` (Cuts/Nesting/Costs) ahora cargan explícitamente el contexto activo correcto tras el borrado.
- [x] **Costs defaults no se aplican**: las nuevas subtabs creaban un `MaterialContext()` sin sembrar los defaults; ahora los tres `_on_tab_added` (Cuts/Nesting/Costs) aplican `app_config.apply_cost_defaults(ctx.perfil)` al crear el contexto, y `_new_job` también. Verificado headless: subtab nueva arranca con op/cut/miter/margin del usuario.
- [x] **Job Explorer "New Job" duplicado**: `ui.new_btn` ("New Job") oculto; queda solo "Create new job" (`_create_job_btn`).
- [x] **Create new job debe persistir**: `_new_job` ahora llama `app._save_job_to_db(silent=True)` tras inicializar el estado → el job (aunque vacío) se inserta en la BD y aparece en la lista sin necesidad de Ctrl+S. `_save_job_to_db` admite `silent` para no mostrar el popup de confirmación.
- [x] **Módulo de dibujo cortado**: `ProfileCreator` forzaba `resize(1060,700)` + `min(900,600)`, que en pantallas pequeñas desbordaba y el gestor de ventanas lo recortaba. Ahora dimensiona al 90% del área disponible de la pantalla (tope 1060×700) y baja el mínimo para caber en portátiles → abre siempre completo.
- [x] **Edit drawing de un cut: barra superior, no panel derecho**: el "Edit drawing" de una pieza ahora abre `CutPieceDialog` (preview 2D en vivo + editores de largo/ingletes) con un **menú superior File → Export DXF / Import DXF / Save As / Save** (Ctrl+S) en vez del `ProfileCreator` con panel derecho. Botonera inferior reducida a Save/Cancel.
- [x] **El dibujo editado afecta al nesting**: al guardar, los nuevos largo/ingletes se escriben en el `Corte` compartido; se invalidan `_poly_cache`/`_engine_piece_cache`/`_viable_cache` y se recomputa `poly_local` de las copias colocadas, así la nueva forma rige el render, la colisión manual y el auto-nest. Si la forma cambió y hay layout, se pregunta **Repetir anidado** / **Mantener colocación** (claves i18n `shape_changed_*`). Si no cambió nada, no se toca el layout.
- [x] **Import/Download template + export de cortes roto**: (a) *download template* fallaba porque `DataValidation.sqref` usaba rangos separados por COMA; OOXML exige espacios → `"D2:D1000 G2:G1000"`. (b) *importar no mostraba los cortes*: `_importar_excel` extendía solo `state.cortes`, pero `_apply_context_to_ui` repinta desde `ctx.cortes`; ahora se vuelcan los cortes importados también al contexto activo. (c) *export listado decía "no nesting data" y "borraba" el preview*: el export de Cuts ahora quick-packea (`recompute_auto_barras`, sin tocar un anidado manual existente) los contextos con cortes pero sin barras, y exporta vía `material_contexts`/`effective_barras` en vez de `state.barras_necesarias`. Verificado E2E: template 5680 B + round-trip, PDF renderizado con bin-packing (2 barras), XLSX de cortes. Tests en `tests/test_excel_template_export.py`.
- [x] **QFont::setPointSize warning**: `QFont::setPointSize: Point size <= 0 (-1)` al arrancar. → Causa: un `font_size_offset` guardado suficientemente negativo hacía que `theme_qt.build_stylesheet` produjera `font-size <= 0`. `base/small/caption_size` ahora con `max(1, …)`. Verificado: con offset=-20 no aparece el warning.
- [x] **Quitar opción de tamaño de fuente**: eliminado el submenú View → "Font size" (`_set_font_size` y su menú). El View menu queda con Theme, Language, Unit system y Color per cut.
- [x] **Exportaciones en general**: probadas E2E con un caso real (largueros con inglete 45° + travesaños) TODAS las salidas: XLSX de cortes, plantilla XLSX, PDF cut-plan (Cuts), XLSX de costes, PDF de presupuesto, DOCX de presupuesto, DXF de nesting (reparseado con ezdxf, 9 entidades) y PDF de nesting (renderizado, muestra los biseles y leyenda por barra). Todas producen archivos válidos; salidas renderizadas a imagen y verificadas.
- [x] **paintEvent error en tab_cortes.py**: `Error calling Python override of QWidget::paintEvent()`. → `paintEvent` reescrito como guard try/finally que SIEMPRE llama `QPainter.end()` (una excepción sin capturar dejaba el painter activo → ese error + widget en blanco); el cuerpo movido a `_do_paint`, y el cambio de geometría diferido con `QTimer.singleShot(0, …)` para no mutar geometría a mitad de pintado.
- [x] **PRIORIDAD — los parámetros de optimización avanzada deben aplicarse de forma VISIBLE**: cableado UI→motor verificado correcto (cada estrategia mapea a su clave; el tiempo se respeta). Causa de "no cambia nada": el bucle de `nest_advanced_timed` agotaba el tiempo con permutaciones aleatorias que casi nunca mejoraban el primer orden. → Sustituido por **búsqueda local iterada** que perturba el mejor orden (swap / reverse / relocate / restart) y conserva mejoras, con paciencia escalada al tiempo. Más tiempo encuentra mejores empaquetados (semilla 0: 0.25 s → 5 barras vs 6 s → **4 barras**); estrategias con layouts distintos. 46 tests del motor OK + regresión `tests/test_nesting_optimization_params.py`.

- [x] **Pérdida de cortes al borrar subtabs**: mismo origen (índice activo desfasado) + los `_on_tab_removed` recargaban el contexto activo sin volcar antes la UI viva, machacando ediciones no guardadas de una subtab superviviente. Ahora cada `_on_tab_removed` (Cuts/Nesting/Costs) vuelca la subtab activa a su contexto ANTES del pop y recarga el contexto correcto. Tests en `tests/test_subtab_delete.py`.
