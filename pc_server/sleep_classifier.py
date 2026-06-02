"""
sleep_classifier.py

睡眠状态分类逻辑。

当前是第一版规则占位：
- 后续接入正式神经网络模型时，只需要替换 classify_sleep_state() 函数内部逻辑。
- socket 接收、Excel 保存、结果回传部分不用改。
"""

from datetime import datetime

from protocol_config import SLEEP_STATE_NAME


def classify_sleep_state(data: dict) -> dict:
    """
    根据一条 sensor_data 生成 sleep_result。

    sleep_state_code:
        0 = 未入睡
        1 = 浅睡眠
        2 = 深度睡眠

    当前临时规则：
        数据无效 -> state_valid = 0
        心率高 或 翻身次数多 -> 未入睡
        心率中等 -> 浅睡眠
        心率较低 且 翻身少 -> 深度睡眠
    """

    sample_id = data.get("sample_id", -1)

    # 1. 检查原始数据是否有效
    if data.get("data_valid") != 1:
        return {
            "type": "sleep_result",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sample_id": sample_id,
            "sleep_state_code": 0,
            "state_valid": 0,
            "remark": "data_invalid",
        }

    # 2. 取出核心字段
    heart_rate = data.get("heart_rate_bpm")
    spo2 = data.get("spo2_percent")
    turnover_count = data.get("turnover_count", 0)

    # 3. 检查核心字段是否缺失
    if heart_rate is None or spo2 is None:
        return {
            "type": "sleep_result",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sample_id": sample_id,
            "sleep_state_code": 0,
            "state_valid": 0,
            "remark": "missing_heart_rate_or_spo2",
        }

    # 4. 第一版临时分类规则
    if heart_rate >= 80 or turnover_count >= 5:
        sleep_state_code = 0
        remark = "rule_awake"

    elif 65 <= heart_rate < 80:
        sleep_state_code = 1
        remark = "rule_light_sleep"

    else:
        sleep_state_code = 2
        remark = "rule_deep_sleep"

    # 5. 组装返回结果
    result = {
        "type": "sleep_result",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sample_id": sample_id,
        "sleep_state_code": sleep_state_code,
        "state_valid": 1,
        "remark": remark,
    }

    return result


def get_sleep_state_text(code: int) -> str:
    """
    将睡眠状态编码转成中文。
    """

    return SLEEP_STATE_NAME.get(code, "未知状态")