"""Self-test for classifier warm-up robustness around JY901-only failures."""

import tempfile
from pathlib import Path

import sleep_classifier


def sensor(sample_id, jy901_only_invalid=False, missing_spo2=False):
    data = {
        "type": "sensor_data",
        "timestamp": "2026-06-12 21:00:{0:02d}".format(sample_id % 60),
        "sample_id": sample_id,
        "heart_rate_bpm": 76 + (sample_id % 4),
        "spo2_percent": 98,
        "accel_x": 0.10,
        "accel_y": 0.20,
        "accel_z": 1.00,
        "turnover_flag": 0,
        "turnover_count": 0,
        "temperature_c": 26.0,
        "humidity_percent": 45,
        "data_valid": 1,
        "checksum_ok": 1,
        "status_code": 0,
        "remark": "selftest",
    }
    if jy901_only_invalid:
        data.update(
            {
                "data_valid": 0,
                "status_code": 0x01,
                "accel_x": None,
                "accel_y": None,
                "accel_z": None,
                "jy901_status": "ERR",
                "remark": "jy901:selftest_nack",
            }
        )
    if missing_spo2:
        data["spo2_percent"] = None
        data["data_valid"] = 0
        data["remark"] = "spo2_missing"
    return data


def main():
    original_history = sleep_classifier.HISTORY_FILE
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            sleep_classifier.HISTORY_FILE = Path(tmpdir) / "sleep_classifier_history.csv"

            for sample_id in range(1, sleep_classifier.WINDOW_POINTS):
                result = sleep_classifier.classify_sleep_state(
                    sensor(sample_id, jy901_only_invalid=(sample_id == 10))
                )
                assert result["state_valid"] == 0
                assert result["remark"] == "model_warmup_{0}_of_{1}".format(
                    sample_id,
                    sleep_classifier.WINDOW_POINTS,
                )

            result = sleep_classifier.classify_sleep_state(
                sensor(sleep_classifier.WINDOW_POINTS)
            )
            assert result["state_valid"] == 1, result
            assert result["remark"].startswith("model_dreamt_gru_conf_")

            invalid = sleep_classifier.classify_sleep_state(
                sensor(sleep_classifier.WINDOW_POINTS + 1, missing_spo2=True)
            )
            assert invalid["state_valid"] == 0
            assert invalid["remark"] == "missing_heart_rate_or_spo2"

            after_invalid = sleep_classifier.classify_sleep_state(
                sensor(sleep_classifier.WINDOW_POINTS + 2)
            )
            assert after_invalid["state_valid"] == 0
            assert after_invalid["remark"] == "model_warmup_1_of_{0}".format(
                sleep_classifier.WINDOW_POINTS
            )
    finally:
        sleep_classifier.HISTORY_FILE = original_history

    print("sleep_classifier_selftest PASS")


if __name__ == "__main__":
    main()
