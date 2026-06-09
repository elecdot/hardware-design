"""
dashboard_server.py

PC 端可视化服务端。

功能：
1. 保持原有 TCP socket 协议，接收硬件 / fake client 的 sensor_data。
2. 保存 Excel、推算睡眠状态，并把 sleep_result 回传给硬件。
3. 同时启动 Web 控制台，实时显示传感器数据和睡眠状态。
4. Web 控制台可以切换自动/手动模式；手动设备控制会在内部映射为 sleep_result 回传。

运行：
    python dashboard_server.py

浏览器打开：
    http://127.0.0.1:8080
"""

import json
import socket
import threading
import traceback
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from excel_utils import init_excel, append_sensor_data, append_sleep_result
from protocol_config import SERVER_HOST, SERVER_PORT, MESSAGE_END, SLEEP_STATE_NAME
from sleep_classifier import classify_sleep_state, get_sleep_state_text


DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8080

# 手动控制区仍展示设备动作；为了兼容硬件端现有协议，内部映射成 sleep_state_code。
MANUAL_CONTROL_OPTIONS = {
    "fan_off": {"label": "关闭风扇", "sleep_state_code": 2},
    "fan_low": {"label": "风扇低速", "sleep_state_code": 1},
    "fan_high": {"label": "风扇高速", "sleep_state_code": 0},
    "warm_on": {"label": "开启保温", "sleep_state_code": 2},
    "warm_off": {"label": "关闭保温", "sleep_state_code": 0},
    "night_mode": {"label": "夜间模式", "sleep_state_code": 2},
}


state_lock = threading.Lock()
send_lock = threading.Lock()
event_condition = threading.Condition()

latest_sensor = None
latest_result = None
latest_outgoing_result = None
active_conn = None
active_addr = None
last_update_at = None
last_transmit_at = None
event_version = 0
control_history = []
data_history = []
data_sequence = 0
control_mode = "auto"
manual_control_key = "fan_low"


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def send_json(conn: socket.socket, obj: dict):
    msg = json.dumps(obj, ensure_ascii=False) + MESSAGE_END
    conn.sendall(msg.encode("utf-8"))


def recv_json_lines(conn: socket.socket):
    buffer = ""

    while True:
        chunk = conn.recv(4096)

        if not chunk:
            break

        buffer += chunk.decode("utf-8")

        while MESSAGE_END in buffer:
            line, buffer = buffer.split(MESSAGE_END, 1)
            line = line.strip()

            if not line:
                continue

            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print("[ERROR] JSON 解析失败:", e)
                print("[ERROR] 原始数据:", line)


def snapshot_state() -> dict:
    with state_lock:
        result = dict(latest_result) if latest_result else None
        if result and "sleep_state_name" not in result:
            code = result.get("sleep_state_code")
            result["sleep_state_name"] = get_sleep_state_text(code)

        outgoing_result = dict(latest_outgoing_result) if latest_outgoing_result else None
        if outgoing_result and "sleep_state_name" not in outgoing_result:
            code = outgoing_result.get("sleep_state_code")
            outgoing_result["sleep_state_name"] = get_sleep_state_text(code)

        manual_option = MANUAL_CONTROL_OPTIONS[manual_control_key]

        return {
            "connected": active_conn is not None,
            "client_addr": f"{active_addr[0]}:{active_addr[1]}" if active_addr else None,
            "last_update_at": last_update_at,
            "last_transmit_at": last_transmit_at,
            "sensor": dict(latest_sensor) if latest_sensor else None,
            "result": result,
            "outgoing_result": outgoing_result,
            "sleep_states": SLEEP_STATE_NAME,
            "control_mode": control_mode,
            "manual_control_key": manual_control_key,
            "manual_control_label": manual_option["label"],
            "manual_signal_code": manual_option["sleep_state_code"],
            "manual_signal_name": get_sleep_state_text(manual_option["sleep_state_code"]),
            "manual_control_options": MANUAL_CONTROL_OPTIONS,
            "control_history": list(control_history[-8:]),
            "data_history": list(data_history),
            "event_version": event_version,
        }


def publish_update():
    global event_version

    with event_condition:
        event_version += 1
        event_condition.notify_all()


def set_active_client(conn: socket.socket, addr):
    global active_conn, active_addr

    with state_lock:
        active_conn = conn
        active_addr = addr
    publish_update()


def clear_active_client(conn: socket.socket):
    global active_conn, active_addr

    with state_lock:
        if active_conn is conn:
            active_conn = None
            active_addr = None
    publish_update()


