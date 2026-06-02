"""
fake_pynq_client.py

运行位置：PC 端

功能：
模拟 PYNQ-Z1 客户端，每隔 2 秒向 PC 服务端发送一条假的 sensor_data。

用于在没有板子的情况下，先测试：
1. socket 是否能通信
2. JSON 是否能解析
3. Excel 是否能保存
4. 服务端是否能返回 sleep_result

运行前：
    先运行 python pc_server.py

运行：
    python fake_pynq_client.py
"""

import json
import random
import socket
import time
from datetime import datetime

from protocol_config import LOCAL_TEST_HOST, SERVER_PORT, MESSAGE_END


def build_fake_sensor_packet(sample_id: int) -> dict:
    """
    构造一条假的 sensor_data 数据包。

    后面真正接 PYNQ 时，这里的假数据会换成真实传感器读取结果。
    """

    heart_rate = random.randint(58, 88)
    spo2 = random.randint(96, 99)

    accel_x = round(random.uniform(-0.20, 0.20), 3)
    accel_y = round(random.uniform(-0.20, 0.20), 3)
    accel_z = round(random.uniform(0.85, 1.10), 3)

    turnover_flag = 1 if random.random() < 0.15 else 0
    turnover_count = random.randint(0, 8)

    temperature = random.randint(24, 30)
    humidity = random.randint(40, 70)

    packet = {
        "type": "sensor_data",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sample_id": sample_id,

        "heart_rate_bpm": heart_rate,
        "spo2_percent": spo2,

        "accel_x": accel_x,
        "accel_y": accel_y,
        "accel_z": accel_z,

        "gyro_x": None,
        "gyro_y": None,
        "gyro_z": None,

        "mag_x": None,
        "mag_y": None,
        "mag_z": None,

        "turnover_flag": turnover_flag,
        "turnover_count": turnover_count,

        "temperature_c": temperature,
        "humidity_percent": humidity,

        "data_valid": 1,
        "status_code": 0,
        "checksum_ok": 1,
        "remark": "fake_client_test",
    }

    return packet


def send_json(sock: socket.socket, obj: dict):
    """
    发送一条 JSON 消息。

    注意：
    末尾一定要加 MESSAGE_END，也就是换行符 \\n。
    服务端就是靠这个判断一条 JSON 是否结束。
    """

    msg = json.dumps(obj, ensure_ascii=False) + MESSAGE_END
    sock.sendall(msg.encode("utf-8"))


def recv_one_json(sock: socket.socket) -> dict:
    """
    接收服务端返回的一条 JSON 消息。
    """

    buffer = ""

    while True:
        chunk = sock.recv(4096)

        if not chunk:
            raise ConnectionError("服务端已断开连接")

        buffer += chunk.decode("utf-8")

        if MESSAGE_END in buffer:
            line, _ = buffer.split(MESSAGE_END, 1)
            return json.loads(line)


def main():
    """
    假客户端主函数。
    """

    print(f"[INFO] 正在连接服务端 {LOCAL_TEST_HOST}:{SERVER_PORT} ...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect((LOCAL_TEST_HOST, SERVER_PORT))

    print("[INFO] 已连接服务端，开始发送假数据")

    try:
        for sample_id in range(1, 11):
            packet = build_fake_sensor_packet(sample_id)

            send_json(sock, packet)
            print("[SEND]", packet)

            result = recv_one_json(sock)
            print("[RECV]", result)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n[INFO] 用户停止假客户端")

    finally:
        sock.close()
        print("[INFO] fake client 已关闭")


if __name__ == "__main__":
    main()