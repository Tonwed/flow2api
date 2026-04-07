"""
Captcha Extension Bridge — integrated into flow2api

Replaces the external captcha_worker.js process.
Chrome extension connects directly to flow2api via WebSocket at /ws/captcha.
The flow_client.py calls CaptchaBridge.solve() in-process.
"""

import asyncio
import uuid
import time
from typing import Optional, Dict, Tuple
from fastapi import WebSocket, WebSocketDisconnect


class CaptchaBridge:
    """Singleton WebSocket bridge between flow2api and Chrome extension."""

    _instance: Optional["CaptchaBridge"] = None

    def __init__(self):
        self._extension_ws: Optional[WebSocket] = None
        self._extension_ua: Optional[str] = None
        self._connected_at: Optional[float] = None
        self._pending: Dict[str, asyncio.Future] = {}
        self._ping_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._solve_count = 0

    @classmethod
    def get_instance(cls) -> "CaptchaBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ===== Properties =====

    @property
    def is_connected(self) -> bool:
        return self._extension_ws is not None

    @property
    def user_agent(self) -> Optional[str]:
        return self._extension_ua

    @property
    def solve_count(self) -> int:
        return self._solve_count

    @property
    def connected_at(self) -> Optional[float]:
        return self._connected_at

    def status_dict(self) -> dict:
        return {
            "extensionConnected": self.is_connected,
            "userAgent": self._extension_ua,
            "solveCount": self._solve_count,
            "connectedAt": self._connected_at,
        }

    # ===== WebSocket Handler =====

    async def handle_websocket(self, ws: WebSocket):
        """Handle a new WebSocket connection from Chrome extension."""
        await ws.accept()

        # Replace any existing connection
        async with self._lock:
            if self._extension_ws is not None:
                try:
                    await self._extension_ws.close(1000, "Replaced by new connection")
                except Exception:
                    pass
            self._extension_ws = ws
            self._extension_ua = None
            self._connected_at = time.time()

        print("[CaptchaBridge] 🔌 Chrome extension connected!")

        # Start ping task
        if self._ping_task is None or self._ping_task.done():
            self._ping_task = asyncio.create_task(self._ping_loop())

        try:
            while True:
                data = await ws.receive_json()
                msg_type = data.get("type")

                if msg_type == "handshake":
                    self._extension_ua = data.get("userAgent")
                    url = data.get("url", "")
                    print(f"[CaptchaBridge] ✅ Handshake: {url}")
                    print(f"[CaptchaBridge]    UA: {self._extension_ua}")

                elif msg_type == "solve_response":
                    req_id = data.get("id")
                    future = self._pending.get(req_id)
                    if future and not future.done():
                        if data.get("success"):
                            future.set_result({
                                "token": data.get("token"),
                                "userAgent": data.get("userAgent") or self._extension_ua,
                            })
                        else:
                            future.set_exception(
                                RuntimeError(data.get("error", "Extension solve failed"))
                            )

                elif msg_type == "pong":
                    pass  # keep-alive ack

        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"[CaptchaBridge] WebSocket error: {e}")
        finally:
            async with self._lock:
                if self._extension_ws is ws:
                    self._extension_ws = None
                    self._extension_ua = None
                    self._connected_at = None
            # Fail all pending requests
            for req_id, future in list(self._pending.items()):
                if not future.done():
                    future.set_exception(RuntimeError("Extension disconnected"))
                self._pending.pop(req_id, None)
            print("[CaptchaBridge] ⚠️ Chrome extension disconnected.")

    # ===== Solve (called by flow_client) =====

    async def solve(self, action: str = "VIDEO_GENERATION", timeout: int = 15) -> Tuple[Optional[str], Optional[str]]:
        """
        Request a reCAPTCHA token from the connected Chrome extension.

        Returns:
            (token, userAgent) on success, (None, None) on failure.
        """
        if not self._extension_ws:
            raise RuntimeError("No Chrome extension connected")

        req_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = future

        try:
            await self._extension_ws.send_json({
                "type": "solve_request",
                "id": req_id,
                "action": action,
            })

            result = await asyncio.wait_for(future, timeout=timeout)
            self._solve_count += 1
            return result.get("token"), result.get("userAgent")
        except asyncio.TimeoutError:
            raise RuntimeError(f"Extension solve timed out ({timeout}s)")
        except Exception:
            raise
        finally:
            self._pending.pop(req_id, None)

    # ===== Keep-alive =====

    async def _ping_loop(self):
        """Send periodic pings to keep the WebSocket alive."""
        while True:
            await asyncio.sleep(25)
            try:
                if self._extension_ws:
                    await self._extension_ws.send_json({"type": "ping"})
            except Exception:
                pass
