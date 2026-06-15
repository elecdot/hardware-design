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


class FakeJY901(object):
    def __init__(self, failures=0):
        self.failures = int(failures)
        self.oneshot_calls = 0

    def oneshot(self, timeout=0.5):
        self.oneshot_calls += 1
        if self.oneshot_calls <= self.failures:
            raise RuntimeError("fake jy901 nack")

    def read_raw(self):
        return {"fake": 1}

    def read_status(self):
        return 0


class FakeSpo2Sample(object):
    bpm = 76
    spo2 = 98
    crc_ok = True
    sensor_off = False
    sensor_error = False


class FakeSpo2(object):
    def has_frame(self):
        return True

    def read_sample(self):
        return FakeSpo2Sample()


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


def fake_scale_raw(_raw):
    return {
        "ax_g": 0.1,
        "ay_g": 0.2,
        "az_g": 1.0,
        "gx_dps": 0.0,
        "gy_dps": 0.0,
        "gz_dps": 0.0,
        "hx_counts": 10,
        "hy_counts": 11,
        "hz_counts": 12,
        "roll_deg": 0.0,
        "pitch_deg": 0.0,
    }


def fake_status_label(_status):
    return "OK"


def sensor_drivers(jy901, spo2=None):
    drivers = {
        "jy901": jy901,
        "jy901_scale_raw": fake_scale_raw,
        "jy901_status_label": fake_status_label,
    }
    if spo2 is not None:
        drivers["spo2"] = spo2
    return drivers


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


def check_jy901_retry_success():
    jy901 = FakeJY901(failures=1)
    board = SleepMonitorBoard(
        drivers=sensor_drivers(jy901, FakeSpo2()),
        jy901_retries=1,
        jy901_retry_delay_s=0.0,
    )
    sample = board.read_sample()
    validate_message(sample, expected_type=SENSOR_DATA)
    assert jy901.oneshot_calls == 2
    assert sample["data_valid"] == 1
    assert sample["imu_valid"] == 1
    assert sample["spo2_valid"] == 1
    assert sample["jy901_attempts"] == 2
    assert sample["remark"] == "jy901_retry_ok_2"


def check_jy901_failure_keeps_classifier_sample_usable():
    board = SleepMonitorBoard(
        drivers=sensor_drivers(FakeJY901(failures=3), FakeSpo2()),
        jy901_retries=1,
        jy901_retry_delay_s=0.0,
    )
    sample = board.read_sample()
    validate_message(sample, expected_type=SENSOR_DATA)
    assert sample["data_valid"] == 1
    assert sample["imu_valid"] == 0
    assert sample["spo2_valid"] == 1
    assert sample["status_code"] & 0x01
    assert sample["jy901_status"] == "ERR"
    assert sample["remark"].startswith("jy901:")


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
    check_jy901_retry_success()
    check_jy901_failure_keeps_classifier_sample_usable()
    check_no_action()
    check_humidifier_target()
    check_ir_send_and_cooldowns()
    check_reject_and_error()
    print("board_orchestrator_selftest PASS")


if __name__ == "__main__":
    main()
