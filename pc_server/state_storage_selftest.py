"""Self-test for PC AppState and JSONL record storage."""

import tempfile

from protocol import (
    CONTROL_COMMAND,
    CONTROL_STATUS,
    SENSOR_DATA,
    SLEEP_RESULT,
    ProtocolError,
)
from protocol_selftest import (
    sample_control_command,
    sample_control_status,
    sample_sensor,
    sample_sleep_result,
)
from state_store import AppState, MODE_AUTO, MODE_MANUAL
from storage import JsonlRecordStorage


def assert_raises_protocol_error(fn):
    try:
        fn()
    except ProtocolError:
        return
    raise AssertionError("expected ProtocolError")


def check_state_store():
    state = AppState(history_limit=2)
    snapshot = state.snapshot()
    assert snapshot["connected"] is False
    assert snapshot["control_mode"] == MODE_AUTO
    assert snapshot["latest_sensor_data"] is None

    state.set_active_client(("192.168.2.10", 51000))
    snapshot = state.snapshot()
    assert snapshot["connected"] is True
    assert snapshot["active_client"]["host"] == "192.168.2.10"

    state.set_control_mode(MODE_MANUAL)
    state.queue_manual_command(
        {
            "target": "ir_ac",
            "command": "temp_26",
            "temperature_setpoint_c": 26,
            "reason": "dashboard_manual",
        }
    )
    snapshot = state.snapshot()
    assert snapshot["control_mode"] == MODE_MANUAL
    assert snapshot["pending_manual_command"]["targets"]["ir_ac"]["command"] == "temp_26"

    pending = state.take_pending_manual_command()
    assert pending["targets"]["ir_ac"]["command"] == "temp_26"
    assert state.snapshot()["pending_manual_command"] is None

    state.queue_manual_command({"target": "humidifier", "enabled": True})
    state.set_control_mode(MODE_AUTO)
    snapshot = state.snapshot()
    assert snapshot["control_mode"] == MODE_AUTO
    assert snapshot["pending_manual_command"] is None

    state.record_sensor_cycle(
        sample_sensor(1),
        sample_sleep_result(1),
        sample_control_command(1),
    )
    state.record_control_status(sample_control_status(1))
    snapshot = state.snapshot()
    assert snapshot["latest_sensor_data"]["sample_id"] == 1
    assert snapshot["latest_sleep_result"]["sample_id"] == 1
    assert snapshot["latest_control_command"]["sample_id"] == 1
    assert snapshot["latest_control_status"]["sample_id"] == 1
    assert snapshot["last_commanded_state"]["ir_ac"]["command"] == "temp_26"
    assert len(snapshot["histories"][SENSOR_DATA]) == 1

    snapshot["latest_sensor_data"]["sample_id"] = 999
    assert state.snapshot()["latest_sensor_data"]["sample_id"] == 1

    state.record_sensor_cycle(
        sample_sensor(2),
        sample_sleep_result(2),
        sample_control_command(2),
    )
    state.record_sensor_cycle(
        sample_sensor(3),
        sample_sleep_result(3),
        sample_control_command(3),
    )
    history = state.snapshot()["histories"][SENSOR_DATA]
    assert len(history) == 2
    assert history[0]["sample_id"] == 2
    assert history[1]["sample_id"] == 3

    state.clear_active_client()
    assert state.snapshot()["connected"] is False


def check_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JsonlRecordStorage(tmpdir)
        messages = [
            sample_sensor(10),
            sample_sleep_result(10),
            sample_control_command(10),
            sample_control_status(10),
        ]

        for message in messages:
            storage.append_record(message)

        assert storage.read_records(SENSOR_DATA)[0]["sample_id"] == 10
        assert storage.read_records(SLEEP_RESULT)[0]["type"] == SLEEP_RESULT
        assert storage.read_records(CONTROL_COMMAND)[0]["type"] == CONTROL_COMMAND
        assert storage.read_records(CONTROL_STATUS)[0]["type"] == CONTROL_STATUS

        assert_raises_protocol_error(
            lambda: storage.append(SLEEP_RESULT, sample_sensor(11))
        )
        assert_raises_protocol_error(lambda: storage.read_records("unknown"))


def main():
    check_state_store()
    check_storage()
    print("state_storage_selftest PASS")


if __name__ == "__main__":
    main()
