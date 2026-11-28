#!/usr/bin/env python3
"""List iOS devices/simulators and capture screenshots via Xcode tooling.

Physical devices go through `xcrun devicectl` (Xcode 15+, works over USB or
Wi-Fi pairing, iOS 17+). Booted simulators go through `xcrun simctl`.

Usage:
    ios_devices.py list [--json] [--no-probe]
    ios_devices.py screenshot --udid <UDID> --kind physical|simulator --out <png>
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

PROBE_TIMEOUT_SECONDS = 15
SCREENSHOT_TIMEOUT_SECONDS = 60


def parse_devicectl_devices(data: dict[str, Any]) -> list[dict[str, str]]:
    """Extract paired physical devices from `devicectl list devices -j` JSON.

    Simulators are skipped here; they come from simctl instead.
    """
    devices: list[dict[str, str]] = []
    for item in data.get("result", {}).get("devices", []):
        hardware = item.get("hardwareProperties", {}) or {}
        props = item.get("deviceProperties", {}) or {}
        conn = item.get("connectionProperties", {}) or {}
        if hardware.get("reality") != "physical":
            continue
        if conn.get("pairingState") != "paired":
            continue
        udid = hardware.get("udid") or item.get("identifier", "")
        if not udid:
            continue
        devices.append(
            {
                "kind": "physical",
                "udid": udid,
                "name": props.get("name", ""),
                "model": hardware.get("marketingName")
                or hardware.get("productType", ""),
                "os": props.get("osVersionNumber", ""),
                "transport": conn.get("transportType", ""),
                "state": "unknown",
            }
        )
    return devices


def parse_simctl_booted(data: dict[str, Any]) -> list[dict[str, str]]:
    """Extract booted simulators from `simctl list devices booted -j` JSON."""
    devices: list[dict[str, str]] = []
    for runtime, entries in sorted(data.get("devices", {}).items()):
        os_version = runtime_to_os(runtime)
        for entry in entries:
            if entry.get("state") != "Booted":
                continue
            devices.append(
                {
                    "kind": "simulator",
                    "udid": entry.get("udid", ""),
                    "name": entry.get("name", ""),
                    "model": device_type_to_model(
                        entry.get("deviceTypeIdentifier", "")
                    ),
                    "os": os_version,
                    "transport": "simulator",
                    "state": "ready",
                }
            )
    return devices


def runtime_to_os(runtime: str) -> str:
    """Turn 'com.apple.CoreSimulator.SimRuntime.iOS-26-5' into 'iOS 26.5'."""
    tail = runtime.rsplit(".", 1)[-1]
    if "-" not in tail:
        return tail
    name, _, version = tail.partition("-")
    return f"{name} {version.replace('-', '.')}"


def device_type_to_model(identifier: str) -> str:
    """Turn 'com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro' into 'iPhone 17 Pro'."""
    if not identifier:
        return ""
    return identifier.rsplit(".", 1)[-1].replace("-", " ")


def lock_state_label(result: dict[str, Any] | None) -> str:
    """Map a devicectl lockState result to a state label.

    None means the probe failed (device not reachable right now).
    """
    if result is None:
        return "unreachable"
    if result.get("passcodeRequired") is True:
        return "locked"
    return "ready"


def format_table(devices: list[dict[str, str]]) -> str:
    """Render devices as a numbered plain-text table."""
    if not devices:
        return "No iOS devices or booted simulators found."
    lines = []
    for index, dev in enumerate(devices, start=1):
        lines.append(
            f"{index}. [{dev['kind']}] {dev['name']} — {dev['model']} "
            f"({dev['os']}) state={dev['state']} udid={dev['udid']}"
        )
    return "\n".join(lines)


def _run_json(cmd: list[str], timeout: int) -> dict[str, Any] | None:
    """Run a command that prints JSON to stdout; return None on failure."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def probe_physical(udid: str) -> str:
    """Probe a physical device's reachability and lock state."""
    data = _run_json(
        [
            "xcrun", "devicectl", "device", "info", "lockState",
            "--device", udid, "-t", str(PROBE_TIMEOUT_SECONDS), "-j", "-",
        ],
        PROBE_TIMEOUT_SECONDS + 5,
    )
    result = data.get("result") if data else None
    return lock_state_label(result if isinstance(result, dict) else None)


