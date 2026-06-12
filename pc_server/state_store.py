"""Thread-safe PC-side state for the integrated dashboard/service.

The state store intentionally has no socket, classifier, policy, or storage
side effects. Service code records validated messages here, then dashboard code
reads serializable snapshots.
"""

import copy
import threading

from protocol import (
    CONTROL_COMMAND,
    CONTROL_MODES,
    CONTROL_STATUS,
    SENSOR_DATA,
    SLEEP_RESULT,
    ProtocolError,
    now_text,
    validate_message,
)


RECORD_TYPES = (SENSOR_DATA, SLEEP_RESULT, CONTROL_COMMAND, CONTROL_STATUS)
MODE_AUTO = "auto"
MODE_MANUAL = "manual"


class AppState(object):
    """Small thread-safe state container for one active PYNQ client."""

    def __init__(self, history_limit=200):
        history_limit = int(history_limit)
        if history_limit <= 0:
            raise ValueError("history_limit must be positive")

        self._lock = threading.RLock()
        self._history_limit = history_limit
        self._active_client = None
        self._control_mode = MODE_AUTO
        self._pending_manual_command = None
        self._last_commanded_state = {
            "ir_ac": {},
            "humidifier": {},
        }
        self._latest = {record_type: None for record_type in RECORD_TYPES}
        self._histories = {record_type: [] for record_type in RECORD_TYPES}
        self._last_update_at = None
        self._last_transmit_at = None
        self._event_version = 0

    def set_active_client(self, address):
        with self._lock:
            self._active_client = _normalize_address(address)
            self._touch()

    def clear_active_client(self, address=None):
        with self._lock:
            if address is not None and self._active_client != _normalize_address(address):
                return False
            if self._active_client is None:
                return False
            self._active_client = None
            self._touch()
            return True

    def set_control_mode(self, mode):
        if mode not in CONTROL_MODES:
            raise ProtocolError("control mode must be auto or manual")
        with self._lock:
            self._control_mode = mode
            if mode == MODE_AUTO:
                self._pending_manual_command = None
            self._touch()

    def queue_manual_command(self, command):
        pending = _normalize_manual_command(command)
        with self._lock:
            self._pending_manual_command = pending
            self._control_mode = MODE_MANUAL
            self._touch()
        return copy.deepcopy(pending)

    def clear_pending_manual_command(self):
        with self._lock:
            if self._pending_manual_command is None:
                return False
            self._pending_manual_command = None
            self._touch()
            return True

    def take_pending_manual_command(self):
        with self._lock:
            pending = copy.deepcopy(self._pending_manual_command)
            self._pending_manual_command = None
            if pending is not None:
                self._touch()
            return pending

    def record_sensor_cycle(self, sensor_data, sleep_result, control_command):
        validate_message(sensor_data, expected_type=SENSOR_DATA)
        validate_message(sleep_result, expected_type=SLEEP_RESULT)
        validate_message(control_command, expected_type=CONTROL_COMMAND)

        with self._lock:
            self._append_unlocked(SENSOR_DATA, sensor_data)
            self._append_unlocked(SLEEP_RESULT, sleep_result)
            self._append_unlocked(CONTROL_COMMAND, control_command)
            self._merge_last_commanded_state(control_command)
            self._last_transmit_at = now_text()
            self._touch()

    def record_control_status(self, control_status):
        validate_message(control_status, expected_type=CONTROL_STATUS)

        with self._lock:
            self._append_unlocked(CONTROL_STATUS, control_status)
            self._touch()

    def record_message(self, message):
        validate_message(message)
        record_type = message["type"]

        with self._lock:
            self._append_unlocked(record_type, message)
            if record_type == CONTROL_COMMAND:
                self._merge_last_commanded_state(message)
                self._last_transmit_at = now_text()
            self._touch()

    def snapshot(self):
        with self._lock:
            latest = copy.deepcopy(self._latest)
            histories = copy.deepcopy(self._histories)
            return {
                "connected": self._active_client is not None,
                "active_client": copy.deepcopy(self._active_client),
                "control_mode": self._control_mode,
                "pending_manual_command": copy.deepcopy(self._pending_manual_command),
                "last_commanded_state": copy.deepcopy(self._last_commanded_state),
                "latest": latest,
                "latest_sensor_data": latest[SENSOR_DATA],
                "latest_sleep_result": latest[SLEEP_RESULT],
                "latest_control_command": latest[CONTROL_COMMAND],
                "latest_control_status": latest[CONTROL_STATUS],
                "histories": histories,
                "last_update_at": self._last_update_at,
                "last_transmit_at": self._last_transmit_at,
                "event_version": self._event_version,
            }

    def _append_unlocked(self, record_type, message):
        item = copy.deepcopy(message)
        self._latest[record_type] = item
        history = self._histories[record_type]
        history.append(item)
        if len(history) > self._history_limit:
            del history[: len(history) - self._history_limit]

    def _merge_last_commanded_state(self, command):
        targets = command.get("targets") or {}
        if "ir_ac" in targets:
            self._last_commanded_state["ir_ac"] = copy.deepcopy(targets["ir_ac"])
        if "humidifier" in targets:
            self._last_commanded_state["humidifier"] = copy.deepcopy(
                targets["humidifier"]
            )

    def _touch(self):
        self._event_version += 1
        self._last_update_at = now_text()


def _normalize_address(address):
    if address is None:
        return None
    if isinstance(address, tuple):
        return {"host": address[0], "port": address[1] if len(address) > 1 else None}
    if isinstance(address, dict):
        return copy.deepcopy(address)
    return {"host": str(address), "port": None}


def _normalize_manual_command(command):
    if command is None:
        return None
    if not isinstance(command, dict):
        raise ProtocolError("manual command must be an object")

    if command.get("type") == CONTROL_COMMAND:
        validate_message(command, expected_type=CONTROL_COMMAND)
        targets = command.get("targets") or {}
        reason = command.get("reason") or "dashboard_manual"
        policy_id = command.get("policy_id") or "comfort_v1"
    else:
        targets = command.get("targets")
        if targets is None:
            targets = _targets_from_manual_action(command)
        reason = command.get("reason") or "dashboard_manual"
        policy_id = command.get("policy_id") or "comfort_v1"
        validate_message(
            {
                "type": CONTROL_COMMAND,
                "timestamp": now_text(),
                "sample_id": 0,
                "mode": MODE_MANUAL,
                "policy_id": policy_id,
                "targets": targets,
                "valid": 1,
                "reason": reason,
            },
            expected_type=CONTROL_COMMAND,
        )

    return {
        "targets": copy.deepcopy(targets),
        "reason": reason,
        "policy_id": policy_id,
    }


def _targets_from_manual_action(command):
    target = command.get("target")
    if target == "ir_ac":
        if "command" not in command:
            raise ProtocolError("manual ir_ac command is required")
        ir_target = {"command": command["command"]}
        if "temperature_setpoint_c" in command:
            ir_target["temperature_setpoint_c"] = command["temperature_setpoint_c"]
        return {"ir_ac": ir_target}

    if target == "humidifier":
        if "enabled" not in command:
            raise ProtocolError("manual humidifier enabled is required")
        return {"humidifier": {"enabled": command["enabled"]}}

    raise ProtocolError("manual command must contain targets or a known target")
