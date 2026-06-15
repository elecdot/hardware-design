"""Self-test for the first-version comfort policy."""

from comfort_policy import (
    MODE_AUTO,
    MODE_MANUAL,
    decide_control_command,
    initial_policy_state,
)


def sensor(sample_id=1, temperature=26.0, humidity=50.0, valid=1, status_code=0):
    return {
        "type": "sensor_data",
        "timestamp": "2026-06-12 21:00:00",
        "sample_id": sample_id,
        "heart_rate_bpm": 76,
        "spo2_percent": 98,
        "temperature_c": temperature,
        "humidity_percent": humidity,
        "data_valid": valid,
        "checksum_ok": 1,
        "status_code": status_code,
    }


def result(sample_id=1, code=1, valid=1, remark="model_dreamt_gru_conf_0.800"):
    return {
        "type": "sleep_result",
        "timestamp": "2026-06-12 21:00:01",
        "sample_id": sample_id,
        "sleep_state_code": code,
        "state_valid": valid,
        "remark": remark,
    }


def assert_targets(command, expected):
    assert command["targets"] == expected, command


def main():
    state = initial_policy_state()

    command, next_state = decide_control_command(
        sensor(humidity=35.0),
        result(code=1),
        state,
        now_s=10.0,
    )
    assert command["reason"] == "humidity_low"
    assert_targets(command, {"humidifier": {"enabled": True}})
    assert next_state["last_humidifier_enabled"] is True

    command, _ = decide_control_command(
        sensor(sample_id=9, humidity=35.0, valid=0, status_code=0x01),
        result(sample_id=9, code=1),
        initial_policy_state(),
        now_s=15.0,
    )
    assert command["reason"] == "humidity_low"
    assert_targets(command, {"humidifier": {"enabled": True}})

    command, next_state = decide_control_command(
        sensor(sample_id=2, humidity=70.0),
        result(sample_id=2, code=1),
        next_state,
        now_s=20.0,
    )
    assert command["reason"] == "humidity_high"
    assert_targets(command, {"humidifier": {"enabled": False}})
    assert next_state["last_humidifier_enabled"] is False

    command, next_state = decide_control_command(
        sensor(sample_id=3, temperature=29.0, humidity=50.0),
        result(sample_id=3, code=0),
        next_state,
        now_s=30.0,
    )
    assert command["targets"]["ir_ac"]["command"] == "temp_25"
    assert command["reason"] == "temperature_high"
    assert next_state["last_ir_command"] == "temp_25"

    command, _ = decide_control_command(
        sensor(sample_id=4, temperature=29.0, humidity=50.0),
        result(sample_id=4, code=0),
        next_state,
        now_s=35.0,
    )
    assert command["targets"] == {}
    assert command["reason"] == "cooldown_same_ir_command"

    command, _ = decide_control_command(
        sensor(sample_id=5, temperature=26.0, humidity=50.0),
        result(sample_id=5, code=1, valid=0, remark="model_warmup_5_of_30"),
        next_state,
        now_s=100.0,
    )
    assert command["targets"] == {}
    assert command["reason"] == "classifier_invalid_model_warmup"

    manual = {
        "targets": {
            "ir_ac": {
                "command": "temp_26",
                "temperature_setpoint_c": 26,
            }
        }
    }
    command, next_state = decide_control_command(
        sensor(sample_id=6),
        result(sample_id=6),
        next_state,
        mode=MODE_MANUAL,
        pending_manual_command=manual,
        now_s=120.0,
    )
    assert command["mode"] == MODE_MANUAL
    assert command["reason"] == "dashboard_manual"
    assert command["targets"]["ir_ac"]["command"] == "temp_26"
    assert next_state["last_ir_command"] == "temp_26"

    command, _ = decide_control_command(
        sensor(sample_id=7),
        result(sample_id=7),
        next_state,
        mode=MODE_MANUAL,
        pending_manual_command=None,
        now_s=130.0,
    )
    assert command["mode"] == MODE_MANUAL
    assert command["targets"] == {}
    assert command["reason"] == "manual_idle"

    command, _ = decide_control_command(
        sensor(sample_id=8, temperature=None, humidity=50.0),
        result(sample_id=8, code=1),
        next_state,
        mode=MODE_AUTO,
        now_s=140.0,
    )
    assert command["targets"] == {}
    assert command["reason"] == "missing_temperature"

    print("comfort_policy_selftest PASS")


if __name__ == "__main__":
    main()
