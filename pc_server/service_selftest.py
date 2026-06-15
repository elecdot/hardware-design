"""Self-test for the PC service composition layer."""

import tempfile

from classifier_adapter import SleepClassifierAdapter
from protocol import CONTROL_COMMAND, CONTROL_STATUS, SENSOR_DATA, SLEEP_RESULT
from protocol_selftest import (
    sample_control_status,
    sample_sensor,
    sample_sleep_result,
)
from service import SleepMonitorPcService
from storage import JsonlRecordStorage


def fake_classifier(sensor_data):
    result = sample_sleep_result(sensor_data["sample_id"])
    result["sleep_state_code"] = 1
    result["state_valid"] = 1
    result["remark"] = "fake_classifier_valid"
    return result


def failing_policy(*_args, **_kwargs):
    raise RuntimeError("policy exploded")


class FakeClock(object):
    def __init__(self, now_s=0.0):
        self.now_s = float(now_s)

    def __call__(self):
        return self.now_s


def high_temperature_sensor(sample_id):
    sample = sample_sensor(sample_id)
    sample["temperature_c"] = 29.0
    sample["humidity_percent"] = 50
    return sample


def ir_control_status(sample_id, command="temp_25", sent=True, skip_reason=None):
    status = sample_control_status(sample_id)
    status["applied"] = {
        "ir_ac": {
            "requested": True,
            "command": command,
            "sent": bool(sent),
            "skipped": not bool(sent),
            "skip_reason": skip_reason,
            "error": None,
            "status": {"done": bool(sent), "error": False, "raw_status": 2},
        }
    }
    status["status_code"] = 0 if sent else 2
    status["remark"] = "ir_ac_sent" if sent else skip_reason
    return status


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JsonlRecordStorage(tmpdir)
        service = SleepMonitorPcService(
            classifier_adapter=SleepClassifierAdapter(fake_classifier),
            storage=storage,
        )

        first = sample_sensor(1)
        first["humidity_percent"] = 35
        result = service.process_sensor_data(first, now_s=10.0)
        sleep_result = result["sleep_result"]
        command = result["control_command"]
        assert sleep_result["type"] == SLEEP_RESULT
        assert sleep_result["sample_id"] == 1
        assert command["type"] == CONTROL_COMMAND
        assert command["targets"] == {"humidifier": {"enabled": True}}

        snapshot = service.snapshot()
        assert snapshot["latest_sensor_data"]["sample_id"] == 1
        assert snapshot["latest_sleep_result"]["sample_id"] == 1
        assert snapshot["latest_control_command"]["sample_id"] == 1
        assert snapshot["last_commanded_state"]["humidifier"]["enabled"] is True

        status = sample_control_status(1)
        service.process_control_status(status)
        assert service.snapshot()["latest_control_status"]["sample_id"] == 1

        assert len(storage.read_records(SENSOR_DATA)) == 1
        assert len(storage.read_records(SLEEP_RESULT)) == 1
        assert len(storage.read_records(CONTROL_COMMAND)) == 1
        assert len(storage.read_records(CONTROL_STATUS)) == 1

        service.queue_manual_command(
            {
                "target": "ir_ac",
                "command": "temp_26",
                "temperature_setpoint_c": 26,
            }
        )
        manual = service.process_sensor_data(sample_sensor(2), now_s=20.0)
        manual_command = manual["control_command"]
        assert manual_command["mode"] == "manual"
        assert manual_command["reason"] == "dashboard_manual"
        assert manual_command["targets"]["ir_ac"]["command"] == "temp_26"
        assert service.snapshot()["pending_manual_command"] is None

        idle = service.process_sensor_data(sample_sensor(3), now_s=30.0)
        idle_command = idle["control_command"]
        assert idle_command["mode"] == "manual"
        assert idle_command["targets"] == {}
        assert idle_command["reason"] == "manual_idle"

        service.set_control_mode("auto")
        auto_idle = service.process_sensor_data(sample_sensor(4), now_s=40.0)
        assert auto_idle["control_command"]["mode"] == "auto"

        clock = FakeClock(100.0)
        runtime_service = SleepMonitorPcService(
            classifier_adapter=SleepClassifierAdapter(fake_classifier),
            time_fn=clock,
        )

        first_ir = runtime_service.process_sensor_data(high_temperature_sensor(10))
        assert first_ir["control_command"]["targets"]["ir_ac"]["command"] == "temp_25"
        clock.now_s = 101.0
        runtime_service.process_control_status(
            ir_control_status(10, command="temp_25", sent=False, skip_reason="ir_ac_missing")
        )

        clock.now_s = 102.0
        retry_ir = runtime_service.process_sensor_data(high_temperature_sensor(11))
        assert retry_ir["control_command"]["targets"]["ir_ac"]["command"] == "temp_25"

        clock.now_s = 103.0
        runtime_service.process_control_status(
            ir_control_status(11, command="temp_25", sent=True)
        )

        clock.now_s = 104.0
        cooldown = runtime_service.process_sensor_data(high_temperature_sensor(12))
        assert cooldown["control_command"]["targets"] == {}
        assert cooldown["control_command"]["reason"] == "cooldown_ir_min_interval"

        clock.now_s = 105.0
        new_session = runtime_service.process_sensor_data(high_temperature_sensor(1))
        assert new_session["control_command"]["targets"]["ir_ac"]["command"] == "temp_25"

    failing_service = SleepMonitorPcService(
        classifier_adapter=SleepClassifierAdapter(fake_classifier),
        policy_decider=failing_policy,
    )
    fallback = failing_service.process_sensor_data(sample_sensor(5), now_s=50.0)
    assert fallback["control_command"]["targets"] == {}
    assert fallback["control_command"]["reason"] == "policy_error:RuntimeError"
    assert "policy exploded" in failing_service.last_error

    print("service_selftest PASS")


if __name__ == "__main__":
    main()
