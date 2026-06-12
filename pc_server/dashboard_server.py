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

import csv
import json
import socket
import threading
import traceback
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from excel_utils import init_excel, append_sensor_data, append_sleep_result
from protocol_config import SERVER_HOST, SERVER_PORT, MESSAGE_END, SLEEP_STATE_NAME
from sleep_classifier import classify_sleep_state, get_sleep_state_text


DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8080
DASHBOARD_HISTORY_LIMIT = 43200
DASHBOARD_CHART_POINTS = 360
DASHBOARD_DEBUG_RECORDS = 80
SESSION_GAP_SECONDS = 30 * 60
MAX_COUNTED_SAMPLE_GAP_SECONDS = 30
DASHBOARD_HISTORY_FILE = Path(__file__).with_name("sleep_classifier_history.csv")

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
previous_sample_time = None
previous_sample_id = None
previous_stage_code = None
previous_stage_valid = False
session_summary = {
    "started_at": None,
    "last_sample_at": None,
    "sample_count": 0,
    "valid_sensor_count": 0,
    "heart_rate_sum": 0.0,
    "spo2_sum": 0.0,
    "temperature_sum": 0.0,
    "humidity_sum": 0.0,
    "spo2_low_count": 0,
    "turnover_count": 0,
    "stage_seconds": {0: 0.0, 1: 0.0, 2: 0.0},
}


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed
    except (TypeError, ValueError):
        return None


def finite_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def new_session_summary():
    return {
        "started_at": None,
        "last_sample_at": None,
        "sample_count": 0,
        "valid_sensor_count": 0,
        "heart_rate_sum": 0.0,
        "spo2_sum": 0.0,
        "temperature_sum": 0.0,
        "humidity_sum": 0.0,
        "spo2_low_count": 0,
        "turnover_count": 0,
        "stage_seconds": {0: 0.0, 1: 0.0, 2: 0.0},
    }


def downsample_history(records, max_points):
    if len(records) <= max_points:
        return list(records)

    step = (len(records) - 1) / (max_points - 1)
    indexes = [round(index * step) for index in range(max_points)]
    return [records[index] for index in indexes]


def build_trend_history(records):
    compact_records = []
    for item in downsample_history(records, DASHBOARD_CHART_POINTS):
        sensor = item.get("sensor_data") or {}
        result = item.get("model_sleep_result") or {}
        compact_records.append(
            {
                "timestamp": item.get("timestamp"),
                "sensor_data": {
                    key: sensor.get(key)
                    for key in (
                        "heart_rate_bpm",
                        "spo2_percent",
                        "temperature_c",
                        "humidity_percent",
                        "accel_x",
                        "accel_y",
                        "accel_z",
                        "turnover_count",
                    )
                },
                "model_sleep_result": {
                    "sleep_state_code": result.get("sleep_state_code"),
                    "state_valid": result.get("state_valid"),
                },
            }
        )
    return compact_records


def build_session_summary():
    summary = dict(session_summary)
    summary["stage_seconds"] = dict(session_summary["stage_seconds"])

    valid_count = summary.pop("valid_sensor_count")
    for field, total_field in (
        ("average_heart_rate", "heart_rate_sum"),
        ("average_spo2", "spo2_sum"),
        ("average_temperature", "temperature_sum"),
        ("average_humidity", "humidity_sum"),
    ):
        total = summary.pop(total_field)
        summary[field] = total / valid_count if valid_count else None

    stage_total = sum(summary["stage_seconds"].values())
    summary["observed_sleep_seconds"] = stage_total
    summary["sleep_seconds"] = (
        summary["stage_seconds"].get(1, 0)
        + summary["stage_seconds"].get(2, 0)
    )
    summary["sleep_ratio"] = (
        summary["sleep_seconds"] / stage_total if stage_total else None
    )
    summary["spo2_low_ratio"] = (
        summary["spo2_low_count"] / valid_count if valid_count else None
    )
    return summary


