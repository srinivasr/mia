"""
utils/config.py — Shared helpers used across all action modules.

Centralises `base_dir()`, `load_config()`, and `get_os()` so each action
file doesn't have to copy-paste them.
"""
import json
import sys
from pathlib import Path


def base_dir() -> Path:
    """Return the brain package root (works both frozen and from source)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # This file lives at brain/utils/config.py → parent.parent = brain/
    return Path(__file__).resolve().parent.parent


_BASE = base_dir()
_CONFIG_PATH = _BASE / "config" / "hardware_config.json"


def load_config() -> dict:
    """Load hardware_config.json, returning {} on any error."""
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_os() -> str:
    """Return 'linux', 'mac', or 'windows' from config or sys.platform."""
    if os_sys := load_config().get("os_system"):
        return os_sys.lower()
    if sys.platform == "darwin":
        return "mac"
    return "linux" if sys.platform.startswith("linux") else "windows"
