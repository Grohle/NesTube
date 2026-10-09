## NesTube 0.1.0

**First release with the new interface: a cleaner, modern window on top of the same nesting engine.**

> **Status:** early release (0.x). The core works and is tested, but interfaces and file formats may still change before 1.0.

### What's new

- **New interface.** NesTube now opens a modern, Figma-style window: a top bar with the six tabs (Jobs, Cuts, Nesting, Costs, Profiles, Stock), panels on the left and right, a floating tool bar on the canvas, and dark and light themes.
- **Same engine underneath.** Every tab runs the same logic as before: collision checks with the real piece contours (miters included), snap, auto-nest, cut lists, costs, the profile catalogue, stock and jobs. Shortcuts are unchanged: Ctrl+Z / Ctrl+Y, Ctrl+Q / Ctrl+E to rotate, Ctrl+H / Ctrl+A to flip, Delete, Esc and Ctrl+S.
- **Profile image viewer.** Profile pictures open full size with zoom, so you can compare sections without leaving the tab.
- **AutoCAD-style drawing module** for custom profiles: a ribbon, a command line (L, REC, C, A, TR…), typed lengths and angles, object snaps (endpoint, midpoint, centre), ORTHO, GRID and dynamic input on the status bar.
- **New logo.**
- **The classic interface is still there.** Start with `--classic` (or set `NESTUBE_CLASSIC=1`) to open the previous Qt window.

### Fixes

- **Moving a piece back to where it was.** A piece grabbed by its middle used to jump so its left end sat under the cursor. Dropping it "back in place" then sent it to another slot, or to the end of the bar. The grab point now stays under the cursor and the piece returns to its own slot.
- **Cutting height.** After opening a job, the Nesting tab could show one cutting height (for example 40 mm) while laying pieces out with another (80 mm). Both now use the height that is shown.
- **Ctrl+click** on a piece selects it again (it used to pan the canvas).
- Pieces at the start of a bar return to their exact position instead of 1.5 mm to the right.

### Testing

The new interface was tested by nesting pieces, then picking them up, rotating them in the air and dropping them on the same bar, on another bar and back into their own slot. This ran with and without miters, margin and common cut, and was repeated through the real window with a real mouse. There were no overlaps and no lost pieces. These checks are now part of the automated test suite.

### Installation

**Windows (installer):** run `NesTube-0.1.0-setup.exe`.  
⚠️ SmartScreen may warn that the program is unsigned. Choose **More info → Run anyway**.

**Windows (portable):** extract `NesTube-0.1.0-windows.zip` and run `NesTube.exe`.

**Linux (portable):** extract `NesTube-0.1.0-linux.zip` and run `./NesTube/NesTube`.  
On Ubuntu/Debian, install the libraries it needs first:  
`sudo apt install libxkbcommon-x11-0 libxcb-xkb1 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libegl1 libnss3 libxcomposite1 libxdamage1 libxrandr2 libxtst6 libasound2`

**macOS (portable):** extract `NesTube-0.1.0-macos.zip` and run `./NesTube/NesTube`.  
⚠️ The app is unsigned, so macOS blocks it the first time. Run `xattr -dr com.apple.quarantine NesTube`, or right-click the program and choose **Open**.

**From source:** see the [README](README.md).

### Known limitations

- The download is large (around 225 MB zipped on Linux) because it includes the web engine used to draw the interface.
- A few dialogs (choosing a material, saving a profile, export options) still open in the classic style.
- The `.nestjob` format and the database layout may change before 1.0.

### Reporting issues

