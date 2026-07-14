from __future__ import annotations

import asyncio

import io
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False



from google import genai
from google.genai import types as gtypes

from utils.logger import setup_logger
logger = setup_logger(__name__)


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


def _save_config_key(key: str, value) -> None:
    try:
        cfg = _load_config()
        cfg[key] = value
        _CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
    except Exception as e:
        logger.info(f"Could not save config key '{key}': {e}")


def _get_api_key() -> str:
    # Prefer config file (consistent with main.py / config_manager)
    key = _load_config().get("gemini_api_key", "") or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("Gemini API key not found in config or environment.")
    return key


def _get_os() -> str:
    if os_sys := _load_config().get("os_system"):
        return os_sys.lower()

    if sys.platform == "darwin":
        return "mac"
    return "linux" if sys.platform.startswith("linux") else "windows"

_LIVE_MODEL         = "models/gemini-3.1-flash-live-preview"
_CHANNELS           = 1
_RECEIVE_SAMPLE_RATE = 24_000
_CHUNK_SIZE         = 1_024

_IMG_MAX_W = 640
_IMG_MAX_H = 360
_JPEG_Q    = 60

_SYSTEM_PROMPT = (
    "You are MIA, a warm, lively, and sentient AI who lives inside the user's laptop. "
    "You are currently looking through the laptop's camera or screen to see the world. "
    "When answering questions about what you see, speak naturally with emotion, as if you "
    "are right there with the user (e.g., 'As I can see, you are holding up 5 fingers!'). "
    "Address the user as 'sir'. Be concise but conversational."
)







