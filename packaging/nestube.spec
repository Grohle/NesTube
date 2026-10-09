# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — NesTube (PySide6 / Qt)
# The main window is the HTML interface (nestube/web) in Qt WebEngine.
#
# Only the Qt modules NesTube imports are bundled; PyInstaller's PySide6 hooks
# add each one's libraries, plugins and data (QtWebEngineProcess, its .pak
# resources and locales included). collect_all("PySide6") used to ship every
# Qt module — Quick 3D, Multimedia with ffmpeg, Designer, PDF, … — tripling
# the download.
import os

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

QT_MODULES = [
    "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "PySide6.QtSvg",
    "PySide6.QtNetwork", "PySide6.QtPrintSupport",
    "PySide6.QtWebChannel", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
]
# Qt modules nothing imports at runtime (dev tools, QML, 3D, media, …).
QT_EXCLUDES = [
    "PySide6.QtDesigner", "PySide6.QtUiTools", "PySide6.QtHelp", "PySide6.QtTest",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras", "PySide6.QtQuick3D",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtSpatialAudio",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs", "PySide6.QtGraphsWidgets",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtSerialPort", "PySide6.QtSerialBus", "PySide6.QtSensors", "PySide6.QtTextToSpeech",
    "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtStateMachine", "PySide6.QtSql",
    "PySide6.QtHttpServer", "PySide6.QtWebSockets", "PySide6.QtLocation",
    "PySide6.QtQuickControls2", "PySide6.QtQuickWidgets", "PySide6.QtWebEngineQuick", "PySide6.QtWebView",
]

font_src = os.path.join(ROOT, "nestube", "fonts")
web_src = os.path.join(ROOT, "nestube", "web")
assets_src = os.path.join(ROOT, "nestube", "assets")
extra_datas = [
    (font_src, "nestube/fonts"),
    (os.path.join(assets_src, "logo.png"), "nestube/assets"),
    (os.path.join(assets_src, "icon.png"), "nestube/assets"),
    (os.path.join(assets_src, "icon.ico"), "nestube/assets"),
    (os.path.join(assets_src, "icons"), "nestube/assets/icons"),
    # HTML interface: nestube/ui_web/window.py loads nestube/web/index.html
    (web_src, "nestube/web"),
]

hidden = list(QT_MODULES)
# The Qt Designer plugin package is a developer tool, never imported by the app.
hidden += collect_submodules("nestube", filter=lambda name: not name.startswith("nestube.ui_qt.designer"))
hidden += [
    "pandas",
    "openpyxl",
    "PIL",
    "docx",
    "ezdxf",
    "fpdf",
    "shapely",
    "numpy",
    "pyclipper",
]

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=extra_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "test", "tests", "customtkinter", "tkinter", "nestube.ui_qt.designer"] + QT_EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── Trim what the Qt hooks pull in but NesTube never loads ────────────────────
# QtWebEngineCore links Qt Quick/QML, so the hooks also collect every QML
# module and its libraries (Quick 3D, Controls styles, Graphs, PDF, …) plus
# ffmpeg. The app has no QML at all: keep the libraries WebEngine links
# (Quick, Qml, QmlModels, QmlWorkerScript, QmlMeta, QuickWidgets, Positioning)
# and drop the rest — by Qt module name, so it holds on Windows (Qt6X.dll),
# Linux (libQt6X.so) and macOS (QtX.framework).
import re  # noqa: E402

_QT_DROP = re.compile(
    r"(?:^|[/\\])(?:lib)?Qt6?(?:"
    r"3D\w*|Quick3D\w*|QuickControls2\w*|QuickDialogs2\w*|QuickTemplates2|QuickLayouts|"
    r"QuickParticles|QuickShapes\w*|QuickEffects|QuickTimeline\w*|QuickVectorImage\w*|Labs\w*|"
    r"Graphs\w*|Charts\w*|DataVisualization\w*|Multimedia\w*|SpatialAudio|Pdf\w*|ShaderTools|"
    r"Location|RemoteObjects\w*|Scxml\w*|StateMachine\w*|Sensors\w*|TextToSpeech|Test|"
    r"WebEngineQuick\w*|WebView\w*|VirtualKeyboard\w*|Designer\w*|Help|UiTools|Bluetooth|Nfc|"
    r"SerialPort|SerialBus|Sql|Quick3DPhysics\w*|Concurrent|Xml|Wayland\w*|WlShell\w*|"
    r"QmlLocalStorage|QmlXmlListModel|QuickTest)"
    r"(?:\.|d?\.dll|\.framework|$)")
_FFMPEG = re.compile(r"(?:^|[/\\])(?:lib)?(?:avcodec|avformat|avutil|swresample|swscale)[-.\d]*\.(?:so|dll|dylib)")
_WEBENGINE_LOCALES_KEEP = ("en-US.pak", "es.pak", "es-419.pak")


def _keep(entry) -> bool:
    dest = entry[0].replace("\\", "/")
    if "/Qt/qml/" in dest or dest.startswith("PySide6/qml/") or "/plugins/qmltooling/" in dest:
        return False
    if "/plugins/wayland-" in dest or "/plugins/egldeviceintegrations/" in dest:
        return False
    # Plugins whose libraries are dropped above: they would fail to load.
    # (Linux runs on xcb/X11, which Wayland desktops serve through XWayland.)
    if re.search(r"/plugins/(platforms/(lib)?qwayland|platforminputcontexts/(lib)?qtvirtualkeyboard|"
                 r"imageformats/(lib)?qpdf|position/(lib)?qtposition_nmea)", dest):
        return False
    if "qtwebengine_locales/" in dest and not dest.endswith(_WEBENGINE_LOCALES_KEEP):
        return False
    if "/translations/" in dest and dest.endswith(".qm"):
        base = dest.rsplit("/", 1)[1]
        if not re.search(r"_(es|en)(_[A-Z]{2})?\.qm$", base):
            return False
    return not (_QT_DROP.search(dest) or _FFMPEG.search(dest))


a.binaries = [e for e in a.binaries if _keep(e)]
a.datas = [e for e in a.datas if _keep(e)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NesTube",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "nestube", "assets", "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="NesTube",
)
