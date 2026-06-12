"""Loopback socket self-test for the minimal PC/PYNQ TCP service."""

import socket
import tempfile
import threading

from classifier_adapter import SleepClassifierAdapter
from protocol import (
    CONTROL_COMMAND,
    CONTROL_STATUS,
    SENSOR_DATA,
    SLEEP_RESULT,
    MessageBuffer,
    encode_message,
)
from protocol_selftest import sample_control_status, sample_sensor, sample_sleep_result
from service import SleepMonitorPcService
from socket_service import handle_client
from storage import JsonlRecordStorage


def fake_classifier(sensor_data):
    result = sample_sleep_result(sensor_data["sample_id"])
    result["state_valid"] = 1
    result["remark"] = "socket_fake_classifier"
    return result


def recv_messages(sock, count):
    buffer = MessageBuffer()
    messages = []
    while len(messages) < count:
        chunk = sock.recv(4096)
        if not chunk:
            break
        messages.extend(buffer.feed(chunk))
    return messages


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

        sensor = sample_sensor(1)
        sensor["humidity_percent"] = 35
        client.sendall(encode_message(sensor).encode("utf-8"))

        responses = recv_messages(client, 2)
        assert len(responses) == 2
        assert responses[0]["type"] == SLEEP_RESULT
        assert responses[1]["type"] == CONTROL_COMMAND
        assert responses[0]["sample_id"] == 1
        assert responses[1]["sample_id"] == 1
        assert responses[1]["targets"] == {"humidifier": {"enabled": True}}

        client.sendall(encode_message(sample_control_status(1)).encode("utf-8"))
        client.close()
        server_thread.join(5.0)
        listener.close()

        assert "error" not in result_box, result_box.get("error")
        stats = result_box["stats"]
        assert stats["received"] == 2
        assert stats["sensor_data"] == 1
        assert stats["control_status"] == 1
        assert stats["sent"] == 2
        assert stats["errors"] == 0

        assert service.snapshot()["connected"] is False
        assert service.snapshot()["latest_control_status"]["sample_id"] == 1
        assert len(storage.read_records(SENSOR_DATA)) == 1
        assert len(storage.read_records(SLEEP_RESULT)) == 1
        assert len(storage.read_records(CONTROL_COMMAND)) == 1
        assert len(storage.read_records(CONTROL_STATUS)) == 1

    print("socket_service_selftest PASS")


if __name__ == "__main__":
    main()
