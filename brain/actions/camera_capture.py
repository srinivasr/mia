import io
import os
import sys
import time
import threading
import json
from pathlib import Path
from typing import Optional

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import PIL.Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

import numpy as np

from utils.logger import setup_logger
from utils.config import base_dir, load_config, get_os as _get_os
logger = setup_logger(__name__)

IMG_MAX_W = 640
IMG_MAX_H = 360
JPEG_QUALITY = 60

_CONFIG_PATH = base_dir() / "config" / "hardware_config.json"

def _write_config(key: str, value) -> None:
    try:
        cfg = load_config()
        cfg[key] = value
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception as e:
        logger.debug(f"Failed to save config {key}: {e}")


def _get_cv2_backend() -> int:
    if not HAS_CV2:
        return 0
    sys_os = _get_os()
    if sys_os == "windows":
        return cv2.CAP_DSHOW    
    if sys_os == "mac":
        return cv2.CAP_AVFOUNDATION  
    return cv2.CAP_ANY

def _test_camera(index: int, backend: int, retries: int = 5) -> bool:
    if not HAS_CV2:
        return False
    
    cap = cv2.VideoCapture(index, backend)
    if not cap.isOpened():
        cap.release()
        return False
        
    for _ in range(retries):
        cap.read()
        
    ret, frame = cap.read()
    cap.release()
    
    return bool(ret and frame is not None and np.mean(frame) > 8)

def _find_camera() -> int:
    backend = _get_cv2_backend()
    logger.info("Detecting camera...")
    
    for i in range(5):
        if _test_camera(i, backend):
            logger.info(f"Using camera {i}")
            _write_config("camera_index", i)
            return i
            
    logger.info("No camera found, using 0")
    _write_config("camera_index", 0)
    return 0

_thread = None
_latest_frame: Optional[tuple[bytes, str]] = None
_lock = threading.Lock()
_listeners = []

def on_new_frame(cb):
    _listeners.append(cb)

def start_feed():
    global _thread
    if not HAS_CV2:
        return
        
    with _lock:
        if _thread and _thread.is_alive():
            return
        _thread = threading.Thread(target=_capture_loop, daemon=True)
        _thread.start()

def _capture_loop():
    global _latest_frame
    
    cfg = load_config()
    idx = int(cfg.get("camera_index", -1))
    if idx < 0:
        idx = _find_camera()
        
    cap = cv2.VideoCapture(idx, _get_cv2_backend())
    
    # Max out hardware settings
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 10000)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 10000)
    cap.set(cv2.CAP_PROP_FPS, 120)
    
    if not cap.isOpened():
        logger.error(f"Failed to open camera {idx}")
        return
        
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(1)
            continue
            
        try:
            # UI frame
            _, ui_buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            ui_bytes = ui_buf.tobytes()

            # AI frame (downscaled)
            if HAS_PIL:
                img = PIL.Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                img.thumbnail((IMG_MAX_W, IMG_MAX_H), PIL.Image.BILINEAR)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=JPEG_QUALITY)
                ai_bytes = buf.getvalue()
            else:
                small = cv2.resize(frame, (IMG_MAX_W, IMG_MAX_H), interpolation=cv2.INTER_AREA)
                _, ai_buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
                ai_bytes = ai_buf.tobytes()
                
            with _lock:
                _latest_frame = (ai_bytes, "image/jpeg")
                
            for cb in _listeners:
                try:
                    cb(ui_bytes)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            
        time.sleep(1/60)

def capture() -> tuple[bytes, str]:
    if not HAS_CV2:
        raise RuntimeError("cv2 not installed")

    start_feed()

    for _ in range(20):
        with _lock:
            if _latest_frame:
                return _latest_frame
        time.sleep(0.1)

    raise RuntimeError("Camera timed out")
