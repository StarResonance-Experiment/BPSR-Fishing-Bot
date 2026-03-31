"""Persist user config to/from a JSON file next to the exe (or project root)."""
import json
import sys
from pathlib import Path


def _user_data_dir() -> Path:
    """Writable directory beside the exe (frozen) or project root (dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[3]


def _config_path() -> Path:
    return _user_data_dir() / "config.json"


def templates_base_user_dir() -> Path:
    """Writable root templates folder (never inside _MEIPASS)."""
    return _user_data_dir() / "templates"


def templates_user_dir(width: int, height: int) -> Path:
    """Writable templates folder for a resolution (never inside _MEIPASS)."""
    return templates_base_user_dir() / f"{width}_{height}"


def rois_save_path(width: int, height: int) -> Path:
    """Writable path for a resolution's rois.json (never inside _MEIPASS)."""
    return templates_user_dir(width, height) / "rois.json"


def save_config(data: dict) -> None:
    path = _config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_rois(path: Path, data: dict) -> None:
    """Save ROI dict to the given rois.json path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_config() -> dict | None:
    """Returns the saved config dict, or None if no file exists / file is corrupt."""
    path = _config_path()
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
