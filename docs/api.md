# rPlayHub SDK — API reference

The engine speaks newline-delimited JSON on `127.0.0.1:9876`. Each request is
`{"id", "method", "params?}`; each reply is `{"id","ok":true,"result":{...}}` or
`{"id","ok":false,"error":{"code","message"}}`. `rplayhub_client.py` wraps all of this.

## Client methods

| Method | Engine call | Returns |
|---|---|---|
| `ping()` | `ping` | `{engine, language}` |
| `list_devices()` | `list_devices` | list of `{udid, name, product_type, os_version, connection, bound}` |
| `first_device()` | — | the bound device, or the first attached |
| `device_info(udid?)` | `device_info` | lockdown info: `default`, `battery`, `disk_usage`, `unavailable` |
| `screenshot()` | `take_screenshot` | raw **PNG** bytes (full resolution) |
| `screenshot_dict()` | `take_screenshot` | `{format, width, height, image_b64}` |
| `tap_fraction(fx, fy)` | `tap` | tap at 0..1 fractions (resolution-independent) |
| `tap(x, y)` | `tap` | tap at device pixels |
| `swipe_fraction(fx0,fy0,fx1,fy1)` | `swipe` | swipe in 0..1 fractions |
| `swipe(x1,y1,x2,y2)` | `swipe` | swipe in pixels |
| `press_home()` | `press_button` | Home gesture |
| `restart()` / `shutdown()` / `sleep()` | `device_action` | power actions |
| `list_apps(include_hidden?)` | `list_apps` | `[{bundleIdentifier, name, version, isFirstParty}]` |
| `launch_app(bundle_id)` | `launch_app` | `{processToken: {processIdentifier, ...}}` |
| `terminate_app(pid)` | `terminate_app` | `{}` |
| `list_processes()` | `list_processes` | running processes |
| `list_profiles()` | `list_profiles` | `{provisioning, configuration}` |
| `list_dir(path, service)` | `list_dir` | Media partition (`media`) or crash reports (`crash`) |
| `read_file(path, service)` | `read_file` | file bytes (≤64 MB) |
| `export_crashes(dir)` | `export_crashes` | copy all crash reports locally |
| `syslog(on_line, stop?)` | `syslog` | stream device log lines (blocking) |

## Coordinates

rPlayHub taps in **0..1 fractions** internally, which is the robust way to drive a phone whose
pixel size you may not know and which changes with the video tier. Prefer `tap_fraction` /
`swipe_fraction`: read the target's position off the screenshot as a proportion (a button 60% down
the screen, centred → `fx=0.5, fy=0.6`). The pixel helpers exist for when you know the exact size
(from `list_devices` → `screen_width/height`, once populated).

## Not yet available

`type_text` and the hardware buttons (lock / volume / Siri) are not implemented — the keyboard and
button HID report formats are still being decoded. For text, tap the field and drive the on-screen
keyboard with `tap_fraction`. Live mirroring needs iOS 27+ (screenshots and everything else work on
older iOS, same limit as Apple's Device Hub).
