"""Loopback self-test for dashboard server service integration."""

import json
import socket
import tempfile
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import dashboard_server
from classifier_adapter import SleepClassifierAdapter
from protocol import CONTROL_COMMAND, CONTROL_STATUS, MessageBuffer, encode_message
from protocol_selftest import sample_control_status, sample_sensor, sample_sleep_result
from service import SleepMonitorPcService
from storage import JsonlRecordStorage


def fake_classifier(sensor_data):
    result = sample_sleep_result(sensor_data["sample_id"])
    result["state_valid"] = 1
    result["remark"] = "dashboard_fake_classifier"
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


def run_server_once(listener, result_box):
    conn, addr = listener.accept()
    try:
        result_box["stats"] = dashboard_server.handle_client(conn, addr)
    except Exception as exc:
        result_box["error"] = exc


def request_json(server, method, path, body=None):
    host, port = server.server_address
    conn = HTTPConnection(host, port, timeout=5.0)
    payload = None
    headers = {}
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=payload, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    assert response.status < 400, raw
    return json.loads(raw.decode("utf-8"))


def request_text(server, path):
    host, port = server.server_address
    conn = HTTPConnection(host, port, timeout=5.0)
    conn.request("GET", path)
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    assert response.status == 200, raw
    return raw.decode("utf-8"), response.getheader("Content-Type")


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        dashboard_server.pc_service = SleepMonitorPcService(
            classifier_adapter=SleepClassifierAdapter(fake_classifier),
            storage=JsonlRecordStorage(tmpdir),
        )

        httpd = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            dashboard_server.DashboardHandler,
        )
        web_thread = threading.Thread(target=httpd.serve_forever)
        web_thread.daemon = True
        web_thread.start()
        try:
            html, html_type = request_text(httpd, "/")
            assert "dashboard.css" in html
            assert "dashboard.js" in html
            assert "Desired State" in html
            assert html_type.startswith("text/html")

            css, css_type = request_text(httpd, "/static/dashboard.css")
            assert ".control-btn" in css
            assert css_type.startswith("text/css")

            js, js_type = request_text(httpd, "/static/dashboard.js")
            assert "function render(data)" in js
            assert "renderDesiredState" in js
            assert js_type.startswith("application/javascript")

            mode_body = request_json(httpd, "POST", "/api/mode", {"mode": "manual"})
            assert mode_body["state"]["control_mode"] == "manual"

            control_body = request_json(
                httpd,
                "POST",
                "/api/control",
                {"command": "ac_temp_26"},
            )
            queued = control_body["control"]
            assert queued["send_status"] == "pending"
            assert queued["targets"]["ir_ac"]["command"] == "temp_26"

            state_body = request_json(httpd, "GET", "/api/state")
            assert state_body["pending_manual_command"]["targets"]["ir_ac"]["command"] == "temp_26"
            assert state_body["desired_state"]["pending"]["summary"] == "AC temp_26"
            assert state_body["desired_state"]["ir_ac"]["power"] == "unknown"
        finally:
            httpd.shutdown()
            httpd.server_close()
            web_thread.join(5.0)

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        host, port = listener.getsockname()

        result_box = {}
        server_thread = threading.Thread(
            target=run_server_once,
            args=(listener, result_box),
        )
        server_thread.daemon = True
        server_thread.start()

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((host, port))
        client.sendall(encode_message(sample_sensor(1)).encode("utf-8"))

        responses = recv_messages(client, 2)
        assert len(responses) == 2
        assert responses[1]["type"] == CONTROL_COMMAND
        assert responses[1]["mode"] == "manual"
        assert responses[1]["targets"]["ir_ac"]["command"] == "temp_26"

        status = sample_control_status(1)
        status["applied"] = {
            "ir_ac": {
                "requested": True,
                "command": "temp_26",
                "sent": True,
                "skipped": False,
                "skip_reason": None,
                "error": None,
                "status": {"done": True, "error": False, "raw_status": 2},
            }
        }
        status["remark"] = "ir_ac_sent"
        client.sendall(encode_message(status).encode("utf-8"))
        client.close()

        server_thread.join(5.0)
        listener.close()

        assert "error" not in result_box, result_box.get("error")
        assert result_box["stats"]["sensor_data"] == 1
        assert result_box["stats"]["control_status"] == 1

        snapshot = dashboard_server.snapshot_state()
        assert snapshot["latest_control_command"]["mode"] == "manual"
        assert snapshot["latest_control_status"]["type"] == CONTROL_STATUS
        assert snapshot["pending_manual_command"] is None
        assert snapshot["desired_state"]["pending"] is None
        assert snapshot["desired_state"]["ir_ac"]["power"] == "on"
        assert snapshot["desired_state"]["ir_ac"]["temperature_setpoint_c"] == 26
        assert snapshot["desired_state"]["ir_ac"]["execution"]["state"] == "sent"

    print("dashboard_server_selftest PASS")


if __name__ == "__main__":
    main()
