"""Minimal TCP loop for the new PC/PYNQ protocol."""

import argparse
import socket
import traceback

from protocol import (
    CONTROL_STATUS,
    SENSOR_DATA,
    MessageBuffer,
    ProtocolError,
    encode_message,
)
from protocol_config import SERVER_HOST, SERVER_PORT
from service import SleepMonitorPcService
from storage import JsonlRecordStorage, default_record_dir


def send_message(conn, message):
    conn.sendall(encode_message(message).encode("utf-8"))


def handle_client(conn, addr, service=None, recv_size=4096):
    """Handle one PYNQ client connection.

    Returns a small stats dictionary for tests and log callers.
    """
    active_service = service or SleepMonitorPcService()
    stats = {
        "received": 0,
        "sensor_data": 0,
        "control_status": 0,
        "sent": 0,
        "errors": 0,
    }
    buffer = MessageBuffer()
    active_service.set_active_client(addr)

    try:
        while True:
            chunk = conn.recv(recv_size)
            if not chunk:
                break
            for message in buffer.feed(chunk):
                stats["received"] += 1
                message_type = message.get("type")

                if message_type == SENSOR_DATA:
                    response = active_service.process_sensor_data(message)
                    send_message(conn, response["sleep_result"])
                    send_message(conn, response["control_command"])
                    stats["sensor_data"] += 1
                    stats["sent"] += 2
                elif message_type == CONTROL_STATUS:
                    active_service.process_control_status(message)
                    stats["control_status"] += 1
                else:
                    stats["errors"] += 1
                    raise ProtocolError(
                        "unexpected client message type: {0}".format(message_type)
                    )
    finally:
        active_service.clear_active_client(addr)
        conn.close()
    return stats


def serve_forever(host=SERVER_HOST, port=SERVER_PORT, service=None, backlog=1):
    """Run the sequential first-version TCP server."""
    active_service = service or SleepMonitorPcService()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, int(port)))
    server.listen(int(backlog))

    print("[INFO] PC socket service listening on {0}:{1}".format(host, port))
    try:
        while True:
            conn, addr = server.accept()
            print("[INFO] client connected: {0}".format(addr))
            try:
                stats = handle_client(conn, addr, active_service)
                print("[INFO] client disconnected: {0} stats={1}".format(addr, stats))
            except KeyboardInterrupt:
                raise
            except Exception:
                print("[ERROR] client handling failed:")
                traceback.print_exc()
    finally:
        server.close()


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run the minimal PC/PYNQ newline-JSON socket service."
    )
    parser.add_argument("--host", default=SERVER_HOST)
    parser.add_argument("--port", type=int, default=SERVER_PORT)
    parser.add_argument("--record-dir", default=default_record_dir())
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    storage = JsonlRecordStorage(args.record_dir)
    service = SleepMonitorPcService(storage=storage)
    serve_forever(args.host, args.port, service=service)


if __name__ == "__main__":
    main()
