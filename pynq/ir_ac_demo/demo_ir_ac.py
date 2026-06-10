"""Small CLI for the TX-only Gree IR AC PYNQ driver."""

import argparse
import json

from ir_ac import (
    DEFAULT_STANDALONE_BASE_ADDR,
    DEFAULT_ADDR_RANGE,
    GREE_YB0F2_COMMANDS,
    GreeIrTransmitter,
    parse_int,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Send one Gree IR AC preset command.")
    parser.add_argument("--bitfile", default=None, help="Optional bitfile to download before MMIO access.")
    parser.add_argument("--base-addr", default=hex(DEFAULT_STANDALONE_BASE_ADDR))
    parser.add_argument("--addr-range", default=hex(DEFAULT_ADDR_RANGE))
    parser.add_argument("--command", default="temp_26", choices=sorted(GREE_YB0F2_COMMANDS.keys()))
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--list-commands", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.list_commands:
        print(json.dumps(GREE_YB0F2_COMMANDS, indent=2, sort_keys=True))
        return

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
    print("before:", ir.status())
    ir.send_command(args.command, timeout=args.timeout)
    print("after:", ir.status())


if __name__ == "__main__":
    main()
