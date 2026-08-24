"""Smoke test: exercise the read-only SDK methods against a running rPlayHub engine.

Run with the engine up (sudo ./host-c/cdhost) and a device bound. Saves a screenshot to
/tmp/rplayhub_smoke.png if the device can mirror (iOS 27+); iOS 26 still answers everything else.

    python3 examples/01_smoke_test.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0])
from rplayhub_client import RPlayHubClient, RPlayHubError


def main() -> int:
    c = RPlayHubClient()

    print("--- ping:", c.ping())

    devices = c.list_devices()
    print(f"\n--- {len(devices)} device(s):")
    for d in devices:
        print(f"  {d.get('name')}  {d.get('product_type')}  iOS {d.get('os_version')}  "
              f"{d.get('connection')}{'  <- bound' if d.get('bound') else ''}")
    if not devices:
        print("  (no device -- bind one in the engine first)")
        return 1

    dev = c.first_device()
    print(f"\n--- device_info ({dev['name']}):")
    info = c.device_info().get("default", {})
    for k in ("ProductType", "ProductVersion", "SerialNumber", "ECID"):
        print(f"  {k}: {info.get(k)}")

    print("\n--- take_screenshot:")
    try:
        shot = c.screenshot_dict()
        png = c.screenshot()
        open("/tmp/rplayhub_smoke.png", "wb").write(png)
        print(f"  {shot['width']}x{shot['height']} {shot['format']}, {len(png)} bytes "
              f"-> /tmp/rplayhub_smoke.png")
    except RPlayHubError as e:
        print(f"  ({e.code}: {e.message})")

    print("\n--- list_apps:")
    try:
        apps = c.list_apps()
        third = [a for a in apps if not a["isFirstParty"]]
        print(f"  {len(apps)} apps, {len(third)} user-installed. First few:")
        for a in third[:5]:
            print(f"    {a['name']}  ({a['bundleIdentifier']} {a['version']})")
    except RPlayHubError as e:
        print(f"  ({e.code}: {e.message})")

    print("\n--- list_profiles:")
    try:
        p = c.list_profiles()
        print(f"  {len(p.get('provisioning', []))} provisioning, "
              f"{len(p.get('configuration', []))} configuration")
    except RPlayHubError as e:
        print(f"  ({e.code}: {e.message})")

    print("\nOK. Input methods (tap_fraction, swipe_fraction, press_home, launch_app) are not")
    print("exercised here so the smoke test never touches the device -- see examples for those.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
