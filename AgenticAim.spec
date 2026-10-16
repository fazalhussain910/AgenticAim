# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/THE AGENTIC STATE (AgenticAim)/AgenticAim', 'AgenticAim'), ('C:/THE AGENTIC STATE (AgenticAim)/frontend/dist', 'frontend/dist')],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.lifespans', 'uvicorn.lifespans.on', 'webview', 'webview.platforms.winforms', 'webview.platforms.edgechromium', 'clr', 'pythonnet', 'psutil', 'pynput', 'mss', 'cv2', 'qdrant_client', 'langgraph', 'langchain_core', 'langchain_openai'],
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
    name='AgenticAim',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AgenticAim',
)
