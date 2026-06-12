"""PC-runnable self-test for the PYNQ board orchestrator skeleton."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PC_SERVER = os.path.join(ROOT, "pc_server")
if PC_SERVER not in sys.path:
    sys.path.insert(0, PC_SERVER)

from board_orchestrator import SleepMonitorBoard
from protocol import CONTROL_STATUS, SENSOR_DATA, validate_message


class FakeClock(object):
    def __init__(self, now_s=0.0):
        self.now_s = float(now_s)

    def __call__(self):
        return self.now_s


class FakeHumidifier(object):
    def __init__(self):
        self.enabled = False

    def manual(self, enabled):
        self.enabled = bool(enabled)

    def status(self):
        return {"humidifier_on": self.enabled}


class FakeIrAc(object):
    def __init__(self, fail=False):
        self.fail = bool(fail)
        self.sent_commands = []

    def send_command(self, command, timeout=15.0):
        if self.fail:
            raise RuntimeError("fake ir failure")
        self.sent_commands.append((command, timeout))

    def status(self):
        command = self.sent_commands[-1][0] if self.sent_commands else None
        return {
            "done": True,
            "error": False,
            "raw_status": 2,
            "command": command,
        }


def command(sample_id, targets, valid=1, mode="auto", reason="selftest"):
    return {
        "type": "control_command",
        "timestamp": "2026-06-12 22:30:00",
        "sample_id": sample_id,
        "mode": mode,
        "policy_id": "comfort_v1",
        "targets": targets,
        "valid": valid,
        "reason": reason,
    }


def check_sample_shape():
    board = SleepMonitorBoard()
    sample = board.read_sample()
    validate_message(sample, expected_type=SENSOR_DATA)
    assert sample["sample_id"] == 1
    assert sample["data_valid"] == 0
    assert sample["remark"] == "jy901_missing"


def check_no_action():
    board = SleepMonitorBoard()
    status = board.apply_control_command(command(2, {}, reason="manual_idle"))
    validate_message(status, expected_type=CONTROL_STATUS)
    assert status["accepted"] == 1
    assert status["status_code"] == 2
    assert status["applied"] == {}
    assert status["remark"] == "manual_idle"


def check_humidifier_target():
    humidifier = FakeHumidifier()
    board = SleepMonitorBoard(drivers={"humidifier": humidifier})
    status = board.apply_control_command(
        command(3, {"humidifier": {"enabled": True}})
    )
    validate_message(status, expected_type=CONTROL_STATUS)
    assert status["accepted"] == 1
    assert status["status_code"] == 0
    assert status["applied"]["humidifier"]["applied"] is True
    assert status["applied"]["humidifier"]["humidifier_on"] is True
    assert humidifier.enabled is True


def check_ir_send_and_cooldowns():
    clock = FakeClock(100.0)
    ir_ac = FakeIrAc()
    board = SleepMonitorBoard(drivers={"ir_ac": ir_ac}, time_fn=clock)

    first = board.apply_control_command(
        command(4, {"ir_ac": {"command": "temp_26", "temperature_setpoint_c": 26}})
    )
    validate_message(first, expected_type=CONTROL_STATUS)
    assert first["accepted"] == 1
    assert first["status_code"] == 0
    assert first["applied"]["ir_ac"]["sent"] is True
    assert ir_ac.sent_commands[0][0] == "temp_26"

    clock.now_s = 102.0
    min_interval = board.apply_control_command(
        command(5, {"ir_ac": {"command": "temp_27", "temperature_setpoint_c": 27}})
    )
    validate_message(min_interval, expected_type=CONTROL_STATUS)
    assert min_interval["status_code"] == 2
    assert min_interval["applied"]["ir_ac"]["skipped"] is True
    assert min_interval["applied"]["ir_ac"]["skip_reason"] == "cooldown_ir_min_interval"

    clock.now_s = 106.0
    repeat = board.apply_control_command(
        command(6, {"ir_ac": {"command": "temp_26", "temperature_setpoint_c": 26}})
    )
    validate_message(repeat, expected_type=CONTROL_STATUS)
    assert repeat["status_code"] == 2
    assert repeat["applied"]["ir_ac"]["skip_reason"] == "cooldown_same_ir_command"


def check_reject_and_error():
    board = SleepMonitorBoard()
    rejected = board.apply_control_command(
        command(7, {"ir_ac": {"command": "cool_16"}})
    )
    validate_message(rejected, expected_type=CONTROL_STATUS)
    assert rejected["accepted"] == 0
    assert rejected["status_code"] == 1
    assert "unknown ir_ac command" in rejected["remark"]

    error_board = SleepMonitorBoard(drivers={"ir_ac": FakeIrAc(fail=True)})
    failed = error_board.apply_control_command(
        command(8, {"ir_ac": {"command": "power_on"}})
    )
    validate_message(failed, expected_type=CONTROL_STATUS)
    assert failed["accepted"] == 1
    assert failed["status_code"] == 3
    assert failed["applied"]["ir_ac"]["error"] == "fake ir failure"


def main():
    check_sample_shape()
    check_no_action()
    check_humidifier_target()
    check_ir_send_and_cooldowns()
    check_reject_and_error()
    print("board_orchestrator_selftest PASS")


if __name__ == "__main__":
    main()