Open an issue at [github.com/Grohle/NesTube/issues](https://github.com/Grohle/NesTube/issues).

---

## NesTube 0.1.0 (Español)

**Primera versión con la interfaz nueva: una ventana más limpia y moderna sobre el mismo motor de anidado.**

> **Estado:** versión temprana (0.x). El núcleo funciona y está probado, pero la interfaz y los formatos de archivo pueden cambiar antes de la 1.0.

### Novedades

- **Interfaz nueva.** NesTube abre ahora una ventana moderna, al estilo de Figma: barra superior con las seis pestañas (Jobs, Cortes, Anidado, Costes, Perfiles, Stock), paneles a izquierda y derecha, barra de herramientas flotante sobre el lienzo y temas oscuro y claro.
- **El mismo motor por debajo.** Cada pestaña usa la misma lógica de siempre: colisiones con el contorno real de las piezas (ingletes incluidos), imán, auto-anidado, lista de cortes, costes, catálogo de perfiles, stock y jobs. Los atajos no cambian: Ctrl+Z / Ctrl+Y, Ctrl+Q / Ctrl+E para rotar, Ctrl+H / Ctrl+A para voltear, Supr, Esc y Ctrl+S.
- **Visor de imágenes de perfiles.** Las fotos de los perfiles se abren a tamaño completo con zoom, para comparar secciones sin salir de la pestaña.
- **Módulo de dibujo al estilo AutoCAD** para perfiles a medida: cinta de herramientas, línea de comandos (L, REC, C, A, TR…), longitudes y ángulos tecleados, referencias a objetos (punto final, punto medio, centro), ORTO, REJILLA y entrada dinámica en la barra de estado.
- **Logo nuevo.**
- **La interfaz clásica sigue disponible.** Arranca con `--classic` (o define `NESTUBE_CLASSIC=1`) para abrir la ventana Qt anterior.

### Correcciones

- **Devolver una pieza a su sitio.** Al coger una pieza por el medio, saltaba para que su extremo izquierdo quedara bajo el cursor. Al soltarla "en su sitio" acababa en otro hueco o al final de la barra. Ahora el punto de agarre se queda bajo el cursor y la pieza vuelve a su hueco.
- **Altura de corte.** Tras abrir un trabajo, la pestaña Anidado podía mostrar una altura de corte (por ejemplo 40 mm) mientras colocaba las piezas con otra (80 mm). Ahora las dos usan la altura que se ve.
- **Ctrl+clic** sobre una pieza vuelve a seleccionarla (antes desplazaba el lienzo).
- Las piezas al principio de la barra vuelven a su posición exacta, no 1,5 mm a la derecha.

### Pruebas

La interfaz nueva se ha probado anidando piezas y después cogiéndolas, rotándolas en el aire y soltándolas en la misma barra, en otra y de vuelta en su hueco. Se hizo con y sin ingletes, margen y corte común, y se repitió en la ventana real con ratón real. No hubo solapes ni piezas perdidas. Estas comprobaciones forman ya parte de los tests automáticos.

### Instalación

**Windows (instalador):** ejecuta `NesTube-0.1.0-setup.exe`.  
⚠️ SmartScreen puede avisar de que el programa no está firmado. Elige **Más información → Ejecutar de todas formas**.

**Windows (portable):** extrae `NesTube-0.1.0-windows.zip` y ejecuta `NesTube.exe`.

**Linux (portable):** extrae `NesTube-0.1.0-linux.zip` y ejecuta `./NesTube/NesTube`.  
En Ubuntu/Debian, instala antes las librerías que necesita:  
`sudo apt install libxkbcommon-x11-0 libxcb-xkb1 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libegl1 libnss3 libxcomposite1 libxdamage1 libxrandr2 libxtst6 libasound2`

**macOS (portable):** extrae `NesTube-0.1.0-macos.zip` y ejecuta `./NesTube/NesTube`.  
⚠️ La aplicación no está firmada, así que macOS la bloquea la primera vez. Ejecuta `xattr -dr com.apple.quarantine NesTube`, o haz clic derecho sobre el programa y elige **Abrir**.

**Desde el código fuente:** ver el [README](README.md).

### Limitaciones conocidas

- La descarga es grande (unos 225 MB en zip en Linux) porque incluye el motor web que dibuja la interfaz.
- Algunos diálogos (elegir material, guardar perfil, opciones de exportación) todavía se abren con el estilo clásico.
- El formato `.nestjob` y la estructura de la base de datos pueden cambiar antes de la 1.0.

### Reportar problemas

Abre un issue en [github.com/Grohle/NesTube/issues](https://github.com/Grohle/NesTube/issues).
