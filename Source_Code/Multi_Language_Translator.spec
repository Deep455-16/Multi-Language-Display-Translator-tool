# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_all

bs4_datas,    bs4_binaries,    bs4_hiddenimports    = collect_all('beautifulsoup4')
dt_datas,     dt_binaries,     dt_hiddenimports     = collect_all('deep_translator')

a = Analysis(
    ['Multi_Language_Translator.py'],
    pathex=[],
    binaries=[] + bs4_binaries + dt_binaries,
    datas=[] + bs4_datas + dt_datas,
    hiddenimports=[
        'deepl',
        'requests',
        'urllib3',
        'bs4',
        'bs4.builder',
        'bs4.builder._htmlparser',
    ] + bs4_hiddenimports + dt_hiddenimports,
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
