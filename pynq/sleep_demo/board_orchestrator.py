"""Reusable PYNQ-side orchestrator for the sleep monitor overlay.

This module is deliberately lightweight and Python 3.6 compatible. It can be
imported on a PC for protocol-shape self-tests, while real hardware binding
continues to live in ``integrated_demo.py`` until the socket client is added.
"""

import time

from integrated_demo import (
    DEFAULT_JY901_MAX_STALE_S,
    DEFAULT_JY901_RETRIES,
    DEFAULT_JY901_RETRY_DELAY_S,
    TurnCounter,
    empty_sample,
    finalize_sample_validity,
    read_dht11,
    read_jy901,
    read_spo2,
    update_humidifier,
)


IR_AC_COMMANDS = {
    "power_on",
    "power_off",
    "temp_24",
    "temp_25",
    "temp_26",
    "temp_27",
    "temp_28",
}

STATUS_OK = 0
STATUS_REJECTED = 1
STATUS_SKIPPED = 2
STATUS_HW_ERROR = 3

DEFAULT_IR_MIN_INTERVAL_S = 5.0
DEFAULT_IR_REPEAT_COOLDOWN_S = 60.0
DEFAULT_IR_TIMEOUT_S = 15.0


class SleepMonitorBoard(object):
    """Top-level board wrapper for sampling and actuator command execution."""

    def __init__(
        self,
        drivers=None,
        sensor_timeout_s=0.5,
        dht11_period_s=2.0,
        jy901_retries=DEFAULT_JY901_RETRIES,
        jy901_retry_delay_s=DEFAULT_JY901_RETRY_DELAY_S,
        jy901_max_stale_s=DEFAULT_JY901_MAX_STALE_S,
        turn_threshold_deg=35.0,
        ir_min_interval_s=DEFAULT_IR_MIN_INTERVAL_S,
        ir_repeat_cooldown_s=DEFAULT_IR_REPEAT_COOLDOWN_S,
        ir_timeout_s=DEFAULT_IR_TIMEOUT_S,
        time_fn=None,
    ):
        self.drivers = drivers or {}
        self.sensor_timeout_s = float(sensor_timeout_s)
        self.dht11_period_s = float(dht11_period_s)
        self.jy901_retries = int(jy901_retries)
        self.jy901_retry_delay_s = float(jy901_retry_delay_s)
        self.jy901_max_stale_s = float(jy901_max_stale_s)
        self.ir_min_interval_s = float(ir_min_interval_s)
        self.ir_repeat_cooldown_s = float(ir_repeat_cooldown_s)
        self.ir_timeout_s = float(ir_timeout_s)
        self.time_fn = time_fn or time.time
        self.turn_counter = TurnCounter(threshold_deg=turn_threshold_deg)
        self.dht_cache = {}
        self.jy901_cache = {}
        self.sample_id = 0
        self.display_values = None
        self.last_ir_command = None
        self.last_ir_at_s = None
        self.last_control_status = None

    def read_sample(self):
        """Read one ``sensor_data`` sample using the currently bound drivers."""
        self.sample_id += 1
        now_s = self.time_fn()
        sample = empty_sample(self.sample_id)
        read_jy901(
            self.drivers,
            sample,
            self.turn_counter,
            self.sensor_timeout_s,
            retries=self.jy901_retries,
            retry_delay_s=self.jy901_retry_delay_s,
            stale_cache=self.jy901_cache,
            now_s=now_s,
            max_stale_s=self.jy901_max_stale_s,
        )
        read_dht11(self.drivers, sample, self.dht_cache, now_s, self.dht11_period_s)
        read_spo2(self.drivers, sample)
        update_humidifier(self.drivers, sample)
        finalize_sample_validity(sample)
        return sample

    def update_display(self, sample, control_status=None):
        """Update TFT display if an LCD driver is present."""
        lcd = self.drivers.get("lcd")
        if lcd is None:
            return None

        from display_ui import draw_dashboard, update_dashboard

        display_sample = dict(sample)
        if control_status is not None:
            display_sample["status_line"] = _short_status_line(control_status)
        if self.display_values is None:
            self.display_values = draw_dashboard(lcd, display_sample)
        else:
            self.display_values = update_dashboard(
                lcd,
                display_sample,
                self.display_values,
            )
        return self.display_values

    def apply_control_command(self, command):
        """Apply one PC-originated ``control_command`` and return status."""
        sample_id = _sample_id(command)
        try:
            _validate_control_command(command)
        except Exception as exc:
            return self._remember_status(
                _rejected_status(sample_id, "invalid_command:{0}".format(exc))
            )

        if _boolish(command.get("valid")) != 1:
            return self._remember_status(
                _rejected_status(sample_id, "command_marked_invalid")
            )

        targets = command.get("targets") or {}
        if not targets:
            return self._remember_status(
                _status(
                    sample_id,
                    accepted=1,
                    applied={},
                    status_code=STATUS_SKIPPED,
                    remark=command.get("reason") or "no_action",
                )
            )

        applied = {}
        target_codes = []
        remarks = []

        if "humidifier" in targets:
            entry, code, remark = self._apply_humidifier(targets["humidifier"])
            applied["humidifier"] = entry
            target_codes.append(code)
            remarks.append(remark)

        if "ir_ac" in targets:
            entry, code, remark = self._apply_ir_ac(targets["ir_ac"])
            applied["ir_ac"] = entry
            target_codes.append(code)
            remarks.append(remark)

        return self._remember_status(
            _status(
                sample_id,
                accepted=1,
                applied=applied,
                status_code=_merge_status_code(target_codes),
                remark="_and_".join([item for item in remarks if item]) or "control_applied",
            )
        )

    def _apply_humidifier(self, target):
        enabled = bool(target.get("enabled"))
        humidifier = self.drivers.get("humidifier")
        if humidifier is None:
            return (
                _humidifier_entry(
                    requested=True,
                    enabled=enabled,
                    applied=False,
                    skipped=True,
                    skip_reason="humidifier_missing",
                    error=None,
                    humidifier_on=None,
                ),
                STATUS_SKIPPED,
                "humidifier_missing",
            )

        try:
            humidifier.manual(enabled)
            status = humidifier.status() if hasattr(humidifier, "status") else {}
            humidifier_on = status.get("humidifier_on", enabled)
            return (
                _humidifier_entry(
                    requested=True,
                    enabled=enabled,
                    applied=True,
                    skipped=False,
                    skip_reason=None,
                    error=None,
                    humidifier_on=bool(humidifier_on),
                ),
                STATUS_OK,
                "humidifier_applied",
            )
        except Exception as exc:
            return (
                _humidifier_entry(
                    requested=True,
                    enabled=enabled,
                    applied=False,
                    skipped=False,
                    skip_reason=None,
                    error=str(exc),
                    humidifier_on=None,
                ),
                STATUS_HW_ERROR,
                "humidifier_error",
            )

    def _apply_ir_ac(self, target):
        command = target.get("command")
        now_s = self.time_fn()
        cooldown_reason = self._ir_cooldown_reason(command, now_s)
        if cooldown_reason:
            return (
                _ir_entry(
                    requested=True,
                    command=command,
                    sent=False,
                    skipped=True,
                    skip_reason=cooldown_reason,
                    error=None,
                    status=None,
                ),
                STATUS_SKIPPED,
                cooldown_reason,
            )

        ir_ac = self.drivers.get("ir_ac")
        if ir_ac is None:
            return (
                _ir_entry(
                    requested=True,
                    command=command,
                    sent=False,
                    skipped=True,
                    skip_reason="ir_ac_missing",
                    error=None,
                    status=None,
                ),
                STATUS_SKIPPED,
                "ir_ac_missing",
            )

        try:
            ir_ac.send_command(command, timeout=self.ir_timeout_s)
            status = ir_ac.status() if hasattr(ir_ac, "status") else _default_ir_status(command)
            self.last_ir_command = command
            self.last_ir_at_s = now_s
            return (
                _ir_entry(
                    requested=True,
                    command=command,
                    sent=True,
                    skipped=False,
                    skip_reason=None,
                    error=None,
                    status=status,
                ),
                STATUS_OK,
                "ir_ac_sent",
            )
        except Exception as exc:
            status = None
            if hasattr(ir_ac, "status"):
                try:
                    status = ir_ac.status()
                except Exception:
                    status = None
            return (
                _ir_entry(
                    requested=True,
                    command=command,
                    sent=False,
                    skipped=False,
                    skip_reason=None,
                    error=str(exc),
                    status=status,
                ),
                STATUS_HW_ERROR,
                "ir_ac_error",
            )

    def _ir_cooldown_reason(self, command, now_s):
        if self.last_ir_at_s is None:
            return None

        elapsed = float(now_s) - float(self.last_ir_at_s)
        if elapsed < self.ir_min_interval_s:
            return "cooldown_ir_min_interval"
        if (
            command == self.last_ir_command
            and elapsed < self.ir_repeat_cooldown_s
        ):
            return "cooldown_same_ir_command"
        return None

    def _remember_status(self, status):
        self.last_control_status = status
        return status


