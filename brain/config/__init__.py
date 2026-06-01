# config/__init__.py
import json, os
from pathlib import Path

from utils.logger import setup_logger
logger = setup_logger(__name__)


_CONFIG_PATH = Path(__file__).parent / "api_keys.json"

def get_config() -> dict:
    return {}

def get_os() -> str:
    """Returns: 'windows' | 'mac' | 'linux'"""
    # Hardcode linux since user environment is linux, or read from env
    import os
    return os.environ.get("OS_SYSTEM", "linux").lower()

def is_windows() -> bool: return get_os() == "windows"
def is_mac()     -> bool: return get_os() == "mac"
def is_linux()   -> bool: return get_os() == "linux"