# MCP server — drive an iPhone from inside a coding agent

`mcp_server.py` is a [Model Context Protocol](https://modelcontextprotocol.io/) stdio server that
exposes a physical iPhone — driven by the rPlayHub engine — as a small set of tools an LLM can
call. Use it to control a real phone from inside Claude Code or OpenAI Codex, no separate API-key
agent needed.

## Tools

| Tool | Args | Notes |
|---|---|---|
| `screenshot` | – | PNG of the phone's screen |
| `tap` | `fx, fy` | 0..1 fractions of the screen |
| `swipe` | `fx0, fy0, fx1, fy1, duration_ms?` | scroll/drag in fractions |
| `press_home` | – | home screen |
| `launch_app` | `bundle_id` | e.g. `com.apple.Preferences` |
| `list_apps` | – | installed apps |
| `device_info` | – | model, iOS, serial, battery |

## Setup

```sh
pip install "mcp[cli]"
# start the engine first (in its own terminal):
#   cd ~/rplay-hub && sudo ./host-c/cdhost
```

### Claude Code

```sh
claude mcp add rplayhub -- python3 ~/rplayhub-sdk/mcp_server.py
```

Then in a session: *"take a screenshot of the phone and open Settings."*

### OpenAI Codex / any MCP client

Point the client at `python3 ~/rplayhub-sdk/mcp_server.py` over stdio.

Coordinates are 0..1 fractions of the screen — the same proportions you can read off the
screenshot the model just saw, so it can aim without knowing the pixel size.