def _validate_control_command(command):
    if not isinstance(command, dict):
        raise ValueError("command must be an object")
    if command.get("type") != "control_command":
        raise ValueError("type must be control_command")
    _sample_id(command)
    if command.get("mode") not in ("auto", "manual"):
        raise ValueError("mode must be auto or manual")
    if not isinstance(command.get("policy_id"), str):
        raise ValueError("policy_id must be a string")
    if not isinstance(command.get("reason"), str):
        raise ValueError("reason must be a string")
    _boolish(command.get("valid"))

    targets = command.get("targets")
    if not isinstance(targets, dict):
        raise ValueError("targets must be an object")
    unknown = set(targets) - set(("ir_ac", "humidifier"))
    if unknown:
        raise ValueError("unknown targets: {0}".format(",".join(sorted(unknown))))
    if "ir_ac" in targets:
        _validate_ir_target(targets["ir_ac"])
    if "humidifier" in targets:
        _validate_humidifier_target(targets["humidifier"])


def _validate_ir_target(target):
    if not isinstance(target, dict):
        raise ValueError("ir_ac target must be an object")
    command = target.get("command")
    if command not in IR_AC_COMMANDS:
        raise ValueError("unknown ir_ac command: {0}".format(command))
    if "temperature_setpoint_c" in target and target["temperature_setpoint_c"] is not None:
        value = int(target["temperature_setpoint_c"])
        if value < 24 or value > 28:
            raise ValueError("temperature_setpoint_c must be 24..28")


