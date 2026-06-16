"""
dashboard_server.py

PC 端可视化服务端。

功能：
1. 使用当前四消息 TCP 协议接收 PYNQ/fake client 的 sensor_data。
2. 通过 SleepMonitorPcService 生成 sleep_result 和 control_command。
3. 记录 control_status，并在 Web 控制台实时显示完整闭环。
4. Web 控制台可以切换自动/手动模式；手动设备控制只排队真实 control_command targets。

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

from protocol import (
    CONTROL_STATUS,
    SENSOR_DATA,
    MessageBuffer,
    ProtocolError,
    encode_message,
)
from protocol_config import SERVER_HOST, SERVER_PORT, SLEEP_STATE_NAME
from service import SleepMonitorPcService
from storage import JsonlRecordStorage, default_record_dir


DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8080
DASHBOARD_HISTORY_LIMIT = 43200
DASHBOARD_CHART_POINTS = 360
DASHBOARD_DEBUG_RECORDS = 80
SESSION_GAP_SECONDS = 30 * 60
MAX_COUNTED_SAMPLE_GAP_SECONDS = 30
DASHBOARD_HISTORY_FILE = Path(__file__).with_name("sleep_classifier_history.csv")
STATIC_DIR = Path(__file__).with_name("static")
STATIC_CONTENT_TYPES = {
    "dashboard.css": "text/css; charset=utf-8",
    "dashboard.js": "application/javascript; charset=utf-8",
    "dashboard.html": "text/html; charset=utf-8",
}

# 手动控制区只排队真实设备命令；实际发送发生在下一条 sensor_data 周期。
MANUAL_CONTROL_OPTIONS = {
    "ac_power_on": {
        "label": "空调开机",
        "code": "AC ON",
        "action": {"target": "ir_ac", "command": "power_on"},
    },
    "ac_power_off": {
        "label": "空调关机",
        "code": "AC OFF",
        "action": {"target": "ir_ac", "command": "power_off"},
    },
    "ac_temp_24": {
        "label": "空调 24°C",
        "code": "AC 24",
        "action": {
            "target": "ir_ac",
            "command": "temp_24",
            "temperature_setpoint_c": 24,
        },
    },
    "ac_temp_26": {
        "label": "空调 26°C",
        "code": "AC 26",
        "action": {
            "target": "ir_ac",
            "command": "temp_26",
            "temperature_setpoint_c": 26,
        },
    },
    "ac_temp_28": {
        "label": "空调 28°C",
        "code": "AC 28",
        "action": {
            "target": "ir_ac",
            "command": "temp_28",
            "temperature_setpoint_c": 28,
        },
    },
    "humidifier_on": {
        "label": "加湿器开",
        "code": "HUM ON",
        "action": {"target": "humidifier", "enabled": True},
    },
    "humidifier_off": {
        "label": "加湿器关",
        "code": "HUM OFF",
        "action": {"target": "humidifier", "enabled": False},
    },
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
data_history = []
data_sequence = 0
manual_control_key = "ac_temp_26"
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

pc_service = SleepMonitorPcService(
    storage=JsonlRecordStorage(default_record_dir()),
)


def read_static_text(name):
    if name not in STATIC_CONTENT_TYPES:
        raise ValueError("unknown static asset: {0}".format(name))
    return (STATIC_DIR / name).read_text(encoding="utf-8")


def read_static_bytes(name):
    if name not in STATIC_CONTENT_TYPES:
        raise ValueError("unknown static asset: {0}".format(name))
    return (STATIC_DIR / name).read_bytes()


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_sleep_state_text(code):
    return SLEEP_STATE_NAME.get(code, "未知状态")


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
    conn.sendall(encode_message(obj).encode("utf-8"))


def format_client_addr(address):
    if not address:
        return None
    if isinstance(address, dict):
        host = address.get("host")
        port = address.get("port")
        return f"{host}:{port}" if port is not None else str(host)
    if isinstance(address, tuple):
        return f"{address[0]}:{address[1]}" if len(address) > 1 else str(address[0])
    return str(address)


def describe_targets(targets):
    targets = targets or {}
    parts = []
    ir_ac = targets.get("ir_ac")
    if ir_ac:
        parts.append("AC {0}".format(ir_ac.get("command", "--")))
    humidifier = targets.get("humidifier")
    if humidifier and "enabled" in humidifier:
        parts.append("加湿器{0}".format("开" if humidifier.get("enabled") else "关"))
    return " / ".join(parts) if parts else "无动作"


def build_control_history_from_snapshot(service_state):
    histories = service_state.get("histories") or {}
    commands = histories.get("control_command") or []
    statuses = histories.get("control_status") or []
    status_by_sample = {item.get("sample_id"): item for item in statuses}

    records = []
    for command in commands[-DASHBOARD_DEBUG_RECORDS:]:
        sample_id = command.get("sample_id")
        targets = command.get("targets") or {}
        status = status_by_sample.get(sample_id)
        send_status = "no_action"
        status_text = command.get("reason", "no_action")
        if targets:
            send_status = "sent"
            status_text = "等待执行状态"
        if status:
            status_code = status.get("status_code")
            if status_code == 0:
                send_status = "applied"
            elif status_code == 2:
                send_status = "skipped"
            elif status_code == 3:
                send_status = "failed"
            elif status_code == 1:
                send_status = "rejected"
            status_text = status.get("remark") or status_text
        records.append(
            {
                "timestamp": command.get("timestamp"),
                "sample_id": sample_id,
                "command_name": describe_targets(targets),
                "command_key": command.get("reason"),
                "send_status": send_status,
                "status_text": status_text,
                "control_command": dict(command),
                "control_status": dict(status) if status else None,
            }
        )
    pending = service_state.get("pending_manual_command")
    if pending:
        records.append(
            {
                "timestamp": now_text(),
                "sample_id": None,
                "command_name": describe_targets(pending.get("targets")),
                "command_key": pending.get("reason", "dashboard_manual"),
                "send_status": "pending",
                "status_text": "等待下一条 sensor_data 下发",
                "control_command": None,
                "control_status": None,
            }
        )
    return records[-8:]


def snapshot_state() -> dict:
    service_state = pc_service.snapshot()
    with state_lock:
        result = dict(latest_result) if latest_result else None
        if result is None and service_state.get("latest_sleep_result"):
            result = dict(service_state["latest_sleep_result"])
        if result and "sleep_state_name" not in result:
            code = result.get("sleep_state_code")
            result["sleep_state_name"] = get_sleep_state_text(code)

        outgoing_result = dict(latest_outgoing_result) if latest_outgoing_result else None
        if outgoing_result and "sleep_state_name" not in outgoing_result:
            code = outgoing_result.get("sleep_state_code")
            outgoing_result["sleep_state_name"] = get_sleep_state_text(code)

        sensor = dict(latest_sensor) if latest_sensor else None
        if sensor is None and service_state.get("latest_sensor_data"):
            sensor = dict(service_state["latest_sensor_data"])

        manual_option = MANUAL_CONTROL_OPTIONS.get(
            manual_control_key,
            MANUAL_CONTROL_OPTIONS["ac_temp_26"],
        )

        return {
            "connected": bool(service_state.get("connected")),
            "client_addr": format_client_addr(service_state.get("active_client")),
            "last_update_at": last_update_at or service_state.get("last_update_at"),
            "last_transmit_at": service_state.get("last_transmit_at"),
            "sensor": sensor,
            "result": result,
            "outgoing_result": outgoing_result,
            "sleep_states": SLEEP_STATE_NAME,
            "control_mode": service_state.get("control_mode", "auto"),
            "manual_control_key": manual_control_key,
            "manual_control_label": manual_option["label"],
            "manual_signal_code": manual_option.get("code"),
            "manual_signal_name": manual_option["label"],
            "manual_control_options": MANUAL_CONTROL_OPTIONS,
            "pending_manual_command": service_state.get("pending_manual_command"),
            "latest_control_command": service_state.get("latest_control_command"),
            "latest_control_status": service_state.get("latest_control_status"),
            "last_commanded_state": service_state.get("last_commanded_state"),
            "control_history": build_control_history_from_snapshot(service_state),
            "data_history": list(data_history[-DASHBOARD_DEBUG_RECORDS:]),
            "trend_history": build_trend_history(data_history),
            "session_summary": build_session_summary(),
            "event_version": max(event_version, service_state.get("event_version", 0)),
        }


def publish_update():
    global event_version

    with event_condition:
        event_version += 1
        event_condition.notify_all()


def set_active_client(conn: socket.socket, addr):
    global active_conn, active_addr

    pc_service.set_active_client(addr)
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
            pc_service.clear_active_client()
    publish_update()


def update_sensor_state(sensor: dict, result: dict, outgoing_result: dict, control_command=None):
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
                "control_command": dict(control_command) if control_command else None,
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


def set_control_mode(mode: str) -> dict:
    try:
        pc_service.set_control_mode(mode)
    except ProtocolError as exc:
        raise ValueError("unknown_mode") from exc

    publish_update()
    return snapshot_state()


def send_selected_manual_control(command_key: str) -> dict:
    global manual_control_key

    if command_key not in MANUAL_CONTROL_OPTIONS:
        raise ValueError("unknown_command")

    option = MANUAL_CONTROL_OPTIONS[command_key]
    action = dict(option["action"])
    action["reason"] = "dashboard_manual"

    with state_lock:
        manual_control_key = command_key
        queued = pc_service.queue_manual_command(action)

    history_packet = {
        "timestamp": now_text(),
        "manual_control_key": command_key,
        "command_name": option["label"],
        "command_key": command_key,
        "targets": queued["targets"],
        "send_status": "pending",
        "status_text": "等待下一条 sensor_data 下发",
    }

    publish_update()
    return history_packet


def handle_client(conn: socket.socket, addr):
    print(f"[INFO] 客户端已连接: {addr}")
    set_active_client(conn, addr)
    stats = {
        "received": 0,
        "sensor_data": 0,
        "control_status": 0,
        "sent": 0,
        "errors": 0,
    }
    buffer = MessageBuffer()

    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break

            for data in buffer.feed(chunk):
                stats["received"] += 1
                print("[RECV]", data)

                message_type = data.get("type")
                if message_type == SENSOR_DATA:
                    response = pc_service.process_sensor_data(data)
                    sleep_result = response["sleep_result"]
                    control_command = response["control_command"]

                    with send_lock:
                        send_json(conn, sleep_result)
                        send_json(conn, control_command)

                    update_sensor_state(
                        data,
                        sleep_result,
                        sleep_result,
                        control_command=control_command,
                    )

                    stats["sensor_data"] += 1
                    stats["sent"] += 2

                    code = sleep_result.get("sleep_state_code")
                    state_text = get_sleep_state_text(code)
                    print(
                        f"[SEND] sample_id={sleep_result.get('sample_id')} "
                        f"state={code}({state_text}) "
                        f"command={control_command.get('reason')}"
                    )
                elif message_type == CONTROL_STATUS:
                    pc_service.process_control_status(data)
                    stats["control_status"] += 1
                    publish_update()
                    print(
                        f"[STATUS] sample_id={data.get('sample_id')} "
                        f"code={data.get('status_code')} remark={data.get('remark')}"
                    )
                else:
                    stats["errors"] += 1
                    raise ProtocolError(
                        "unexpected client message type: {0}".format(message_type)
                    )

    except ConnectionResetError:
        print("[WARN] 客户端连接被重置")
    except ProtocolError as exc:
        stats["errors"] += 1
        print("[ERROR] 协议错误:", exc)
    except Exception:
        stats["errors"] += 1
        print("[ERROR] 服务端处理客户端时发生异常：")
        traceback.print_exc()
    finally:
        clear_active_client(conn)
        conn.close()
        print(f"[INFO] 客户端已断开: {addr} stats={stats}")
    return stats


def run_socket_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_HOST, SERVER_PORT))
    server.listen(1)

    print("=" * 60)
    print("[INFO] PC socket 服务端启动成功")
    print(f"[INFO] 监听地址: {SERVER_HOST}:{SERVER_PORT}")
    print("[INFO] 使用四消息协议: sensor_data -> sleep_result/control_command -> control_status")
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
            self.send_body(
                HTTPStatus.OK,
                DASHBOARD_HTML.encode("utf-8"),
                STATIC_CONTENT_TYPES["dashboard.html"],
            )
            return

        if path.startswith("/static/"):
            name = path.rsplit("/", 1)[-1]
            if name in ("dashboard.css", "dashboard.js"):
                self.send_body(
                    HTTPStatus.OK,
                    read_static_bytes(name),
                    STATIC_CONTENT_TYPES[name],
                )
                return
            self.send_json_body(HTTPStatus.NOT_FOUND, {"error": "not_found"})
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


DASHBOARD_HTML = read_static_text("dashboard.html")


def main():
    restore_dashboard_history()
    socket_thread = threading.Thread(target=run_socket_server, daemon=True)
    socket_thread.start()
    run_web_server()


if __name__ == "__main__":
    main()