def history_row_to_dashboard_record(row, record_id):
    def number(name, integer=False):
        value = finite_float(row.get(name))
        if value is None:
            return None
        return int(value) if integer else value

    sensor = {
        "type": "sensor_data",
        "timestamp": row.get("sensor_timestamp"),
        "sample_id": number("sample_id", integer=True),
        "heart_rate_bpm": number("heart_rate_bpm"),
        "spo2_percent": number("spo2_percent"),
        "accel_x": number("accel_x"),
        "accel_y": number("accel_y"),
        "accel_z": number("accel_z"),
        "turnover_flag": number("turnover_flag", integer=True),
        "turnover_count": number("turnover_count", integer=True),
        "temperature_c": number("temperature_c"),
        "humidity_percent": number("humidity_percent"),
        "data_valid": number("data_valid", integer=True),
    }
    stage_code = number("sleep_state_code", integer=True)
    result = {
        "type": "sleep_result",
        "timestamp": row.get("sensor_timestamp"),
        "sample_id": sensor["sample_id"],
        "sleep_state_code": stage_code,
        "sleep_state_name": get_sleep_state_text(stage_code),
        "state_valid": number("state_valid", integer=True) or 0,
        "remark": row.get("result_remark") or "",
    }
    return {
        "id": record_id,
        "timestamp": sensor["timestamp"],
        "sample_id": sensor["sample_id"],
        "sensor_data": sensor,
        "model_sleep_result": result,
        "outgoing_sleep_result": result,
    }