def _validate_humidifier_target(target):
    if not isinstance(target, dict):
        raise ValueError("humidifier target must be an object")
    if "enabled" not in target:
        raise ValueError("humidifier.enabled is required")
    _boolish(target["enabled"])


def _status(sample_id, accepted, applied, status_code, remark):
    return {
        "type": "control_status",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sample_id": sample_id,
        "accepted": 1 if accepted else 0,
        "applied": applied,
        "status_code": int(status_code),
        "remark": str(remark),
    }


def _rejected_status(sample_id, remark):
    return _status(
        sample_id,
        accepted=0,
        applied={},
        status_code=STATUS_REJECTED,
        remark=remark,
    )


def _ir_entry(requested, command, sent, skipped, skip_reason, error, status):
    return {
        "requested": bool(requested),
        "command": command,
        "sent": bool(sent),
        "skipped": bool(skipped),
        "skip_reason": skip_reason,
        "error": error,
        "status": status,
    }


def _humidifier_entry(
    requested,
    enabled,
    applied,
    skipped,
    skip_reason,
    error,
    humidifier_on,
):
    return {
        "requested": bool(requested),
        "enabled": bool(enabled),
        "applied": bool(applied),
        "skipped": bool(skipped),
        "skip_reason": skip_reason,
        "error": error,
        "humidifier_on": humidifier_on,
    }


def _default_ir_status(command):
    return {
        "done": True,
        "error": False,
        "raw_status": 2,
        "command": command,
    }


def _short_status_line(status):
    applied = status.get("applied") or {}
    ir_status = applied.get("ir_ac") or {}
    if ir_status.get("sent"):
        return "AC {0} sent".format(ir_status.get("command"))
    if ir_status.get("skipped"):
        return "AC skip {0}".format(ir_status.get("skip_reason"))
    humidifier = applied.get("humidifier") or {}
    if humidifier.get("applied"):
        return "HUM {0}".format("ON" if humidifier.get("enabled") else "OFF")
    return status.get("remark", "")


def _merge_status_code(codes):
    if not codes:
        return STATUS_SKIPPED
    if STATUS_HW_ERROR in codes:
        return STATUS_HW_ERROR
    if STATUS_REJECTED in codes:
        return STATUS_REJECTED
    if STATUS_SKIPPED in codes:
        return STATUS_SKIPPED
    return STATUS_OK


def _sample_id(command):
    try:
        return int(command.get("sample_id", -1))
    except (TypeError, ValueError):
        raise ValueError("sample_id must be an integer")


def _boolish(value):
    if isinstance(value, bool):
        return 1 if value else 0
    if value in (0, 1):
        return int(value)
    raise ValueError("value must be boolean-like")
