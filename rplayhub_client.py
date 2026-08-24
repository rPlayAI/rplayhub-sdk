"""
Thin Python client for the rPlayHub engine's JSON-line control protocol on 127.0.0.1:9876.

rPlayHub is "adb for iPhone": a from-scratch CoreDevice host that mirrors and controls a physical
iPhone with no Xcode and no Apple daemons in the runtime path. This client is the programmable
half -- drive the phone from code so an AI agent can use it the way a person would: screenshot it,
tap, swipe, launch apps, read the device, pull files.

Each call opens a fresh TCP connection, sends one JSON line, reads one JSON line, and closes.
Stateless and easy to reason about. The engine must be running (sudo ./host-c/cdhost) with a
device bound.

    from rplayhub_client import RPlayHubClient
    c = RPlayHubClient()
    dev = c.first_device()
    open("screen.png", "wb").write(c.screenshot())     # what's on the phone
    c.tap_fraction(0.5, 0.5)                            # tap the middle, resolution-independent
    c.swipe_fraction(0.5, 0.8, 0.5, 0.2)               # scroll up
    print([a["name"] for a in c.list_apps() if not a["isFirstParty"]][:10])
    c.launch_app("com.apple.Preferences")              # open Settings
"""

from __future__ import annotations

import base64
import json
import socket
import uuid
from typing import Any, Callable, Iterator


