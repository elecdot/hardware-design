"""First-version comfort policy for sleep-state-aware actuator control.

The policy is deliberately a pure function over dictionaries so it can be
tested before socket, dashboard, storage, or PYNQ integration work starts.
"""

from protocol import build_no_action_command, now_text, validate_message


POLICY_ID = "comfort_v1"

MODE_AUTO = "auto"
MODE_MANUAL = "manual"

IR_MIN_INTERVAL_S = 5.0
IR_REPEAT_COOLDOWN_S = 60.0

HUMIDITY_LOW = 40.0
HUMIDITY_HIGH = 60.0

TEMP_BANDS = {
    0: (24.5, 27.0),
    1: (24.0, 27.5),
    2: (23.5, 28.0),
}

AGGRESSIVENESS = {
    0: 1.0,
    1: 0.6,
    2: 0.3,
}


def initial_policy_state(now_s=0.0):
    return {
        "last_ir_command": None,
        "last_ir_at_s": None,
        "last_humidifier_enabled": None,
        "last_commanded_state": {
            "ir_ac": {},
            "humidifier": {},
        },
        "now_s": float(now_s),
    }


def decide_control_command(
    sensor_data,
    sleep_result,
    policy_state=None,
    mode=MODE_AUTO,
    pending_manual_command=None,
    now_s=None,
):
    """Build one control_command for a sensor/sample cycle.

    Returns ``(command, next_policy_state)``. ``next_policy_state`` is a shallow
    dictionary suitable for passing into the next policy call.
    """
    state = _copy_policy_state(policy_state)
    now_value = _resolve_now(state, now_s)
    sample_id = sensor_data.get("sample_id", sleep_result.get("sample_id", -1))

    if mode == MODE_MANUAL:
        command = _manual_command(sample_id, pending_manual_command)
        next_state = _update_state_from_command(state, command, now_value)
        validate_message(command, expected_type="control_command")
        return command, next_state

    if mode != MODE_AUTO:
        command = _no_action(sample_id, MODE_AUTO, "invalid_mode")
        validate_message(command, expected_type="control_command")
        return command, state

    invalid_reason = _invalid_auto_reason(sensor_data, sleep_result)
    if invalid_reason:
        command = _no_action(sample_id, MODE_AUTO, invalid_reason)
        validate_message(command, expected_type="control_command")
        return command, state

    sleep_code = int(sleep_result.get("sleep_state_code"))
    temperature = _float(sensor_data.get("temperature_c"))
    humidity = _float(sensor_data.get("humidity_percent"))

    targets = {}
    reasons = []

    humidifier_target, humidifier_reason = _humidifier_decision(humidity, state)
    if humidifier_target is not None:
        targets["humidifier"] = {"enabled": humidifier_target}
        reasons.append(humidifier_reason)

    ir_command, ir_reason = _ir_decision(temperature, sleep_code, state, now_value)
    if ir_command is not None:
        targets["ir_ac"] = _ir_target(ir_command)
        reasons.append(ir_reason)
    elif ir_reason:
        reasons.append(ir_reason)

    if not targets:
        reason = "_".join(reasons) if reasons else "comfort_no_action"
        command = _no_action(sample_id, MODE_AUTO, reason)
        validate_message(command, expected_type="control_command")
        return command, state

    command = {
        "type": "control_command",
        "timestamp": now_text(),
        "sample_id": sample_id,
        "mode": MODE_AUTO,
        "policy_id": POLICY_ID,
        "targets": targets,
        "valid": 1,
        "reason": "_and_".join(reasons),
    }
    next_state = _update_state_from_command(state, command, now_value)
    validate_message(command, expected_type="control_command")
    return command, next_state


def _manual_command(sample_id, pending_manual_command):
    if not pending_manual_command:
        return _no_action(sample_id, MODE_MANUAL, "manual_idle")

    if pending_manual_command.get("type") == "control_command":
        command = dict(pending_manual_command)
        command["timestamp"] = now_text()
        command["sample_id"] = sample_id
        command["mode"] = MODE_MANUAL
        command["policy_id"] = command.get("policy_id") or POLICY_ID
        command["valid"] = command.get("valid", 1)
        command["reason"] = command.get("reason") or "dashboard_manual"
        validate_message(command, expected_type="control_command")
        return command

    targets = pending_manual_command.get("targets")
    if targets is None:
        targets = _manual_targets_from_action(pending_manual_command)

    command = {
        "type": "control_command",
        "timestamp": now_text(),
        "sample_id": sample_id,
        "mode": MODE_MANUAL,
        "policy_id": POLICY_ID,
        "targets": targets,
        "valid": 1,
        "reason": pending_manual_command.get("reason") or "dashboard_manual",
    }
    validate_message(command, expected_type="control_command")
    return command


