"""A Gemini agent that drives the iPhone through rPlayHub (function calling).

Same loop as the Claude/OpenAI samples, swapped to Gemini.

    export GEMINI_API_KEY=...
    python3 examples/03_gemini_agent.py "open Settings and turn on Airplane Mode"

Needs: pip install google-genai ; the rPlayHub engine running with a device bound (iOS 17+; the loop is screenshot-based,
so live video / iOS 27 is not required).
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 2)[0])
from rplayhub_client import RPlayHubClient

try:
    from google import genai
    from google.genai import types
except ImportError:
    sys.exit("pip install google-genai")

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

TOOLS = [types.Tool(function_declarations=[
    {"name": "tap", "description": "Tap at 0..1 fractions of the screen.",
     "parameters": {"type": "object", "properties": {"fx": {"type": "number"}, "fy": {"type": "number"}},
                    "required": ["fx", "fy"]}},
    {"name": "swipe", "description": "Swipe/scroll (fx0,fy0)->(fx1,fy1) in 0..1 fractions.",
     "parameters": {"type": "object", "properties": {
         "fx0": {"type": "number"}, "fy0": {"type": "number"},
         "fx1": {"type": "number"}, "fy1": {"type": "number"}},
         "required": ["fx0", "fy0", "fx1", "fy1"]}},
    {"name": "home", "description": "Go to the home screen.", "parameters": {"type": "object", "properties": {}}},
    {"name": "launch", "description": "Launch an app by bundle id.",
     "parameters": {"type": "object", "properties": {"bundle_id": {"type": "string"}}, "required": ["bundle_id"]}},
    {"name": "done", "description": "Call when the goal is achieved.",
     "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}}},
])]


def screen_part(c: RPlayHubClient) -> types.Part:
    return types.Part.from_bytes(data=c.screenshot(), mime_type="image/png")


def run(goal: str) -> None:
    c = RPlayHubClient()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents = [types.Content(role="user", parts=[
        types.Part.from_text(text=f"Goal: {goal}. Here is the phone screen. Achieve it one action "
                                  f"at a time, checking each screenshot. Call done when finished."),
        screen_part(c),
    ])]

    for _ in range(40):
        resp = client.models.generate_content(
            model=MODEL, contents=contents,
            config=types.GenerateContentConfig(tools=TOOLS))
        call = None
        for cand in resp.candidates or []:
            for part in cand.content.parts or []:
                if getattr(part, "function_call", None):
                    call = part.function_call
                elif getattr(part, "text", None) and part.text.strip():
                    print(f"[gemini] {part.text.strip()}")
        if not call:
            print("[gemini] (no tool call -- stopping)")
            return
        contents.append(resp.candidates[0].content)
        args = dict(call.args)
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
        contents.append(types.Content(role="user", parts=[
            types.Part.from_function_response(name=call.name, response={"result": "done"}),
            types.Part.from_text(text="New screen:"), screen_part(c)]))

    print("[stop] hit the step limit")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('usage: python3 03_gemini_agent.py "your goal"')
    run(sys.argv[1])
