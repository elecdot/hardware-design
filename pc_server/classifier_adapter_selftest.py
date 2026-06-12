"""Self-test for the sleep classifier adapter."""

from classifier_adapter import SleepClassifierAdapter, classify_sensor_data
from protocol import SLEEP_RESULT, validate_message
from protocol_selftest import sample_sensor


def valid_classifier(sensor_data):
    return {
        "type": SLEEP_RESULT,
        "timestamp": "2026-06-12 22:00:00",
        "sample_id": sensor_data["sample_id"],
        "sleep_state_code": 2,
        "state_valid": 1,
        "remark": "fake_conf_0.900",
    }


def minimal_classifier(_sensor_data):
    return {
        "sleep_state_code": 1,
        "state_valid": 1,
        "remark": "minimal_fake",
    }


def invalid_classifier(_sensor_data):
    return {
        "type": SLEEP_RESULT,
        "timestamp": "2026-06-12 22:00:00",
        "sample_id": 99,
        "sleep_state_code": 99,
        "state_valid": 1,
        "remark": "bad_code",
    }


def raising_classifier(_sensor_data):
    raise RuntimeError("model unavailable")


def main():
    adapter = SleepClassifierAdapter(classifier=valid_classifier)
    result = adapter.classify(sample_sensor(12))
    validate_message(result, expected_type=SLEEP_RESULT)
    assert result["sample_id"] == 12
    assert result["sleep_state_code"] == 2
    assert result["state_valid"] == 1
    assert adapter.last_error is None

    adapter = SleepClassifierAdapter(classifier=minimal_classifier)
    result = adapter.classify(sample_sensor(13))
    validate_message(result, expected_type=SLEEP_RESULT)
    assert result["sample_id"] == 13
    assert result["sleep_state_code"] == 1

    adapter = SleepClassifierAdapter(classifier=invalid_classifier)
    result = adapter.classify(sample_sensor(14))
    validate_message(result, expected_type=SLEEP_RESULT)
    assert result["sample_id"] == 14
    assert result["state_valid"] == 0
    assert result["remark"].startswith("classifier_error:")
    assert "sleep_state_code" in adapter.last_error

    adapter = SleepClassifierAdapter(classifier=raising_classifier)
    result = adapter.classify(sample_sensor(15))
    validate_message(result, expected_type=SLEEP_RESULT)
    assert result["sample_id"] == 15
    assert result["state_valid"] == 0
    assert result["remark"].startswith("classifier_error:")
    assert "model unavailable" in adapter.last_error

    bad_sensor = sample_sensor(16)
    bad_sensor["data_valid"] = "bad"
    result = adapter.classify(bad_sensor)
    validate_message(result, expected_type=SLEEP_RESULT)
    assert result["sample_id"] == 16
    assert result["state_valid"] == 0
    assert result["remark"].startswith("classifier_input_invalid:")

    result = classify_sensor_data(sample_sensor(17), adapter=SleepClassifierAdapter(valid_classifier))
    assert result["sample_id"] == 17

    print("classifier_adapter_selftest PASS")


if __name__ == "__main__":
    main()
