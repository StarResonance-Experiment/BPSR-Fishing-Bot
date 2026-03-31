# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for BPSR Fishing Bot GUI
# Run with:  pyinstaller build.spec --clean

block_cipher = None

a = Analysis(
    ["gui.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Resolution-specific template sets + their rois.json
        ("src/fishbot/assets/templates/1280_720",  "assets/templates/1280_720"),
        ("src/fishbot/assets/templates/1920_1080", "assets/templates/1920_1080"),
        ("src/fishbot/assets/templates/2560_1440", "assets/templates/2560_1440"),
    ],
    hiddenimports=[
        # PyQt6
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        # OpenCV
        "cv2",
        # Screen capture
        "mss",
        "mss.windows",
        # Input
        "pyautogui",
        "pyscreeze",
        "mouseinfo",
        "keyboard",
        # Stdlib extras sometimes missed by the hook
        "multiprocessing.pool",
        "multiprocessing.managers",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused heavy packages to keep the exe smaller
        "matplotlib",
        "numpy.distutils",
        "tkinter",
        "unittest",
        "xmlrpc",
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="BPSR-Fishing-Bot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # compress with UPX if available (smaller file)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # no black console window behind the GUI
    uac_admin=True,     # request administrator elevation on launch
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="src/fishbot/assets/app.ico",  # uncomment and add an .ico to use a custom icon
)
