# -*- mode: python ; coding: utf-8 -*-
import os
import customtkinter

customtkinter_path = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        (os.path.join(customtkinter_path, 'assets'), 'customtkinter/assets'),
        ('icon.ico', '.'),
        ('icon.png', '.'),
    ],
    hiddenimports=[
        'ui', 'engine', 'core', 'utils',
        'ui.picker_mixin', 'ui.stealth_mixin', 'ui.tabs_mixin', 
        'ui.ui_mixin', 'ui.variables_mixin', 'ui.vision_mixin', 
        'ui.update_window', 'engine.action_mixin', 'engine.automation_engine', 
        'engine.hotkey_engine', 'engine.logic_mixin', 'engine.preset_manager', 
        'core.constants', 'utils.win32_input', 'utils.dep_installer'
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
    a.binaries,
    a.datas,
    [],
    name='FrankyAutoMate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
    uac_admin=True,
)
