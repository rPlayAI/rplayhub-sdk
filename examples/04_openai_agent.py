"""An OpenAI agent that drives the iPhone through rPlayHub (Responses API + function tools).

Same loop as the Claude sample: screenshot -> model looks -> model calls a tool -> repeat.

    export OPENAI_API_KEY=sk-...
    python3 examples/04_openai_agent.py "open Settings and turn on Airplane Mode"

Needs: pip install openai ; the rPlayHub engine running with an iOS 27 device.
"""
from __future__ import annotations

import base64
import os
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 2)[0])
from rplayhub_client import RPlayHubClient

try:
    from openai import OpenAI
except ImportError:
    sys.exit("pip install openai")

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6-terra")

# Responses-API function tools: flat type/name/description/parameters.
TOOLS = [
    {"type": "function", "name": "tap", "description": "Tap at 0..1 fractions of the screen.",
     "parameters": {"type": "object", "properties": {"fx": {"type": "number"}, "fy": {"type": "number"}},
                    "required": ["fx", "fy"]}},
    {"type": "function", "name": "swipe", "description": "Swipe/scroll (fx0,fy0)->(fx1,fy1), 0..1 fractions.",
     "parameters": {"type": "object", "properties": {
         "fx0": {"type": "number"}, "fy0": {"type": "number"},
         "fx1": {"type": "number"}, "fy1": {"type": "number"}},
         "required": ["fx0", "fy0", "fx1", "fy1"]}},
    {"type": "function", "name": "home", "description": "Go to the home screen.",
     "parameters": {"type": "object", "properties": {}}},
    {"type": "function", "name": "launch", "description": "Launch an app by bundle id.",
     "parameters": {"type": "object", "properties": {"bundle_id": {"type": "string"}},
                    "required": ["bundle_id"]}},
    {"type": "function", "name": "done", "description": "Call when the goal is achieved.",
     "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}}},
]


def screenshot_input(c: RPlayHubClient) -> dict:
    png = base64.b64encode(c.screenshot()).decode()
    return {"type": "input_image", "image_url": f"data:image/png;base64,{png}"}


def run(goal: str) -> None:
    import json
    c = RPlayHubClient()
    llm = OpenAI()
    msgs = [{"role": "user", "content": [
        {"type": "input_text", "text": f"Goal: {goal}. Here is the phone screen. Achieve it one "
                                       f"action at a time, checking each new screenshot. Call done when finished."},
        screenshot_input(c),
    ]}]

    for _ in range(40):
        resp = llm.responses.create(model=MODEL, input=msgs, tools=TOOLS)
        calls = [o for o in resp.output if getattr(o, "type", None) == "function_call"]
        if (resp.output_text or "").strip():
            print(f"[gpt] {resp.output_text.strip()}")
        if not calls:
            print("[gpt] (no tool call -- stopping)")
            return
        msgs += resp.output
        for call in calls:
            args = json.loads(call.arguments or "{}")
            print(f"  -> {call.name}({args})")
            if call.name == "done":
                print(f"[done] {args.get('summary', '')}")
                return
            if call.name == "tap":
                c.tap_fraction(args["fx"], args["fy"])
            elif call.name == "swipe":
                c.swipe_fraction(args["fx0"], args["fy0"], args["fx1"], args["fy1"])
            elif call.name == "home":
                c.press_home()
            elif call.name == "launch":
                c.launch_app(args["bundle_id"])
            time.sleep(1.2)
            msgs.append({"type": "function_call_output", "call_id": call.call_id,
                         "output": "done"})
        msgs.append({"role": "user", "content": [
            {"type": "input_text", "text": "New screen:"}, screenshot_input(c)]})

    print("[stop] hit the step limit")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('usage: python3 04_openai_agent.py "your goal"')
    run(sys.argv[1])
