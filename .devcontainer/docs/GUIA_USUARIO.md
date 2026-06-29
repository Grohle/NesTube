# Nestify

> Válido para la línea **Qt** (`2.0.0-alpha`). Para instalación consulta el
> [README](../README.md). Esta guía recorre la aplicación módulo a módulo,
> con una captura de cada pestaña.

Nestify ayuda a talleres de fabricación metálica a planificar el corte de
barras, tubos y perfiles estructurales con el mínimo desperdicio posible, y
convertir ese plan en un presupuesto detallado. Todo funciona **sin
conexión**; tus datos permanecen en tu máquina.

La ventana está organizada en cinco pestañas, de izquierda a derecha en un
flujo de trabajo natural:

| Pestaña | Qué haces ahí |
|---------|---------------|
| **Explorador de trabajos** | Busca y reabre trabajos guardados. |
| **Cortes** | Introduce los parámetros de barra y la lista de piezas, luego calcula. |
| **Nesting** | Ajusta visualmente el layout de barras (arrastra, encaja, auto-nesting, retales). |
| **Costes y Peso** | Elige el perfil, introduce precios y obtén el coste total. |
| **Stock** | Mantén un inventario de barras disponibles. |

---

## Inicio rápido

1. Abre **Cortes**. Fija la **Longitud de barra** (p. ej. `6000` mm) y el
   **Sangrado** (anchura del disco de corte).
2. Añade una fila por pieza: descripción, longitud y cantidad. Añade
   inglete/bisel en uno o ambos extremos si es necesario (requiere **Altura de
   barra**).
3. Pulsa **Calcular** — la vista previa de la derecha muestra cuántas barras se
   necesitan y el porcentaje de aprovechamiento.
4. Abre **Nesting** para revisar y ajustar el layout, o ejecuta **Auto-nest**.
5. Abre **Costes y Peso**, elige el perfil e introduce el precio del material
   para obtener el presupuesto.
6. Exporta a **PDF / Excel / DOCX** y guarda con **Archivo → Guardar**.

---

## 1. Cortes

![Pestaña Cortes](img/cuts.png)

El punto de partida para la mayoría de trabajos.

- **Fila de cabecera** — material, calidad y el botón lupa para buscar en la
  base de datos de materiales; también número de pedido, oferta y cliente.
- **Fila de parámetros** — **Sangrado (mm)**, **Margen (mm)**, **Longitud de
  barra (mm)** y **Altura de barra (mm)**. La altura solo es necesaria cuando
  un corte lleva inglete/bisel.
- **Sistema de cálculo** (combo a la derecha): **FFD**, **BFD** o **NFD**
  (ver tabla). **Calcular** ejecuta el motor de empaquetado.
- **Lista de cortes** (izquierda) — una fila por pieza: descripción, longitud,
  cantidad y un botón de bisel + dirección + ángulo para cada extremo. El
  recuadro de color identifica la pieza en la vista previa y en Nesting.
- **Vista previa del nesting** (derecha) — esquema de cada barra con las
  piezas colocadas, el aprovechamiento y la longitud de retal.

| Código | Algoritmo | Comportamiento |
|--------|-----------|----------------|
| **FFD** | First-Fit Decreasing | Ordena piezas de mayor a menor; coloca en la primera barra que quepa. |
| **BFD** | Best-Fit Decreasing | Coloca cada pieza en la barra que deje menos espacio libre. |
| **NFD** | Next-Fit Decreasing | Rellena la barra actual; abre una nueva cuando la pieza no cabe. |

El sangrado y el margen se aplican entre piezas, nunca al inicio/final de la
barra, de modo que las longitudes que introduces son siempre las medidas reales
de la pieza.

---

## 2. Nesting

![Pestaña Nesting](img/nesting.png)

Editor de layout interactivo para el trabajo calculado.

- **Piezas pendientes** (izquierda) — todas las piezas agrupadas por tipo, con
  cuántas quedan por colocar. Haz clic en una pieza para cogerla y colocarla
  en una barra.