def update_sensor_state(sensor: dict, result: dict, outgoing_result: dict):
    global latest_sensor, latest_result, latest_outgoing_result
    global last_update_at, last_transmit_at
    global data_history, data_sequence

    result_with_name = dict(result)
    result_with_name["sleep_state_name"] = get_sleep_state_text(
        result_with_name.get("sleep_state_code")
    )

    outgoing_with_name = dict(outgoing_result)
    outgoing_with_name["sleep_state_name"] = get_sleep_state_text(
        outgoing_with_name.get("sleep_state_code")
    )

    with state_lock:
        updated_at = now_text()
        latest_sensor = dict(sensor)
        latest_result = result_with_name
        latest_outgoing_result = outgoing_with_name
        last_update_at = updated_at
        last_transmit_at = outgoing_with_name.get("timestamp")
        data_sequence += 1
        data_history.append(
            {
                "id": data_sequence,
                "timestamp": sensor.get("timestamp") or updated_at,
                "sample_id": sensor.get("sample_id"),
                "sensor_data": dict(sensor),
                "model_sleep_result": result_with_name,
                "outgoing_sleep_result": outgoing_with_name,
            }
        )
    publish_update()


def build_sleep_result(sample_id: int, sleep_state_code: int, remark: str) -> dict:
    return {
        "type": "sleep_result",
        "timestamp": now_text(),
        "sample_id": sample_id,
        "sleep_state_code": sleep_state_code,
        "state_valid": 1,
        "remark": remark,
    }


def build_manual_sleep_result(base_result=None) -> dict:
    with state_lock:
        selected_key = manual_control_key
        selected_option = MANUAL_CONTROL_OPTIONS[selected_key]

    sample_id = base_result.get("sample_id", -1) if base_result else -1
    return build_sleep_result(
        sample_id,
        selected_option["sleep_state_code"],
        f"manual_override_{selected_key}",
    )


def select_outgoing_result(model_result: dict) -> dict:
    with state_lock:
        mode = control_mode

    if mode == "manual":
        return build_manual_sleep_result(model_result)

    outgoing = dict(model_result)
    outgoing["remark"] = f"auto_{outgoing.get('remark', 'model_result')}"
    return outgoing


def set_control_mode(mode: str) -> dict:
    global control_mode

    if mode not in {"auto", "manual"}:
        raise ValueError("unknown_mode")

    with state_lock:
        control_mode = mode

    publish_update()
    return snapshot_state()


def send_selected_manual_control(command_key: str) -> dict:
    global control_history, manual_control_key, latest_outgoing_result, last_transmit_at

    if command_key not in MANUAL_CONTROL_OPTIONS:
        raise ValueError("unknown_command")

    with state_lock:
        manual_control_key = command_key
        conn = active_conn
        mode = control_mode
        base_result = dict(latest_result) if latest_result else None

    hardware_packet = build_manual_sleep_result(base_result)
    history_packet = dict(hardware_packet)
    history_packet["sleep_state_name"] = get_sleep_state_text(
        hardware_packet["sleep_state_code"]
    )
    history_packet["manual_control_key"] = command_key
    history_packet["command_name"] = MANUAL_CONTROL_OPTIONS[command_key]["label"]

    if mode != "manual":
        history_packet["send_status"] = "mode_auto"
    elif conn is None:
        history_packet["send_status"] = "no_client"
    else:
        try:
            with send_lock:
                send_json(conn, hardware_packet)
            history_packet["send_status"] = "sent"
            print("[MANUAL_SEND]", hardware_packet)
        except OSError as exc:
            history_packet["send_status"] = "send_failed"
            history_packet["error"] = str(exc)

    outgoing_result = {
        key: hardware_packet[key]
        for key in ("type", "timestamp", "sample_id", "sleep_state_code", "state_valid", "remark")
        if key in hardware_packet
    }

    with state_lock:
        latest_outgoing_result = dict(outgoing_result)
        if history_packet["send_status"] == "sent":
            last_transmit_at = hardware_packet["timestamp"]
        control_history.append(history_packet)
        control_history = control_history[-30:]

    publish_update()
    return history_packet


def handle_client(conn: socket.socket, addr):
    print(f"[INFO] 客户端已连接: {addr}")
    set_active_client(conn, addr)

    try:
        for data in recv_json_lines(conn):
            print("[RECV]", data)

            if data.get("type") != "sensor_data":
                print("[WARN] 收到非 sensor_data 类型，已忽略:", data.get("type"))
                continue

            append_sensor_data(data)

            result = classify_sleep_state(data)
            append_sleep_result(result)

            outgoing_result = select_outgoing_result(result)

            with send_lock:
                send_json(conn, outgoing_result)

            update_sensor_state(data, result, outgoing_result)

            code = outgoing_result.get("sleep_state_code")
            state_text = get_sleep_state_text(code)
            print(
                f"[SEND] sample_id={result.get('sample_id')} "
                f"state={code}({state_text})"
            )

    except ConnectionResetError:
        print("[WARN] 客户端连接被重置")
    except Exception:
        print("[ERROR] 服务端处理客户端时发生异常：")
        traceback.print_exc()
    finally:
        clear_active_client(conn)
        conn.close()
        print(f"[INFO] 客户端已断开: {addr}")


