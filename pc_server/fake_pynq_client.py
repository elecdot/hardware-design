"""PC-side fake PYNQ client for the new newline-JSON protocol."""

import argparse
import random
import socket
import time

from protocol import (
    CONTROL_COMMAND,
    CONTROL_STATUS,
    SENSOR_DATA,
    SLEEP_RESULT,
    STATUS_OK,
    STATUS_SKIPPED,
    MessageBuffer,
    encode_message,
    now_text,
    validate_message,
)
from protocol_config import LOCAL_TEST_HOST, SERVER_PORT


def build_fake_sensor_packet(sample_id, rng=None):
    """Build one realistic-enough sensor_data packet for PC-only testing."""
    active_rng = rng or random
    temperature, humidity = _environment_pattern(sample_id)

    packet = {
        "type": SENSOR_DATA,
        "timestamp": now_text(),
        "sample_id": sample_id,
        "heart_rate_bpm": active_rng.randint(62, 84),
        "spo2_percent": active_rng.randint(96, 99),
        "accel_x": round(active_rng.uniform(-0.18, 0.18), 3),
        "accel_y": round(active_rng.uniform(-0.18, 0.18), 3),
        "accel_z": round(active_rng.uniform(0.86, 1.08), 3),
        "gyro_x": None,
        "gyro_y": None,
        "gyro_z": None,
        "mag_x": None,
        "mag_y": None,
        "mag_z": None,
        "turnover_flag": 1 if active_rng.random() < 0.12 else 0,
        "turnover_count": max(0, int(sample_id / 8)),
        "temperature_c": temperature,
        "humidity_percent": humidity,
        "data_valid": 1,
        "status_code": 0,
        "checksum_ok": 1,
        "remark": "fake_pynq_client",
    }
    validate_message(packet, expected_type=SENSOR_DATA)
    return packet


def build_fake_control_status(command):
    """Pretend the PYNQ side accepted and handled one control_command."""
    validate_message(command, expected_type=CONTROL_COMMAND)
    targets = command.get("targets") or {}
    applied = {}

    if "ir_ac" in targets:
        ir_target = targets["ir_ac"]
        applied["ir_ac"] = {
            "requested": True,
            "command": ir_target.get("command"),
            "sent": True,
            "skipped": False,
            "skip_reason": None,
            "error": None,
            "status": {
                "done": True,
                "error": False,
                "raw_status": 2,
            },
        }

    if "humidifier" in targets:
        humidifier = targets["humidifier"]
        enabled = bool(humidifier.get("enabled"))
        applied["humidifier"] = {
            "requested": True,
            "enabled": enabled,
            "applied": True,
            "skipped": False,
            "skip_reason": None,
            "error": None,
            "humidifier_on": enabled,
        }

    status_code = STATUS_OK if applied else STATUS_SKIPPED
    remark = "fake_control_applied" if applied else command.get("reason", "no_action")
    status = {
        "type": CONTROL_STATUS,
        "timestamp": now_text(),
        "sample_id": command["sample_id"],
        "accepted": 1,
        "applied": applied,
        "status_code": status_code,
        "remark": remark,
    }
    validate_message(status, expected_type=CONTROL_STATUS)
    return status


def run_fake_client(
    host=LOCAL_TEST_HOST,
    port=SERVER_PORT,
    samples=10,
    interval=2.0,
    timeout=5.0,
    seed=None,
    verbose=True,
):
    rng = random.Random(seed)
    stats = {
        "sensor_data": 0,
        "sleep_result": 0,
        "control_command": 0,
        "control_status": 0,
    }
    buffer = MessageBuffer()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(float(timeout))

    if verbose:
        print("[INFO] connecting to {0}:{1}".format(host, port))
    sock.connect((host, int(port)))

    try:
        for sample_id in range(1, int(samples) + 1):
            sensor_data = build_fake_sensor_packet(sample_id, rng)
            _send_message(sock, sensor_data)
            stats["sensor_data"] += 1
            if verbose:
                print("[SEND sensor_data]", _brief_sensor(sensor_data))

            responses = _recv_messages(sock, buffer, 2)
            sleep_result, control_command = _validate_pc_responses(
                sample_id,
                responses,
            )
            stats["sleep_result"] += 1
            stats["control_command"] += 1
            if verbose:
                print("[RECV sleep_result]", _brief_result(sleep_result))
                print("[RECV control_command]", _brief_command(control_command))

            control_status = build_fake_control_status(control_command)
            _send_message(sock, control_status)
            stats["control_status"] += 1
            if verbose:
                print("[SEND control_status]", _brief_status(control_status))

            if interval:
                time.sleep(float(interval))
    finally:
        sock.close()

    return stats


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run a fake PYNQ client against the new PC socket service."
    )
    parser.add_argument("--host", default=LOCAL_TEST_HOST)
    parser.add_argument("--port", type=int, default=SERVER_PORT)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=1)
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    stats = run_fake_client(
        host=args.host,
        port=args.port,
        samples=args.samples,
        interval=args.interval,
        timeout=args.timeout,
        seed=args.seed,
        verbose=True,
    )
    print("[INFO] fake client complete: {0}".format(stats))


def _environment_pattern(sample_id):
    pattern = int(sample_id) % 4
    if pattern == 1:
        return 29.0, 35
    if pattern == 2:
        return 26.0, 50
    if pattern == 3:
        return 23.0, 65
    return 25.5, 45


def _send_message(sock, message):
    sock.sendall(encode_message(message).encode("utf-8"))


def _recv_messages(sock, buffer, count):
    messages = []
    while len(messages) < count:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("server closed the connection")
        messages.extend(buffer.feed(chunk))
    return messages[:count]


def _validate_pc_responses(sample_id, messages):
    if len(messages) != 2:
        raise RuntimeError("expected two PC response messages")
    sleep_result, control_command = messages
    validate_message(sleep_result, expected_type=SLEEP_RESULT)
    validate_message(control_command, expected_type=CONTROL_COMMAND)
    if sleep_result["sample_id"] != sample_id:
        raise RuntimeError("sleep_result sample_id mismatch")
    if control_command["sample_id"] != sample_id:
        raise RuntimeError("control_command sample_id mismatch")
    return sleep_result, control_command


def _brief_sensor(sensor_data):
    return {
        "sample_id": sensor_data["sample_id"],
        "heart_rate_bpm": sensor_data["heart_rate_bpm"],
        "spo2_percent": sensor_data["spo2_percent"],
        "temperature_c": sensor_data["temperature_c"],
        "humidity_percent": sensor_data["humidity_percent"],
    }


def _brief_result(sleep_result):
    return {
        "sample_id": sleep_result["sample_id"],
        "sleep_state_code": sleep_result["sleep_state_code"],
        "state_valid": sleep_result["state_valid"],
        "remark": sleep_result["remark"],
    }


def _brief_command(command):
    return {
        "sample_id": command["sample_id"],
        "mode": command["mode"],
        "targets": command["targets"],
        "reason": command["reason"],
    }


def _brief_status(status):
    return {
        "sample_id": status["sample_id"],
        "status_code": status["status_code"],
        "applied": status["applied"],
        "remark": status["remark"],
    }


if __name__ == "__main__":
    main()
