# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Enterprise Text Compare.

This single spec file is used on all three platforms. PyInstaller always
builds a native executable for whatever OS it is *run* on, so producing
Windows/Linux/macOS builds means running:

    pyinstaller packaging/enterprise_text_compare.spec

...once on a Windows machine, once on a Linux machine, and once on each
macOS architecture (Intel and Apple Silicon) you want to support. There is
no cross-compilation. See README.md, section 20 ("PyInstaller Build
Instructions"), for full per-platform instructions.
"""
import sys
from pathlib import Path

block_cipher = None

# Resolve project root relative to this spec file (packaging/ is one level
# down from the project root).
PROJECT_ROOT = Path(SPECPATH).resolve().parent

# Icon files are optional: if you have not supplied resources/icons/app_icon.ico
# (Windows) or resources/icons/app_icon.icns (macOS), PyInstaller falls back to
# its default icon rather than failing the build. Drop your own icon files in
# place to brand the executable/bundle.
_ICO_PATH = PROJECT_ROOT / "resources" / "icons" / "app_icon.ico"
_ICNS_PATH = PROJECT_ROOT / "resources" / "icons" / "app_icon.icns"
WIN_ICON = str(_ICO_PATH) if _ICO_PATH.is_file() else None
MAC_ICON = str(_ICNS_PATH) if _ICNS_PATH.is_file() else None

a = Analysis(
    [str(PROJECT_ROOT / "run.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / "resources"), "resources"),
        (str(PROJECT_ROOT / "LICENSE"), "."),
        (str(PROJECT_ROOT / "THIRD_PARTY_NOTICES.md"), "."),
    ],
    hiddenimports=[
        "charset_normalizer",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Reduce bundle size: exclude Qt modules the application does not use.
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtNetwork",
        "PySide6.QtBluetooth",
        "PySide6.QtNfc",
        "PySide6.QtPositioning",
        "PySide6.QtSensors",
        "PySide6.QtSerialPort",
    ],
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
    name="EnterpriseTextCompare",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI application: no console window on Windows/macOS
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # macOS: set to 'x86_64', 'arm64', or 'universal2' as needed
    codesign_identity=None,
    entitlements_file=None,
    icon=WIN_ICON if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="EnterpriseTextCompare",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="EnterpriseTextCompare.app",
        icon=MAC_ICON,
        bundle_identifier="com.enterprisetextcompare.app",
        info_plist={
            "CFBundleName": "Enterprise Text Compare",
            "CFBundleDisplayName": "Enterprise Text Compare",
            "CFBundleVersion": "1.0.0",
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,  # allow dark mode
        },
    )
