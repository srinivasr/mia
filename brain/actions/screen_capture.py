import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    import mss
    import mss.tools
    _MSS = True
except ImportError:
    _MSS = False

try:
    import PIL.Image
    _PIL = True
except ImportError:
    _PIL = False

from utils.logger import setup_logger
logger = setup_logger(__name__)

_IMG_MAX_W = 640
_IMG_MAX_H = 360
_JPEG_Q    = 60

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

_BASE        = _base_dir()
_CONFIG_PATH = _BASE / "config" / "hardware_config.json"

def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _get_os() -> str:
    if os_sys := _load_config().get("os_system"):
        return os_sys.lower()

    if sys.platform == "darwin":
        return "mac"
    return "linux" if sys.platform.startswith("linux") else "windows"

def _compress(img_bytes: bytes, source_format: str = "PNG") -> tuple[bytes, str]:
    if not _PIL:
        return img_bytes, f"image/{source_format.lower()}"

    try:
        img = PIL.Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img.thumbnail((_IMG_MAX_W, _IMG_MAX_H), PIL.Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=_JPEG_Q, optimize=False)
        return buf.getvalue(), "image/jpeg"
    except Exception as e:
        logger.exception("Operation failed")
        return img_bytes, f"image/{source_format.lower()}"

def capture_screen() -> tuple[bytes, str]:
    if _get_os() == "linux" and os.environ.get("XDG_SESSION_TYPE") == "wayland":
        try:
            result = subprocess.run(
                ["gdbus", "call", "--session", "--dest", "org.gnome.Shell.Screenshot", 
                 "--object-path", "/org/gnome/Shell/Screenshot", "--method", "org.gnome.Shell.Screenshot.Screenshot", 
                 "true", "false", "/tmp/mia_screenshot.png"],
                capture_output=True, text=True, check=True
            )
            match = re.search(r"'(.*?)'", result.stdout)
            if match:
                filepath = match.group(1)
                with open(filepath, "rb") as f:
                    img_bytes = f.read()
                try:
                    os.remove(filepath)
                except Exception:
                    pass
                return _compress(img_bytes, "PNG")
        except Exception as e:
            logger.exception("Operation failed")

    if not _MSS:
        raise RuntimeError("mss is not installed. Run: pip install mss")

    with mss.mss() as sct:
        monitors = sct.monitors          # [0] = all combined, [1..n] = real screens
        target   = monitors[1] if len(monitors) > 1 else monitors[0]
        shot     = sct.grab(target)
        png      = mss.tools.to_png(shot.rgb, shot.size)

    return _compress(png, "PNG")