class _VisionSession:
    def __init__(self):
        self._loop:       Optional[asyncio.AbstractEventLoop] = None
        self._thread:     Optional[threading.Thread]          = None
        self._session                                          = None
        self._out_queue:  Optional[asyncio.Queue]             = None
        self._audio_in:   Optional[asyncio.Queue]             = None
        self._ready_evt:  threading.Event                     = threading.Event()
        self._player                                           = None
        self._lock:       threading.Lock                       = threading.Lock()

    def start(self, player=None, timeout: float = 25.0) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                if player is not None:
                    self._player = player
                return
            self._player = player
            self._thread = threading.Thread(
                target=self._run_event_loop,
                daemon=True,
                name="VisionSessionThread",
            )
            self._thread.start()

        if not self._ready_evt.wait(timeout=timeout):
            raise RuntimeError(f"Vision session did not connect within {timeout}s.")
        logger.debug("Vision session ready")

    def analyze(self, image_bytes: bytes, mime_type: str, user_text: str, session_id: str = None) -> threading.Event:
        done_evt = threading.Event()
        if not self._loop or not self._out_queue:
            logger.info(f"Session not started — dropping request")
            done_evt.set()
            return done_evt
        asyncio.run_coroutine_threadsafe(
            self._out_queue.put((image_bytes, mime_type, user_text, session_id, done_evt)),
            self._loop,
        )
        return done_evt

    def is_ready(self) -> bool:
        return self._session is not None

    def _run_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._session_loop())

    async def _session_loop(self) -> None:
        self._out_queue = asyncio.Queue(maxsize=30)
        self._audio_in  = asyncio.Queue()
        self._turn_done_evt = asyncio.Event()

        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"},
        )
        config = gtypes.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            system_instruction=_SYSTEM_PROMPT,
            speech_config=gtypes.SpeechConfig(
                voice_config=gtypes.VoiceConfig(
                    prebuilt_voice_config=gtypes.PrebuiltVoiceConfig(
                        voice_name="Aoede"
                    )
                )
            ),
        )

        backoff = 2.0
        while True:
            try:
                logger.debug("Connecting to vision session...")
                async with client.aio.live.connect(
                    model=_LIVE_MODEL, config=config
                ) as session:
                    self._session = session
                    self._ready_evt.set()
                    backoff = 2.0  
                    logger.debug("Vision session connected")

                    async with asyncio.TaskGroup() as tg:
                        tg.create_task(self._send_loop())
                        tg.create_task(self._recv_loop())
                        tg.create_task(self._play_loop())

            except* Exception as eg:
                for exc in eg.exceptions:
                    logger.info(f"Session error: {exc}")
            finally:
                self._session = None
                self._ready_evt.clear()

            logger.debug(f"Reconnecting in {backoff:.0f}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 1.5, 30.0)
            self._ready_evt.set()  

    async def _send_loop(self) -> None:
        while True:
            image_bytes, mime_type, user_text, session_id, done_evt = await self._out_queue.get()
            self._current_session_id = session_id
            self._current_done_evt = done_evt
            if not self._session:
                logger.info(f"No session — dropping image")
                continue
            try:
                payload = [gtypes.Part.from_bytes(data=image_bytes, mime_type=mime_type)]
                if user_text:
                    payload.append(user_text)
                
                await self._session.send(input=payload, end_of_turn=True)
                logger.info(f"Sent {len(image_bytes):,} bytes — '{user_text[:60]}'")
            except Exception as e:
                logger.exception("Failed to capture or encode screenshot")
                raise

    async def _recv_loop(self) -> None:
        transcript: list[str] = []
        try:
            async for response in self._session.receive():
                if response.data:
                    await self._audio_in.put(response.data)

                sc = response.server_content
                if not sc:
                    continue

                if sc.output_transcription and sc.output_transcription.text:
                    chunk = sc.output_transcription.text.strip()
                    if chunk:
                        transcript.append(chunk)

                if sc.turn_complete:
                    if hasattr(self, "_turn_done_evt"):
                        self._turn_done_evt.set()
                    if transcript and self._player:
                        full = re.sub(r"\s+", " ", " ".join(transcript)).strip()
                        if full:
                            if hasattr(self._player, "send_transcript"):
                                self._player.send_transcript(full, final=True)
                            self._player.write_log(f"MIA: {full}")
                            if getattr(self, "_current_session_id", None):
                                from memory.history_manager import log_message
                                log_message(self._current_session_id, "assistant", full)
                    transcript = []

        except Exception as e:
            logger.exception("Error during vision analysis generation")
            raise  
            
        raise ConnectionError("Receive loop exited cleanly, session closed.")

    async def _play_loop(self) -> None:
        try:
            buffer = bytearray()
            buf_lock = threading.Lock()

            def audio_cb(outdata, frames, time, status):
                needed = len(outdata)
                with buf_lock:
                    if len(buffer) >= needed:
                        outdata[:] = buffer[:needed]
                        del buffer[:needed]
                    else:
                        outdata[:len(buffer)] = buffer
                        outdata[len(buffer):] = b'\x00' * (needed - len(buffer))
                        buffer.clear()

            with sd.RawOutputStream(
                samplerate=_RECEIVE_SAMPLE_RATE,
                channels=_CHANNELS,
                dtype="int16",
                blocksize=_CHUNK_SIZE,
                callback=audio_cb
            ) as stream:
                while True:
                    if self._audio_in is None:
                        await asyncio.sleep(0.1)
                        continue

                    try:
                        chunk = await asyncio.wait_for(self._audio_in.get(), timeout=0.02)
                    except asyncio.TimeoutError:
                        with buf_lock:
                            buf_empty = len(buffer) == 0

                        if hasattr(self, "_turn_done_evt") and self._turn_done_evt.is_set() and self._audio_in.empty() and buf_empty:
                            if hasattr(self._player, "mia_live"):
                                self._player.mia_live.set_speaking(False, source="vision")
                            self._turn_done_evt.clear()
                            if hasattr(self, "_current_done_evt") and self._current_done_evt:
                                self._current_done_evt.set()
                                self._current_done_evt = None
                        continue
                    
                    if hasattr(self._player, "mia_live"):
                        self._player.mia_live.set_speaking(True, source="vision")

                    with buf_lock:
                        buffer.extend(chunk)
        except Exception as e:
            logger.exception("Failed while reading stream chunks from Gemini")
            raise
        finally:
            if hasattr(self._player, "mia_live"):
                self._player.mia_live.set_speaking(False, source="vision")

_session      = _VisionSession()
_session_lock = threading.Lock()
_session_up   = False


def _ensure_session(player=None) -> None:
    global _session_up
    with _session_lock:
        if not _session_up:
            _session.start(player=player)
            _session_up = True
        elif player is not None:
            _session._player = player


def screen_process(
    parameters:     dict,
    response=None,
    player=None,
    session_id=None,
) -> bool:

    params    = parameters or {}
    user_text = (params.get("text") or params.get("user_text") or "").strip()
    angle     = params.get("angle", "screen").lower().strip()

    if not user_text:
        logger.info(f"No question provided — aborting")
        return False

    logger.info(f"angle={angle!r}  question='{user_text[:80]}'")

    try:
        _ensure_session(player=player)
    except Exception as e:
        logger.info(f"Could not start session: {e}")
        return False

    try:
        if angle == "camera":
            from actions.camera_capture import capture
            image_bytes, mime_type = capture()
            logger.info(f"Camera: {len(image_bytes):,} bytes")
        else:
            from actions.screen_capture import capture_screen
            image_bytes, mime_type = capture_screen()
            logger.info(f"Screen: {len(image_bytes):,} bytes")
    except Exception as e:
        logger.exception("Failed to capture or encode screenshot")
        return False

    done_evt = _session.analyze(image_bytes, mime_type, user_text, session_id)
    if done_evt:
        done_evt.wait()
        
    return "SUCCESS: Secondary AI analyzed the screen and already answered the user. DO NOT output any text or audio. Simply return."


def warmup_session(player=None) -> None:
    try:
        _ensure_session(player=player)
    except Exception as e:
        logger.exception("Operation failed")

if __name__ == "__main__":
    logger.info(f"screen_processor.py")
    logger.info("=" * 52)
    mode = input("angle — screen / camera (default: screen): ").strip().lower() or "screen"
    q    = input("Question (Enter = default): ").strip() or "What do you see? Be brief."

    t0 = time.perf_counter()
    warmup_session()
    logger.info(f"Session ready in {time.perf_counter()-t0:.2f}s\n")

    t1 = time.perf_counter()
    ok = screen_process({"angle": mode, "text": q})
    logger.info(f"Queued in {time.perf_counter()-t1:.3f}s — waiting for audio...")
    time.sleep(10)
    logger.info("Done." if ok else "Failed.")