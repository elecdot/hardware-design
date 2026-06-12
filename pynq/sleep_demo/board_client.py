"""PYNQ-side socket client for the sleep monitor protocol."""

import argparse
import json
import socket
import time

from board_orchestrator import SleepMonitorBoard


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9000
DEFAULT_INTERVAL_S = 1.0
DEFAULT_RESPONSE_TIMEOUT_S = 2.0
DEFAULT_RECONNECT_INTERVAL_S = 3.0
MESSAGE_END = "\n"


class BoardProtocolError(RuntimeError):
    pass


class MessageBuffer(object):
    def __init__(self):
        self._buffer = ""

    def feed(self, chunk):
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8")
        self._buffer += chunk
        messages = []
        while MESSAGE_END in self._buffer:
            line, self._buffer = self._buffer.split(MESSAGE_END, 1)
            line = line.strip()
            if line:
                messages.append(decode_message(line))
        return messages


def encode_message(message):
    return json.dumps(message, ensure_ascii=False, separators=(",", ":")) + MESSAGE_END


def decode_message(line):
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    try:
        message = json.loads(line.strip())
    except ValueError as exc:
        raise BoardProtocolError("invalid JSON response") from exc
    if not isinstance(message, dict):
        raise BoardProtocolError("response must be a JSON object")
    if "type" not in message:
        raise BoardProtocolError("response missing type")
    return message


def send_message(sock, message):
    sock.sendall(encode_message(message).encode("utf-8"))


def recv_messages(sock, buffer, count, timeout_s):
    previous_timeout = sock.gettimeout()
    sock.settimeout(float(timeout_s))
    messages = []
    try:
        while len(messages) < count:
            chunk = sock.recv(4096)
            if not chunk:
                raise BoardProtocolError("PC closed the socket")
            messages.extend(buffer.feed(chunk))
    finally:
        sock.settimeout(previous_timeout)
    return messages[:count]


def run_client_session(
    board,
    sock,
    samples=0,
    interval_s=DEFAULT_INTERVAL_S,
    response_timeout_s=DEFAULT_RESPONSE_TIMEOUT_S,
    verbose=True,
):
    """Run one connected PYNQ-to-PC session."""
    stats = {
        "sensor_data": 0,
        "sleep_result": 0,
        "control_command": 0,
        "control_status": 0,
    }
    buffer = MessageBuffer()

    while int(samples) == 0 or stats["sensor_data"] < int(samples):
        sample = board.read_sample()
        send_message(sock, sample)
        stats["sensor_data"] += 1
        if verbose:
            print("[SEND sensor_data] sample_id={0}".format(sample.get("sample_id")))

        responses = recv_messages(sock, buffer, 2, response_timeout_s)
        sleep_result, control_command = _validate_response_pair(
            sample.get("sample_id"),
            responses,
        )
        stats["sleep_result"] += 1
        stats["control_command"] += 1
        if verbose:
            print(
                "[RECV sleep_result] sample_id={0} state={1} valid={2}".format(
                    sleep_result.get("sample_id"),
                    sleep_result.get("sleep_state_code"),
                    sleep_result.get("state_valid"),
                )
            )
            print(
                "[RECV control_command] sample_id={0} targets={1} reason={2}".format(
                    control_command.get("sample_id"),
                    control_command.get("targets"),
                    control_command.get("reason"),
                )
            )

        status = board.apply_control_command(control_command)
        board.update_display(sample, status)
        send_message(sock, status)
        stats["control_status"] += 1
        if verbose:
            print(
                "[SEND control_status] sample_id={0} code={1} remark={2}".format(
                    status.get("sample_id"),
                    status.get("status_code"),
                    status.get("remark"),
                )
            )

        if interval_s:
            time.sleep(float(interval_s))

    return stats


def run_board_client(
    board,
    host,
    port,
    samples=0,
    interval_s=DEFAULT_INTERVAL_S,
    response_timeout_s=DEFAULT_RESPONSE_TIMEOUT_S,
    reconnect_interval_s=DEFAULT_RECONNECT_INTERVAL_S,
    verbose=True,
):
    """Connect to PC and run a first-version single-client loop."""
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if verbose:
                print("[INFO] connecting to {0}:{1}".format(host, port))
            sock.connect((host, int(port)))
            stats = run_client_session(
                board,
                sock,
                samples=samples,
                interval_s=interval_s,
                response_timeout_s=response_timeout_s,
                verbose=verbose,
            )
            return stats
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            if int(samples) > 0:
                raise
            if verbose:
                print("[WARN] PC connection failed: {0}".format(exc))
                print("[INFO] retrying in {0:.1f}s".format(float(reconnect_interval_s)))
            time.sleep(float(reconnect_interval_s))
        finally:
            sock.close()


