"""
pc_server.py

运行位置：PC 端

功能：
1. 开启 TCP socket 服务端
2. 接收 PYNQ / fake client 发来的 JSON 数据
3. 保存 sensor_data 到 Excel
4. 调用分类函数生成 sleep_result
5. 保存 sleep_result 到 Excel
6. 把 sleep_result 通过 socket 回传给客户端

运行：
    python pc_server.py
"""

import json
import socket
import traceback

from protocol_config import SERVER_HOST, SERVER_PORT, MESSAGE_END
from excel_utils import init_excel, append_sensor_data, append_sleep_result
from sleep_classifier import classify_sleep_state, get_sleep_state_text


def send_json(conn: socket.socket, obj: dict):
    """
    发送一条 JSON 消息。

    注意：
    每条 JSON 后面都加 MESSAGE_END，也就是换行符 \\n。
    这样客户端才能知道一条消息在哪里结束。
    """

    msg = json.dumps(obj, ensure_ascii=False) + MESSAGE_END
    conn.sendall(msg.encode("utf-8"))


def recv_json_lines(conn: socket.socket):
    """
    按行接收 JSON。

    TCP 是字节流，可能会出现：
    - 一次 recv 收到半条 JSON
    - 一次 recv 收到多条 JSON

    所以我们约定：
    每条 JSON 末尾都加 \\n。
    接收端按 \\n 分割。
    """

    buffer = ""

    while True:
        chunk = conn.recv(4096)

        # 如果 chunk 为空，说明客户端断开连接
        if not chunk:
            break

        buffer += chunk.decode("utf-8")

        while MESSAGE_END in buffer:
            line, buffer = buffer.split(MESSAGE_END, 1)
            line = line.strip()

            if not line:
                continue

            try:
                data = json.loads(line)
                yield data

            except json.JSONDecodeError as e:
                print("[ERROR] JSON 解析失败:", e)
                print("[ERROR] 原始数据:", line)


def handle_client(conn: socket.socket, addr):
    """
    处理一个客户端连接。
    """

    print(f"[INFO] 客户端已连接: {addr}")

    try:
        for data in recv_json_lines(conn):
            print("[RECV]", data)

            # 只处理 sensor_data 类型的数据
            if data.get("type") != "sensor_data":
                print("[WARN] 收到非 sensor_data 类型，已忽略:", data.get("type"))
                continue

            # 1. 保存原始传感器数据到 Excel
            append_sensor_data(data)

            # 2. 调用分类函数
            result = classify_sleep_state(data)

            # 3. 保存分类结果到 Excel
            append_sleep_result(result)

            # 4. 把分类结果回传给客户端
            send_json(conn, result)

            code = result.get("sleep_state_code")
            state_text = get_sleep_state_text(code)

            print(
                f"[SEND] sample_id={result.get('sample_id')} "
                f"state={code}({state_text})"
            )

    except ConnectionResetError:
        print("[WARN] 客户端连接被重置")

    except Exception:
        print("[ERROR] 服务端处理客户端时发生异常：")
        traceback.print_exc()

    finally:
        conn.close()
        print(f"[INFO] 客户端已断开: {addr}")


def main():
    """
    服务端主函数。
    """

    # 启动前先确保 Excel 文件存在
    init_excel()

    # 创建 TCP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 避免刚关闭程序后端口暂时占用导致无法重启
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # 绑定 IP 和端口
    server.bind((SERVER_HOST, SERVER_PORT))

    # 开始监听
    server.listen(5)

    print("=" * 60)
    print("[INFO] PC socket 服务端启动成功")
    print(f"[INFO] 监听地址: {SERVER_HOST}:{SERVER_PORT}")
    print("[INFO] 等待客户端连接...")
    print("[INFO] 提醒：程序运行时不要打开 sleep_monitor_data.xlsx")
    print("=" * 60)

    try:
        while True:
            conn, addr = server.accept()
            handle_client(conn, addr)

    except KeyboardInterrupt:
        print("\n[INFO] 用户停止服务端")

    finally:
        server.close()
        print("[INFO] 服务端已关闭")


if __name__ == "__main__":
    main()