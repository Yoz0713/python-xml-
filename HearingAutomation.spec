# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# Get Flet path dynamically
try:
    import flet
    flet_path = os.path.dirname(flet.__file__)
except:
    flet_path = ''

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('src', 'src'),
    ],
    hiddenimports=[
        'flet',
        'flet_core',
        'flet_runtime',
        'playwright',
        'playwright.sync_api',
        'playwright.async_api',
        'watchdog',
        'watchdog.observers',
        'watchdog.events',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Add flet data if found
if flet_path and os.path.exists(flet_path):
    a.datas += [(os.path.join('flet', f), os.path.join(flet_path, f), 'DATA') 
                for f in os.listdir(flet_path) if not f.startswith('__')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HearingAutomation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
