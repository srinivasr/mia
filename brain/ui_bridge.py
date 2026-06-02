"""
ui_bridge.py — WebSocket bridge for the frontend UI.

Exposes the same interface (set_state, write_log, muted, on_text_command,
current_file, wait_for_api_key) but communicates with the Svelte/Tauri
frontend over a WebSocket server on ws://127.0.0.1:8765.

Protocol (JSON over WebSocket):
  Server → Client:  {"type": "state",   "state": "LISTENING|SPEAKING|THINKING"}
  Server → Client:  {"type": "log",     "text": "..."}
  Client → Server:  {"type": "text_command", "text": "..."}
  Client → Server:  {"type": "mute",    "muted": true|false}
  Client → Server:  {"type": "file",    "path": "..."}

  Setup wizard protocol:
  Client → Server:  {"type": "get_config"}
  Server → Client:  {"type": "config", "configured": bool, "key_valid": bool|null,
                     "checks": {...}, "check_errors": {...}}
  Client → Server:  {"type": "set_api_key", "key": "..."}
  Server → Client:  {"type": "config_update", "key_valid": bool}
  Client → Server:  {"type": "run_checks"}
  Server → Client:  {"type": "config_update", "checks": {...}, "errors": {...}}
  Client → Server:  {"type": "config_done"}
  Server → Client:  {"type": "config_update", "config_done": true}
  Server → Client:  {"type": "open_url", "url": "..."}
  Server → Client:  {"type": "minimize_to_orb"}
"""

import asyncio
import json
import threading
from typing import Callable, Optional, Set

from utils.logger import setup_logger
logger = setup_logger(__name__)

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    raise ImportError("websockets is required: pip install websockets>=12.0")

WS_HOST = "127.0.0.1"
WS_PORT = 8765

