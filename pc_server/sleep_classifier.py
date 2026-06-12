"""
基于 DREAMT 可穿戴睡眠数据集训练的轻量级时序分类器。

公开数据集:
    https://github.com/anonymousbil/DREAMT

模型输入保持为一条 sensor_data 字典，输出保持为原项目的 sleep_result
字典。由于 socket 每次只传一个采样点，本模块会把采样点持久化到同目录
的 sleep_classifier_history.csv，并从最近历史中构造 30 秒窗口。

训练标签映射:
    W          -> 0 未入睡
    N1/N2/REM  -> 1 浅睡眠
    N3         -> 2 深度睡眠

模型为单向 GRU，只使用当前及过去的数据。权重从同目录的
sleep_model.bin 读取，部署时不依赖 PyTorch/TensorFlow。
"""

import csv
import math
import os
import statistics
import struct
import threading
import zlib
from datetime import datetime
from pathlib import Path

from protocol_config import SLEEP_STATE_NAME


# 板端 integrated_demo.py 默认每 1 秒生成一个 sensor_data。
WINDOW_POINTS = 30
MODEL_CONTEXT_WINDOWS = 240
MAX_HISTORY_ROWS = 43200
SESSION_GAP_SECONDS = 30 * 60
EXPECTED_NIGHT_SECONDS = 8 * 60 * 60
SAMPLE_INTERVAL_SECONDS = 1.0
ACTIVITY_CALIBRATION_FACTOR = 4.927663

HISTORY_FILE = Path(__file__).with_name("sleep_classifier_history.csv")
MODEL_FILE = Path(__file__).with_name("sleep_model.bin")
_HISTORY_LOCK = threading.RLock()
_HISTORY_FIELDS = [
    "sensor_timestamp",
    "sample_id",
    "heart_rate_bpm",
    "spo2_percent",
    "accel_x",
    "accel_y",
    "accel_z",
    "turnover_flag",
    "turnover_count",
    "temperature_c",
    "humidity_percent",
    "data_valid",
    "sleep_state_code",
    "state_valid",
    "result_remark",
]


def _reshape(values, rows, columns):
    return [
        list(values[row * columns:(row + 1) * columns])
        for row in range(rows)
    ]


def _load_model():
    header_struct = struct.Struct("<8s6I")
    try:
        raw = MODEL_FILE.read_bytes()
    except OSError as error:
        raise RuntimeError(f"cannot read sleep model: {MODEL_FILE}") from error
    if len(raw) < header_struct.size:
        raise RuntimeError("sleep model file is truncated")
    magic, version, input_size, hidden_size, head_size, classes, checksum = (
        header_struct.unpack_from(raw)
    )
    payload = raw[header_struct.size:]
    if (
        magic != b"SLPGRU2\0"
        or version != 2
        or (input_size, hidden_size, head_size, classes) != (6, 16, 12, 3)
        or zlib.crc32(payload) != checksum
    ):
        raise RuntimeError("sleep model file has an invalid format")
    values = struct.unpack("<1407f", payload)
    cursor = 0

    def take(count):
        nonlocal cursor
        result = values[cursor:cursor + count]
        cursor += count
        return result

    model = {
        "weight_ih": _reshape(take(48 * 6), 48, 6),
        "weight_hh": _reshape(take(48 * 16), 48, 16),
        "bias_ih": list(take(48)),
        "bias_hh": list(take(48)),
        "head_weight": _reshape(take(12 * 16), 12, 16),
        "head_bias": list(take(12)),
        "output_weight": _reshape(take(3 * 12), 3, 12),
        "output_bias": list(take(3)),
        "feature_mean": list(take(6)),
        "feature_std": list(take(6)),
    }
    if cursor != len(values):
        raise RuntimeError("sleep model has an invalid size")
    return model


_MODEL = _load_model()


def _now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _result(sample_id, code, valid, remark):
    return {
        "type": "sleep_result",
        "timestamp": _now_text(),
        "sample_id": sample_id,
        "sleep_state_code": code,
        "state_valid": valid,
        "remark": remark,
    }


def _float(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _int(value, default=-1):
    number = _float(value)
    return int(number) if number is not None else default


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _row_is_valid(row):
    return (
        _int(row.get("data_valid"), 0) == 1
        and _float(row.get("heart_rate_bpm")) is not None
        and _float(row.get("spo2_percent")) is not None
    )


def _read_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        with HISTORY_FILE.open("r", encoding="utf-8", newline="") as file:
            return list(csv.DictReader(file))
    except (OSError, csv.Error):
        return []


def _write_history(rows):
    rows = rows[-MAX_HISTORY_ROWS:]
    temp_file = HISTORY_FILE.with_suffix(".csv.tmp")
    with temp_file.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=_HISTORY_FIELDS,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp_file, HISTORY_FILE)


