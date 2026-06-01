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
        """Check if the API key is configured using the config_manager."""
        from memory.config_manager import is_configured
        
        if is_configured():
            logger.info("API key found in .env.")
        else:
            logger.info("No valid gemini_api_key found in .env.")

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