def _manual_targets_from_action(action):
    target = action.get("target")
    if target == "ir_ac":
        return {"ir_ac": _ir_target(action.get("command"))}
    if target == "humidifier":
        return {"humidifier": {"enabled": bool(action.get("enabled"))}}
    return {}


def _invalid_auto_reason(sensor_data, sleep_result):
    if _boolish(sensor_data.get("data_valid")) != 1:
        return "sensor_data_invalid"
    if _boolish(sleep_result.get("state_valid")) != 1:
        remark = str(sleep_result.get("remark", "classifier_invalid"))
        if "warmup" in remark:
            return "classifier_invalid_model_warmup"
        return "classifier_invalid"
    if _float(sensor_data.get("temperature_c")) is None:
        return "missing_temperature"
    if _float(sensor_data.get("humidity_percent")) is None:
        return "missing_humidity"
    return None


def _humidifier_decision(humidity, state):
    if humidity is None:
        return None, "missing_humidity"
    if humidity < HUMIDITY_LOW:
        if state.get("last_humidifier_enabled") is True:
            return None, "humidifier_already_on"
        return True, "humidity_low"
    if humidity > HUMIDITY_HIGH:
        if state.get("last_humidifier_enabled") is False:
            return None, "humidifier_already_off"
        return False, "humidity_high"
    return None, "humidity_comfort"


def _ir_decision(temperature, sleep_code, state, now_s):
    if temperature is None:
        return None, "missing_temperature"

    low, high = TEMP_BANDS.get(int(sleep_code), TEMP_BANDS[1])
    if low <= temperature <= high:
        return None, None

    command = None
    reason = None
    if temperature > high:
        command = _high_temp_command(temperature, high)
        reason = "temperature_high"
    elif temperature < low:
        command = _low_temp_command(temperature, low)
        reason = "temperature_low"

    if command is None:
        return None, reason

    cooldown_reason = _ir_cooldown_reason(command, state, now_s)
    if cooldown_reason:
        return None, cooldown_reason
    return command, reason


def _high_temp_command(temperature, high):
    delta = temperature - high
    if delta >= 3.0:
        return "temp_24"
    if delta >= 1.5:
        return "temp_25"
    return "temp_26"


def _low_temp_command(temperature, low):
    delta = low - temperature
    if delta >= 1.5:
        return "temp_28"
    return "temp_27"


def _ir_cooldown_reason(command, state, now_s):
    last_at = state.get("last_ir_at_s")
    if last_at is None:
        return None

    elapsed = now_s - float(last_at)
    if elapsed < IR_MIN_INTERVAL_S:
        return "cooldown_ir_min_interval"
    if (
        state.get("last_ir_command") == command
        and elapsed < IR_REPEAT_COOLDOWN_S
    ):
        return "cooldown_same_ir_command"
    return None


def _ir_target(command):
    if command is None:
        return {}
    target = {"command": command}
    if command.startswith("temp_"):
        target["temperature_setpoint_c"] = int(command.split("_", 1)[1])
    return target


def _update_state_from_command(state, command, now_s):
    next_state = _copy_policy_state(state)
    next_state["now_s"] = float(now_s)

    targets = command.get("targets") or {}
    ir_target = targets.get("ir_ac")
    if ir_target and ir_target.get("command"):
        command_name = ir_target["command"]
        next_state["last_ir_command"] = command_name
        next_state["last_ir_at_s"] = float(now_s)
        next_state["last_commanded_state"]["ir_ac"] = dict(ir_target)

    humidifier = targets.get("humidifier")
    if humidifier and "enabled" in humidifier:
        enabled = bool(humidifier["enabled"])
        next_state["last_humidifier_enabled"] = enabled
        next_state["last_commanded_state"]["humidifier"] = {"enabled": enabled}

    return next_state


def _no_action(sample_id, mode, reason):
    return build_no_action_command(
        sample_id,
        mode=mode,
        reason=reason,
        policy_id=POLICY_ID,
    )


def _resolve_now(state, now_s):
    if now_s is not None:
        return float(now_s)
    if state.get("now_s") is not None:
        return float(state["now_s"])
    return 0.0


def _copy_policy_state(state):
    base = initial_policy_state()
    if state:
        base.update(state)
        last = state.get("last_commanded_state") or {}
        base["last_commanded_state"] = {
            "ir_ac": dict(last.get("ir_ac") or {}),
            "humidifier": dict(last.get("humidifier") or {}),
        }
    return base


def _float(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and abs(number) != float("inf") else None


def _boolish(value):
    if value is True:
        return 1
    if value is False:
        return 0
    if value in (0, 1):
        return int(value)
    return None
