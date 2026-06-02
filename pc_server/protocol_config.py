"""
protocol_config.py

统一保存 socket 通信、Excel 文件、字段表、睡眠状态编码等配置。
后续如果要改字段名、端口号、Excel 文件名，优先改这里。
"""

# =========================
# Socket 配置
# =========================

# PC 服务端监听地址：
# 0.0.0.0 表示监听本机所有网卡，后面 PYNQ 通过网口连接 PC 时也能访问。
SERVER_HOST = "0.0.0.0"

# PC 服务端端口，客户端必须保持一致。
SERVER_PORT = 9000

# 纯 PC 本机测试时，假客户端连接 127.0.0.1。
LOCAL_TEST_HOST = "127.0.0.1"

# 每条 JSON 消息以换行符结尾，用来解决 TCP 粘包问题。
MESSAGE_END = "\n"


# =========================
# Excel 配置
# =========================

EXCEL_FILE = "sleep_monitor_data.xlsx"

SENSOR_SHEET = "sensor_data"
RESULT_SHEET = "sleep_result"


# =========================
# sensor_data 字段
# 板端上传 / PC端保存
# =========================

SENSOR_FIELDS = [
    "timestamp",
    "sample_id",

    "heart_rate_bpm",
    "spo2_percent",

    "accel_x",
    "accel_y",
    "accel_z",

    "gyro_x",
    "gyro_y",
    "gyro_z",

    "mag_x",
    "mag_y",
    "mag_z",

    "turnover_flag",
    "turnover_count",

    "temperature_c",
    "humidity_percent",

    "data_valid",
    "status_code",
    "checksum_ok",
    "remark",
]


# =========================
# sleep_result 字段
# PC端分类 / 回传板端
# =========================

RESULT_FIELDS = [
    "timestamp",
    "sample_id",
    "sleep_state_code",
    "sleep_state_name",
    "state_valid",
    "remark",
]


# =========================
# 睡眠状态编码
# =========================

SLEEP_STATE_NAME = {
    0: "未入睡",
    1: "浅睡眠",
    2: "深度睡眠",
}