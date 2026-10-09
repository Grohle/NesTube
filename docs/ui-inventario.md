# NesTube — inventario de la interfaz y mapa a la nueva UI web

Este documento lista **todos** los menús, botones, controles, atajos, ventanas (diálogos) y avisos de la
interfaz Qt actual (`nestube/ui_qt/`) y dónde queda cada uno en la nueva interfaz HTML
(`nestube/web/`). Los textos son los de `nestube/i18n.py` en español.

La nueva interfaz sigue un esquema tipo Figma:

| Zona | Contenido |
|---|---|
| Barra superior | Menú principal (logo **N**), selector de pestañas, nombre del trabajo, catálogo, atajos, tema, zoom, Exportar y Auto-anidar |
| Panel izquierdo ("capas") | Sub-pestañas de material y la lista de lo que se edita (piezas, trabajos…) |
| Centro | Lienzo infinito (Anidado) o contenido de la pestaña |
| Panel derecho ("inspector") | Propiedades y ajustes de lo seleccionado |
| Barra de estado | Estado del anidado, coordenadas del cursor en mm, base de datos y versión |

---

## 1. Barra de menús → menú principal

En Qt es una barra de menús. En la web es **un único botón (logo N)** con los menús como submenús, igual que el menú principal de Figma. Mismo orden y mismos elementos.

| Menú | Elemento | Atajo | Acción |
|---|---|---|---|
| **Archivo** | Abrir | | Abre un trabajo (BD o `.nestjob`) |
| | Guardar | `Ctrl+S` | Guarda el trabajo (global) |
| | Guardar como | | Guarda con otro nombre / exporta `.nestjob` |
| | Guardar configuración del programa | | Exporta las preferencias a `.json` |
| | Cargar configuración del programa | | Importa preferencias desde `.json` |
| | Copias de seguridad | | Diálogo de copias de la BD |
| | Gestión de base de datos | | Ubicación de la BD y de las copias |
| | Salir | | Cierra la app (pregunta si hay cambios sin guardar en el anidado) |
| **Vista** | Tema ▸ Oscuro / Claro | | Cambia el tema (también con el botón sol/luna de la barra superior) |
| | Idioma ▸ English / Español | | |
| | Sistema de unidades ▸ Métrico (mm, kg) / Imperial (in, lb) | | |
| | Colores por corte en anidado (casilla) | | Un color por corte en el lienzo |
| | *Atajos de teclado* (**nuevo**) | `?` | Muestra la tabla de atajos |
| **Configuración** | Materiales ▸ Añadir material / Gestionar materiales | | |
| | Perfiles y tubos ▸ Añadir perfil / Editar perfiles | | Editor de perfiles / gestor de perfiles |
| | Configuración PDF ▸ Fuente PDF / Plantilla PDF base / Editar plantillas | | |
| | Valores de coste por defecto | | |
| | Tiempos de optimización (1–6) | | |
| | Disposición del anidado | | |
| | Asignación de nombres | | |
| | Restablecer ajustes | | Pregunta antes |
| **Acerca de** | Acerca de NesTube | | Versión y búsqueda de actualizaciones |
| **Ayuda** | Tutorial interactivo | | |
| | GitHub / Issues | | |
| | *Catálogo de ventanas y avisos* (**nuevo, solo maqueta**) | | Revisión de todas las ventanas y avisos |

## 2. Pestañas

| Qt | Web (selector de la barra superior) |
|---|---|
| Explorador de Jobs | **Jobs** |
| Cortes | **Cortes** |
| Anidado | **Anidado** |
| Costes y Peso | **Costes** |
| Perfiles y Tubos | **Perfiles** |
| Stock | **Stock** |

**Sub-pestañas de material** (Cortes, Anidado y Costes): en Qt es una fila de pestañas con un botón `+`. En la web pasan a la sección **Materiales** del panel izquierdo, como las "páginas" de Figma: `+` añade una y el clic derecho permite Renombrar o Eliminar pestaña. Costes añade la entrada **Total · todos los materiales**.

## 3. Atajos de teclado (idénticos a Qt)

