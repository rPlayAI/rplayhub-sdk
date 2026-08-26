# rPlayHub SDK

Drive a real iPhone from code — screenshot it, tap it, swipe it, launch apps,
read the device — so an AI agent can use the phone the way a person would.

[rPlayHub](../rplay-hub) is *"adb for iPhone"*: a from-scratch CoreDevice host that mirrors and
controls a physical iPhone with **no Xcode and no Apple daemons in the runtime path**. This
repository is the programmable half — a thin client, an MCP server that plugs into Claude Code and
OpenAI Codex, and working agent samples for Claude, Gemini, and OpenAI.

```python
from rplayhub_client import RPlayHubClient

c = RPlayHubClient()
dev = c.first_device()
open("screen.png", "wb").write(c.screenshot())     # what's on the phone
c.tap_fraction(0.5, 0.5)                            # tap the middle (resolution-independent)
c.swipe_fraction(0.5, 0.8, 0.5, 0.2)               # scroll up
c.launch_app("com.apple.Preferences")              # open Settings
```

Everything runs against a **physical iPhone**, not a simulator. No jailbreak, no app installed on
the phone.

## Requirements

| | |
|---|---|
| **iPhone** | **iOS 17 or later** — for everything the SDK does (screenshot, tap, swipe, apps, files, device info, power, syslog). CoreDevice, which the engine speaks, arrived in iOS 17. |
| **iOS 27+** | only for **live video mirroring** in the rPlayHub *app's* View Screen — the SDK does not use it, so the SDK and the agent samples work fine on iOS 17–26. (iOS 26 and earlier "cannot mirror," same limit as Apple's Device Hub, but they screenshot and take input.) |
| **On the phone** | Developer Mode on (Settings → Privacy & Security), and the phone paired + trusted with the host once over USB. |
| **Host** | macOS with the rPlayHub engine running; a paired iPhone on USB (preferred) or Wi‑Fi. |

The agent loop drives the phone by **screenshot → look → tap**, which needs no live video — so an
iOS 26 phone automates just as well as an iOS 27 one; you just won't see a moving mirror.

## What you can do

| | |
|---|---|
| **See** | full-resolution PNG screenshots (`screenshot`) |
| **Touch** | tap, swipe — in 0..1 fractions or device pixels; Home gesture |
| **Apps** | list installed apps, launch, terminate, list processes |
| **Device** | model / iOS / serial / ECID / battery / storage; provisioning & config profiles |
| **Files** | browse the Media partition, pull files, export crash reports (AFC) |
| **Power** | restart, shut down, sleep/lock |
| **Console** | stream the device syslog |

Live screen mirroring needs iOS 27+ (the same limit Apple's Device Hub has); screenshots and
everything else work on older iOS too.

## Setup

```sh
# 1. Run the engine (from the rplay-hub checkout) with a paired iPhone attached:
cd ~/rplay-hub && sudo ./host-c/cdhost      # bind a device; keep this running

# 2. Use the SDK:
python3 examples/01_smoke_test.py            # exercises the read-only methods
```

The engine holds the privileged tunnel; the SDK is an ordinary TCP client of its JSON API on
`127.0.0.1:9876`. See [rplay-hub's PROTOCOL.md](../rplay-hub/app/api/PROTOCOL.md) for the wire
contract and [docs/api.md](docs/api.md) for the client.

## Files

```
rplayhub_client.py         the client — one class, the whole API
mcp_server.py              MCP stdio server for Claude Code / Codex   (docs/mcp.md)
examples/01_smoke_test.py    read-only tour of the API
examples/02_claude_agent.py  "AI drives the phone" loop -- Anthropic  (ANTHROPIC_API_KEY)
examples/03_gemini_agent.py  the same loop -- Gemini              (GEMINI_API_KEY)
examples/04_openai_agent.py  the same loop -- OpenAI              (OPENAI_API_KEY)
docs/api.md                client reference
docs/mcp.md                MCP setup
docs/help.html             rPlayHub app help (open in a browser)
```

## Coordinates

The phone is driven in **0..1 fractions** of the screen — the robust choice when you may not know
the pixel size (and it changes with the video tier). Read a target's position off the screenshot as
a proportion — a button 60% down and centred is `(0.5, 0.6)` — and pass it to `tap_fraction`. Pixel
helpers (`tap`, `swipe`) exist for when you know the exact size.

## Not yet available

`type_text` and the hardware buttons (lock / volume / Siri) — the keyboard and button HID report
formats are still being decoded. For text, tap the field and drive the on-screen keyboard with
taps. Pair / Unpair and multi-device are on the rplay-hub roadmap.
