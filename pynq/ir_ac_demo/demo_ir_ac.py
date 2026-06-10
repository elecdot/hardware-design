"""Small CLI for the TX-only Gree IR AC PYNQ driver."""

import argparse
import json
import time

from ir_ac import (
    DEFAULT_STANDALONE_BASE_ADDR,
    DEFAULT_ADDR_RANGE,
    GREE_YB0F2_COMMANDS,
    GreeIrTransmitter,
    parse_int,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Send one or more Gree IR AC preset commands.")
    parser.add_argument("--bitfile", default=None, help="Optional bitfile to download before MMIO access.")
    parser.add_argument("--base-addr", default=hex(DEFAULT_STANDALONE_BASE_ADDR))
    parser.add_argument("--addr-range", default=hex(DEFAULT_ADDR_RANGE))
    parser.add_argument("--command", default="temp_26", choices=sorted(GREE_YB0F2_COMMANDS.keys()))
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--repeat",
        type=int,
        default=None,
        help="Number of TX attempts. Defaults to 1 unless --duration is set.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Repeat until this many seconds have elapsed. If --repeat is also set, stop at whichever limit is reached first.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Seconds to wait between repeated TX attempts.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue later attempts after a TX error or timeout.",
    )
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--list-commands", action="store_true")
    return parser.parse_args(argv)


def timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def should_continue(start_time, attempts, repeat, duration):
    if repeat is not None and attempts >= repeat:
        return False
    if duration is not None and attempts > 0:
        if time.time() - start_time >= duration:
            return False
    return True


def sleep_before_next(start_time, duration, interval):
    sleep_s = max(0.0, float(interval))
    if duration is not None:
        remaining = float(duration) - (time.time() - start_time)
        sleep_s = min(sleep_s, max(0.0, remaining))
    if sleep_s > 0:
        time.sleep(sleep_s)


def main(argv=None):
    args = parse_args(argv)
    if args.list_commands:
        print(json.dumps(GREE_YB0F2_COMMANDS, indent=2, sort_keys=True))
        return

    if args.repeat is not None and args.repeat < 1:
        raise ValueError("--repeat must be >= 1")
    if args.duration is not None and args.duration <= 0:
        raise ValueError("--duration must be > 0")
    if args.interval < 0:
        raise ValueError("--interval must be >= 0")

    repeat = args.repeat
    if repeat is None and args.duration is None:
        repeat = 1

    base_addr = parse_int(args.base_addr)
    addr_range = parse_int(args.addr_range)
    if args.bitfile:
        ir = GreeIrTransmitter.from_bitfile(
            args.bitfile,
            base_addr=base_addr,
            addr_range=addr_range,
            download=not args.no_download,
        )
    else:
        ir = GreeIrTransmitter.from_base_addr(base_addr, addr_range)

    print("base_addr: 0x%08X" % base_addr)
    print(
        "smoke: command=%s repeat=%s duration=%s interval=%.3f timeout=%.3f"
        % (args.command, repeat, args.duration, args.interval, args.timeout)
    )

    start_time = time.time()
    attempts = 0
    failures = 0

    while should_continue(start_time, attempts, repeat, args.duration):
        attempts += 1
        print("[%s] attempt %d before: %s" % (timestamp(), attempts, ir.status()))
        try:
            ir.send_command(args.command, timeout=args.timeout)
            print("[%s] attempt %d after: %s" % (timestamp(), attempts, ir.status()))
        except Exception as exc:
            failures += 1
            print("[%s] attempt %d ERROR: %s" % (timestamp(), attempts, exc))
            print("[%s] attempt %d status: %s" % (timestamp(), attempts, ir.status()))
            if not args.continue_on_error:
                raise

        if should_continue(start_time, attempts, repeat, args.duration):
            sleep_before_next(start_time, args.duration, args.interval)

    elapsed = time.time() - start_time
    print(
        "summary: attempts=%d failures=%d elapsed_s=%.3f command=%s"
        % (attempts, failures, elapsed, args.command)
    )


if __name__ == "__main__":
    main()
