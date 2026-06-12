"""Self-test for the new-protocol fake PYNQ client."""

import socket
import tempfile
import threading

from classifier_adapter import SleepClassifierAdapter
from fake_pynq_client import build_fake_control_status, run_fake_client
from protocol import CONTROL_COMMAND, SENSOR_DATA, SLEEP_RESULT
from protocol_selftest import sample_control_command, sample_sleep_result
from service import SleepMonitorPcService
from socket_service import handle_client
from storage import JsonlRecordStorage


def fake_classifier(sensor_data):
    result = sample_sleep_result(sensor_data["sample_id"])
    result["sleep_state_code"] = 1
    result["state_valid"] = 1
    result["remark"] = "fake_client_test_classifier"
    return result


def run_server_once(listener, service, result_box):
    conn, addr = listener.accept()
    try:
        result_box["stats"] = handle_client(conn, addr, service)
    except Exception as exc:
        result_box["error"] = exc


def main():
    status = build_fake_control_status(sample_control_command(7))
    assert status["sample_id"] == 7
    assert status["accepted"] == 1
    assert status["applied"]["ir_ac"]["sent"] is True
    assert status["applied"]["humidifier"]["applied"] is True

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JsonlRecordStorage(tmpdir)
        service = SleepMonitorPcService(
            classifier_adapter=SleepClassifierAdapter(fake_classifier),
            storage=storage,
        )

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        host, port = listener.getsockname()

        result_box = {}
        server_thread = threading.Thread(
            target=run_server_once,
            args=(listener, service, result_box),
        )
        server_thread.daemon = True
        server_thread.start()

        stats = run_fake_client(
            host=host,
            port=port,
            samples=3,
            interval=0.0,
            timeout=5.0,
            seed=123,
            verbose=False,
        )

        server_thread.join(5.0)
        listener.close()

        assert "error" not in result_box, result_box.get("error")
        assert stats == {
            "sensor_data": 3,
            "sleep_result": 3,
            "control_command": 3,
            "control_status": 3,
        }
        assert result_box["stats"]["sensor_data"] == 3
        assert result_box["stats"]["control_status"] == 3
        assert len(storage.read_records(SENSOR_DATA)) == 3
        assert len(storage.read_records(SLEEP_RESULT)) == 3
        assert len(storage.read_records(CONTROL_COMMAND)) == 3
        assert service.snapshot()["connected"] is False

    print("fake_pynq_client_selftest PASS")


if __name__ == "__main__":
    main()