| Atajo | Ámbito | Acción |
|---|---|---|
| `Ctrl+S` | Global | Guardar (en Anidado: guardar anidado) |
| `Ctrl+Z` | Anidado | Deshacer |
| `Ctrl+Y` | Anidado | Rehacer |
| `Ctrl+Q` | Anidado | Rotar la pieza flotante 90° antihorario (ciclo de orientaciones) |
| `Ctrl+E` | Anidado | Rotar la pieza flotante 90° horario |
| `Ctrl+H` | Anidado | Reflejar horizontal (pieza flotante o selección) |
| `Ctrl+A` | Anidado | Reflejar vertical (**no** es "seleccionar todo", igual que en Qt) |
| `Supr` | Anidado | Quitar de barra la selección |
| `Esc` | Anidado | Detener el auto-anidado › soltar la pieza flotante › deseleccionar (en ese orden) |
| `Ctrl+Z` / `Ctrl+Y` | Editor de perfiles | Deshacer / rehacer el dibujo |
| `Enter`, `Tab`, `<`, dígitos, `Retroceso`, `Esc` | Editor de perfiles (polilínea) | Entrada numérica de longitud y ángulo; `Esc` termina |
| `?` | Global (**nuevo**) | Tabla de atajos |

Como en Qt (`WidgetWithChildrenShortcut`), los atajos de Anidado solo actúan en esa pestaña y nunca mientras se escribe en un campo.

**Ratón en el lienzo** (de `nesting_view.py` y `tab_nesting.py`):

| Gesto | Acción |
|---|---|
| Rueda | Zoom ×1,15 por paso, centrado en el cursor |
| Botón central, o `Ctrl` + arrastrar | Desplazar |
| Arrastrar en vacío sin nada seleccionado | Desplazar |
| Arrastrar en vacío con selección | Selección por área (`Ctrl` la suma a la actual) |
| Clic en pieza | Seleccionar |
| `Ctrl` + clic | Selección múltiple (contorno magenta) |
| Clic sobre la única pieza ya seleccionada | Cogerla para moverla; el siguiente clic la suelta |
| Arrastrar una pieza (> 5 px) | Mover; si se suelta en posición inválida, vuelve a su sitio |
| Clic derecho en pieza | Menú contextual |
| Clic en el % de zoom | Volver al 100 % y centrar |

## 4. Anidado

| Control Qt | Web | Notas |
|---|---|---|
| Guardar (icono) | Barra flotante inferior | `Ctrl+S` |
| Limpiar (icono) | Barra flotante | Pide confirmación |
| Exportar ▾: Exportar PDF · Imprimir… · Exportar DXF · Exportar anidado (PNG) | Barra superior **Exportar ▾** | PDF e Imprimir abren "Seleccionar anidados para exportar" |
| Interruptor Avanzado | Inspector › Motor › Simple / Avanzado | |
| Usar stock | Inspector › Material y stock | |
| Auto elegir material | Inspector › Material y stock | Activo solo con "Usar stock" |
| Chip "Stock: …" (clic = desvincular) | Inspector › chip con ✕ | |
| + Añadir barra | Barra flotante **Barra** e Inspector › Barras | Con stock manual abre "Seleccionar barra de stock" |
| Retales | Barra flotante **Retales** → Inspector › Retales | |
| Rotar ↺ / Reflejar ⇕ / Reflejar ⇄ / Rotar ↻ | Barra flotante | Mismos atajos |
| Zoom 100 % | Barra superior (pastilla %) | Menú: Acercar / Alejar / Ajustar |
| Combo Todo / Solo pendientes | Flecha del botón **Auto-anidar** e Inspector › Motor | |
| Auto-anidar (se vuelve **■ Detener** en rojo) | Botón principal de la barra superior | Panel de progreso flotante; `Esc` detiene |
| Pérdida corte, Margen, Longitud barra, Altura barra (mm) | Inspector › Barra | |
| Corte común | Inspector › Barra y barra flotante | |
| Snap | Inspector › Barra y barra flotante | |
| Tiempo de optimización: 1 (1s) · 2 (5s) · 3 (10s) · 4 (20s) · 5 (30s) · 6 (∞) | Inspector › Motor › Tiempo | Solo en Avanzado |
| Estrategia: Por longitud · Compactación NFP · Retales reutilizables · Simetría (emparejamiento) · Mín. longitud total | Inspector › Motor › Estrategia | Solo en Avanzado |
| Sistema de cálculo: FFD · BFD · NFD | Inspector › Motor | Solo en Simple |
| Sel. material + campo de material | Inspector › Material y stock | |
| Quitar de barra / Eliminar pieza | **Barra contextual** flotante sobre el lienzo al seleccionar | |
| Lista "N piezas pendientes" con filtro Todas / Completas / Pendientes | Panel izquierdo › Piezas | Barra de progreso por pieza |
| Lista de barras (Bar N (n), ↑ ↓, Mostrar todas, plegar y desplegar) | Inspector › **Barras** | Miniatura de cada barra y % de aprovechamiento |
| Panel de retales: Longitud mínima, Margen, ↻, Aplicar, Borrar selección, Borrar todos los retales | Inspector › **Retales** | |
| Estado "Estrategia · N bars · x/y placed · %" | Barra de estado e Inspector › Resultado | |

