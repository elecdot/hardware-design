"""Canonical newline-JSON protocol helpers for the PC/PYNQ link.

This module intentionally uses only the Python standard library so it can be
reused by PC tests and, if needed, copied to the PYNQ side without dependency
changes.
"""

import json
from datetime import datetime

from protocol_config import MESSAGE_END


SENSOR_DATA = "sensor_data"
SLEEP_RESULT = "sleep_result"
CONTROL_COMMAND = "control_command"
CONTROL_STATUS = "control_status"

MESSAGE_TYPES = {
    SENSOR_DATA,
    SLEEP_RESULT,
    CONTROL_COMMAND,
    CONTROL_STATUS,
}

IR_AC_COMMANDS = {
    "power_on",
    "power_off",
    "temp_24",
    "temp_25",
    "temp_26",
    "temp_27",
    "temp_28",
}

CONTROL_MODES = {"auto", "manual"}
CONTROL_TARGETS = {"ir_ac", "humidifier"}

STATUS_OK = 0
STATUS_REJECTED = 1
STATUS_SKIPPED = 2
STATUS_HW_ERROR = 3
CONTROL_STATUS_CODES = {
    STATUS_OK,
    STATUS_REJECTED,
    STATUS_SKIPPED,
    STATUS_HW_ERROR,
}


class ProtocolError(ValueError):
    """Raised when a message violates the project socket protocol."""


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def encode_message(message, validate=True):
    """Serialize one protocol message and append the newline terminator."""
    if validate:
        validate_message(message)
    return json.dumps(message, ensure_ascii=False, separators=(",", ":")) + MESSAGE_END


def decode_message(line, validate=True):
    """Decode one newline-delimited JSON message."""
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    line = line.strip()
    if not line:
        raise ProtocolError("empty message")
    try:
        message = json.loads(line)
    except ValueError as exc:
        raise ProtocolError("invalid JSON") from exc
    if validate:
        validate_message(message)
    return message


class MessageBuffer(object):
    """Incrementally split TCP byte streams into validated JSON messages."""

    def __init__(self, validate=True):
        self._buffer = ""
        self._validate = bool(validate)

    def feed(self, chunk):
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8")
        self._buffer += chunk

        messages = []
        while MESSAGE_END in self._buffer:
            line, self._buffer = self._buffer.split(MESSAGE_END, 1)
            if not line.strip():
                continue
            messages.append(decode_message(line, validate=self._validate))
        return messages


def validate_message(message, expected_type=None):
    if not isinstance(message, dict):
        raise ProtocolError("message must be an object")
    message_type = message.get("type")
    if message_type not in MESSAGE_TYPES:
        raise ProtocolError("unknown message type: {0}".format(message_type))
    if expected_type is not None and message_type != expected_type:
        raise ProtocolError(
            "expected {0}, got {1}".format(expected_type, message_type)
        )

    if message_type == SENSOR_DATA:
        _validate_sensor_data(message)
    elif message_type == SLEEP_RESULT:
        _validate_sleep_result(message)
    elif message_type == CONTROL_COMMAND:
        _validate_control_command(message)
    elif message_type == CONTROL_STATUS:
        _validate_control_status(message)
    return message


def build_no_action_command(sample_id, mode="auto", reason="no_action", policy_id="comfort_v1"):
    return {
        "type": CONTROL_COMMAND,
        "timestamp": now_text(),
        "sample_id": sample_id,
        "mode": mode,
        "policy_id": policy_id,
        "targets": {},
        "valid": 1,
        "reason": reason,
    }


def build_rejected_status(sample_id, reason, remark=None):
    return {
        "type": CONTROL_STATUS,
        "timestamp": now_text(),
        "sample_id": sample_id,
        "accepted": 0,
        "applied": {},
        "status_code": STATUS_REJECTED,
        "remark": remark or reason,
    }


def _validate_sensor_data(message):
    _require(message, ("type", "timestamp", "sample_id", "data_valid", "status_code"))
    _require_intish(message, "sample_id")
    _require_boolish(message, "data_valid")
    _require_intish(message, "status_code")
    if "checksum_ok" in message and message.get("checksum_ok") is not None:
        _require_boolish(message, "checksum_ok")


def _validate_sleep_result(message):
    _require(
        message,
        ("type", "timestamp", "sample_id", "sleep_state_code", "state_valid", "remark"),
    )
    _require_intish(message, "sample_id")
    _require_intish(message, "sleep_state_code")
    if int(message["sleep_state_code"]) not in (0, 1, 2):
        raise ProtocolError("sleep_state_code must be 0, 1, or 2")
    _require_boolish(message, "state_valid")


