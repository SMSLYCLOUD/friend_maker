# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect hidden imports for Playwright and other libs
hidden_imports = [
    'playwright',
    'customtkinter',
    'ollama',
    'app.database',
    'app.ui',
    'app.ai',
    'app.platforms',
    'app.automation',
    'app.utils',
    'sqlite3',
    'pydantic',
    'cryptography'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app', 'app'), # Include the source if needed, or rely on pure analysis.
        # Usually better to rely on imports, but including assets is key.
        # ('assets', 'assets'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SocialGrowthAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Set to True to debug if it crashes on start
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico'
)