def restore_dashboard_history():
    global latest_sensor, latest_result, latest_outgoing_result
    global last_update_at, data_history, data_sequence
    global previous_sample_time, previous_sample_id
    global previous_stage_code, previous_stage_valid
    global session_summary

    try:
        with DASHBOARD_HISTORY_FILE.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
    except (OSError, csv.Error):
        return

    session_rows = []
    last_time = None
    last_id = None
    for row in rows:
        sample_time = parse_datetime(row.get("sensor_timestamp"))
        sample_id = finite_float(row.get("sample_id"))
        starts_new_session = False
        if last_time is not None and sample_time is not None:
            gap_seconds = (sample_time - last_time).total_seconds()
            starts_new_session = gap_seconds < 0 or gap_seconds > SESSION_GAP_SECONDS
        if (
            not starts_new_session
            and sample_id is not None
            and last_id is not None
            and sample_id < last_id
        ):
            starts_new_session = True
        if starts_new_session:
            session_rows = []
        session_rows.append(row)
        last_time = sample_time or last_time
        last_id = sample_id if sample_id is not None else last_id

    if not session_rows:
        return

    session_summary = new_session_summary()
    all_records = []
    previous_time = None
    previous_code = None
    previous_valid = False

    for record_id, row in enumerate(session_rows, start=1):
        record = history_row_to_dashboard_record(row, record_id)
        sensor = record["sensor_data"]
        result = record["model_sleep_result"]
        sample_time = parse_datetime(sensor.get("timestamp"))

        if sample_time and previous_time and previous_valid:
            gap_seconds = (sample_time - previous_time).total_seconds()
            if 0 < gap_seconds <= MAX_COUNTED_SAMPLE_GAP_SECONDS:
                session_summary["stage_seconds"][previous_code] += gap_seconds

        if session_summary["started_at"] is None:
            session_summary["started_at"] = sensor.get("timestamp")
        session_summary["last_sample_at"] = sensor.get("timestamp")
        session_summary["sample_count"] += 1

        heart_rate = finite_float(sensor.get("heart_rate_bpm"))
        spo2 = finite_float(sensor.get("spo2_percent"))
        temperature = finite_float(sensor.get("temperature_c"))
        humidity = finite_float(sensor.get("humidity_percent"))
        data_valid = int(finite_float(sensor.get("data_valid")) or 0) == 1
        if data_valid and all(
            value is not None for value in (heart_rate, spo2, temperature, humidity)
        ):
            session_summary["valid_sensor_count"] += 1
            session_summary["heart_rate_sum"] += heart_rate
            session_summary["spo2_sum"] += spo2
            session_summary["temperature_sum"] += temperature
            session_summary["humidity_sum"] += humidity
            if spo2 < 95:
                session_summary["spo2_low_count"] += 1

        turnover_count = finite_float(sensor.get("turnover_count"))
        if turnover_count is not None:
            session_summary["turnover_count"] = int(turnover_count)

        stage_code = result.get("sleep_state_code")
        state_valid = int(finite_float(result.get("state_valid")) or 0) == 1
        previous_code = stage_code if state_valid and stage_code in {0, 1, 2} else 0
        previous_valid = True
        previous_time = sample_time or previous_time
        all_records.append(record)

    data_history = all_records[-DASHBOARD_HISTORY_LIMIT:]
    data_sequence = len(all_records)
    last_record = all_records[-1]
    latest_sensor = dict(last_record["sensor_data"])
    latest_result = dict(last_record["model_sleep_result"])
    latest_outgoing_result = dict(last_record["outgoing_sleep_result"])
    last_update_at = last_record["timestamp"]
    previous_sample_time = previous_time
    previous_sample_id = finite_float(latest_sensor.get("sample_id"))
    previous_stage_code = previous_code
    previous_stage_valid = previous_valid
    print(f"[INFO] Dashboard 已恢复最近会话 {len(all_records)} 条历史记录")


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
            "data_history": list(data_history[-DASHBOARD_DEBUG_RECORDS:]),
            "trend_history": build_trend_history(data_history),
            "session_summary": build_session_summary(),
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
    global previous_sample_time, previous_sample_id
    global previous_stage_code, previous_stage_valid
    global session_summary

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
        sample_time = parse_datetime(sensor.get("timestamp")) or datetime.now()
        sample_id = sensor.get("sample_id")
        numeric_sample_id = finite_float(sample_id)
        is_new_session = False

        if previous_sample_time is not None:
            gap_seconds = (sample_time - previous_sample_time).total_seconds()
            if gap_seconds < 0 or gap_seconds > SESSION_GAP_SECONDS:
                is_new_session = True
            elif (
                numeric_sample_id is not None
                and previous_sample_id is not None
                and numeric_sample_id < previous_sample_id
            ):
                is_new_session = True

        if is_new_session:
            data_history = []
            session_summary = new_session_summary()
            previous_sample_time = None
            previous_sample_id = None
            previous_stage_code = None
            previous_stage_valid = False

        if previous_sample_time is not None and previous_stage_valid:
            gap_seconds = (sample_time - previous_sample_time).total_seconds()
            if 0 < gap_seconds <= MAX_COUNTED_SAMPLE_GAP_SECONDS:
                session_summary["stage_seconds"][previous_stage_code] += gap_seconds

        if session_summary["started_at"] is None:
            session_summary["started_at"] = sample_time.isoformat(sep=" ", timespec="seconds")
        session_summary["last_sample_at"] = sample_time.isoformat(sep=" ", timespec="seconds")
        session_summary["sample_count"] += 1

        heart_rate = finite_float(sensor.get("heart_rate_bpm"))
        spo2 = finite_float(sensor.get("spo2_percent"))
        temperature = finite_float(sensor.get("temperature_c"))
        humidity = finite_float(sensor.get("humidity_percent"))
        data_valid = int(finite_float(sensor.get("data_valid")) or 0) == 1
        if data_valid and all(
            value is not None for value in (heart_rate, spo2, temperature, humidity)
        ):
            session_summary["valid_sensor_count"] += 1
            session_summary["heart_rate_sum"] += heart_rate
            session_summary["spo2_sum"] += spo2
            session_summary["temperature_sum"] += temperature
            session_summary["humidity_sum"] += humidity
            if spo2 < 95:
                session_summary["spo2_low_count"] += 1

        turnover_count = finite_float(sensor.get("turnover_count"))
        if turnover_count is not None:
            session_summary["turnover_count"] = int(turnover_count)

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
        data_history = data_history[-DASHBOARD_HISTORY_LIMIT:]

        stage_code = result_with_name.get("sleep_state_code")
        state_valid = (
            int(finite_float(result_with_name.get("state_valid")) or 0) == 1
        )
        previous_stage_code = (
            stage_code if state_valid and stage_code in {0, 1, 2} else 0
        )
        previous_stage_valid = True
        previous_sample_time = sample_time
        previous_sample_id = (
            numeric_sample_id if numeric_sample_id is not None else previous_sample_id
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

    .analysis-panel {
      margin-top: 18px;
    }

    .analysis-layout {
      display: grid;
      grid-template-columns: minmax(0, 1.75fr) minmax(300px, 0.85fr);
      align-items: stretch;
    }

    .trend-column {
      min-width: 0;
      padding: 18px;
    }

    .summary-column {
      min-width: 0;
      padding: 18px;
      border-left: 1px solid var(--line);
      background: linear-gradient(180deg, #fbfdff, #f6fafb);
    }

    .section-heading {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }

    .section-heading h3 {
      margin: 0;
      font-size: 16px;
    }

    .section-heading span {
      color: var(--muted);
      font-size: 12px;
      text-align: right;
    }

    .vital-charts {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .chart-card {
      min-width: 0;
      padding: 13px 13px 8px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }

    .chart-card.stage-card {
      margin-top: 12px;
      padding-bottom: 12px;
    }

    .chart-title {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 6px;
      font-size: 13px;
      font-weight: 800;
    }

    .chart-title span {
      color: var(--muted);
      font-size: 11px;
      font-weight: 600;
    }

    .trend-svg {
      display: block;
      width: 100%;
      height: 150px;
      overflow: visible;
    }

    .stage-card .trend-svg {
      height: 178px;
    }

    .chart-grid {
      stroke: #e7edf3;
      stroke-width: 1;
    }

    .chart-axis-text {
      fill: #7b8793;
      font-size: 10px;
    }

    .chart-line {
      fill: none;
      stroke-width: 2.4;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .chart-empty {
      fill: #8a96a2;
      font-size: 13px;
      text-anchor: middle;
    }

    .duration-list {
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }

    .duration-track {
      display: flex;
      width: 100%;
      height: 14px;
      border-radius: 999px;
      background: #eaf0f5;
      overflow: hidden;
    }

    .duration-segment {
      height: 100%;
      min-width: 0;
      transition: width 0.25s ease;
    }

    .duration-details {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-top: 12px;
    }

    .duration-detail {
      min-width: 0;
      text-align: center;
    }

    .duration-name {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      color: var(--muted);
      font-size: 11px;
      white-space: nowrap;
    }

    .stage-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex: 0 0 auto;
    }

    .duration-value {
      display: block;
      margin-top: 4px;
      font-size: 14px;
      font-weight: 800;
      white-space: nowrap;
    }

    .duration-percent {
      display: block;
      margin-top: 2px;
      color: var(--muted);
      font-size: 10px;
    }

    .score-card {
      display: grid;
      grid-template-columns: 104px minmax(0, 1fr);
      gap: 14px;
      align-items: center;
      margin-top: 14px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }

    .score-ring {
      width: 96px;
      height: 96px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      background: conic-gradient(var(--brand) 0deg, var(--brand) 0deg, #e7edf3 0deg);
      position: relative;
    }

    .score-ring::before {
      content: "";
      position: absolute;
      inset: 9px;
      border-radius: 50%;
      background: #fff;
    }

    .score-number {
      position: relative;
      z-index: 1;
      font-size: 27px;
      line-height: 1;
      font-weight: 850;
    }

    .score-number small {
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }

    .score-label {
      margin-bottom: 5px;
      font-size: 18px;
      font-weight: 800;
    }

    .score-description {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.55;
    }

    .summary-metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 9px;
      margin-top: 12px;
    }

    .summary-metric {
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.82);
    }

    .summary-metric span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      margin-bottom: 4px;
    }

    .summary-metric strong {
      font-size: 17px;
    }

    .advice-box {
      margin-top: 14px;
      padding: 14px;
      border: 1px solid rgba(36, 107, 254, 0.18);
      border-radius: 8px;
      background: var(--brand-soft);
    }

    .advice-title {
      margin-bottom: 9px;
      font-size: 14px;
      font-weight: 850;
    }

    .advice-list {
      margin: 0;
      padding-left: 18px;
      color: #3f5268;
      font-size: 12px;
      line-height: 1.65;
    }

    .analysis-disclaimer {
      margin-top: 10px;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.5;
    }

    @media (max-width: 900px) {
      .layout {
        grid-template-columns: 1fr;
      }

      .control-panel {
        position: static;
      }

      .analysis-layout {
        grid-template-columns: 1fr;
      }

      .summary-column {
        border-left: 0;
        border-top: 1px solid var(--line);
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

      .vital-charts {
        grid-template-columns: 1fr;
      }

      .trend-column,
      .summary-column {
        padding: 14px;
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

    <section class="panel analysis-panel">
      <div class="panel-head">
        <h2 class="panel-title">睡眠趋势与分析</h2>
        <div id="analysisRange" class="panel-note">等待有效睡眠数据</div>
      </div>

      <div class="analysis-layout">
        <div class="trend-column">
          <div class="section-heading">
            <h3>体征变化曲线</h3>
            <span>当前会话 · 长时数据自动降采样</span>
          </div>

          <div class="vital-charts">
            <article class="chart-card">
              <div class="chart-title">心率 <span>bpm</span></div>
              <svg id="heartChart" class="trend-svg" viewBox="0 0 600 170" preserveAspectRatio="none"></svg>
            </article>
            <article class="chart-card">
              <div class="chart-title">血氧饱和度 <span>%</span></div>
              <svg id="spo2Chart" class="trend-svg" viewBox="0 0 600 170" preserveAspectRatio="none"></svg>
            </article>
            <article class="chart-card">
              <div class="chart-title">环境温度 <span>°C</span></div>
              <svg id="temperatureChart" class="trend-svg" viewBox="0 0 600 170" preserveAspectRatio="none"></svg>
            </article>
            <article class="chart-card">
              <div class="chart-title">环境湿度 <span>%</span></div>
              <svg id="humidityChart" class="trend-svg" viewBox="0 0 600 170" preserveAspectRatio="none"></svg>
            </article>
            <article class="chart-card">
              <div class="chart-title">体动强度 <span>三轴合成 g</span></div>
              <svg id="accelChart" class="trend-svg" viewBox="0 0 600 170" preserveAspectRatio="none"></svg>
            </article>
            <article class="chart-card">
              <div class="chart-title">累计翻身次数 <span>次</span></div>
              <svg id="turnoverChart" class="trend-svg" viewBox="0 0 600 170" preserveAspectRatio="none"></svg>
            </article>
          </div>

          <article class="chart-card stage-card">
            <div class="chart-title">睡眠阶段变化 <span>未入睡 / 浅睡眠 / 深度睡眠</span></div>
            <svg id="stageChart" class="trend-svg" viewBox="0 0 600 190" preserveAspectRatio="none"></svg>
          </article>
        </div>

        <aside class="summary-column">
          <div class="section-heading">
            <h3>睡眠统计与建议</h3>
            <span>当前会话</span>
          </div>

          <div id="durationList" class="duration-list"></div>

          <div class="score-card">
            <div id="scoreRing" class="score-ring">
              <div id="sleepScore" class="score-number">--<small>分</small></div>
            </div>
            <div>
              <div id="scoreLabel" class="score-label">数据积累中</div>
              <div id="scoreDescription" class="score-description">持续监测后将结合睡眠结构、心率与血氧给出综合评价。</div>
            </div>
          </div>

          <div class="summary-metrics">
            <div class="summary-metric"><span>平均心率</span><strong id="averageHeart">--</strong></div>
            <div class="summary-metric"><span>平均血氧</span><strong id="averageSpo2">--</strong></div>
            <div class="summary-metric"><span>睡眠占比</span><strong id="sleepRatio">--</strong></div>
            <div class="summary-metric"><span>累计监测</span><strong id="observedTime">--</strong></div>
          </div>

          <div class="advice-box">
            <div class="advice-title">个性化睡眠建议</div>
            <ul id="adviceList" class="advice-list">
              <li>等待更多有效数据后生成建议。</li>
            </ul>
          </div>
          <div class="analysis-disclaimer">睡眠阶段与评分为算法估算结果，仅用于日常趋势观察，不能替代医疗诊断。</div>
        </aside>
      </div>
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

    function numberOrNull(value) {
      if (value === null || value === undefined || value === "") return null;
      const number = Number(value);
      return Number.isFinite(number) ? number : null;
    }

    function formatDuration(totalSeconds) {
      const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0));
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const remainingSeconds = seconds % 60;
      if (hours) return `${hours}小时${minutes}分`;
      if (minutes) return `${minutes}分${remainingSeconds}秒`;
      return `${remainingSeconds}秒`;
    }

    function formatClock(value) {
      const date = value ? new Date(String(value).replace(" ", "T")) : null;
      if (!date || Number.isNaN(date.getTime())) return "--:--";
      return date.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
      });
    }

    function chartFrame(minValue, maxValue, color) {
      const left = 48;
      const right = 586;
      const top = 12;
      const bottom = 142;
      const lines = [0, 0.5, 1].map((ratio) => {
        const y = top + (bottom - top) * ratio;
        const value = maxValue - (maxValue - minValue) * ratio;
        return `<line class="chart-grid" x1="${left}" y1="${y}" x2="${right}" y2="${y}"></line>
          <text class="chart-axis-text" x="4" y="${y + 3}">${value.toFixed(value < 10 ? 1 : 0)}</text>`;
      }).join("");
      return { left, right, top, bottom, color, markup: lines };
    }

    function renderLineChart(svgId, history, field, options) {
      const svg = $(svgId);
      const points = (history || []).map((item, index) => {
        const sensor = item.sensor_data || {};
        const rawValue = typeof field === "function" ? field(sensor) : sensor[field];
        return { index, value: numberOrNull(rawValue) };
      }).filter((item) => item.value !== null);

      if (points.length < 2) {
        svg.innerHTML = `<text class="chart-empty" x="300" y="85">等待更多采样点</text>`;
        return;
      }

      const values = points.map((item) => item.value);
      let minValue = Math.min(...values);
      let maxValue = Math.max(...values);
      const minSpan = options.minSpan || 1;
      if (maxValue - minValue < minSpan) {
        const center = (maxValue + minValue) / 2;
        minValue = center - minSpan / 2;
        maxValue = center + minSpan / 2;
      } else {
        const padding = (maxValue - minValue) * 0.12;
        minValue -= padding;
        maxValue += padding;
      }
      if (options.floor !== undefined) minValue = Math.min(options.floor, minValue);
      if (options.ceiling !== undefined) maxValue = Math.max(options.ceiling, maxValue);
      if (maxValue <= minValue) maxValue = minValue + minSpan;

      const frame = chartFrame(minValue, maxValue, options.color);
      const denominator = Math.max(1, history.length - 1);
      const path = points.map((point, pointIndex) => {
        const x = frame.left + (point.index / denominator) * (frame.right - frame.left);
        const y = frame.bottom - ((point.value - minValue) / (maxValue - minValue)) * (frame.bottom - frame.top);
        return `${pointIndex ? "L" : "M"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      }).join(" ");
      const firstTime = history[0] && history[0].timestamp;
      const lastTime = history[history.length - 1] && history[history.length - 1].timestamp;

      svg.innerHTML = `${frame.markup}
        <path class="chart-line" stroke="${options.color}" d="${path}"></path>
        <text class="chart-axis-text" x="${frame.left}" y="163">${formatClock(firstTime)}</text>
        <text class="chart-axis-text" x="${frame.right}" y="163" text-anchor="end">${formatClock(lastTime)}</text>`;
    }

    function renderStageChart(history) {
      const svg = $("stageChart");
      const points = (history || []).map((item, index) => {
        const result = item.model_sleep_result || {};
        const code = numberOrNull(result.sleep_state_code);
        const valid = Number(result.state_valid) === 1;
        return { index, code: valid && [0, 1, 2].includes(code) ? code : 0 };
      });

      if (!points.length) {
        svg.innerHTML = `<text class="chart-empty" x="300" y="95">等待睡眠监测数据</text>`;
        return;
      }

      const left = 72;
      const right = 586;
      const stageY = { 0: 24, 1: 84, 2: 144 };
      const labels = [
        { code: 0, text: "未入睡", color: "#d17916" },
        { code: 1, text: "浅睡眠", color: "#246bfe" },
        { code: 2, text: "深度睡眠", color: "#0f9f9a" }
      ];
      const grid = labels.map((item) => `
        <line class="chart-grid" x1="${left}" y1="${stageY[item.code]}" x2="${right}" y2="${stageY[item.code]}"></line>
        <circle cx="7" cy="${stageY[item.code] - 3}" r="4" fill="${item.color}"></circle>
        <text class="chart-axis-text" x="16" y="${stageY[item.code]}">${item.text}</text>
      `).join("");
      const denominator = Math.max(1, history.length - 1);
      let path = "";
      points.forEach((point, index) => {
        const x = points.length === 1
          ? left
          : left + (point.index / denominator) * (right - left);
        const y = stageY[point.code];
        if (index === 0) {
          path = `M ${x.toFixed(2)} ${y}`;
          return;
        }
        path += ` H ${x.toFixed(2)} V ${y}`;
      });
      if (points.length === 1) {
        path += ` H ${right}`;
      }

      svg.innerHTML = `${grid}
        <path class="chart-line" stroke="#53667a" d="${path}"></path>
        <text class="chart-axis-text" x="${left}" y="181">${formatClock(history[0].timestamp)}</text>
        <text class="chart-axis-text" x="${right}" y="181" text-anchor="end">${formatClock(history[history.length - 1].timestamp)}</text>`;
    }

    function buildSleepEvaluation(summary) {
      const stageSeconds = summary.stage_seconds || {};
      const observed = Number(summary.observed_sleep_seconds) || 0;
      const sleeping = Number(summary.sleep_seconds) || 0;
      const deep = Number(stageSeconds["2"] ?? stageSeconds[2]) || 0;
      const sleepRatio = summary.sleep_ratio;
      const averageHeart = numberOrNull(summary.average_heart_rate);
      const averageSpo2 = numberOrNull(summary.average_spo2);
      const lowSpo2Ratio = numberOrNull(summary.spo2_low_ratio);

      if (observed < 30 || summary.sample_count < 15) {
        return {
          score: null,
          label: "数据积累中",
          description: "至少积累 30 秒有效阶段数据后生成初步趋势评价。",
          advice: ["保持设备稳定佩戴并继续监测，以获得更完整的睡眠结构。"]
        };
      }

      let score = 20;
      score += Math.min(40, Math.max(0, Number(sleepRatio || 0) * 40));
      const deepRatio = sleeping ? deep / sleeping : 0;
      score += Math.min(20, deepRatio / 0.2 * 20);

      if (averageSpo2 !== null) {
        score += averageSpo2 >= 95 ? 15 : Math.max(0, (averageSpo2 - 88) / 7 * 15);
      }
      if (averageHeart !== null) {
        score += averageHeart >= 45 && averageHeart <= 80 ? 5 : 2;
      }
      if (lowSpo2Ratio !== null) score -= Math.min(15, lowSpo2Ratio * 60);
      score = Math.round(Math.min(100, Math.max(0, score)));

      let label = "睡眠状态一般";
      let description = "当前睡眠结构仍有改善空间，建议结合整夜趋势持续观察。";
      if (score >= 85) {
        label = "睡眠状态良好";
        description = "当前阶段结构和主要体征整体平稳。";
      } else if (score >= 70) {
        label = "睡眠状态尚可";
        description = "整体表现尚可，个别指标可继续关注。";
      } else if (score < 55) {
        label = "建议重点关注";
        description = "当前睡眠连续性或体征指标存在较明显波动。";
      }

      const advice = [];
      if (sleepRatio !== null && sleepRatio < 0.75) {
        advice.push("未入睡时间占比较高，建议固定入睡时间并减少睡前强光和电子设备使用。");
      }
      if (sleeping >= 30 * 60 && deepRatio < 0.12) {
        advice.push("深睡占比较低，可尝试保持规律运动，并避免临睡前摄入咖啡因。");
      }
      if (averageSpo2 !== null && (averageSpo2 < 95 || (lowSpo2Ratio || 0) > 0.05)) {
        advice.push("监测到血氧偏低趋势，请检查传感器佩戴；若反复出现或伴随不适，建议咨询医生。");
      }
      if (averageHeart !== null && averageHeart > 80) {
        advice.push("睡眠期平均心率偏高，建议避免睡前剧烈运动、酒精和过量进食。");
      }
      const averageTemperature = numberOrNull(summary.average_temperature);
      const averageHumidity = numberOrNull(summary.average_humidity);
      if (averageTemperature !== null && (averageTemperature < 18 || averageTemperature > 26)) {
        advice.push("睡眠环境温度偏离舒适区间，可将室温调整到约 18–26°C。");
      }
      if (averageHumidity !== null && (averageHumidity < 40 || averageHumidity > 65)) {
        advice.push("环境湿度不够理想，建议尽量维持在 40%–65%。");
      }
      if (!advice.length) {
        advice.push("当前主要指标较平稳，继续保持规律作息并完成整夜监测。");
      }

      return { score, label, description, advice };
    }

    function renderAnalysis(history, summary) {
      renderLineChart("heartChart", history, "heart_rate_bpm", {
        color: "#d84a4a", minSpan: 12
      });
      renderLineChart("spo2Chart", history, "spo2_percent", {
        color: "#246bfe", minSpan: 4, floor: 90, ceiling: 100
      });
      renderLineChart("temperatureChart", history, "temperature_c", {
        color: "#d17916", minSpan: 4
      });
      renderLineChart("humidityChart", history, "humidity_percent", {
        color: "#0f9f9a", minSpan: 10
      });
      renderLineChart("accelChart", history, (sensor) => {
        const ax = numberOrNull(sensor.accel_x);
        const ay = numberOrNull(sensor.accel_y);
        const az = numberOrNull(sensor.accel_z);
        if ([ax, ay, az].some((value) => value === null)) return null;
        return Math.sqrt(ax * ax + ay * ay + az * az);
      }, {
        color: "#7c5ce0", minSpan: 0.15, floor: 0
      });
      renderLineChart("turnoverChart", history, "turnover_count", {
        color: "#53667a", minSpan: 2, floor: 0
      });
      renderStageChart(history);

      const stageSeconds = summary.stage_seconds || {};
      const observed = Number(summary.observed_sleep_seconds) || 0;
      const stages = [
        { code: 0, name: "未入睡", color: "#d17916" },
        { code: 1, name: "浅睡眠", color: "#246bfe" },
        { code: 2, name: "深度睡眠", color: "#0f9f9a" }
      ].map((stage) => {
        const seconds = Number(stageSeconds[String(stage.code)] ?? stageSeconds[stage.code]) || 0;
        const percent = observed ? seconds / observed * 100 : 0;
        return { ...stage, seconds, percent };
      });
      const segments = stages.map((stage) => `
        <div class="duration-segment"
          title="${stage.name} ${formatDuration(stage.seconds)}"
          style="width:${stage.percent.toFixed(2)}%;background:${stage.color}">
        </div>
      `).join("");
      const details = stages.map((stage) => `
        <div class="duration-detail">
          <span class="duration-name"><span class="stage-dot" style="background:${stage.color}"></span>${stage.name}</span>
          <strong class="duration-value">${formatDuration(stage.seconds)}</strong>
          <span class="duration-percent">${stage.percent.toFixed(1)}%</span>
        </div>
      `).join("");
      $("durationList").innerHTML = `
        <div class="duration-track">${segments}</div>
        <div class="duration-details">${details}</div>
      `;

      const evaluation = buildSleepEvaluation(summary);
      const score = evaluation.score;
      $("sleepScore").innerHTML = `${score === null ? "--" : score}<small>分</small>`;
      $("scoreLabel").textContent = evaluation.label;
      $("scoreDescription").textContent = evaluation.description;
      const scoreDegrees = score === null ? 0 : score * 3.6;
      $("scoreRing").style.background = `conic-gradient(var(--brand) 0deg, var(--brand) ${scoreDegrees}deg, #e7edf3 ${scoreDegrees}deg)`;

      const averageHeart = numberOrNull(summary.average_heart_rate);
      const averageSpo2 = numberOrNull(summary.average_spo2);
      $("averageHeart").textContent = averageHeart === null ? "--" : `${averageHeart.toFixed(1)} bpm`;
      $("averageSpo2").textContent = averageSpo2 === null ? "--" : `${averageSpo2.toFixed(1)}%`;
      $("sleepRatio").textContent = summary.sleep_ratio === null || summary.sleep_ratio === undefined
        ? "--"
        : `${(Number(summary.sleep_ratio) * 100).toFixed(1)}%`;
      $("observedTime").textContent = formatDuration(observed);
      $("adviceList").innerHTML = evaluation.advice.map((item) => `<li>${escapeHtml(item)}</li>`).join("");

      if (summary.started_at && summary.last_sample_at) {
        $("analysisRange").textContent = `${formatClock(summary.started_at)} - ${formatClock(summary.last_sample_at)}`;
      } else {
        $("analysisRange").textContent = "等待有效睡眠数据";
      }
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
      const dataHistory = data.data_history || [];
      renderDebug(dataHistory);
      renderAnalysis(data.trend_history || dataHistory, data.session_summary || {});

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
    restore_dashboard_history()
    socket_thread = threading.Thread(target=run_socket_server, daemon=True)
    socket_thread.start()
    run_web_server()


if __name__ == "__main__":
    main()
