"""A minimal Claude agent that drives the iPhone through rPlayHub.

Give it a goal in plain English; it loops: screenshot -> Claude looks -> Claude calls a tool
(tap / swipe / home / launch) -> repeat, until Claude says done. This is the "AI uses the phone
like a person" loop, ~120 lines.

    export ANTHROPIC_API_KEY=sk-ant-...
    python3 examples/02_claude_agent.py "open Settings and turn on Airplane Mode"

Needs: pip install anthropic ; the rPlayHub engine running with a device bound (iOS 17+).
"""
from __future__ import annotations

import base64
import os
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 2)[0])
from rplayhub_client import RPlayHubClient

try:
    import anthropic
except ImportError:
    sys.exit("pip install anthropic")

MODEL = "claude-sonnet-5"   # any current Claude model; see the claude-api skill for ids

TOOLS = [
    {"name": "tap", "description": "Tap at a point given as 0..1 fractions of the screen.",
     "input_schema": {"type": "object", "properties": {
         "fx": {"type": "number"}, "fy": {"type": "number"}}, "required": ["fx", "fy"]}},
    {"name": "swipe", "description": "Swipe/scroll from (fx0,fy0) to (fx1,fy1), all 0..1 fractions.",
     "input_schema": {"type": "object", "properties": {
         "fx0": {"type": "number"}, "fy0": {"type": "number"},
         "fx1": {"type": "number"}, "fy1": {"type": "number"}},
         "required": ["fx0", "fy0", "fx1", "fy1"]}},
    {"name": "home", "description": "Go to the home screen.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "launch", "description": "Launch an app by bundle id (e.g. com.apple.Preferences).",
     "input_schema": {"type": "object", "properties": {
         "bundle_id": {"type": "string"}}, "required": ["bundle_id"]}},
    {"name": "done", "description": "Call when the goal is achieved.",
     "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}}}},
]


def screenshot_block(c: RPlayHubClient) -> dict:
    png = c.screenshot()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                        "data": base64.b64encode(png).decode()}}


def run(goal: str) -> None:
    c = RPlayHubClient()
    llm = anthropic.Anthropic()
    messages = [{"role": "user", "content": [
        {"type": "text", "text": f"Goal: {goal}\nHere is the phone screen. Achieve the goal one "
                                 f"action at a time, checking each new screenshot. Call done when finished."},
        screenshot_block(c),
    ]}]

    for step in range(40):
        resp = llm.messages.create(model=MODEL, max_tokens=1024, tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        calls = [b for b in resp.content if b.type == "tool_use"]
        for b in resp.content:
            if b.type == "text" and b.text.strip():
                print(f"[claude] {b.text.strip()}")
        if not calls:
            print("[claude] (no tool call -- stopping)")
            return
        results = []
        for call in calls:
            name, args = call.name, call.input
            print(f"  -> {name}({args})")
            if name == "done":
                print(f"[done] {args.get('summary', '')}")
                return
            if name == "tap":
                c.tap_fraction(args["fx"], args["fy"])
            elif name == "swipe":
                c.swipe_fraction(args["fx0"], args["fy0"], args["fx1"], args["fy1"])
            elif name == "home":
                c.press_home()
            elif name == "launch":
                c.launch_app(args["bundle_id"])
            time.sleep(1.2)   # let the UI settle before the next screenshot
            results.append({"type": "tool_result", "tool_use_id": call.id,
                            "content": [{"type": "text", "text": "done"}, screenshot_block(c)]})
        messages.append({"role": "user", "content": results})

    print("[stop] hit the step limit")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('usage: python3 02_claude_agent.py "your goal in plain English"')
    run(sys.argv[1])
