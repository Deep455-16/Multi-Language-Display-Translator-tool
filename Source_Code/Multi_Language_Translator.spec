# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['Multi_Language_Translator.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'deep_translator',
        'deep_translator.translators',
        'deep_translator.translators.google',
        'deep_translator.translators.mymemory',
        'deepl',
        'requests',
        'bs4',
        'urllib3',
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
    name='Multi_Language_Translator',
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
    icon=['app.ico'],
)
