import os
import sys
from pathlib import Path
from dotenv import load_dotenv, set_key

from utils.logger import setup_logger
logger = setup_logger(__name__)


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR    = get_base_dir()
# The .env is stored at the root of the mia_n_eve project
ENV_FILE = BASE_DIR.parent / ".env"

# Load the .env file automatically
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)

def ensure_config_dir() -> None:
    pass

def config_exists() -> bool:
    return ENV_FILE.exists()

def save_api_keys(gemini_api_key: str) -> None:
    ENV_FILE.touch(exist_ok=True)
    set_key(str(ENV_FILE), "GEMINI_API_KEY", gemini_api_key.strip())
    # Ensure it's loaded into the current process environment too
    os.environ["GEMINI_API_KEY"] = gemini_api_key.strip()

def load_api_keys() -> dict:
    # Maintain backwards compatibility for any dict-based retrievals
    return {
        "gemini_api_key": os.environ.get("GEMINI_API_KEY")
    }

def get_gemini_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY")

def is_configured() -> bool:
    key = get_gemini_key()
    return bool(key and len(key) > 15)