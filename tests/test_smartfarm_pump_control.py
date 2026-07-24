from __future__ import annotations

import pytest

from scripts import smartfarm_pump_control
from scripts.smartfarm_pump_control import MAX_ON_SECONDS, control_pump


class FakeSocket:
    def __init__(self, response: bytes) -> None:
        self.response = response
        self.sent: list[bytes] = []

    def sendall(self, packet: bytes) -> None:
        self.sent.append(packet)

    def recv(self, _size: int) -> bytes:
        return self.response


def test_publish_requires_matching_qos1_puback() -> None:
    socket = FakeSocket(b"\x40\x02\x00\x01")
    smartfarm_pump_control._publish(socket, "farm/zone2/pump/cmd", "off")
    assert socket.sent[0][0] == 0x32

    with pytest.raises(RuntimeError, match="mqtt_puback_failed"):
        smartfarm_pump_control._publish(
            FakeSocket(b"\x40\x02\x00\x02"),
            "farm/zone2/pump/cmd",
            "off",
        )


def test_dry_run_on_is_confirmation_bound_and_auto_off() -> None:
    result = control_pump(
        zone="zone2",
        action="on",
        confirmed=True,
        duration_seconds=5,
        dry_run=True,
    )
    assert result["commands"] == ["on", "off"]
    assert result["autoOffSeconds"] == 5
    assert result["topic"] == "farm/zone2/pump/cmd"


def test_on_without_confirmation_is_blocked() -> None:
    with pytest.raises(PermissionError, match="explicit_confirmation_required"):
        control_pump(
            zone="zone2",
            action="on",
            confirmed=False,
            duration_seconds=5,
            dry_run=True,
        )


def test_confirmed_on_is_still_fail_closed_without_verified_watchdog() -> None:
    with pytest.raises(
        PermissionError,
        match="on_blocked_until_independent_hardware_watchdog_is_verified",
    ):
        control_pump(
            zone="zone2",
            action="on",
            confirmed=True,
            duration_seconds=5,
            dry_run=False,
        )


@pytest.mark.parametrize("zone", ["zone0", "../zone2", "zone2/pump", "greenhouse"])
def test_zone_is_fail_closed(zone: str) -> None:
    with pytest.raises(ValueError, match="invalid_zone"):
        control_pump(
            zone=zone,
            action="off",
            confirmed=True,
            duration_seconds=5,
            dry_run=True,
        )


def test_duration_cannot_exceed_firmware_safety_limit() -> None:
    with pytest.raises(ValueError, match=f"duration_must_be_1_to_{MAX_ON_SECONDS}"):
        control_pump(
            zone="zone2",
            action="on",
            confirmed=True,
            duration_seconds=MAX_ON_SECONDS + 1,
            dry_run=True,
        )


def test_off_dry_run_needs_no_on_confirmation() -> None:
    result = control_pump(
        zone="zone2",
        action="off",
        confirmed=False,
        duration_seconds=5,
        dry_run=True,
    )
    assert result["commands"] == ["off"]


def test_off_retries_transient_publish_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def flaky_publish(*_args: object) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise OSError("temporary")

    monkeypatch.setattr(smartfarm_pump_control, "publish_once", flaky_publish)
    result = control_pump(
        zone="zone2",
        action="off",
        confirmed=False,
        duration_seconds=5,
    )
    assert attempts == 3
    assert result["commandState"] == "off_published_broker_acknowledged"
    assert result["physicalStateVerified"] is False
    assert result["publishAttempts"] == 3


def test_off_reports_failure_after_three_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def failed_publish(*_args: object) -> None:
        nonlocal attempts
        attempts += 1
        raise OSError("offline")

    monkeypatch.setattr(smartfarm_pump_control, "publish_once", failed_publish)
    with pytest.raises(RuntimeError, match="off_publish_failed_after_3_attempts"):
        control_pump(
            zone="zone2",
            action="off",
            confirmed=False,
            duration_seconds=5,
        )
    assert attempts == 3
