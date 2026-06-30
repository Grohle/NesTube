## Nestify 1.0.0-pre-alpha.1

**First public pre-release of Nestify — bar, tube, and profile cutting optimizer for metal fabrication shops.**

> **Status:** pre-alpha. The core works, but interfaces and file formats may still change before 1.0.0.

### What's in this release

- Three bin-packing algorithms (FFD, BFD, NFD) with kerf and end-margin support
- Interactive nesting canvas with miter/bevel geometry and manual adjustment
- Costs & Weight tab — weight, cost per piece, labour, and total job cost
- Profile & tube library (IPE, HEA, UPN, SHS, CHS, angles, …) plus user-defined custom sections
- Stock inventory with offcut reuse and serial traceability
- Export to PDF, Excel, Word, and DXF
- All data in one local SQLite database — relocatable to a shared drive, with automatic rolling backups on launch
- English and Spanish UI; dark and light themes
- Fully offline — no accounts, no telemetry

### Installation

**Windows (installer):** run `Nestify-1.0.0-pre-alpha.1-setup.exe`.  
⚠️ SmartScreen may warn that the binary is unsigned — choose **More info → Run anyway**.

**Windows (portable):** extract `Nestify-1.0.0-pre-alpha.1-windows.zip` and run `Nestify.exe`.

**Linux (portable):** extract `Nestify-1.0.0-pre-alpha.1-linux.tar.gz` and run `./Nestify/Nestify`.  
Requires: `libxkbcommon-x11-0 libxcb-xkb1 libxcb-cursor0 libegl1`  
On Ubuntu/Debian: `sudo apt install libxkbcommon-x11-0 libxcb-xkb1 libxcb-cursor0 libegl1`

**From source:** see [README](README.md).

### Known limitations

- This is a pre-alpha. Some edge cases and UI rough edges remain.
- The `.nestjob` file format and database schema may change before 1.0.0.

### Reporting issues

Open an issue at [github.com/Grohle/Nestify/issues](https://github.com/Grohle/Nestify/issues).

---

## Nestify 1.0.0-pre-alpha.1 (Español)

**Primera pre-versión pública de Nestify — optimizador de corte de barras, tubos y perfiles para talleres metálicos.**

> **Estado:** pre-alpha. El núcleo funciona, pero las interfaces y formatos de archivo pueden cambiar antes de la versión 1.0.0.

### Qué incluye esta versión

- Tres algoritmos de empaquetado (FFD, BFD, NFD) con soporte de kerf y margen
- Lienzo de nesting interactivo con geometría de inglete/bisel y ajuste manual
- Pestaña de Costes y Peso — peso, coste por pieza, mano de obra y coste total
- Biblioteca de perfiles y tubos (IPE, HEA, UPN, SHS, CHS, angulares, …) más secciones personalizadas
- Inventario de stock con reutilización de retales y trazabilidad por número de serie
- Exportación a PDF, Excel, Word y DXF
- Todos los datos en una única base de datos SQLite local — relocalizable, con copias de seguridad automáticas
- Interfaz en español e inglés; temas oscuro y claro
- Totalmente sin conexión — sin cuentas ni telemetría

### Instalación

**Windows (instalador):** ejecuta `Nestify-1.0.0-pre-alpha.1-setup.exe`.  
⚠️ SmartScreen puede avisar de que el binario no está firmado — elige **Más información → Ejecutar de todas formas**.

**Windows (portable):** extrae `Nestify-1.0.0-pre-alpha.1-windows.zip` y ejecuta `Nestify.exe`.

**Linux (portable):** extrae `Nestify-1.0.0-pre-alpha.1-linux.tar.gz` y ejecuta `./Nestify/Nestify`.  
Dependencias: `libxkbcommon-x11-0 libxcb-xkb1 libxcb-cursor0 libegl1`  
En Ubuntu/Debian: `sudo apt install libxkbcommon-x11-0 libxcb-xkb1 libxcb-cursor0 libegl1`

**Desde el código fuente:** ver [README](README.md).

### Limitaciones conocidas

- Es una pre-alpha; quedan algunos casos límite y aspectos de la interfaz por pulir.
- El formato `.nestjob` y el esquema de la base de datos pueden cambiar antes de la versión 1.0.0.

### Reportar problemas

Abre un issue en [github.com/Grohle/Nestify/issues](https://github.com/Grohle/Nestify/issues).
