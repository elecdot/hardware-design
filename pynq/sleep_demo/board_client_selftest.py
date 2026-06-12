"""PC-runnable loopback self-test for the PYNQ board socket client."""

import os
import socket
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
PC_SERVER = os.path.join(ROOT, "pc_server")
if PC_SERVER not in sys.path:
    sys.path.insert(0, PC_SERVER)

from board_client import run_client_session
from classifier_adapter import SleepClassifierAdapter
from protocol import CONTROL_COMMAND, CONTROL_STATUS, SENSOR_DATA, SLEEP_RESULT
from protocol_selftest import sample_sensor, sample_sleep_result
from service import SleepMonitorPcService
from socket_service import handle_client
from storage import JsonlRecordStorage


class FakeBoard(object):
    def __init__(self):
        self.sample_id = 0
        self.commands = []
        self.statuses = []
        self.display_updates = 0

    def read_sample(self):
        self.sample_id += 1
        sample = sample_sensor(self.sample_id)
        sample["humidity_percent"] = 35 if self.sample_id == 1 else 50
        return sample

    def apply_control_command(self, command):
        self.commands.append(command)
        applied = {}
        targets = command.get("targets") or {}
        if "humidifier" in targets:
            enabled = bool(targets["humidifier"].get("enabled"))
            applied["humidifier"] = {
                "requested": True,
                "enabled": enabled,
                "applied": True,
                "skipped": False,
                "skip_reason": None,
                "error": None,
                "humidifier_on": enabled,
            }
        status = {
            "type": "control_status",
            "timestamp": "2026-06-12 23:00:00",
            "sample_id": command["sample_id"],
            "accepted": 1,
            "applied": applied,
            "status_code": 0 if applied else 2,
            "remark": "fake_board_applied" if applied else command.get("reason", "no_action"),
        }
        self.statuses.append(status)
        return status

    def update_display(self, sample, status):
        self.display_updates += 1


def fake_classifier(sensor_data):
    result = sample_sleep_result(sensor_data["sample_id"])
    result["state_valid"] = 1
    result["remark"] = "board_client_fake_classifier"
    return result


def run_server_once(listener, service, result_box):
    conn, addr = listener.accept()
    try:
        result_box["stats"] = handle_client(conn, addr, service)
    except Exception as exc:
        result_box["error"] = exc


def main():
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

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((host, port))
        board = FakeBoard()
        stats = run_client_session(
            board,
            client,
            samples=2,
            interval_s=0.0,
            response_timeout_s=5.0,
            verbose=False,
        )
        client.close()
        server_thread.join(5.0)
        listener.close()

        assert "error" not in result_box, result_box.get("error")
        assert stats == {
            "sensor_data": 2,
            "sleep_result": 2,
            "control_command": 2,
            "control_status": 2,
        }
        assert len(board.commands) == 2
        assert len(board.statuses) == 2
        assert board.display_updates == 2
        assert board.commands[0]["type"] == CONTROL_COMMAND
        assert result_box["stats"]["sensor_data"] == 2
        assert result_box["stats"]["control_status"] == 2
        assert len(storage.read_records(SENSOR_DATA)) == 2
        assert len(storage.read_records(SLEEP_RESULT)) == 2
        assert len(storage.read_records(CONTROL_COMMAND)) == 2
        assert len(storage.read_records(CONTROL_STATUS)) == 2

    print("board_client_selftest PASS")


if __name__ == "__main__":
    main()