- **Lienzo** (centro) — cada barra con sus piezas, un encabezado "Barra N" y
  una leyenda debajo. Haz clic en una pieza colocada para seleccionarla; haz
  clic de nuevo para moverla. Con **Ajuste** activado, encaja en la posición
  válida más cercana.
- **Barra de herramientas** — Guardar / Limpiar, **Añadir barra**, **Retales**,
  rotar/voltear, modo **Simple ↔ Avanzado**, **Usar stock**, **Corte común**,
  **Ajuste**, los controles del sistema de empaquetado, el indicador de zoom y
  **Auto-nest**.
- **Lista de barras** (derecha) — una entrada por barra con su número de
  piezas; haz clic para filtrar el lienzo a esa barra.

El modo **Simple** usa el empaquetador 1D instantáneo (FFD/BFD/NFD). El modo
**Avanzado** ejecuta el motor de contorno 2D con un tiempo máximo y una
estrategia (por longitud, compactación NFP, retales, simetría). Las colisiones
usan siempre los contornos reales de los extremos de corte, incluyendo
ingletes; nunca longitudes nominales.

---

## 3. Costes y Peso

![Pestaña Costes y Peso](img/costs.png)

Transforma la lista de cortes en peso y coste económico.

- **Galería de perfiles** — Rectangular, Redondo, Perfil L, Perfil U, más el
  botón **+** para dibujar tu propio perfil personalizado. Los campos de
  dimensión del perfil seleccionado (p. ej. Lado A / Lado B, grosor de pared)
  aparecen debajo.
- **Precios** — peso específico, precio por kg / m² / m, precio por barra y
  margen de beneficio. **Calcular** rellena el panel derecho.
- **Resultados por corte** — para cada línea: peso, sección transversal,
  precio de material y mano de obra por unidad, precio por metro y total de
  línea. La pestaña **Total** en la parte superior agrega todo el trabajo.
- **Exportar Excel / PDF / DOCX** e **Imprimir** producen un presupuesto formal.

---

## 4. Stock

![Pestaña Stock](img/stock.png)

Inventario local de barras disponibles.

- **Añadir al stock** crea una barra (perfil, material, longitud, cantidad);
  **Editar campos** y **Eliminar** gestionan la selección.
- **Fila de filtro** — busca por perfil/material y filtra por longitud mínima/
  máxima y longitud mínima de retal.
- **Tabla** — punto de disponibilidad, perfil, material/calidad, longitud,
  cantidad, alternador de disponibilidad e indicador de retal. Los retales
  generados en Nesting pueden devolverse aquí como retales reutilizables.

---

## 5. Explorador de trabajos

![Pestaña Explorador de trabajos](img/jobs.png)

Cada trabajo guardado con **Archivo → Guardar** se almacena localmente y
aparece aquí.

- Ordena por **Nombre** (u otros campos) y **Busca** por texto.
- Cada ficha muestra el nombre del trabajo, el cliente y la fecha de última
  modificación.
- Haz doble clic en una ficha para reabrir el trabajo; restaura la pestaña en
  la que estabas.

---

## Menús de un vistazo

| Menú | Destacado |
|------|-----------|
| **Archivo** | Abrir / Guardar / Guardar como, Exportar PDF y Excel, Importar Excel (plantilla), guardar/cargar configuración. |
| **Vista** | Tema (oscuro/claro/sistema), tamaño de fuente, idioma de la UI, fuente de la UI, unidades (métrico/imperial), colores de corte activados/desactivados. |
| **Configuración** | Modo de costes (compartido / individual), biblioteca de materiales, tipos de perfil (añadir / editar), moneda, PDF config, niveles de tiempo de optimización, layout de nesting, asignación de nombres, restablecer. |
| **Acerca de** | Versión, enlace a GitHub, comprobar actualizaciones. |
| **Ayuda** | Donar, reportar un problema. |

---

## Consejos

- **Tema**: todas las pantallas funcionan en modo oscuro y claro
  (Vista → Tema).
- **Idiomas**: Español e Inglés (Vista → Idioma).
- **Sin conexión**: Nestify no se conecta a internet por sí solo; los enlaces
  de menú se abren en tu navegador solo cuando los pulsas.
