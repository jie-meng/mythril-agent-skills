"""Tests for ios-screen-reader skill scripts."""

from pathlib import Path

import pytest

DEVICECTL_JSON = {
    "result": {
        "devices": [
            {
                "identifier": "BC57-PHYS",
                "hardwareProperties": {
                    "reality": "physical",
                    "udid": "00008030-0006642A14D1802E",
                    "marketingName": "iPhone 11",
                    "productType": "iPhone12,1",
                },
                "deviceProperties": {"name": "My iPhone", "osVersionNumber": "27.2.1"},
                "connectionProperties": {
                    "pairingState": "paired",
                    "transportType": "localNetwork",
                },
            },
            {
                "identifier": "SIM-1",
                "hardwareProperties": {"reality": "simulated", "udid": "4FA3"},
                "deviceProperties": {"name": "iPhone 17"},
                "connectionProperties": {"pairingState": "paired"},
            },
            {
                "identifier": "UNPAIRED",
                "hardwareProperties": {"reality": "physical", "udid": "0000-UNPAIRED"},
                "deviceProperties": {"name": "Stranger"},
                "connectionProperties": {"pairingState": "unpaired"},
            },
            {
                "identifier": "NO-MARKETING",
                "hardwareProperties": {
                    "reality": "physical",
                    "udid": "0000-IPAD",
                    "productType": "iPad12,1",
                },
                "deviceProperties": {"name": "My iPad"},
                "connectionProperties": {"pairingState": "paired"},
            },
        ]
    }
}

SIMCTL_JSON = {
    "devices": {
        "com.apple.CoreSimulator.SimRuntime.iOS-26-5": [
            {
                "udid": "4FA3",
                "name": "iPhone 17",
                "state": "Booted",
                "deviceTypeIdentifier": "com.apple.CoreSimulator.SimDeviceType.iPhone-17",
            },
            {"udid": "OFF", "name": "iPhone 16", "state": "Shutdown"},
        ],
        "com.apple.CoreSimulator.SimRuntime.iOS-18-6": [],
    }
}


class TestParseDevicectlDevices:
    """Tests for ios_devices.parse_devicectl_devices."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from ios_devices import parse_devicectl_devices
        self.func = parse_devicectl_devices

    def test_keeps_only_paired_physical(self):
        udids = [d["udid"] for d in self.func(DEVICECTL_JSON)]
        assert udids == ["00008030-0006642A14D1802E", "0000-IPAD"]

    def test_fields(self):
        dev = self.func(DEVICECTL_JSON)[0]
        assert dev == {
            "kind": "physical",
            "udid": "00008030-0006642A14D1802E",
            "name": "My iPhone",
            "model": "iPhone 11",
            "os": "27.2.1",
            "transport": "localNetwork",
            "state": "unknown",
        }

    def test_model_falls_back_to_product_type(self):
        assert self.func(DEVICECTL_JSON)[1]["model"] == "iPad12,1"

    def test_empty(self):
        assert self.func({}) == []


class TestParseSimctlBooted:
    """Tests for ios_devices.parse_simctl_booted."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from ios_devices import parse_simctl_booted
        self.func = parse_simctl_booted

    def test_only_booted(self):
        devices = self.func(SIMCTL_JSON)
        assert len(devices) == 1
        assert devices[0]["udid"] == "4FA3"
        assert devices[0]["kind"] == "simulator"
        assert devices[0]["os"] == "iOS 26.5"
        assert devices[0]["model"] == "iPhone 17"
        assert devices[0]["state"] == "ready"

    def test_empty(self):
        assert self.func({"devices": {}}) == []


class TestRuntimeToOs:
    """Tests for ios_devices.runtime_to_os."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from ios_devices import runtime_to_os
        self.func = runtime_to_os

    def test_ios(self):
        assert self.func("com.apple.CoreSimulator.SimRuntime.iOS-26-5") == "iOS 26.5"

    def test_three_part(self):
        assert self.func("com.apple.CoreSimulator.SimRuntime.iOS-18-6-1") == "iOS 18.6.1"

    def test_no_dash(self):
        assert self.func("weird") == "weird"


class TestDeviceTypeToModel:
    """Tests for ios_devices.device_type_to_model."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from ios_devices import device_type_to_model
        self.func = device_type_to_model

    def test_model(self):
        ident = "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro"
        assert self.func(ident) == "iPhone 17 Pro"

    def test_empty(self):
        assert self.func("") == ""


class TestLockStateLabel:
    """Tests for ios_devices.lock_state_label."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from ios_devices import lock_state_label
        self.func = lock_state_label

    def test_unreachable(self):
        assert self.func(None) == "unreachable"

    def test_locked(self):
        assert self.func({"passcodeRequired": True}) == "locked"

    def test_ready(self):
        result = {"passcodeRequired": False, "unlockedSinceBoot": True}
        assert self.func(result) == "ready"


class TestFormatTable:
    """Tests for ios_devices.format_table."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from ios_devices import format_table, parse_simctl_booted
        self.func = format_table
        self.sims = parse_simctl_booted(SIMCTL_JSON)

    def test_empty(self):
        assert "No iOS devices" in self.func([])

    def test_row(self):
        assert self.func(self.sims) == (
            "1. [simulator] iPhone 17 — iPhone 17 (iOS 26.5) state=ready udid=4FA3"
        )


class TestScreenshotCommand:
    """Tests for ios_devices.screenshot_command."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from ios_devices import screenshot_command
        self.func = screenshot_command

    def test_physical(self):
        cmd = self.func("UDID", "physical", Path("/x/s.png"))
        assert cmd[:5] == ["xcrun", "devicectl", "device", "capture", "screenshot"]
        assert cmd[cmd.index("--device") + 1] == "UDID"
        assert cmd[cmd.index("--destination") + 1] == "/x/s.png"

    def test_simulator(self):
        cmd = self.func("UDID", "simulator", Path("/x/s.png"))
        assert cmd == ["xcrun", "simctl", "io", "UDID", "screenshot", "/x/s.png"]

    def test_unknown_kind(self):
        with pytest.raises(ValueError):
            self.func("UDID", "android", Path("/x/s.png"))