class UIBridge:
    """
    Drop-in replacement for MiaUI. Implements the same interface consumed by
    MiaLive in main.py but routes all state/log events to connected WebSocket
    clients instead of a Tkinter window.
    """

    def __init__(self):
        self._clients: Set[WebSocketServerProtocol] = set()
        self._clients_lock = threading.Lock()

        self._muted: bool = False
        self._current_file: Optional[str] = None
        self._state: str = "IDLE"

        self.on_text_command: Optional[Callable[[str], None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._api_key_event = threading.Event()

        # Setup wizard state
        self._config_event = asyncio.Event()
        self._configured: bool = False
        self._check_results: dict = {
            "mic": None, "speakers": None,
            "internet": None, "gemini": None,
        }
        self._checks_running: bool = False
        self._check_errors: dict = {}

    @property
    def muted(self) -> bool:
        return self._muted

    @property
    def current_file(self) -> Optional[str]:
        return self._current_file

    def set_state(self, state: str) -> None:
        """Broadcast state change to all connected clients."""
        self._state = state
        self._broadcast({"type": "state", "state": state})

    def write_log(self, text: str) -> None:
        """Broadcast a log line to all connected clients."""
        logger.info(text)
        self._broadcast({"type": "log", "text": text})

    def wait_for_api_key(self) -> None:
        """Legacy sync check — async config flow replaces this."""
        pass

    async def wait_for_config(self) -> None:
        """Block until the frontend completes the setup wizard (always runs checks)."""
        from memory.config_manager import is_configured
        if is_configured():
            self._configured = True
            logger.info("Config already present, skipping key step but running checks.")
        else:
            logger.info("Config missing — waiting for setup wizard...")
        self.send_config_status()
        await self._config_event.wait()
        logger.info("Setup wizard completed.")

    def send_config_status(self) -> None:
        """Broadcast current configuration status to frontend."""
        from memory.config_manager import is_configured, get_gemini_key
        configured = is_configured()
        key = get_gemini_key()
        self._broadcast({
            "type": "config",
            "configured": configured,
            "key_valid": bool(key and len(key) > 15) if configured else None,
            "checks": self._check_results,
            "check_errors": self._check_errors,
        })

    def send_config_update(self, **kwargs) -> None:
        """Broadcast a config_update message with arbitrary fields."""
        self._broadcast({"type": "config_update", **kwargs})

    async def _handle_get_config(self) -> None:
        """Respond with current config status."""
        self.send_config_status()

    async def _handle_set_api_key(self, key: str) -> None:
        """Save the API key and report validity."""
        from memory.config_manager import save_api_keys, get_gemini_key
        save_api_keys(key)
        actual = get_gemini_key()
        valid = bool(actual and len(actual) > 15)
        self._configured = valid
        self.send_config_update(key_valid=valid)
        if valid:
            logger.info("API key saved and validated.")

    async def _run_checks(self) -> None:
        """Run hardware and connectivity checks sequentially, reporting each."""
        if self._checks_running:
            logger.info("Checks already in progress, ignoring duplicate request.")
            return

        self._checks_running = True
        results = dict(self._check_results)
        errors: dict[str, str] = {}
        self._check_errors.clear()

        try:
            # ── Mic check: record 3s audio, detect speech via WebRTC VAD ──
            self.send_config_update(checks={"mic": "listening"})
            logger.info("Mic check: listening for speech...")

            def _record_and_detect_vad() -> tuple[bool, str]:
                import sounddevice as sd
                import numpy as np
                try:
                    import _webrtcvad as vad_mod
                except ImportError:
                    import webrtcvad as vad_mod

                duration = 3
                sample_rate = 16000
                frame_ms = 30
                frame_size = int(sample_rate * frame_ms / 1000)  # 480

                recording = sd.rec(
                    int(duration * sample_rate),
                    samplerate=sample_rate,
                    channels=1,
                    dtype="int16",
                )
                sd.wait()
                audio = recording.flatten()

                vad = vad_mod.create()
                vad_mod.init(vad)
                vad_mod.set_mode(vad, 2)

                speech_frames = 0
                total_frames = 0
                for i in range(0, len(audio) - frame_size + 1, frame_size):
                    frame = audio[i:i + frame_size].tobytes()
                    total_frames += 1
                    try:
                        if vad_mod.process(vad, sample_rate, frame, frame_size):
                            speech_frames += 1
                    except Exception:
                        pass

                logger.info(f"Mic VAD: {speech_frames}/{total_frames} speech frames")
                if speech_frames >= 3:
                    return True, ""
                return False, "No speech detected — speak into your microphone and try again"

            try:
                mic_ok, mic_err = await asyncio.to_thread(_record_and_detect_vad)
                results["mic"] = mic_ok
                if mic_err:
                    errors["mic"] = mic_err
                logger.info(f"Mic check: {'OK' if mic_ok else 'FAIL'}")
            except Exception as e:
                results["mic"] = False
                estr = str(e).lower()
                if "portaudio" in estr or "device" in estr:
                    errors["mic"] = "No microphone found — check your audio input device"
                elif "access" in estr or "denied" in estr or "permission" in estr:
                    errors["mic"] = "Microphone access denied — check system permissions"
                else:
                    errors["mic"] = f"Microphone error: {str(e)[:80]}"
                logger.warning(f"Mic check: FAIL — {e}")
            self._check_results.update(results)
            self._check_errors.update(errors)
            self.send_config_update(
                checks={"mic": results["mic"]},
                errors={"mic": errors.get("mic", "")},
            )

            # ── Speakers check ──
            try:
                import sounddevice as sd
                sd.check_output_settings(samplerate=24000, channels=1)
                results["speakers"] = True
                logger.info("Speakers check: OK")
            except Exception as e:
                results["speakers"] = False
                errors["speakers"] = "No speakers/headphones found — check your audio output device"
                logger.warning(f"Speakers check: FAIL — {e}")
            self._check_results.update(results)
            self._check_errors.update(errors)
            self.send_config_update(
                checks={"speakers": results["speakers"]},
                errors={"speakers": errors.get("speakers", "")},
            )

            # ── Internet check: socket DNS + TCP ──
            def _check_internet() -> tuple[bool, str]:
                import socket
                try:
                    socket.getaddrinfo("google.com", 80)
                except socket.gaierror:
                    return False, "Unable to resolve hostnames — check your DNS/network settings"
                try:
                    sock = socket.create_connection(("google.com", 80), timeout=5)
                    sock.close()
                    return True, ""
                except socket.timeout:
                    return False, "Connection timed out — check your internet connection"
                except OSError as e:
                    return False, f"Network error: {str(e)[:80]}"

            try:
                net_ok, net_err = await asyncio.to_thread(_check_internet)
                results["internet"] = net_ok
                if net_err:
                    errors["internet"] = net_err
                logger.info(f"Internet check: {'OK' if net_ok else 'FAIL'}")
            except Exception as e:
                results["internet"] = False
                errors["internet"] = f"Internet check error: {str(e)[:80]}"
                logger.warning(f"Internet check: FAIL — {e}")
            self._check_results.update(results)
            self._check_errors.update(errors)
            self.send_config_update(
                checks={"internet": results["internet"]},
                errors={"internet": errors.get("internet", "")},
            )

            # ── Gemini API check ──
            try:
                from google import genai
                from google.genai import types as genai_types
                from memory.config_manager import get_gemini_key
                key = get_gemini_key()
                if key:
                    client = genai.Client(
                        api_key=key,
                        http_options={"api_version": "v1beta"},
                    )
                    client.models.list()
                    results["gemini"] = True
                    logger.info("Gemini API check: OK")
                else:
                    results["gemini"] = False
                    errors["gemini"] = "No API key configured"
                    logger.warning("Gemini API check: FAIL — no key")
            except Exception as e:
                results["gemini"] = False
                estr = str(e).lower()
                if "401" in estr or "unauthorized" in estr or "permission" in estr:
                    errors["gemini"] = "API key rejected — check your key at aistudio.google.com"
                elif "404" in estr or "not found" in estr:
                    errors["gemini"] = "Gemini API endpoint not found — check your API version"
                elif "429" in estr or "quota" in estr or "rate" in estr:
                    errors["gemini"] = "API rate limit exceeded — wait a moment and try again"
                elif "502" in estr or "503" in estr or "unavailable" in estr:
                    errors["gemini"] = "Gemini API is currently unavailable — try again later"
                elif "timeout" in estr or "timed out" in estr:
                    errors["gemini"] = "Request timed out — check your internet connection"
                else:
                    errors["gemini"] = f"Could not reach Gemini API: {str(e)[:80]}"
                logger.warning(f"Gemini API check: FAIL — {e}")
            self._check_results.update(results)
            self._check_errors.update(errors)
            self.send_config_update(
                checks={"gemini": results["gemini"]},
                errors={"gemini": errors.get("gemini", "")},
            )

        except Exception as e:
            logger.exception("Unexpected error during checks")
            results = {k: False for k in self._check_results}
            for k in results:
                errors[k] = f"Setup error: {str(e)[:80]}"
            self._check_results.update(results)
            self._check_errors.update(errors)
            self.send_config_update(checks=dict(results), errors=dict(errors))

        finally:
            self._checks_running = False

    async def _handle_config_done(self) -> None:
        """Finalize setup and unblock wait_for_config."""
        self._configured = True
        self._config_event.set()
        self.send_config_update(config_done=True)
        logger.info("Config done — unblocking main loop.")

    def send_open_url(self, url: str) -> None:
        """Tell frontend to open a URL in the system browser."""
        self._broadcast({"type": "open_url", "url": url})

    def send_minimize(self) -> None:
        """Tell frontend to minimize the HUD to orb-only mode."""
        self._broadcast({"type": "minimize_to_orb"})

    def _broadcast(self, payload: dict) -> None:
        """Thread-safe fire-and-forget broadcast to all WS clients."""
        if not self._loop:
            return
        msg = json.dumps(payload)
        with self._clients_lock:
            clients = set(self._clients)
        for ws in clients:
            asyncio.run_coroutine_threadsafe(self._send(ws, msg), self._loop)

    @staticmethod
    async def _send(ws: "WebSocketServerProtocol", msg: str) -> None:
        try:
            await ws.send(msg)
        except Exception:
            pass

    async def _handle(self, ws: "WebSocketServerProtocol") -> None:
        logger.info(f"Frontend connected: {ws.remote_address}")
        with self._clients_lock:
            self._clients.add(ws)

        try:
            await ws.send(json.dumps({"type": "state", "state": self._state}))
        except Exception:
            pass

        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    mtype = msg.get("type")

                    if mtype == "text_command":
                        text = str(msg.get("text", "")).strip()
                        if text and self.on_text_command:
                            self.on_text_command(text)

                    elif mtype == "mute":
                        self._muted = bool(msg.get("muted", False))
                        logger.info(f"Mute -> {self._muted}")

                    elif mtype == "file":
                        self._current_file = msg.get("path")
                        logger.info(f"File set -> {self._current_file}")

                    elif mtype == "get_config":
                        await self._handle_get_config()

                    elif mtype == "set_api_key":
                        await self._handle_set_api_key(str(msg.get("key", "")))

                    elif mtype == "run_checks":
                        asyncio.create_task(self._run_checks())

                    elif mtype == "config_done":
                        await self._handle_config_done()

                    elif mtype == "world_monitor":
                        url = "https://www.worldmonitor.app/?lat=22.4589&lon=82.7533&zoom=3.01&view=global&timeRange=7d&layers=conflicts%2Cbases%2Chotspots%2Cnuclear%2Csanctions%2Cweather%2Ceconomic%2Cwaterways%2Coutages%2Cmilitary%2Cnatural%2CiranAttacks"
                        self.send_open_url(url)
                        self.send_minimize()

                    elif mtype == "stt_request":
                        pass

                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.exception("Error during camera/UI thread execution")

        except Exception as e:
            logger.info(f"Frontend disconnected: {e}")
        finally:
            with self._clients_lock:
                self._clients.discard(ws)

    async def serve(self) -> None:
        """Start the WebSocket server."""
        self._loop = asyncio.get_event_loop()
        logger.info(f"WS server starting on ws://{WS_HOST}:{WS_PORT}")
        async with websockets.serve(self._handle, WS_HOST, WS_PORT, max_size=10_485_760):
            logger.info(f"WS server ready ws://{WS_HOST}:{WS_PORT}")
            await asyncio.Future()
