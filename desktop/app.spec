# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the desktop build (one-folder, windowed)."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

REPO = Path(SPECPATH).resolve().parent  # noqa: F821 - provided by PyInstaller
BACKEND = REPO / "backend"
DIST_DIR = REPO / "web" / "dist"

if not DIST_DIR.is_dir():
    raise SystemExit("缺少 web/dist，先在 web/ 目录执行 npm run build")

datas = [
    (str(BACKEND / "config" / "rec.yaml"), "config"),
    (str(DIST_DIR), "web/dist"),
    (str(REPO / "desktop" / "version_info.txt"), "desktop"),
]

hiddenimports = (
    collect_submodules("app")
    + collect_submodules("uvicorn")
    + ["wx.html2", "sqlalchemy.dialects.sqlite"]
)

a = Analysis(  # noqa: F821
    [str(REPO / "desktop" / "main.py")],
    pathex=[str(BACKEND), str(REPO / "desktop")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pandas", "scipy", "sklearn", "pytest", "httpx"],
    noarchive=False,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GexingTuijian",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    version=str(REPO / "desktop" / "version_info.txt"),
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="GexingTuijian",
)
