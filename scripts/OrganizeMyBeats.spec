# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Organize My Beats macOS app."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent
ENTRY = str(ROOT / "src" / "organize_my_beats" / "mac_app.py")
ICON = str(ROOT / "assets" / "AppIcon.icns")

pyqt_datas, pyqt_binaries, pyqt_hiddenimports = collect_all("PyQt5")
mutagen_datas, mutagen_binaries, mutagen_hiddenimports = collect_all("mutagen")

a = Analysis(
    [ENTRY],
    pathex=[str(ROOT / "src")],
    binaries=pyqt_binaries + mutagen_binaries,
    datas=pyqt_datas + mutagen_datas,
    hiddenimports=[
        "organize_my_beats",
        "organize_my_beats.advanced_gui",
        "organize_my_beats.organize_my_beats",
        "PyQt5.sip",
        *pyqt_hiddenimports,
        *mutagen_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Organize My Beats",
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
    icon=ICON if Path(ICON).exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Organize My Beats",
)

app = BUNDLE(
    coll,
    name="Organize My Beats.app",
    icon=ICON if Path(ICON).exists() else None,
    bundle_identifier="com.shaheerislam.organizemybeats",
    info_plist={
        "CFBundleName": "Organize My Beats",
        "CFBundleDisplayName": "Organize My Beats",
        "CFBundleShortVersionString": "1.0",
        "CFBundleVersion": "1.0.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.13.0",
        "NSRequiresAquaSystemAppearance": False,
    },
)
