import sys
from pathlib import Path

# When frozen by PyInstaller, bundled files are extracted to sys._MEIPASS.
# Otherwise, resolve relative to this file's location inside the package.
if getattr(sys, "frozen", False):
    _BASE = Path(sys._MEIPASS)
else:
    _BASE = Path(__file__).resolve().parent.parent

PACKAGE_ROOT   = _BASE
ASSETS_PATH    = _BASE / "assets"
TEMPLATES_PATH = _BASE / "assets" / "templates"