def build_board(args):
    if args.dry_run:
        return SleepMonitorBoard()

    from integrated_demo import bind_drivers, parse_args

    demo_args = parse_args(_integrated_demo_argv(args))
    drivers = bind_drivers(demo_args)
    return SleepMonitorBoard(
        drivers=drivers,
        sensor_timeout_s=args.sensor_timeout,
        dht11_period_s=args.dht11_period,
        turn_threshold_deg=args.turn_threshold_deg,
        ir_min_interval_s=args.ir_min_interval,
        ir_repeat_cooldown_s=args.ir_repeat_cooldown,
        ir_timeout_s=args.ir_timeout,
    )


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Run the PYNQ board socket client.")
    parser.add_argument("--host", required=True, help="PC server IPv4 address.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--samples", type=int, default=0, help="0 means run until Ctrl-C.")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_S)
    parser.add_argument("--response-timeout", type=float, default=DEFAULT_RESPONSE_TIMEOUT_S)
    parser.add_argument("--reconnect-interval", type=float, default=DEFAULT_RECONNECT_INTERVAL_S)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bitfile", default=None)
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--no-display", action="store_true")
    parser.add_argument("--skip-artifact-check", action="store_true")
    parser.add_argument("--metadata-source", choices=("auto", "overlay", "static"), default="auto")
    parser.add_argument("--sensor-timeout", type=float, default=0.5)
    parser.add_argument("--dht11-period", type=float, default=2.0)
    parser.add_argument("--spo2-frame-len", type=int, choices=(5, 7), default=5)
    parser.add_argument("--tft-clkdiv", type=int, default=50)
    parser.add_argument("--jy901-clkdiv", type=int, default=500)
    parser.add_argument("--humidity-low", type=int, default=45)
    parser.add_argument("--humidity-hysteresis", type=int, default=5)
    parser.add_argument("--dry-alert-s", type=int, default=10)
    parser.add_argument("--turn-threshold-deg", type=float, default=35.0)
    parser.add_argument("--ir-min-interval", type=float, default=5.0)
    parser.add_argument("--ir-repeat-cooldown", type=float, default=60.0)
    parser.add_argument("--ir-timeout", type=float, default=15.0)
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    board = build_board(args)
    stats = run_board_client(
        board,
        args.host,
        args.port,
        samples=args.samples,
        interval_s=args.interval,
        response_timeout_s=args.response_timeout,
        reconnect_interval_s=args.reconnect_interval,
        verbose=True,
    )
    print("[INFO] board client stopped: {0}".format(stats))


def _validate_response_pair(sample_id, messages):
    if len(messages) != 2:
        raise BoardProtocolError("expected sleep_result and control_command")
    sleep_result, control_command = messages
    if sleep_result.get("type") != "sleep_result":
        raise BoardProtocolError("first response must be sleep_result")
    if control_command.get("type") != "control_command":
        raise BoardProtocolError("second response must be control_command")
    if int(sleep_result.get("sample_id", -1)) != int(sample_id):
        raise BoardProtocolError("sleep_result sample_id mismatch")
    if int(control_command.get("sample_id", -1)) != int(sample_id):
        raise BoardProtocolError("control_command sample_id mismatch")
    return sleep_result, control_command


def _integrated_demo_argv(args):
    argv = []
    if args.bitfile:
        argv.extend(["--bitfile", args.bitfile])
    argv.extend(["--samples", "0"])
    argv.extend(["--interval", str(args.interval)])
    argv.extend(["--sensor-timeout", str(args.sensor_timeout)])
    argv.extend(["--dht11-period", str(args.dht11_period)])
    argv.extend(["--metadata-source", args.metadata_source])
    argv.extend(["--spo2-frame-len", str(args.spo2_frame_len)])
    argv.extend(["--tft-clkdiv", str(args.tft_clkdiv)])
    argv.extend(["--jy901-clkdiv", str(args.jy901_clkdiv)])
    argv.extend(["--humidity-low", str(args.humidity_low)])
    argv.extend(["--humidity-hysteresis", str(args.humidity_hysteresis)])
    argv.extend(["--dry-alert-s", str(args.dry_alert_s)])
    argv.extend(["--turn-threshold-deg", str(args.turn_threshold_deg)])
    if args.allow_missing:
        argv.append("--allow-missing")
    if args.no_download:
        argv.append("--no-download")
    if args.no_display:
        argv.append("--no-display")
    if args.skip_artifact_check:
        argv.append("--skip-artifact-check")
    return argv


if __name__ == "__main__":
    main()
