# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for a native, standalone build on the machine that runs it.
# The installers run it automatically; manual use:
#     pip install . "pyinstaller>=6.11"
#     pyinstaller --noconfirm packaging/PasswordManager.spec
# Output in dist/: "Password Manager.app" on macOS, PasswordManager.exe on Windows,
# PasswordManager on Linux.
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

from password_manager import __version__

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    datas=collect_data_files("password_manager"),  # the GUI artwork
    # mysql-connector imports its auth plugins and error locales dynamically.
    hiddenimports=collect_submodules("mysql.connector"),
    excludes=["pytest", "PyInstaller"],
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="PasswordManager", console=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="PasswordManager")
    app = BUNDLE(
        coll,
        name="Password Manager.app",
        bundle_identifier="io.github.tgvenomyt.passwordmanager",
        version=__version__,
        info_plist={"CFBundleDisplayName": "Password Manager", "NSHighResolutionCapable": True,
                    "LSMinimumSystemVersion": "11.0"},
    )
else:
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="PasswordManager",
        console=sys.platform != "win32",  # Windows: no console window behind the GUI
        upx=False,
    )
