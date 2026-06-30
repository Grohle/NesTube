# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — NesTube (PySide6 / Qt) (PySide6 / Qt)
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

pyside_datas, pyside_binaries, pyside_hidden = collect_all("PySide6")

font_src = os.path.join(ROOT, "nestube", "fonts")
assets_src = os.path.join(ROOT, "nestube", "assets")
extra_datas = [
    (font_src, "nestube/fonts"),
    (os.path.join(assets_src, "logo.png"), "nestube/assets"),
    (os.path.join(assets_src, "icon.png"), "nestube/assets"),
    (os.path.join(assets_src, "icon.ico"), "nestube/assets"),
    (os.path.join(assets_src, "icons"), "nestube/assets/icons"),
]

hidden = list(pyside_hidden)
hidden += collect_submodules("nestube")
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
    binaries=pyside_binaries,
    datas=pyside_datas + extra_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "test", "tests", "customtkinter", "tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

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