def run_socket_server():
    init_excel()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(5)

    print("=" * 60)
    print("[INFO] PC socket 服务端启动成功")
    print(f"[INFO] 监听地址: {SERVER_HOST}:{SERVER_PORT}")
    print("[INFO] 提醒：程序运行时不要打开 sleep_monitor_data.xlsx")
    print("=" * 60)

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    finally:
        server.close()


class DashboardHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("[WEB]", fmt % args)

    def send_body(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json_body(self, status: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_body(status, body, "application/json; charset=utf-8")

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.send_body(HTTPStatus.OK, DASHBOARD_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return

        if path == "/api/state":
            self.send_json_body(HTTPStatus.OK, snapshot_state())
            return

        if path == "/events":
            self.handle_events()
            return

        self.send_json_body(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path

        if path not in {"/api/control", "/api/mode"}:
            self.send_json_body(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length else b"{}"

        try:
            body = json.loads(raw_body.decode("utf-8"))
            if path == "/api/mode":
                state = set_control_mode(body.get("mode"))
                self.send_json_body(HTTPStatus.OK, {"state": state})
                return

            command_key = body.get("command")
            packet = send_selected_manual_control(command_key)
            self.send_json_body(HTTPStatus.OK, {"control": packet, "state": snapshot_state()})
        except ValueError:
            self.send_json_body(HTTPStatus.BAD_REQUEST, {"error": "invalid_request"})
        except json.JSONDecodeError:
            self.send_json_body(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})

    def handle_events(self):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        last_version = -1

        while True:
            data = snapshot_state()
            version = data["event_version"]

            if version != last_version:
                payload = json.dumps(data, ensure_ascii=False)
                try:
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break
                last_version = version

            with event_condition:
                event_condition.wait(timeout=10)


def run_web_server():
    httpd = ThreadingHTTPServer((DASHBOARD_HOST, DASHBOARD_PORT), DashboardHandler)
    print(f"[INFO] Web 控制台启动成功: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    httpd.serve_forever()


DASHBOARD_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>睡眠监测控制台</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #65717d;
      --line: #dce3ea;
      --panel: #ffffff;
      --bg: #eef3f7;
      --brand: #246bfe;
      --brand-soft: #e7efff;
      --aqua: #0f9f9a;
      --green: #2c9f68;
      --orange: #d17916;
      --red: #d84a4a;
      --shadow: 0 18px 45px rgba(42, 61, 83, 0.13);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(135deg, rgba(36, 107, 254, 0.12), rgba(15, 159, 154, 0.08) 42%, transparent 72%),
        var(--bg);
      color: var(--ink);
      font-family: Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
      letter-spacing: 0;
    }

    button, input {
      font: inherit;
    }

    .app {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 34px;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 16px 0 24px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 13px;
      min-width: 0;
    }

    .mark {
      width: 48px;
      height: 48px;
      border-radius: 8px;
      background: linear-gradient(145deg, #246bfe, #0f9f9a);
      box-shadow: 0 10px 24px rgba(36, 107, 254, 0.28);
      position: relative;
      flex: 0 0 auto;
    }

    .mark::before {
      content: "";
      position: absolute;
      width: 22px;
      height: 22px;
      border-radius: 50%;
      top: 9px;
      left: 10px;
      box-shadow: 8px 3px 0 0 rgba(255, 255, 255, 0.94);
      transform: rotate(-28deg);
    }

    .mark::after {
      content: "";
      position: absolute;
      left: 12px;
      right: 12px;
      bottom: 12px;
      height: 4px;
      border-radius: 99px;
      background: rgba(255, 255, 255, 0.9);
    }

    h1 {
      margin: 0;
      font-size: clamp(24px, 3vw, 36px);
      line-height: 1.15;
      letter-spacing: 0;
    }

    .subtitle {
      margin-top: 5px;
      color: var(--muted);
      font-size: 14px;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 36px;
      padding: 7px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.72);
      color: var(--muted);
      white-space: nowrap;
    }

    .dot {
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--red);
      box-shadow: 0 0 0 4px rgba(216, 74, 74, 0.12);
    }

    .dot.connected {
      background: var(--green);
      box-shadow: 0 0 0 4px rgba(44, 159, 104, 0.14);
    }

    .modebar {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 14px;
      margin: -4px 0 22px;
    }

    .mode-label {
      color: var(--muted);
      font-size: 14px;
      font-weight: 700;
      white-space: nowrap;
    }

    .mode-label.active {
      color: var(--ink);
    }

    .switch {
      position: relative;
      width: 70px;
      height: 36px;
      display: inline-block;
    }

    .switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .slider {
      position: absolute;
      inset: 0;
      cursor: pointer;
      border-radius: 999px;
      background: var(--brand);
      box-shadow: inset 0 0 0 1px rgba(23, 32, 42, 0.08), 0 10px 24px rgba(36, 107, 254, 0.18);
      transition: background 0.18s ease;
    }

    .slider::before {
      content: "";
      position: absolute;
      width: 28px;
      height: 28px;
      left: 4px;
      top: 4px;
      border-radius: 50%;
      background: #fff;
      box-shadow: 0 5px 12px rgba(23, 32, 42, 0.24);
      transition: transform 0.18s ease;
    }

    .switch input:checked + .slider {
      background: var(--aqua);
    }

    .switch input:checked + .slider::before {
      transform: translateX(34px);
    }

    .mode-hint {
      min-height: 22px;
      padding: 4px 10px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.72);
      font-size: 12px;
      white-space: nowrap;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 18px;
      align-items: start;
    }

    .panel {
      background: rgba(255, 255, 255, 0.88);
      border: 1px solid rgba(220, 227, 234, 0.92);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 18px 20px 14px;
      border-bottom: 1px solid var(--line);
    }

    .panel-title {
      margin: 0;
      font-size: 17px;
      letter-spacing: 0;
    }

    .panel-note {
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }

    .state-band {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 16px;
      align-items: center;
      padding: 22px 20px;
      background: linear-gradient(135deg, #f8fbff, #eef8f6);
      border-bottom: 1px solid var(--line);
    }

    .state-label {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 4px;
    }

    .state-value {
      font-size: clamp(30px, 5vw, 52px);
      line-height: 1;
      font-weight: 750;
      letter-spacing: 0;
    }

    .state-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 86px;
      height: 86px;
      border-radius: 8px;
      color: #fff;
      background: var(--brand);
      font-size: 28px;
      font-weight: 800;
      box-shadow: 0 14px 30px rgba(36, 107, 254, 0.24);
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      padding: 16px;
    }

    .metric {
      min-height: 128px;
      padding: 15px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 12px;
    }

    .metric-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
    }

    .icon {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      display: inline-grid;
      place-items: center;
      flex: 0 0 auto;
      background: var(--brand-soft);
      color: var(--brand);
    }

    .icon svg {
      width: 19px;
      height: 19px;
      stroke: currentColor;
      stroke-width: 2.2;
      fill: none;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .metric-value {
      font-size: 32px;
      line-height: 1;
      font-weight: 760;
      letter-spacing: 0;
    }

    .unit {
      margin-left: 5px;
      color: var(--muted);
      font-size: 14px;
      font-weight: 600;
    }

    .metric-foot {
      min-height: 18px;
      color: var(--muted);
      font-size: 12px;
    }

    .control-panel {
      position: sticky;
      top: 18px;
    }

    .controls {
      display: grid;
      gap: 10px;
      padding: 16px;
    }

    .control-btn {
      width: 100%;
      min-height: 48px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 14px;
      cursor: pointer;
      transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
    }

    .control-btn:hover {
      transform: translateY(-1px);
      border-color: rgba(36, 107, 254, 0.45);
      box-shadow: 0 12px 24px rgba(42, 61, 83, 0.11);
    }

    .control-btn.active {
      border-color: rgba(15, 159, 154, 0.64);
      background: #f0fbf9;
      box-shadow: 0 10px 22px rgba(15, 159, 154, 0.12);
    }

    .control-btn:disabled {
      cursor: not-allowed;
      opacity: 0.52;
      transform: none;
      box-shadow: none;
    }

    .btn-main {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }

    .btn-label {
      font-weight: 700;
      white-space: nowrap;
    }

    .btn-code {
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }

    .history {
      border-top: 1px solid var(--line);
      padding: 14px 16px 16px;
    }

    .history-title {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 10px;
    }

    .history-list {
      display: grid;
      gap: 8px;
    }

    .history-item {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      padding: 9px 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
      color: var(--muted);
      font-size: 12px;
    }

    .history-item strong {
      display: block;
      color: var(--ink);
      font-size: 13px;
      margin-bottom: 2px;
    }

    .sent {
      color: var(--green);
      font-weight: 700;
    }

    .failed {
      color: var(--red);
      font-weight: 700;
    }

    .debug-toggle {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 0 16px 16px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
    }

    .debug-toggle-text {
      min-width: 0;
    }

    .debug-title {
      font-weight: 800;
      margin-bottom: 2px;
    }

    .debug-subtitle {
      color: var(--muted);
      font-size: 12px;
    }

    .mini-switch {
      position: relative;
      width: 52px;
      height: 28px;
      flex: 0 0 auto;
      display: inline-block;
    }

    .mini-switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .mini-slider {
      position: absolute;
      inset: 0;
      border-radius: 999px;
      background: #cfd8e2;
      cursor: pointer;
      transition: background 0.18s ease;
    }

    .mini-slider::before {
      content: "";
      position: absolute;
      width: 22px;
      height: 22px;
      left: 3px;
      top: 3px;
      border-radius: 50%;
      background: #fff;
      box-shadow: 0 4px 10px rgba(23, 32, 42, 0.22);
      transition: transform 0.18s ease;
    }

    .mini-switch input:checked + .mini-slider {
      background: var(--brand);
    }

    .mini-switch input:checked + .mini-slider::before {
      transform: translateX(24px);
    }

    .debug-panel {
      display: none;
      grid-template-columns: 220px minmax(0, 1fr);
      gap: 0;
      margin: 0 16px 16px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      overflow: hidden;
      min-height: 260px;
    }

    .debug-panel.open {
      display: grid;
    }

    .debug-list {
      border-right: 1px solid var(--line);
      background: #f8fbff;
      max-height: 360px;
      overflow: auto;
    }

    .debug-item {
      width: 100%;
      border: 0;
      border-bottom: 1px solid var(--line);
      background: transparent;
      color: var(--ink);
      text-align: left;
      padding: 10px 12px;
      cursor: pointer;
    }

    .debug-item:hover,
    .debug-item.active {
      background: var(--brand-soft);
    }

    .debug-item strong {
      display: block;
      font-size: 13px;
      margin-bottom: 3px;
    }

    .debug-item span {
      color: var(--muted);
      font-size: 12px;
    }

    .debug-empty {
      padding: 14px;
      color: var(--muted);
      font-size: 13px;
    }

    .debug-detail {
      margin: 0;
      padding: 14px;
      background: #101820;
      color: #d9edf0;
      font-size: 12px;
      line-height: 1.5;
      overflow: auto;
      max-height: 360px;
    }

    @media (max-width: 900px) {
      .layout {
        grid-template-columns: 1fr;
      }

      .control-panel {
        position: static;
      }
    }

    @media (max-width: 680px) {
      .app {
        width: min(100% - 20px, 1180px);
        padding-top: 14px;
      }

      .topbar {
        align-items: flex-start;
        flex-direction: column;
      }

      .modebar {
        flex-wrap: wrap;
        justify-content: flex-start;
      }

      .metrics {
        grid-template-columns: 1fr;
      }

      .debug-panel.open {
        grid-template-columns: 1fr;
      }

      .debug-list {
        border-right: 0;
        border-bottom: 1px solid var(--line);
        max-height: 180px;
      }

      .state-band {
        grid-template-columns: 1fr;
      }

      .state-badge {
        width: 86px;
      }
    }
  </style>
</head>
<body>
  <main class="app">
    <header class="topbar">
      <div class="brand">
        <div class="mark" aria-hidden="true"></div>
        <div>
          <h1>睡眠监测控制台</h1>
          <div class="subtitle">PC 服务端 · 传感器实时状态 · 硬件控制回传</div>
        </div>
      </div>
      <div class="status-pill">
        <span id="connDot" class="dot"></span>
        <span id="connText">等待硬件连接</span>
      </div>
    </header>

    <div class="modebar">
      <span id="autoLabel" class="mode-label active">自动控制</span>
      <label class="switch" title="切换自动控制和手动控制">
        <input id="modeSwitch" type="checkbox">
        <span class="slider"></span>
      </label>
      <span id="manualLabel" class="mode-label">手动控制</span>
      <span id="modeHint" class="mode-hint">按模型结果回传硬件</span>
    </div>

    <section class="layout">
      <div class="panel">
        <div class="panel-head">
          <h2 class="panel-title">显示区</h2>
          <div id="lastUpdate" class="panel-note">暂无采样</div>
        </div>

        <div class="state-band">
          <div>
            <div class="state-label">推算睡眠状态</div>
            <div id="sleepState" class="state-value">等待数据</div>
          </div>
          <div id="stateBadge" class="state-badge">--</div>
        </div>

        <div class="metrics">
          <article class="metric">
            <div class="metric-top">
              <span>心率</span>
              <span class="icon"><svg viewBox="0 0 24 24"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z"/></svg></span>
            </div>
            <div><span id="heartRate" class="metric-value">--</span><span class="unit">bpm</span></div>
            <div id="heartHint" class="metric-foot">等待传感器上传</div>
          </article>

          <article class="metric">
            <div class="metric-top">
              <span>血氧</span>
              <span class="icon"><svg viewBox="0 0 24 24"><path d="M12 2.5S6 9.2 6 14a6 6 0 0 0 12 0c0-4.8-6-11.5-6-11.5Z"/><path d="M9 14h6"/></svg></span>
            </div>
            <div><span id="spo2" class="metric-value">--</span><span class="unit">%</span></div>
            <div id="spo2Hint" class="metric-foot">等待传感器上传</div>
          </article>

          <article class="metric">
            <div class="metric-top">
              <span>温度</span>
              <span class="icon"><svg viewBox="0 0 24 24"><path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0Z"/><path d="M12 9v7"/></svg></span>
            </div>
            <div><span id="temperature" class="metric-value">--</span><span class="unit">°C</span></div>
            <div id="tempHint" class="metric-foot">等待传感器上传</div>
          </article>

          <article class="metric">
            <div class="metric-top">
              <span>湿度</span>
              <span class="icon"><svg viewBox="0 0 24 24"><path d="M12 3v18"/><path d="M7 8a5 5 0 0 0 10 0"/><path d="M5 14a7 7 0 0 0 14 0"/></svg></span>
            </div>
            <div><span id="humidity" class="metric-value">--</span><span class="unit">%</span></div>
            <div id="humidityHint" class="metric-foot">等待传感器上传</div>
          </article>

          <article class="metric">
            <div class="metric-top">
              <span>翻身次数</span>
              <span class="icon"><svg viewBox="0 0 24 24"><path d="M3 12h18"/><path d="m8 7-5 5 5 5"/><path d="m16 7 5 5-5 5"/></svg></span>
            </div>
            <div><span id="turnover" class="metric-value">--</span><span class="unit">次</span></div>
            <div id="turnoverHint" class="metric-foot">等待传感器上传</div>
          </article>

          <article class="metric">
            <div class="metric-top">
              <span>体动加速度</span>
              <span class="icon"><svg viewBox="0 0 24 24"><path d="M4 17 10 7l4 6 2-3 4 7"/><path d="M4 20h16"/></svg></span>
            </div>
            <div><span id="accel" class="metric-value">--</span><span class="unit">g</span></div>
            <div id="accelHint" class="metric-foot">等待传感器上传</div>
          </article>
        </div>

        <div class="debug-toggle">
          <div class="debug-toggle-text">
            <div class="debug-title">调试信息</div>
            <div class="debug-subtitle">查看已收到的传感器 JSON 与回传结果</div>
          </div>
          <label class="mini-switch" title="显示或隐藏调试信息">
            <input id="debugSwitch" type="checkbox">
            <span class="mini-slider"></span>
          </label>
        </div>

        <div id="debugPanel" class="debug-panel">
          <div id="debugList" class="debug-list">
            <div class="debug-empty">暂无数据</div>
          </div>
          <pre id="debugDetail" class="debug-detail">选择左侧记录查看详情</pre>
        </div>
      </div>

      <aside class="panel control-panel">
        <div class="panel-head">
          <h2 class="panel-title">控制区</h2>
          <div class="panel-note">手动设备控制</div>
        </div>

        <div class="controls">
          <button class="control-btn" data-command="fan_off">
            <span class="btn-main"><span class="icon"><svg viewBox="0 0 24 24"><path d="M12 12 4 7a6 6 0 0 1 8 5Z"/><path d="m12 12 8-5a6 6 0 0 1-8 5Z"/><path d="m12 12 1 9a6 6 0 0 1-1-9Z"/><path d="m12 12-1-9a6 6 0 0 1 1 9Z"/><circle cx="12" cy="12" r="2"/></svg></span><span class="btn-label">关闭风扇</span></span>
            <span class="btn-code">FAN 0</span>
          </button>
          <button class="control-btn" data-command="fan_low">
            <span class="btn-main"><span class="icon"><svg viewBox="0 0 24 24"><path d="M12 12 4 7a6 6 0 0 1 8 5Z"/><path d="m12 12 8-5a6 6 0 0 1-8 5Z"/><path d="m12 12 1 9a6 6 0 0 1-1-9Z"/><path d="m12 12-1-9a6 6 0 0 1 1 9Z"/><circle cx="12" cy="12" r="2"/></svg></span><span class="btn-label">风扇低速</span></span>
            <span class="btn-code">FAN 1</span>
          </button>
          <button class="control-btn" data-command="fan_high">
            <span class="btn-main"><span class="icon"><svg viewBox="0 0 24 24"><path d="M12 12 4 7a6 6 0 0 1 8 5Z"/><path d="m12 12 8-5a6 6 0 0 1-8 5Z"/><path d="m12 12 1 9a6 6 0 0 1-1-9Z"/><path d="m12 12-1-9a6 6 0 0 1 1 9Z"/><circle cx="12" cy="12" r="2"/></svg></span><span class="btn-label">风扇高速</span></span>
            <span class="btn-code">FAN 2</span>
          </button>
          <button class="control-btn" data-command="warm_on">
            <span class="btn-main"><span class="icon"><svg viewBox="0 0 24 24"><path d="M8 14a4 4 0 1 0 8 0c0-3-4-8-4-8s-4 5-4 8Z"/><path d="M12 2v4"/></svg></span><span class="btn-label">开启保温</span></span>
            <span class="btn-code">TEMP +</span>
          </button>
          <button class="control-btn" data-command="warm_off">
            <span class="btn-main"><span class="icon"><svg viewBox="0 0 24 24"><path d="M8 14a4 4 0 1 0 8 0c0-3-4-8-4-8s-4 5-4 8Z"/><path d="M4 4l16 16"/></svg></span><span class="btn-label">关闭保温</span></span>
            <span class="btn-code">TEMP -</span>
          </button>
          <button class="control-btn" data-command="night_mode">
            <span class="btn-main"><span class="icon"><svg viewBox="0 0 24 24"><path d="M20 14.5A7.5 7.5 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"/></svg></span><span class="btn-label">夜间模式</span></span>
            <span class="btn-code">MODE</span>
          </button>
        </div>

        <div class="history">
          <div class="history-title">最近控制指令</div>
          <div id="historyList" class="history-list">
            <div class="history-item"><span>暂无控制记录</span><span>--</span></div>
          </div>
        </div>
      </aside>
    </section>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);
    let selectedDebugId = null;

    function valueOrDash(value, digits = null) {
      if (value === null || value === undefined || value === "") return "--";
      if (typeof value === "number" && digits !== null) return value.toFixed(digits);
      return value;
    }

    function classifyHint(type, value) {
      if (value === null || value === undefined) return "等待传感器上传";
      if (type === "heart") {
        if (value >= 80) return "心率相对偏高";
        if (value >= 65) return "心率处于平稳区间";
        return "心率较低，身体较放松";
      }
      if (type === "spo2") return value >= 95 ? "血氧处于正常观察范围" : "血氧偏低，需要关注";
      if (type === "temp") return value > 28 ? "温度偏高，可考虑风扇" : "温度处于舒适范围";
      if (type === "humidity") return value > 65 ? "湿度偏高" : "湿度处于舒适范围";
      if (type === "turnover") return value >= 5 ? "翻身较频繁" : "体动较少";
      return "三轴加速度合成值";
    }

    function stateColor(code) {
      if (code === 0) return "#d17916";
      if (code === 1) return "#246bfe";
      if (code === 2) return "#0f9f9a";
      return "#65717d";
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function renderDebug(history) {
      const records = history || [];

      if (!records.length) {
        selectedDebugId = null;
        $("debugList").innerHTML = `<div class="debug-empty">暂无数据</div>`;
        $("debugDetail").textContent = "暂无调试信息";
        return;
      }

      if (!records.some((item) => item.id === selectedDebugId)) {
        selectedDebugId = records[records.length - 1].id;
      }

      $("debugList").innerHTML = records.slice().reverse().map((item) => {
        const active = item.id === selectedDebugId ? " active" : "";
        const sample = item.sample_id === null || item.sample_id === undefined ? "--" : item.sample_id;
        return `<button class="debug-item${active}" data-id="${item.id}">
          <strong>${escapeHtml(item.timestamp || "未知时间")}</strong>
          <span>sample_id: ${escapeHtml(sample)}</span>
        </button>`;
      }).join("");

      document.querySelectorAll(".debug-item").forEach((button) => {
        button.addEventListener("click", () => {
          selectedDebugId = Number(button.dataset.id);
          renderDebug(records);
        });
      });

      const selected = records.find((item) => item.id === selectedDebugId) || records[records.length - 1];
      $("debugDetail").textContent = JSON.stringify(selected, null, 2);
    }

    function render(data) {
      $("connDot").classList.toggle("connected", Boolean(data.connected));
      $("connText").textContent = data.connected ? `硬件已连接 ${data.client_addr || ""}` : "等待硬件连接";
      $("lastUpdate").textContent = data.last_update_at ? `最近采样 ${data.last_update_at}` : "暂无采样";

      const manualMode = data.control_mode === "manual";
      $("modeSwitch").checked = manualMode;
      $("autoLabel").classList.toggle("active", !manualMode);
      $("manualLabel").classList.toggle("active", manualMode);
      $("modeHint").textContent = manualMode
        ? `手动控制：${data.manual_control_label || "风扇低速"}`
        : "按实时状态自动调节";

      const sensor = data.sensor || {};
      const result = data.result || {};
      const code = result.sleep_state_code;
      const stateName = result.sleep_state_name || "等待数据";

      $("sleepState").textContent = stateName;
      $("stateBadge").textContent = code === undefined || code === null ? "--" : code;
      $("stateBadge").style.background = stateColor(code);

      $("heartRate").textContent = valueOrDash(sensor.heart_rate_bpm);
      $("spo2").textContent = valueOrDash(sensor.spo2_percent);
      $("temperature").textContent = valueOrDash(sensor.temperature_c);
      $("humidity").textContent = valueOrDash(sensor.humidity_percent);
      $("turnover").textContent = valueOrDash(sensor.turnover_count);

      const ax = Number(sensor.accel_x || 0);
      const ay = Number(sensor.accel_y || 0);
      const az = Number(sensor.accel_z || 0);
      const accelMagnitude = sensor.accel_x === undefined ? null : Math.sqrt(ax * ax + ay * ay + az * az);
      $("accel").textContent = valueOrDash(accelMagnitude, 2);

      $("heartHint").textContent = classifyHint("heart", sensor.heart_rate_bpm);
      $("spo2Hint").textContent = classifyHint("spo2", sensor.spo2_percent);
      $("tempHint").textContent = classifyHint("temp", sensor.temperature_c);
      $("humidityHint").textContent = classifyHint("humidity", sensor.humidity_percent);
      $("turnoverHint").textContent = classifyHint("turnover", sensor.turnover_count);
      $("accelHint").textContent = accelMagnitude === null ? "等待传感器上传" : `x=${valueOrDash(sensor.accel_x)} y=${valueOrDash(sensor.accel_y)} z=${valueOrDash(sensor.accel_z)}`;
      renderDebug(data.data_history || []);

      document.querySelectorAll(".control-btn").forEach((button) => {
        button.disabled = !manualMode;
        button.classList.toggle("active", button.dataset.command === data.manual_control_key);
      });

      const history = data.control_history || [];
      $("historyList").innerHTML = history.length
        ? history.slice().reverse().map((item) => {
            const ok = item.send_status === "sent";
            const waiting = item.send_status === "no_client";
            const auto = item.send_status === "mode_auto";
            return `<div class="history-item">
              <span><strong>${item.command_name || item.command_key}</strong>${item.timestamp || ""}</span>
              <span class="${ok ? "sent" : "failed"}">${ok ? "已发送" : waiting ? "待连接" : auto ? "自动中" : "未发送"}</span>
            </div>`;
          }).join("")
        : `<div class="history-item"><span>暂无控制记录</span><span>--</span></div>`;
    }

    async function loadState() {
      const res = await fetch("/api/state");
      render(await res.json());
    }

    async function sendControl(command) {
      const res = await fetch("/api/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command })
      });
      const body = await res.json();
      if (body.state) render(body.state);
    }

    async function setMode(mode) {
      const res = await fetch("/api/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode })
      });
      const body = await res.json();
      if (body.state) render(body.state);
    }

    document.querySelectorAll(".control-btn").forEach((button) => {
      button.addEventListener("click", () => sendControl(button.dataset.command));
    });

    $("modeSwitch").addEventListener("change", (event) => {
      setMode(event.target.checked ? "manual" : "auto");
    });

    $("debugSwitch").addEventListener("change", (event) => {
      $("debugPanel").classList.toggle("open", event.target.checked);
    });

    const events = new EventSource("/events");
    events.onmessage = (event) => render(JSON.parse(event.data));
    events.onerror = () => setTimeout(loadState, 1200);
    loadState();
  </script>
</body>
</html>
"""


def main():
    socket_thread = threading.Thread(target=run_socket_server, daemon=True)
    socket_thread.start()
    run_web_server()


if __name__ == "__main__":
    main()