def probe_all(
    devices: list[dict[str, str]],
    probe: Callable[[str], str],
    max_workers: int = 8,
) -> None:
    """Set each device's ``state`` by running *probe* on all UDIDs in parallel.

    Probes of unreachable devices take up to the full timeout, so running
    them concurrently bounds `list` to roughly one timeout, not one per device.
    """
    if not devices:
        return
    workers = max(1, min(max_workers, len(devices)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        states = list(pool.map(probe, [d["udid"] for d in devices]))
    for dev, state in zip(devices, states):
        dev["state"] = state


def list_devices(probe: bool) -> list[dict[str, str]]:
    """Collect paired physical devices and booted simulators."""
    devices: list[dict[str, str]] = []
    data = _run_json(["xcrun", "devicectl", "list", "devices", "-j", "-"], 60)
    if data is not None:
        devices.extend(parse_devicectl_devices(data))
    if probe:
        probe_all(devices, probe_physical)
    sims = _run_json(["xcrun", "simctl", "list", "devices", "booted", "-j"], 60)
    if sims is not None:
        devices.extend(parse_simctl_booted(sims))
    return devices


def screenshot_command(udid: str, kind: str, out: Path) -> list[str]:
    """Build the screenshot command for a physical device or simulator."""
    if kind == "physical":
        return [
            "xcrun", "devicectl", "device", "capture", "screenshot",
            "--device", udid, "--destination", str(out),
        ]
    if kind == "simulator":
        return ["xcrun", "simctl", "io", udid, "screenshot", str(out)]
    raise ValueError(f"Unknown device kind: {kind!r} (expected physical|simulator)")


def take_screenshot(udid: str, kind: str, out: Path) -> int:
    """Capture a PNG screenshot; return a process exit code."""
    if out.suffix.lower() != ".png":
        print("ERROR: --out must end with .png", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = screenshot_command(udid, kind, out)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=SCREENSHOT_TIMEOUT_SECONDS, check=False,
        )
    except subprocess.TimeoutExpired:
        print("ERROR: screenshot timed out — is the device awake and reachable?",
              file=sys.stderr)
        return 1
    if proc.returncode != 0 or not out.exists():
        print(f"ERROR: screenshot failed:\n{proc.stderr.strip() or proc.stdout.strip()}",
              file=sys.stderr)
        return 1
    print(str(out))
    return 0


def preflight() -> str | None:
    """Return an error message if the host cannot run iOS tooling."""
    if platform.system() != "Darwin":
        return "iOS devices can only be read from macOS (Xcode is required)."
    if shutil.which("xcrun") is None:
        return "xcrun not found — install Xcode and run `xcode-select --install`."
    return None


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List paired devices and booted simulators")
    p_list.add_argument("--json", action="store_true", help="Print JSON")
    p_list.add_argument("--no-probe", action="store_true",
                        help="Skip the reachability/lock probe for physical devices")

    p_shot = sub.add_parser("screenshot", help="Capture a PNG screenshot")
    p_shot.add_argument("--udid", required=True)
    p_shot.add_argument("--kind", required=True, choices=["physical", "simulator"])
    p_shot.add_argument("--out", required=True, type=Path)

    args = parser.parse_args()
    error = preflight()
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if args.command == "list":
        devices = list_devices(probe=not args.no_probe)
        if args.json:
            print(json.dumps(devices, ensure_ascii=False, indent=2))
        else:
            print(format_table(devices))
        return 0
    return take_screenshot(args.udid, args.kind, args.out)


if __name__ == "__main__":
    sys.exit(main())