def _new_history_row(data):
    return {
        "sensor_timestamp": data.get("timestamp") or _now_text(),
        "sample_id": data.get("sample_id", -1),
        "heart_rate_bpm": data.get("heart_rate_bpm", ""),
        "spo2_percent": data.get("spo2_percent", ""),
        "accel_x": data.get("accel_x", ""),
        "accel_y": data.get("accel_y", ""),
        "accel_z": data.get("accel_z", ""),
        "turnover_flag": data.get("turnover_flag", 0),
        "turnover_count": data.get("turnover_count", 0),
        "temperature_c": data.get("temperature_c", ""),
        "humidity_percent": data.get("humidity_percent", ""),
        "data_valid": data.get("data_valid", 0),
        "sleep_state_code": "",
        "state_valid": 0,
        "result_remark": "",
    }


def _starts_new_session(rows, row):
    if not rows:
        return False

    previous = rows[-1]
    current_id = _int(row.get("sample_id"))
    previous_id = _int(previous.get("sample_id"))
    if current_id >= 0 and previous_id >= 0 and current_id < previous_id:
        return True

    current_time = _parse_time(row.get("sensor_timestamp"))
    previous_time = _parse_time(previous.get("sensor_timestamp"))
    if current_time and previous_time:
        gap = current_time.timestamp() - previous_time.timestamp()
        if gap < 0 or gap > SESSION_GAP_SECONDS:
            return True
    return False


def _same_sample(left, right):
    return (
        str(left.get("sample_id")) == str(right.get("sample_id"))
        and str(left.get("sensor_timestamp")) == str(right.get("sensor_timestamp"))
    )


def _mean(values):
    return sum(values) / len(values)


def _std(values):
    if len(values) < 2:
        return 0.0
    center = _mean(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / len(values))


def _median(values):
    return statistics.median(values) if values else 0.0


def _movement_index(window):
    magnitudes = []
    for row in window:
        vector = tuple(_float(row.get(axis)) for axis in ("accel_x", "accel_y", "accel_z"))
        if all(value is not None for value in vector):
            magnitudes.append(math.sqrt(sum(value * value for value in vector)))

    if len(magnitudes) == WINDOW_POINTS:
        block_size = 5
        activity = sum(
            _std(magnitudes[start:start + block_size])
            for start in range(0, WINDOW_POINTS, block_size)
        )
        return min(3.0, activity * ACTIVITY_CALIBRATION_FACTOR)

    turnover_rate = _mean([
        1.0 if _int(row.get("turnover_flag"), 0) else 0.0
        for row in window
    ])
    return min(3.0, turnover_rate * 0.8)


def _elapsed_progress(rows, end_index):
    first_time = _parse_time(rows[0].get("sensor_timestamp"))
    end_time = _parse_time(rows[end_index].get("sensor_timestamp"))
    if first_time and end_time:
        elapsed = max(0.0, end_time.timestamp() - first_time.timestamp())
    else:
        elapsed = end_index * SAMPLE_INTERVAL_SECONDS
    return min(1.0, elapsed / EXPECTED_NIGHT_SECONDS)


def _window_features(rows, window, end_index, heart_baseline):
    heart_rates = [_float(row["heart_rate_bpm"]) for row in window]
    heart_mean = _mean(heart_rates)
    heart_std = _std(heart_rates)
    heart_range = max(heart_rates) - min(heart_rates)

    features = [
        heart_mean,
        (heart_mean - heart_baseline) / 10.0,
        math.log1p(max(0.0, heart_std)),
        math.log1p(max(0.0, heart_range)),
        math.log1p(_movement_index(window) * 20.0),
        _elapsed_progress(rows, end_index),
    ]

    normalized = []
    for value, center, scale in zip(
        features,
        _MODEL["feature_mean"],
        _MODEL["feature_std"],
    ):
        normalized.append(max(-5.0, min(5.0, (value - center) / scale)))
    return normalized


def _linear(weights, bias, values):
    return [
        sum(weight * value for weight, value in zip(row, values)) + offset
        for row, offset in zip(weights, bias)
    ]


def _sigmoid(value):
    if value >= 0:
        inverse = math.exp(-value)
        return 1.0 / (1.0 + inverse)
    exponent = math.exp(value)
    return exponent / (1.0 + exponent)


