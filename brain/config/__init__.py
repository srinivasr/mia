# config/__init__.py
import os
import sys
from utils.config import load_config

def get_config() -> dict:
    return load_config()

def get_os() -> str:
    """Returns: 'windows' | 'mac' | 'linux'"""
    if os_sys := os.environ.get("OS_SYSTEM"):
        return os_sys.lower()
    if os_sys := load_config().get("os_system"):
        return os_sys.lower()
    if sys.platform == "darwin":
        return "mac"
    return "linux" if sys.platform.startswith("linux") else "windows"

def is_windows() -> bool: return get_os() == "windows"
def is_mac()     -> bool: return get_os() == "mac"
def is_linux()   -> bool: return get_os() == "linux"