class RPlayHubError(RuntimeError):
    """Engine returned ok=false. `.code` is the machine-readable error code."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class RPlayHubClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9876, timeout_s: float = 30.0):
        self.host = host
        self.port = port
        self.timeout_s = timeout_s

    # --- low-level ---------------------------------------------------------

    def _connect(self) -> socket.socket:
        try:
            return socket.create_connection((self.host, self.port), timeout=self.timeout_s)
        except ConnectionRefusedError:
            raise RPlayHubError(
                "engine_not_running",
                f"nothing is listening on {self.host}:{self.port} -- start the rPlayHub engine "
                "(sudo ./host-c/cdhost) and bind a device") from None

    def _request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        req = {"id": str(uuid.uuid4()), "method": method}
        if params:
            req["params"] = params
        line = (json.dumps(req) + "\n").encode()
        with self._connect() as s:
            s.sendall(line)
            buf = bytearray()
            while 0x0A not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    raise RPlayHubError("connection_closed", "engine closed without a response")
                buf.extend(chunk)
        resp = json.loads(bytes(buf).split(b"\n", 1)[0].decode())
        if not resp.get("ok"):
            err = resp.get("error", {}) or {}
            raise RPlayHubError(err.get("code", "unknown"), err.get("message", "(no message)"))
        return resp.get("result", {})

    # --- device ------------------------------------------------------------

    def ping(self) -> dict[str, Any]:
        return self._request("ping")

    def list_devices(self) -> list[dict[str, Any]]:
        return self._request("list_devices").get("devices", [])

    def first_device(self) -> dict[str, Any]:
        """The bound device, or the first attached one. Raises if none."""
        devices = self.list_devices()
        if not devices:
            raise RPlayHubError("device_not_found", "no device -- start the engine and bind one")
        for d in devices:
            if d.get("bound"):
                return d
        return devices[0]

    def device_info(self, udid: str | None = None) -> dict[str, Any]:
        """Full lockdown info: name, model, iOS, ECID, serial, battery, storage."""
        return self._request("device_info", {"udid": udid} if udid else {})

    def tunnel_info(self) -> dict[str, Any]:
        return self._request("tunnel_info")

    def stream_info(self) -> dict[str, Any]:
        return self._request("stream_info")

    # --- screen ------------------------------------------------------------

    def screenshot(self) -> bytes:
        """Raw PNG bytes of the phone's current screen (full resolution)."""
        return base64.b64decode(self._request("take_screenshot")["image_b64"])

    def screenshot_dict(self) -> dict[str, Any]:
        """Full result: format, width, height, image_b64."""
        return self._request("take_screenshot")

    # --- input -------------------------------------------------------------
    #
    # rPlayHub taps in resolution-independent 0..1 fractions internally, which is the robust way
    # to drive a phone whose pixel size you may not know. Pixel helpers are provided for when you
    # do (they need the bound device's screen size).

    def tap_fraction(self, fx: float, fy: float, duration_ms: int = 60) -> dict[str, Any]:
        """Tap at (fx, fy), each 0..1 across the screen. (0.5, 0.5) is the middle."""
        return self._request("tap", {"fx": fx, "fy": fy, "duration_ms": duration_ms})

    def swipe_fraction(self, fx0: float, fy0: float, fx1: float, fy1: float,
                       duration_ms: int = 300) -> dict[str, Any]:
        """Swipe from (fx0,fy0) to (fx1,fy1) in 0..1 fractions. Scroll up = high y to low y."""
        return self._request("swipe", {"fx0": fx0, "fy0": fy0, "fx1": fx1, "fy1": fy1,
                                        "duration_ms": duration_ms})

    def tap(self, x: int, y: int, duration_ms: int = 60) -> dict[str, Any]:
        """Tap at device pixels (x, y)."""
        return self._request("tap", {"x": x, "y": y, "duration_ms": duration_ms})

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> dict[str, Any]:
        """Swipe between device-pixel points."""
        return self._request("swipe", {"x1": x1, "y1": y1, "x2": x2, "y2": y2,
                                        "duration_ms": duration_ms})

    def press_home(self, hold_ms: int = 60) -> dict[str, Any]:
        """Press the Home gesture (bottom-edge swipe)."""
        return self._request("press_button", {"button": "home", "hold_ms": hold_ms})

    # NOTE: type_text and hardware buttons (lock/volume/Siri) are not implemented yet -- the
    # keyboard/button HID report formats are still being decoded. Tap a field and drive the
    # on-screen keyboard with tap_fraction for now.

    # --- power (diagnostics_relay) -----------------------------------------

    def restart(self) -> dict[str, Any]:
        """Reboot the device. The tunnel drops; reconnect after ~45s."""
        return self._request("device_action", {"action": "restart"})

    def shutdown(self) -> dict[str, Any]:
        """Power the device off (needs a manual power-on afterwards)."""
        return self._request("device_action", {"action": "shutdown"})

    def sleep(self) -> dict[str, Any]:
        """Lock the screen (recoverable)."""
        return self._request("device_action", {"action": "sleep"})

    # --- apps --------------------------------------------------------------

    def list_apps(self, include_hidden: bool = False) -> list[dict[str, Any]]:
        """[{bundleIdentifier, name, version, isFirstParty}, ...] -- installation_proxy."""
        return self._request("list_apps", {"include_hidden": include_hidden})

    def launch_app(self, bundle_id: str) -> dict[str, Any]:
        """Bring an app to the foreground (terminates a running instance first)."""
        return self._request("launch_app", {"bundle_id": bundle_id})

    def terminate_app(self, pid: int, signal: int = 9) -> dict[str, Any]:
        return self._request("terminate_app", {"pid": pid, "signal": signal})

    def list_processes(self) -> list[dict[str, Any]]:
        return self._request("list_processes").get("processTokens", [])

    def list_profiles(self) -> dict[str, Any]:
        """{provisioning: [...], configuration: [...]} -- misagent + MCInstall."""
        return self._request("list_profiles")

    # --- files (AFC) -------------------------------------------------------

    def list_dir(self, path: str = "/", service: str = "media") -> list[dict[str, Any]]:
        """Browse the Media partition (service='media') or crash reports (service='crash')."""
        return self._request("list_dir", {"path": path, "service": service}).get("entries", [])

    def read_file(self, path: str, service: str = "media") -> bytes:
        """Pull a file (<=64 MB) off the device."""
        return base64.b64decode(self._request("read_file", {"path": path, "service": service})["data_b64"])

    def export_crashes(self, dir: str) -> dict[str, Any]:
        """Copy every crash report into a local directory."""
        return self._request("export_crashes", {"dir": dir})

    # --- console (streaming) ----------------------------------------------

    def syslog(self, on_line: Callable[[str], None], stop: Callable[[], bool] | None = None) -> None:
        """Stream the device syslog, calling on_line(line) for each line. Blocks until the engine
        closes or `stop()` returns True (checked between lines). Opens a dedicated connection."""
        with self._connect() as s:
            s.sendall((json.dumps({"id": "syslog", "method": "syslog"}) + "\n").encode())
            buf = bytearray()
            first = True
            while True:
                if stop and stop():
                    return
                while 0x0A in buf:
                    raw, _, rest = bytes(buf).partition(b"\n")
                    buf = bytearray(rest)
                    if not raw:
                        continue
                    obj = json.loads(raw.decode())
                    if first:
                        first = False
                        if not obj.get("ok"):
                            err = obj.get("error", {}) or {}
                            raise RPlayHubError(err.get("code", "unknown"), err.get("message", ""))
                        continue
                    if obj.get("event") == "syslog":
                        on_line(obj.get("line", ""))
                chunk = s.recv(65536)
                if not chunk:
                    return
                buf.extend(chunk)
