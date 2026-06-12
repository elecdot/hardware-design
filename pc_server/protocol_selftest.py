"""Self-test for the PC/PYNQ newline-JSON protocol helpers."""

from protocol import (
    CONTROL_COMMAND,
    CONTROL_STATUS,
    SENSOR_DATA,
    SLEEP_RESULT,
    MessageBuffer,
    ProtocolError,
    build_no_action_command,
    decode_message,
    encode_message,
    validate_message,
)


def sample_sensor(sample_id=1):
    return {
        "type": SENSOR_DATA,
        "timestamp": "2026-06-12 21:00:00",
        "sample_id": sample_id,
        "heart_rate_bpm": 76,
        "spo2_percent": 98,
        "accel_x": 0.12,
        "accel_y": -0.03,
        "accel_z": 0.98,
        "gyro_x": None,
        "gyro_y": None,
        "gyro_z": None,
        "mag_x": None,
        "mag_y": None,
        "mag_z": None,
        "turnover_flag": 0,
        "turnover_count": 3,
        "temperature_c": 26,
        "humidity_percent": 38,
        "data_valid": 1,
        "status_code": 0,
        "checksum_ok": 1,
        "remark": "selftest",
    }


def sample_sleep_result(sample_id=1):
    return {
        "type": SLEEP_RESULT,
        "timestamp": "2026-06-12 21:00:01",
        "sample_id": sample_id,
        "sleep_state_code": 1,
        "state_valid": 1,
        "remark": "model_dreamt_gru_conf_0.821",
    }


def sample_control_command(sample_id=1):
    return {
        "type": CONTROL_COMMAND,
        "timestamp": "2026-06-12 21:00:01",
        "sample_id": sample_id,
        "mode": "auto",
        "policy_id": "comfort_v1",
        "targets": {
            "ir_ac": {
                "command": "temp_26",
                "temperature_setpoint_c": 26,
            },
            "humidifier": {
                "enabled": True,
            },
        },
        "valid": 1,
        "reason": "light_sleep_temp_high_humidity_low",
    }


def sample_control_status(sample_id=1):
    return {
        "type": CONTROL_STATUS,
        "timestamp": "2026-06-12 21:00:02",
        "sample_id": sample_id,
        "accepted": 1,
        "applied": {
            "ir_ac": {
                "requested": True,
                "command": "temp_26",
                "sent": True,
                "skipped": False,
                "skip_reason": None,
                "error": None,
                "status": {
                    "done": True,
                    "error": False,
                    "raw_status": 2,
                },
            },
            "humidifier": {
                "requested": True,
                "enabled": True,
                "applied": True,
                "skipped": False,
                "skip_reason": None,
                "error": None,
                "humidifier_on": True,
            },
        },
        "status_code": 0,
        "remark": "control_applied",
    }


def assert_raises_protocol_error(message):
    try:
        validate_message(message)
    except ProtocolError:
        return
    raise AssertionError("expected ProtocolError for {0}".format(message))


def main():
    messages = [
        sample_sensor(),
        sample_sleep_result(),
        sample_control_command(),
        build_no_action_command(1, reason="classifier_invalid_model_warmup"),
        sample_control_status(),
    ]

    for message in messages:
        validate_message(message)
        encoded = encode_message(message)
        decoded = decode_message(encoded)
        assert decoded == message

    buffer = MessageBuffer()
    combined = encode_message(sample_sleep_result(2)) + encode_message(sample_control_command(2))
    first = combined[:17]
    second = combined[17:]
    assert buffer.feed(first) == []
    decoded = buffer.feed(second)
    assert len(decoded) == 2
    assert decoded[0]["type"] == SLEEP_RESULT
    assert decoded[1]["type"] == CONTROL_COMMAND

    bad_command = sample_control_command()
    bad_command["targets"]["ir_ac"]["command"] = "cool_16"
    assert_raises_protocol_error(bad_command)

    bad_status = sample_control_status()
    bad_status["status_code"] = 99
    assert_raises_protocol_error(bad_status)

    print("protocol_selftest PASS")


if __name__ == "__main__":
    main()
