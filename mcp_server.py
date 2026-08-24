"""MCP stdio server exposing a physical iPhone (via rPlayHub) to a coding agent.

Drop this into Claude Code or OpenAI Codex and the model can screenshot, tap, swipe, go home, and
launch apps on a real iPhone -- without you standing up a separate API-key agent. It talks to the
rPlayHub engine on 127.0.0.1:9876 through rplayhub_client.

    pip install "mcp[cli]"
    # then register it -- see docs/mcp.md

Tools are intentionally small and resolution-independent: coordinates are 0..1 fractions of the
screen, the same space you can read off the screenshot's proportions.
"""
from __future__ import annotations

import io
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from rplayhub_client import RPlayHubClient, RPlayHubError

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.utilities.types import Image
except ImportError:
    sys.exit('pip install "mcp[cli]"')

mcp = FastMCP("rplayhub-iphone")
_client = RPlayHubClient()


@mcp.tool()
def screenshot() -> Image:
    """Return a PNG of the iPhone's current screen. Read coordinates off it as 0..1 fractions."""
    return Image(data=_client.screenshot(), format="png")


@mcp.tool()
def tap(fx: float, fy: float) -> str:
    """Tap at (fx, fy), each 0..1 across the screen. (0.5, 0.5) is the middle."""
    _client.tap_fraction(fx, fy)
    return f"tapped ({fx:.3f}, {fy:.3f})"


@mcp.tool()
def swipe(fx0: float, fy0: float, fx1: float, fy1: float, duration_ms: int = 300) -> str:
    """Swipe/scroll from (fx0,fy0) to (fx1,fy1), all 0..1 fractions. Scroll up: high y to low y."""
    _client.swipe_fraction(fx0, fy0, fx1, fy1, duration_ms=duration_ms)
    return f"swiped ({fx0:.2f},{fy0:.2f})->({fx1:.2f},{fy1:.2f})"


@mcp.tool()
def press_home() -> str:
    """Go to the iPhone home screen."""
    _client.press_home()
    return "home"


@mcp.tool()
def launch_app(bundle_id: str) -> str:
    """Launch an app by bundle id, e.g. com.apple.Preferences or com.apple.mobilesafari."""
    _client.launch_app(bundle_id)
    return f"launched {bundle_id}"


@mcp.tool()
def list_apps() -> list[dict]:
    """List installed apps: name, bundleIdentifier, version, isFirstParty."""
    return _client.list_apps()


@mcp.tool()
def device_info() -> dict:
    """Model, iOS version, serial, ECID, battery, storage."""
    try:
        return _client.device_info()
    except RPlayHubError as e:
        return {"error": f"{e.code}: {e.message}"}


if __name__ == "__main__":
    mcp.run()