def _validate_control_command(message):
    _require(
        message,
        ("type", "timestamp", "sample_id", "mode", "policy_id", "targets", "valid", "reason"),
    )
    _require_intish(message, "sample_id")
    if message.get("mode") not in CONTROL_MODES:
        raise ProtocolError("mode must be auto or manual")
    if not isinstance(message.get("policy_id"), str):
        raise ProtocolError("policy_id must be a string")
    if not isinstance(message.get("reason"), str):
        raise ProtocolError("reason must be a string")
    _require_boolish(message, "valid")

    targets = message.get("targets")
    if not isinstance(targets, dict):
        raise ProtocolError("targets must be an object")
    unknown = set(targets) - CONTROL_TARGETS
    if unknown:
        raise ProtocolError("unknown target(s): {0}".format(", ".join(sorted(unknown))))

    if "ir_ac" in targets:
        _validate_ir_ac_target(targets["ir_ac"])
    if "humidifier" in targets:
        _validate_humidifier_target(targets["humidifier"])


def _validate_control_status(message):
    _require(
        message,
        ("type", "timestamp", "sample_id", "accepted", "applied", "status_code", "remark"),
    )
    _require_intish(message, "sample_id")
    _require_boolish(message, "accepted")
    if not isinstance(message.get("applied"), dict):
        raise ProtocolError("applied must be an object")
    _require_intish(message, "status_code")
    if int(message["status_code"]) not in CONTROL_STATUS_CODES:
        raise ProtocolError("invalid control status_code")
    if not isinstance(message.get("remark"), str):
        raise ProtocolError("remark must be a string")

    applied = message["applied"]
    unknown = set(applied) - CONTROL_TARGETS
    if unknown:
        raise ProtocolError("unknown applied target(s): {0}".format(", ".join(sorted(unknown))))
    if "ir_ac" in applied:
        _validate_ir_ac_status(applied["ir_ac"])
    if "humidifier" in applied:
        _validate_humidifier_status(applied["humidifier"])


def _validate_ir_ac_target(target):
    if not isinstance(target, dict):
        raise ProtocolError("ir_ac target must be an object")
    command = target.get("command")
    if command not in IR_AC_COMMANDS:
        raise ProtocolError("unknown ir_ac command: {0}".format(command))
    if "temperature_setpoint_c" in target and target["temperature_setpoint_c"] is not None:
        value = _number(target["temperature_setpoint_c"], "temperature_setpoint_c")
        if value < 24 or value > 28:
            raise ProtocolError("temperature_setpoint_c must be 24..28")


def _validate_humidifier_target(target):
    if not isinstance(target, dict):
        raise ProtocolError("humidifier target must be an object")
    if "enabled" not in target:
        raise ProtocolError("humidifier.enabled is required")
    _boolish(target["enabled"], "humidifier.enabled")


def _validate_ir_ac_status(status):
    if not isinstance(status, dict):
        raise ProtocolError("ir_ac status must be an object")
    for field in ("requested", "sent", "skipped"):
        if field in status:
            _boolish(status[field], "ir_ac.{0}".format(field))
    if status.get("command") is not None and status.get("command") not in IR_AC_COMMANDS:
        raise ProtocolError("unknown ir_ac status command")
    if "status" in status and status["status"] is not None:
        if not isinstance(status["status"], dict):
            raise ProtocolError("ir_ac.status must be an object")


def _validate_humidifier_status(status):
    if not isinstance(status, dict):
        raise ProtocolError("humidifier status must be an object")
    for field in ("requested", "enabled", "applied", "skipped", "humidifier_on"):
        if field in status and status[field] is not None:
            _boolish(status[field], "humidifier.{0}".format(field))


def _require(message, fields):
    for field in fields:
        if field not in message:
            raise ProtocolError("missing required field: {0}".format(field))


def _require_intish(message, field):
    if field not in message:
        raise ProtocolError("missing required field: {0}".format(field))
    _intish(message[field], field)


def _require_boolish(message, field):
    if field not in message:
        raise ProtocolError("missing required field: {0}".format(field))
    _boolish(message[field], field)


def _intish(value, field):
    if isinstance(value, bool):
        raise ProtocolError("{0} must be an integer".format(field))
    try:
        int(value)
    except (TypeError, ValueError):
        raise ProtocolError("{0} must be an integer".format(field))


def _boolish(value, field):
    if isinstance(value, bool):
        return
    if value in (0, 1):
        return
    raise ProtocolError("{0} must be boolean-like".format(field))


def _number(value, field):
    if isinstance(value, bool):
        raise ProtocolError("{0} must be a number".format(field))
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ProtocolError("{0} must be a number".format(field))