**Menú contextual de pieza (lienzo):** Mover · Cambiar valores · — · Voltear horizontal · Voltear vertical · — · Editar dibujo · Exportar DXF · — · Quitar de barra · Eliminar pieza.

**Menú contextual de pieza (lista lateral):** Cambiar valores · — · Editar dibujo · Exportar DXF · — · Eliminar pieza.

## 5. Explorador de Jobs

| Control | Web |
|---|---|
| Campo de búsqueda: Nombre · Cliente · Perfil/Tubo · Pedido · Oferta | Panel izquierdo |
| Buscar trabajos… / 🔍 / ✕ | Panel izquierdo (filtra al escribir) |
| Lista de jobs (nombre, cliente, fecha) | Panel izquierdo |
| Nuevo trabajo | `+` del panel y botón de la cabecera |
| Detalle: Descripción, Cliente, Pedido, Oferta (el nombre no se puede editar) | Inspector › Detalles |
| Tabla de piezas (#, Descripción, Longitud, Cant.) | Centro, con resumen del material, barras, aprovechamiento y total |
| Barras de stock usadas / retales generados | Centro › Trazabilidad de stock |
| Guardar cambios · Abrir job · Eliminar job | Inspector |

## 6. Cortes

| Control | Web |
|---|---|
| Material (buscar perfil, material o calidad… + 🔍) | Panel izquierdo › Trabajo |
| Nº Pedido · Oferta · Cliente · + Añadir campo (clic derecho: Editar campo) | Panel izquierdo › Trabajo |
| Pérdida corte · Margen · Longitud barra · Altura barra | Panel izquierdo › Barra |
| Sistema de cálculo FFD/BFD/NFD | Panel izquierdo › Barra |
| Descargar plantilla XLSX · Importar XLSX · Exportar Excel · Exportar PDF · Exportar DXF de contornos | Iconos de la cabecera |
| + Añadir corte · Calcular | Cabecera |
| Fila: #, Descripción, Longitud, Cant., Inglete 1 (casilla + dirección + grados), Inglete 2, Forma/color (abre el editor de la pieza), ✕ Eliminar corte | Tabla central editable |
| Vista previa del anidado (Barra N, %, R…) | Inspector + botón **Abrir en Anidado** |

## 7. Costes y Peso

| Control | Web |
|---|---|
| Sub-pestañas + Total | Panel izquierdo › Materiales |
| Buscar perfil, material o calidad… | Panel izquierdo |
| Ficha del perfil (h, b, tw, tf, sección, peso lineal) + Editar material | Panel izquierdo |
| Calcular · Limpiar | Cabecera |
| Excel · PDF · DOCX · Imprimir | Iconos de la cabecera |
| Peso: kg/m · Peso específico (t/m³) · Espesor de pared · Sección maciza | Inspector |
| Precios: €/kg · €/m · Precio por barra · Margen de beneficio % · Moneda | Inspector |
| Mano de obra: Tiempo corte recto (min) · Extra inglete (%) · Coste operario | Inspector |
| Modo de cálculo: Cortes compartidos (optimizado) / Cortes individuales | Inspector |
| Repartir coste de retales · Confirmar configuración antes de calcular | Inspector |
| Resultados por corte (Peso/ud, Área/ud, Material/ud, Mano de obra/ud, Total/ud, €/m, Total línea) | Tabla central con fila TOTAL PEDIDO y tarjetas de resumen |
| "Basado en el anidado completado" / "Cálculo rápido" | Chip de la cabecera |

## 8. Perfiles y Tubos

| Control | Web |
|---|---|
| Buscar… · Lista / Cuadrícula · Nuevo perfil/tubo · Editar · Materiales | Cabecera |
| Tabla (miniatura, Nombre, Material, h, b, tw, tf, Sección, Peso lineal) | Centro; **nuevo:** filtros por familia (IPE/HEA, UPN/C/Z, Angulares, Tubos, Macizos, Ranurados) |
| Doble clic | Abre el editor de perfiles |
| — | **Nuevo:** inspector con dibujo de la sección, geometría, Editar dibujo y Cambiar material |

## 9. Stock

| Control | Web |
|---|---|
| + Añadir al stock · Editar campos · Eliminar · Exportar Excel | Cabecera |
| Buscar Perfil/Material… · Todos los perfiles · "N items · M ud" | Cabecera |
| Seleccionar todos · Long. mín. · Long. máx. · Largo mínimo retal | Segunda fila de la cabecera |
| Tabla: ☐, estado, Perfil/Material, Calidad, Largo, Cantidad, Disponible, Retal, Job de creación, Usado en jobs (clic → Explorador de Jobs) | Centro |
| — | **Nuevo:** inspector con resumen (barras disponibles, retales, metros lineales), ficha y trazabilidad |

## 10. Ventanas (diálogos)

Todas están maquetadas en `nestube/web/js/dialogs.js` (el módulo de dibujo, en `js/cad.js`) y se pueden revisar desde **Ayuda › Catálogo de ventanas y avisos**.

| Ventana (Qt) | Contenido principal |
|---|---|
| Abrir / Guardar como / Cargar configuración | Lista de trabajos, `.nestjob`, `.json` |
| Copias de seguridad | Lista de copias · Crear copia ahora · Restaurar desde archivo… · Restaurar seleccionada |
| Gestión de base de datos | Ruta de la BD y de las copias (Examinar…) · Frecuencia · Última copia · Cambiar ubicación · Cargar BD · Crear copia · Gestionar copias |
| Añadir material / Gestionar materiales | Lista + Nombre, Calidad, Peso específico · Nueva · Eliminar · Guardar |
| Gestionar perfiles | Lista + Material, Calidad, Peso específico, Dimensiones (Editar campos) · Asignar imagen · Módulo de dibujo · Eliminar |
| Módulo de dibujo (editor de perfil) | Herramientas: Seleccionar, Línea, Polígono, Rectángulo, Círculo, Arco 3pt, Arco CSE, Arco exacto, Borrar, Marcar vano, Recortar, Extender, Ortogonal, Deshacer/Rehacer · Datos del perfil · Lados y espesores · Importar/Exportar DXF · Exportar PNG · Importar imagen · Limpiar · Generar perfil · Guardar |
| Fuente PDF · Plantilla PDF base · Editar plantillas | Fuente · plantilla FastReport · editor de campos (Nesting PDF / Presupuesto PDF) |
| Valores de coste por defecto | Coste operario /h · Tiempo corte recto · Extra inglete % · Margen de beneficio % |
| Tiempos de optimización (1–6) | Nivel 1–5 en segundos; nivel 6 ∞ |
| Disposición del anidado | Panel piezas / Panel barras (Izquierda/Derecha) · Zona snap (mm) · Colores por corte |
| Asignación de nombres | Prefijo de trabajo · Prefijo de retal |
| Acerca de NesTube | Versión · Buscar actualización · No mostrar de nuevo |
| Seleccionar anidados para exportar | Casillas por material · Seleccionar/Deseleccionar todos · Exportar seleccionados |
| Buscar perfiles y tubos (Sel. material) | Modo Perfiles y Tubos / Material / Stock · Largo mín. · Seleccionar |
| Seleccionar barra de stock | Tabla de stock · Ver retales · Añadir cant. · Borrar cant. · Crear nueva · Bloquear/Desbloquear |
| Añadir al stock / Editar stock | Perfil, tipo, material, calidad, dimensiones según tipo, largo, cantidad, peso y precios, disponible, notas |
| Editar campos (stock) | Columnas visibles |
| Crear nuevo job | Nombre automático, descripción, cliente, pedido, longitud, cantidad |
| Añadir campo (Cortes) | Nombre del campo |
| Cambiar valores (pieza) | Descripción, Cant., Largo, Inglete 1/2, color |
| Editar dibujo (pieza de corte) | Contorno con ingletes · Importar/Exportar DXF · Guardar / Guardar como |
| Seleccionar altura de corte | Caras del perfil con varias alturas |

## 11. Avisos (QMessageBox)

Hay **93** avisos distintos en el código: 36 de información, 25 advertencias, 17 errores y 15 preguntas. Están todos en `nestube/web/js/alerts.js` con el texto real y se ven con un componente único de aviso.

Propuesta de comportamiento en la web:

- **Pregunta, advertencia y error:** ventana modal, con icono y color según el tipo, igual que en Qt.
- **Información de éxito** ("Guardado", "Exportado en…"): notificación breve no bloqueante, en vez de un modal que obliga a pulsar Aceptar. Se puede volver al modal si se prefiere.

Avisos ya conectados a su flujo real en la maqueta:

- Limpiar el anidado.
- Auto-anidar en modo «Todo» con piezas ya colocadas.
- Eliminar pieza (una o varias).
- Retales sin stock, retales sin longitud mínima, borrar todos los retales.
- Salir de Anidado con cambios sin guardar (Guardar / Descartar / Cancelar).
- Exportar sin anidado.
- Restablecer ajustes.
- Guardar y eliminar job.
- Restaurar una copia de seguridad.

## 12. Visor de imágenes de perfiles

Las miniaturas de perfil son los PNG de `Profiles/` (`app_config.PROFILES_DIR`), las que asigna el usuario o las generadas desde el módulo de dibujo. En Qt aparecen en cuatro sitios; en la web, en todos ellos y además en un visor a pantalla completa.

| Dónde (Qt) | Web |
|---|---|
| Galería de Costes (`ProfileTile`: hasta 5 recientes + tile `+` Añadir perfil; combo "Todos los perfiles"; modo bloqueado con un perfil de catálogo) | Costes › panel izquierdo › **Perfil**: rejilla de miniaturas, `+`, combo, ficha con imagen grande. Doble clic en una miniatura abre el visor |
| Catálogo Perfiles y Tubos (Lista con icono / Cuadrícula con iconos) | Miniatura real en la lista y en la cuadrícula; el inspector muestra la imagen grande, **Ver imagen** y **Asignar imagen** |
| Gestionar perfiles (miniatura en la lista + Asignar imagen) | Miniaturas en la lista, imagen grande clicable, **Ver imagen** y **Asignar imagen** (PNG o JPEG) |
| Módulo de dibujo (vista previa · ⮕ Generar perfil · Importar imagen) | Paleta Propiedades › **Imagen del perfil**: Generar (desde el dibujo actual), Importar imagen y clic para abrir el visor |
| Buscar perfiles y tubos (selector de material) | Rejilla de miniaturas + lista de materiales + Gestionar materiales |

**Visor** (nuevo): anterior/siguiente con tira de miniaturas; zoom con la rueda, `+`, `−`, `0` (ajustar) y `1` (1:1); fondo de cuadros, claro u oscuro (`B`); nombre del archivo, tamaño en px y material; botones Asignar imagen y Exportar PNG; `Esc` para cerrar.

## 13. Módulo de dibujo (estilo AutoCAD)

Mismas herramientas y comportamiento que `profile_creator.py`, organizados como en AutoCAD para que quien venga de AutoCAD lo entienda a la primera.

| Zona | Contenido |
|---|---|
| Cinta de opciones | **Dibujo**: Línea, Polígono, Rectángulo, Círculo, Arco 3 puntos, Arco centro-inicio-fin, Arco exacto… · **Modificar**: Borrar, Recortar, Extender · **Perfil**: Marcar vano, Asignar dimensión, Asignar espesor · **Utilidades**: Seleccionar, Deshacer, Rehacer, Zoom extensión · **Archivo**: Importar DXF, Exportar DXF, Exportar PNG (transparente) |
| Espacio modelo | Fondo oscuro, cursor en cruz con caja de selección, icono SCP (X/Y), rejilla de 10 mm (mayor cada 50), Y hacia arriba, unidades en mm, etiqueta de ventana gráfica `[−][Superior][2D Estructura alámbrica]` |
| Referencias a objetos | Mismo orden de prioridad que `_snap`: Punto final □ · Punto medio △ · Centro ○ · Cercano ⧖ · Rejilla, con marcador amarillo y etiqueta |
| Entrada dinámica | Junto al cursor: campos de longitud y ángulo. Se teclea la longitud; `Tab` o `<` pasa al ángulo; `Enter` fija el punto (igual que en Qt) |
| Línea de comandos | Historial de 3 líneas + mensaje de la orden activa ("LINEA Precise punto siguiente o [Deshacer]:"). Acepta coordenadas absolutas `X,Y` |
| Barra de estado | Coordenadas X, Y, Z · MODELO · **REJILLA** (F7) · **FORZC** (F9) · **ORTO** (F8) · **REFENT** (F3) ▾ modos · **DIN** (F12) |
| Paleta Propiedades | Imagen del perfil · Selección (tipo, longitud, vano) · Asignar dimensión / espesor · Lados y espesores (+ lado manual, quitar último) · Datos del perfil |
| Barra de título | Limpiar · ⮕ Generar perfil (dibujo actual) · Guardar · Cerrar |

**Órdenes y alias** (nuevos, solo en el módulo de dibujo):

| Orden | Alias |
|---|---|
| LINEA (polilínea) | `L`, `PL`, `LINEA`, `LINE` |
| POLIGONO | `POL` (pide número de lados, por defecto 6) |
| RECTANG | `REC` |
| CIRCULO | `C` |
| ARCO 3 puntos / centro-inicio-fin / exacto | `A` / `ACIF` / `AE` |
| BORRA | `B`, `E`, `Supr` con selección |
| RECORTA | `TR` |
| ALARGA (extender) | `EX`, `AL` |
| VANO (marcar hueco) | `VANO` |
| ZOOM extensión | `Z`, doble clic con la rueda |
| Deshacer / Rehacer | `U`, `Ctrl+Z` / `Ctrl+Y` |

`Enter` o `Espacio` con la línea de comandos vacía repiten la última orden (igual que AutoCAD). `Esc` cancela la orden y, si no hay ninguna activa, la selección. Clic derecho termina la polilínea o repite la orden. Escribir en cualquier parte va a la línea de comandos. Rueda = zoom en el cursor; botón central = desplazar.

## 14. Tutorial interactivo

Los mismos 14 pasos y textos de `tutorial.py` (Bienvenido, Las pestañas, Añade tus cortes, Parámetros de barra, Calcular, Auto-anidar, Estrategia, Tiempo de optimización, Ajuste manual, Costes y Peso, Perfiles y Tubos, Stock, Trabajos, ¡Listo!). Se muestran como tarjetas que resaltan el control correspondiente. Botones Saltar / Atrás / Siguiente / Terminar; teclas `→` `Enter` `Espacio` (siguiente), `←` (atrás) y `Esc` (salir). Se abre desde **Ayuda › Tutorial interactivo**.

## 15. Ventanas añadidas en esta revisión

Generar retales (Largo mínimo retal, Actualizar, Retales válidos, Añadir al stock, Eliminar seleccionados, Eliminar todos) · Editar/Añadir tipo de perfil (campos, material, peso específico, calidad, notas, Editar campos) · Buscar perfiles y tubos (selector de material con miniaturas).

### Lista completa de avisos

**Ventana principal**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Advertencia | No hay ningún trabajo abierto. |
| Información | Información | Costes rellenados desde el stock de este material. |
| Pregunta | Cambios sin guardar en el Nesting | El nesting tiene cambios sin guardar.  ¿Guardar antes de salir de esta pestaña? |
| Información | Sistema de unidades | Unidades: Métrico (mm, kg) |
| Información | Tiempos de optimización (1–6) | Tiempos de optimización guardados. |
| Información | Valores de coste por defecto | Valores de coste por defecto guardados. |
| Información | Fuente de interfaz | La fuente se aplicará al reiniciar NesTube. |
| Pregunta | Restablecer ajustes | ¿Restablecer todos los ajustes a valores predeterminados (inglés, EUR, métrico)? |
| Error | Error al abrir | No se pudo leer el archivo: [Errno 13] Permiso denegado |
| Información | Guardar | Configuración guardada correctamente. |
| Error | Error al guardar | No se pudo guardar: [Errno 13] Permiso denegado |
| Información | Abrir Job | Job guardado correctamente. |
| Error | Error al abrir | Detalle del error: [Errno 13] Permiso denegado: «C:\NesTube\export.pdf». |
| Información | Guardar configuración del programa | Configuración del programa guardada. |
| Error | Error de configuración | Detalle del error: [Errno 13] Permiso denegado: «C:\NesTube\export.pdf». |
| Advertencia | Importar Excel | Error al importar Excel |
| Información | Importar Excel | Importados 3 cortes desde Excel |
| Error | Error al importar Excel | Detalle del error: [Errno 13] Permiso denegado: «C:\NesTube\export.pdf». |
| Advertencia | Exportar XLSX | No hay cortes para exportar. |
| Información | Exportar XLSX | 3 cortes exportados correctamente. |
| Error | Exportar XLSX | Detalle del error: [Errno 13] Permiso denegado: «C:\NesTube\export.pdf». |
| Error | Error al exportar | Detalle del error: [Errno 13] Permiso denegado: «C:\NesTube\export.pdf». |

**Diálogo · backup**

| Tipo | Título | Mensaje |
|---|---|---|
| Información | Copias de seguridad de la base de datos | Copia de seguridad creada. |
| Advertencia | Copias de seguridad de la base de datos | Selecciona una copia para restaurar. |
| Pregunta | Copias de seguridad de la base de datos | ¿Restaurar esta copia? La app deberá reiniciarse. |
| Información | Copias de seguridad de la base de datos | Copia restaurada. Reinicia NesTube. |
| Error | Copias de seguridad de la base de datos | No se pudo restaurar la copia. |

**Diálogo · change values**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Exportar DXF de cortes | Introduce la altura de barra para generar el contorno correcto. |
| Error | Exportar DXF de cortes | Detalle del error: [Errno 13] Permiso denegado: «C:\NesTube\export.pdf». |
| Información | Exportar DXF de cortes | Operación completada. |

**Diálogo · cut piece**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Importar DXF | No se pudo importar el DXF: el archivo no contiene contornos cerrados. |

**Diálogo · database management**

| Tipo | Título | Mensaje |
|---|---|---|
| Pregunta | Gestión de base de datos | ¿Copiar la base de datos actual a la nueva ubicación? |
| Error | Gestión de base de datos | Detalle del error: [Errno 13] Permiso denegado: «C:\NesTube\export.pdf». |
| Información | Gestión de base de datos | Ubicación de la base de datos actualizada. Reinicia NesTube. |
| Información | Gestión de base de datos | Copia de seguridad creada. |
| Advertencia | Gestión de base de datos | Aún no hay copias. |

**Diálogo · materials manager**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Advertencia | Indica el nombre del material. |
| Advertencia | Advertencia | Ya existe un material con ese nombre y calidad. |
| Información | Materiales | Material guardado. |
| Advertencia | Advertencia | Selecciona un material de la lista. |
| Pregunta | Eliminar | ¿Eliminar el material ««X»»? |

**Diálogo · nesting layout**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Advertencia | Introduce un valor numérico válido para la zona snap. |

**Diálogo · pdf template editor**

| Tipo | Título | Mensaje |
|---|---|---|
| Información | Plantilla FastReport | Sin plantilla FastReport configurada. |
| Advertencia | Plantilla FastReport | El archivo de plantilla FastReport ya no existe. |
| Información | Editar plantilla PDF | Plantilla guardada correctamente. |
| Error | Error al guardar | Detalle del error: [Errno 13] Permiso denegado: «C:\NesTube\export.pdf». |

**Diálogo · profile creator**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Importar imagen | (sin imagen) |
| Error | ⭱ Exportar DXF | Detalle del error: [Errno 13] Permiso denegado: «C:\NesTube\export.pdf». |
| Error | ⭱ Exportar PNG (transparente) | Detalle del error: [Errno 13] Permiso denegado: «C:\NesTube\export.pdf». |

**Diálogo · profile manager**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Advertencia | Selecciona un tipo de perfil. |
| Advertencia | Advertencia | Solo se aceptan imágenes PNG o JPEG (.png, .jpg, .jpeg). |
| Pregunta | Eliminar | ¿Eliminar el perfil '«X»'? |

**Diálogo · retal**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Advertencia | No hay retales que superen el largo mínimo |
| Información | Generar retales | 3 retales añadidos al stock. |

**Diálogo · stock add**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Advertencia | Indica el perfil o material. |
| Advertencia | Advertencia | Indica una longitud de barra válida (> 0). |
| Advertencia | Error de datos | Revisa los datos introducidos. |

**Diálogo · stock bar picker**

| Tipo | Título | Mensaje |
|---|---|---|
| Información | Seleccionar barra de stock | Esta barra está bloqueada y no se puede seleccionar. |

**Cortes**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Advertencia | Longitud de barra inválida. Introduce un número positivo. |
| Advertencia | Advertencia | Error de datos |
| Advertencia | Advertencia | Para aplicar un inglete debes indicar la altura de barra (Bar height). |
| Información | Sin cortes | No hay cortes para exportar. |
| Información | Exportar DXF de cortes | 3 archivo(s) DXF exportados. |

**Explorador de Jobs**

| Tipo | Título | Mensaje |
|---|---|---|
| Pregunta | Guardar cambios | ¿Guardar los cambios del job ««X»»? |
| Advertencia | Advertencia | Selecciona un job de la lista |
| Error | Error al abrir | No hay jobs guardados |
| Pregunta | Eliminar Job | ¿Eliminar el job ««X»»? |

**Anidado**

| Tipo | Título | Mensaje |
|---|---|---|
| Pregunta | Eliminar pieza | ¿Eliminar 3 piezas permanentemente? |
| Pregunta | ¿Borrar piezas colocadas? | El modo 'Todo' eliminará las 3 pieza(s) ya colocadas.  ¿Continuar? |
| Pregunta | Eliminar pieza | ¿Eliminar pieza permanentemente? |
| Pregunta | Cambiar valores | ¿Recalcular nesting para actualizar geometría? |
| Información | Generar Retales | Solo se pueden generar retales si se ha usado stock. |
| Información | Generar Retales | No hay retales que cumplan el largo minimo. |
| Información | Generar Retales | Retales guardados en stock. |
| Pregunta | Borrar todos los retales | ¿Borrar todos los retales de este material del stock? |
| Información | Borrar todos los retales | 3 retales borrados del stock. |
| Información | Exportar | Sin datos de anidado. Ejecuta el anidado automático o coloca piezas primero. |
| Advertencia | Exportar PDF | Revisa los datos introducidos. |
| Información | Exportar PDF | Diagrama de anidado guardado en: C:\… |
| Información | Exportar DXF | Diagrama de anidado guardado en: C:\… |
| Información | Usar stock | No hay barras de stock. Añade barras en la pestaña Stock primero. |
| Información | Exportar anidado (PNG) | Sin datos |
| Información | Exportar anidado (PNG) | Diagrama de anidado guardado en: C:\… |
| Pregunta | Limpiar | ¿Borrar el anidado actual? Esta acción no se puede deshacer. |

**Costes y Peso**

| Tipo | Título | Mensaje |
|---|---|---|
| Error | Sin cortes | No hay cortes definidos. Ve a la pestaña Cortes y añade los cortes primero. |
| Error | Error de datos | Longitud de barra inválida. Introduce un número positivo. |
| Error | Tipo de perfil | Selecciona un tipo de perfil. |

**Stock**

| Tipo | Título | Mensaje |
|---|---|---|
| Advertencia | Advertencia | Selecciona un elemento del stock. |
| Información | Stock | Stock actualizado. |
| Información | Stock | Stock guardado. |
| Información | Exportar Excel | Sin datos |
| Información | Exportar Excel | Excel guardado en: C:\… |
| Pregunta | Eliminar | ¿Eliminar los 2 elementos seleccionados del stock? |
