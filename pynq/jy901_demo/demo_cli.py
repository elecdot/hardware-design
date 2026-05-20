from __future__ import division
from __future__ import print_function

import argparse
import json
import sys
import time

from jy901_driver import (
    DEFAULT_ADDR_RANGE,
    DEFAULT_BASE_ADDR,
    DEFAULT_BITFILE,
    DEFAULT_I2C_CLKDIV,
    EXPECTED_VERSION,
    JY901DemoDriver,
    download_bitstream,
    scale_raw,
    status_label,
)


def parse_int(value):
    return int(value, 0)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Minimal JY901 AXI I2C demo for PYNQ-Z1 Python 2.7.",
    )
    parser.add_argument("--bitfile", default=DEFAULT_BITFILE, help="bitstream path")
    parser.add_argument("--base-addr", type=parse_int, default=DEFAULT_BASE_ADDR, help="AXI base address")
    parser.add_argument("--addr-range", type=parse_int, default=DEFAULT_ADDR_RANGE, help="AXI address range")
    parser.add_argument("--i2c-clkdiv", type=parse_int, default=DEFAULT_I2C_CLKDIV, help="I2C clock divider")
    parser.add_argument("--duration", type=float, default=20.0, help="demo duration in seconds")
    parser.add_argument("--interval", type=float, default=0.5, help="poll interval in seconds")
    parser.add_argument("--jsonl", default=None, help="optional JSONL output path")
    parser.add_argument("--oneshot-timeout", type=float, default=1.0, help="oneshot timeout in seconds")
    return parser


def motion_hint(previous_scaled, scaled):
    if previous_scaled is None:
        return "start", 0.0

    d_roll = abs(scaled["roll_deg"] - previous_scaled["roll_deg"])
    d_pitch = abs(scaled["pitch_deg"] - previous_scaled["pitch_deg"])
    score = d_roll + d_pitch

    if score >= 35.0:
        return "turn", score
    if score >= 8.0:
        return "move", score
    return "still", score


def write_jsonl(handle, record):
    if handle is not None:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()


def print_header():
    print(
        "%7s %8s %8s %7s %7s %7s %8s %8s %8s %8s %8s"
        % ("time", "cnt", "status", "ax_g", "ay_g", "az_g", "roll", "pitch", "yaw", "temp_c", "motion")
    )
    print("-" * 96)


def print_row(elapsed, raw, scaled, status, motion):
    print(
        "%7.2f %8d %8s %7.3f %7.3f %7.3f %8.2f %8.2f %8.2f %8.2f %8s"
        % (
            elapsed,
            raw["sample_cnt"],
            status_label(status),
            scaled["ax_g"],
            scaled["ay_g"],
            scaled["az_g"],
            scaled["roll_deg"],
            scaled["pitch_deg"],
            scaled["yaw_deg"],
            scaled["temp_c"],
            motion,
        )
    )


def make_record(elapsed, raw, scaled, status, error_code, motion, motion_score):
    return {
        "elapsed_s": elapsed,
        "sample_cnt": raw["sample_cnt"],
        "status": status,
        "error_code": error_code,
        "raw": raw,
        "scaled": scaled,
        "demo": {
            "motion": motion,
            "motion_score": motion_score,
        },
    }


def run(args):
    jsonl = None
    driver = None
    try:
        print("JY901 AXI demo")
        print("bitfile      : %s" % args.bitfile)
        print("base address : 0x%08X" % args.base_addr)
        print("addr range   : 0x%X" % args.addr_range)
        print("i2c clkdiv   : %d" % args.i2c_clkdiv)
        print("runtime note : target board Python 2.7.10, Linux 4.6.0-xilinx")

        if args.jsonl:
            jsonl = open(args.jsonl, "a")
            print("jsonl output : %s" % args.jsonl)

        print("downloading bitstream...")
        download_bitstream(args.bitfile)
        print("bitstream downloaded")

        driver = JY901DemoDriver(args.base_addr, args.addr_range)
        version = driver.check_version()
        print("VERSION      : 0x%08X PASS" % version)

        driver.configure(i2c_clkdiv=args.i2c_clkdiv)
        initial_status = driver.read_status()
        print("initial STATUS: 0x%08X scl=%d sda=%d" % (
            initial_status["raw"],
            initial_status["scl_in"],
            initial_status["sda_in"],
        ))

        first = driver.oneshot(timeout=args.oneshot_timeout)
        if first["after_count"] <= first["before_count"]:
            raise RuntimeError(
                "initial SAMPLE_CNT did not increment: %d -> %d"
                % (first["before_count"], first["after_count"])
            )
        print("initial oneshot: PASS sample_cnt %d -> %d" % (first["before_count"], first["after_count"]))

        print_header()
        start_time = time.time()
        previous_scaled = None
        previous_count = first["after_count"]

        while True:
            now = time.time()
            elapsed = now - start_time
            if elapsed > args.duration:
                break

            shot = driver.oneshot(timeout=args.oneshot_timeout)
            if shot["after_count"] <= previous_count:
                raise RuntimeError(
                    "SAMPLE_CNT did not increment: %d -> %d"
                    % (previous_count, shot["after_count"])
                )

            status = driver.read_status()
            if status["ack_error"] or status["timeout"]:
                raise RuntimeError(
                    "I2C status error status=0x%08X error_code=0x%02X"
                    % (status["raw"], driver.error_code())
                )

            raw = driver.read_raw()
            scaled = scale_raw(raw)
            motion, score = motion_hint(previous_scaled, scaled)
            print_row(elapsed, raw, scaled, status, motion)
            write_jsonl(jsonl, make_record(elapsed, raw, scaled, status, driver.error_code(), motion, score))

            previous_scaled = scaled
            previous_count = shot["after_count"]
            time.sleep(args.interval)

        print("demo complete: PASS, final sample_cnt=%d" % previous_count)
        return 0
    finally:
        if driver is not None:
            driver.stop()
        if jsonl is not None:
            jsonl.close()


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except KeyboardInterrupt:
        sys.stderr.write("interrupted\n")
        return 130
    except Exception as exc:
        sys.stderr.write("ERROR: %s\n" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