def _gru_step(features, hidden):
    input_part = _linear(_MODEL["weight_ih"], _MODEL["bias_ih"], features)
    hidden_part = _linear(_MODEL["weight_hh"], _MODEL["bias_hh"], hidden)

    reset = [
        _sigmoid(input_part[index] + hidden_part[index])
        for index in range(16)
    ]
    update = [
        _sigmoid(input_part[16 + index] + hidden_part[16 + index])
        for index in range(16)
    ]
    candidate = [
        math.tanh(
            input_part[32 + index]
            + reset[index] * hidden_part[32 + index]
        )
        for index in range(16)
    ]
    return [
        (1.0 - update[index]) * candidate[index]
        + update[index] * hidden[index]
        for index in range(16)
    ]


def _predict(rows):
    # 从当前点反向切分互不重叠的 30 秒窗口。这样每次调用都会推断
    # 当前时刻，同时避免把高度重叠的 1 秒滑窗反复累计进 GRU。
    end_indices = list(range(
        len(rows) - 1,
        WINDOW_POINTS - 2,
        -WINDOW_POINTS,
    ))
    end_indices = list(reversed(end_indices[:MODEL_CONTEXT_WINDOWS]))

    hidden = [0.0] * 16
    for end_index in end_indices:
        window = rows[end_index - WINDOW_POINTS + 1:end_index + 1]
        if len(window) != WINDOW_POINTS or not all(_row_is_valid(row) for row in window):
            hidden = [0.0] * 16
            continue
        heart_baseline = _median([
            _float(row.get("heart_rate_bpm"))
            for row in rows[:end_index + 1]
            if _row_is_valid(row)
        ])
        features = _window_features(
            rows,
            window,
            end_index,
            heart_baseline,
        )
        hidden = _gru_step(features, hidden)

    head = [
        max(0.0, value)
        for value in _linear(
            _MODEL["head_weight"],
            _MODEL["head_bias"],
            hidden,
        )
    ]
    logits = _linear(
        _MODEL["output_weight"],
        _MODEL["output_bias"],
        head,
    )
    code = max(range(3), key=logits.__getitem__)
    peak = max(logits)
    denominator = sum(math.exp(value - peak) for value in logits)
    confidence = math.exp(logits[code] - peak) / denominator
    return code, confidence


def _valid_suffix_length(rows):
    count = 0
    for row in reversed(rows):
        if not _row_is_valid(row):
            break
        count += 1
    return count


def classify_sleep_state(data: dict) -> dict:
    """
    保存单点传感器数据，并在历史窗口足够后返回睡眠阶段。

    sleep_state_code:
        0 = 未入睡
        1 = 浅睡眠
        2 = 深度睡眠

    前 WINDOW_POINTS - 1 个有效点返回 state_valid=0；第 WINDOW_POINTS
    个点起使用当前及历史数据推断。
    """

    sample_id = data.get("sample_id", -1)
    if data.get("data_valid") != 1:
        invalid_result = _result(sample_id, 0, 0, "data_invalid")
    elif (
        _float(data.get("heart_rate_bpm")) is None
        or _float(data.get("spo2_percent")) is None
    ):
        invalid_result = _result(
            sample_id,
            0,
            0,
            "missing_heart_rate_or_spo2",
        )
    else:
        invalid_result = None

    with _HISTORY_LOCK:
        rows = _read_history()
        row = _new_history_row(data)
        if _starts_new_session(rows, row):
            rows = []
        if not rows or not _same_sample(rows[-1], row):
            rows.append(row)

        if invalid_result is not None:
            rows[-1]["sleep_state_code"] = invalid_result["sleep_state_code"]
            rows[-1]["state_valid"] = invalid_result["state_valid"]
            rows[-1]["result_remark"] = invalid_result["remark"]
            _write_history(rows)
            return invalid_result

        available = _valid_suffix_length(rows)
        if available < WINDOW_POINTS:
            result = _result(
                sample_id,
                0,
                0,
                f"model_warmup_{available}_of_{WINDOW_POINTS}",
            )
        else:
            code, confidence = _predict(rows)
            result = _result(
                sample_id,
                code,
                1,
                f"model_dreamt_gru_conf_{confidence:.3f}",
            )

        rows[-1]["sleep_state_code"] = result["sleep_state_code"]
        rows[-1]["state_valid"] = result["state_valid"]
        rows[-1]["result_remark"] = result["remark"]
        _write_history(rows)
        return result


def get_sleep_state_text(code: int) -> str:
    """将睡眠状态编码转成中文。"""

    return SLEEP_STATE_NAME.get(code, "未知状态")
