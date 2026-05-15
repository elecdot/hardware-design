#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""Generate GTKWave save files for the I2C/JY901 simulations."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_SIM_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BUILD_DIR = REPO_SIM_DIR / "build"
DEFAULT_OUT_DIR = DEFAULT_BUILD_DIR / "waves"
DEFAULT_VCD_DIR = DEFAULT_BUILD_DIR / "vcd"


@dataclass(frozen=True)
class Trace:
    path: str
    flags: str = "@28"


@dataclass(frozen=True)
class Group:
    name: str
    traces: tuple[Trace, ...]


@dataclass(frozen=True)
class Bench:
    key: str
    top: str
    vcd: str
    groups: tuple[Group, ...]
    views: dict[str, tuple[str, ...]]


def t(path: str, flags: str = "@28") -> Trace:
    return Trace(path=path, flags=flags)


SAMPLER_GROUPS = (
    Group(
        "tb_control",
        (
            t("tb_jy901_sampler.clk"),
            t("tb_jy901_sampler.resetn"),
            t("tb_jy901_sampler.enable"),
            t("tb_jy901_sampler.oneshot_start"),
            t("tb_jy901_sampler.clear_done"),
            t("tb_jy901_sampler.clear_error"),
            t("tb_jy901_sampler.dev_addr[6:0]"),
            t("tb_jy901_sampler.start_reg[7:0]"),
            t("tb_jy901_sampler.word_count[7:0]"),
            t("tb_jy901_sampler.i2c_clkdiv[15:0]"),
        ),
    ),
    Group(
        "i2c_bus",
        (
            t("tb_jy901_sampler.i2c_scl"),
            t("tb_jy901_sampler.i2c_sda"),
            t("tb_jy901_sampler.scl_in"),
            t("tb_jy901_sampler.sda_in"),
            t("tb_jy901_sampler.scl_drive_low"),
            t("tb_jy901_sampler.sda_drive_low"),
            t("tb_jy901_sampler.slave.sda_drive_low"),
        ),
    ),
    Group(
        "sampler_fsm",
        (
            t("tb_jy901_sampler.dut.state[1:0]"),
            t("tb_jy901_sampler.dut.core_start"),
            t("tb_jy901_sampler.dut.core_cfg_write"),
            t("tb_jy901_sampler.dut.pending_cfg"),
            t("tb_jy901_sampler.dut.core_done"),
            t("tb_jy901_sampler.dut.done"),
            t("tb_jy901_sampler.dut.data_valid"),
            t("tb_jy901_sampler.dut.ack_error"),
            t("tb_jy901_sampler.dut.timeout"),
            t("tb_jy901_sampler.dut.error_code[7:0]"),
            t("tb_jy901_sampler.dut.sample_cnt[31:0]"),
        ),
    ),
    Group(
        "i2c_core",
        (
            t("tb_jy901_sampler.dut.u_i2c_master_core.state[4:0]"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.step[2:0]"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.tick"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.busy"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.done"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.tx_byte[7:0]"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.shifter[7:0]"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.bit_cnt[3:0]"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.byte_cnt[4:0]"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.rx_valid"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.rx_index[4:0]"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.rx_data[7:0]"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.ack_error"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.timeout"),
            t("tb_jy901_sampler.dut.u_i2c_master_core.error_code[7:0]"),
        ),
    ),
    Group(
        "sample_data",
        (
            t("tb_jy901_sampler.data0[15:0]"),
            t("tb_jy901_sampler.data1[15:0]"),
            t("tb_jy901_sampler.data2[15:0]"),
            t("tb_jy901_sampler.data12[15:0]"),
            t("tb_jy901_sampler.sample_cnt[31:0]"),
        ),
    ),
    Group(
        "slave_model",
        (
            t("tb_jy901_sampler.slave.reg_addr[7:0]"),
            t("tb_jy901_sampler.slave.byte_value[7:0]"),
            t("tb_jy901_sampler.slave.master_ack"),
            t("tb_jy901_sampler.slave.nack_reg"),
            t("tb_jy901_sampler.slave.nack_addr_read"),
            t("tb_jy901_sampler.slave.sda_drive_low"),
        ),
    ),
)


AXI_GROUPS = (
    Group(
        "tb_control",
        (
            t("tb_axi_i2c_jy901_top.clk"),
            t("tb_axi_i2c_jy901_top.resetn"),
            t("tb_axi_i2c_jy901_top.status[31:0]"),
            t("tb_axi_i2c_jy901_top.rd[31:0]"),
            t("tb_axi_i2c_jy901_top.sample_cnt[31:0]"),
        ),
    ),
    Group(
        "axi_lite_bus",
        (
            t("tb_axi_i2c_jy901_top.s_axi_awaddr[6:0]"),
            t("tb_axi_i2c_jy901_top.s_axi_awvalid"),
            t("tb_axi_i2c_jy901_top.s_axi_awready"),
            t("tb_axi_i2c_jy901_top.s_axi_wdata[31:0]"),
            t("tb_axi_i2c_jy901_top.s_axi_wstrb[3:0]"),
            t("tb_axi_i2c_jy901_top.s_axi_wvalid"),
            t("tb_axi_i2c_jy901_top.s_axi_wready"),
            t("tb_axi_i2c_jy901_top.s_axi_bvalid"),
            t("tb_axi_i2c_jy901_top.s_axi_bready"),
            t("tb_axi_i2c_jy901_top.s_axi_araddr[6:0]"),
            t("tb_axi_i2c_jy901_top.s_axi_arvalid"),
            t("tb_axi_i2c_jy901_top.s_axi_arready"),
            t("tb_axi_i2c_jy901_top.s_axi_rdata[31:0]"),
            t("tb_axi_i2c_jy901_top.s_axi_rvalid"),
            t("tb_axi_i2c_jy901_top.s_axi_rready"),
        ),
    ),
    Group(
        "axi_registers",
        (
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.write_fire"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.read_fire"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.wr_addr[4:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.rd_addr[4:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.read_mux[31:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.enable"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.oneshot_start_pulse"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.auto_mode"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.clear_done_pulse"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.clear_error_pulse"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.cfg_write_start_pulse"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.soft_reset_pulse"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.dev_addr[6:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.start_reg[7:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.word_count[7:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_axi_lite_regs.i2c_clkdiv[15:0]"),
        ),
    ),
    Group(
        "i2c_bus",
        (
            t("tb_axi_i2c_jy901_top.i2c_scl"),
            t("tb_axi_i2c_jy901_top.i2c_sda"),
            t("tb_axi_i2c_jy901_top.dut.scl_in"),
            t("tb_axi_i2c_jy901_top.dut.sda_in"),
            t("tb_axi_i2c_jy901_top.dut.scl_drive_low"),
            t("tb_axi_i2c_jy901_top.dut.sda_drive_low"),
            t("tb_axi_i2c_jy901_top.slave.sda_drive_low"),
        ),
    ),
    Group(
        "sampler_fsm",
        (
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.state[1:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.core_start"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.core_cfg_write"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.pending_cfg"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.core_done"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.done"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.data_valid"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.ack_error"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.timeout"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.error_code[7:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.sample_cnt[31:0]"),
        ),
    ),
    Group(
        "i2c_core",
        (
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.state[4:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.step[2:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.tick"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.busy"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.done"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.tx_byte[7:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.shifter[7:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.bit_cnt[3:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.byte_cnt[4:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.rx_valid"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.rx_index[4:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.rx_data[7:0]"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.ack_error"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.timeout"),
            t("tb_axi_i2c_jy901_top.dut.u_jy901_sampler.u_i2c_master_core.error_code[7:0]"),
        ),
    ),
    Group(
        "sample_data",
        (
            t("tb_axi_i2c_jy901_top.dut.data0[15:0]"),
            t("tb_axi_i2c_jy901_top.dut.data1[15:0]"),
            t("tb_axi_i2c_jy901_top.dut.data2[15:0]"),
            t("tb_axi_i2c_jy901_top.dut.data12[15:0]"),
            t("tb_axi_i2c_jy901_top.dut.sample_cnt[31:0]"),
            t("tb_axi_i2c_jy901_top.ax_raw[31:0]"),
            t("tb_axi_i2c_jy901_top.ay_raw[31:0]"),
            t("tb_axi_i2c_jy901_top.temp_raw[31:0]"),
        ),
    ),
    Group(
        "slave_model",
        (
            t("tb_axi_i2c_jy901_top.slave.expect_cfg_write"),
            t("tb_axi_i2c_jy901_top.slave.cfg_write_seen"),
            t("tb_axi_i2c_jy901_top.slave.cfg_reg_addr[7:0]"),
            t("tb_axi_i2c_jy901_top.slave.cfg_word[15:0]"),
            t("tb_axi_i2c_jy901_top.slave.nack_reg"),
            t("tb_axi_i2c_jy901_top.slave.nack_addr_read"),
            t("tb_axi_i2c_jy901_top.slave.nack_cfg_low"),
            t("tb_axi_i2c_jy901_top.slave.nack_cfg_high"),
            t("tb_axi_i2c_jy901_top.slave.sda_drive_low"),
        ),
    ),
)


TIMEOUT_GROUPS = (
    Group(
        "tb_control",
        (
            t("tb_i2c_master_timeout.clk"),
            t("tb_i2c_master_timeout.resetn"),
            t("tb_i2c_master_timeout.start"),
        ),
    ),
    Group(
        "i2c_bus",
        (
            t("tb_i2c_master_timeout.i2c_scl"),
            t("tb_i2c_master_timeout.i2c_sda"),
            t("tb_i2c_master_timeout.scl_drive_low"),
            t("tb_i2c_master_timeout.sda_drive_low"),
        ),
    ),
    Group(
        "i2c_core",
        (
            t("tb_i2c_master_timeout.dut.state[4:0]"),
            t("tb_i2c_master_timeout.dut.step[2:0]"),
            t("tb_i2c_master_timeout.dut.tick"),
            t("tb_i2c_master_timeout.dut.div_cnt[15:0]"),
            t("tb_i2c_master_timeout.dut.timeout_cnt[31:0]"),
            t("tb_i2c_master_timeout.dut.busy"),
            t("tb_i2c_master_timeout.dut.done"),
            t("tb_i2c_master_timeout.dut.ack_error"),
            t("tb_i2c_master_timeout.dut.timeout"),
            t("tb_i2c_master_timeout.dut.error_code[7:0]"),
        ),
    ),
    Group(
        "result",
        (
            t("tb_i2c_master_timeout.done"),
            t("tb_i2c_master_timeout.timeout"),
            t("tb_i2c_master_timeout.ack_error"),
            t("tb_i2c_master_timeout.error_code[7:0]"),
        ),
    ),
)


BENCHES = {
    "sampler": Bench(
        key="sampler",
        top="tb_jy901_sampler",
        vcd="tb_jy901_sampler.vcd",
        groups=SAMPLER_GROUPS,
        views={
            "quick": ("tb_control", "i2c_bus", "sampler_fsm", "sample_data"),
            "i2c": ("tb_control", "i2c_bus", "i2c_core", "slave_model"),
            "data": ("tb_control", "sampler_fsm", "sample_data"),
            "errors": ("tb_control", "i2c_bus", "sampler_fsm", "i2c_core", "slave_model"),
            "all": tuple(group.name for group in SAMPLER_GROUPS),
        },
    ),
    "axi": Bench(
        key="axi",
        top="tb_axi_i2c_jy901_top",
        vcd="tb_axi_i2c_jy901_top.vcd",
        groups=AXI_GROUPS,
        views={
            "quick": ("tb_control", "axi_lite_bus", "axi_registers", "i2c_bus", "sample_data"),
            "axi": ("tb_control", "axi_lite_bus", "axi_registers"),
            "i2c": ("tb_control", "i2c_bus", "sampler_fsm", "i2c_core", "slave_model"),
            "data": ("tb_control", "axi_registers", "sampler_fsm", "sample_data"),
            "errors": ("tb_control", "axi_registers", "i2c_bus", "sampler_fsm", "i2c_core", "slave_model"),
            "all": tuple(group.name for group in AXI_GROUPS),
        },
    ),
    "timeout": Bench(
        key="timeout",
        top="tb_i2c_master_timeout",
        vcd="tb_i2c_master_timeout.vcd",
        groups=TIMEOUT_GROUPS,
        views={
            "quick": ("tb_control", "i2c_bus", "result"),
            "i2c": ("tb_control", "i2c_bus", "i2c_core", "result"),
            "errors": ("tb_control", "i2c_bus", "i2c_core", "result"),
            "all": tuple(group.name for group in TIMEOUT_GROUPS),
        },
    ),
}


def normalize_vcd_var_name(raw_name: str) -> str:
    raw_name = raw_name.strip()
    match = re.fullmatch(r"(.+?)\s+(\[[^\]]+\])", raw_name)
    if match:
        return f"{match.group(1)}{match.group(2)}"
    return raw_name


def read_vcd_signals(vcd_path: Path) -> set[str]:
    signals: set[str] = set()
    scopes: list[str] = []
    var_re = re.compile(r"^\$var\s+\S+\s+\d+\s+\S+\s+(.+?)\s+\$end$")

    with vcd_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line == "$enddefinitions $end":
                break
            if line.startswith("$scope "):
                parts = line.split()
                if len(parts) >= 4:
                    scopes.append(parts[2])
                continue
            if line.startswith("$upscope"):
                if scopes:
                    scopes.pop()
                continue
            match = var_re.match(line)
            if match and scopes:
                name = normalize_vcd_var_name(match.group(1))
                full_path = ".".join((*scopes, name))
                signals.add(full_path)
                if "[" in name:
                    signals.add(".".join((*scopes, name.split("[", 1)[0])))

    return signals


def selected_groups(bench: Bench, view: str) -> tuple[Group, ...]:
    if view not in bench.views:
        valid = ", ".join(sorted(bench.views))
        raise ValueError(f"unknown view '{view}' for {bench.key}; valid views: {valid}")
    by_name = {group.name: group for group in bench.groups}
    return tuple(by_name[name] for name in bench.views[view])


def relpath_for_savefile(path: Path, start: Path) -> str:
    return os.path.relpath(path.resolve(), start.resolve()).replace(os.sep, "/")


def write_gtkw(
    bench: Bench,
    view: str,
    out_dir: Path,
    vcd_override: Path | None,
    validate: bool,
    strict: bool,
) -> tuple[Path, list[str]]:
    groups = selected_groups(bench, view)
    out_dir = out_dir if out_dir.is_absolute() else REPO_SIM_DIR / out_dir
    if vcd_override is not None and not vcd_override.is_absolute():
        vcd_override = REPO_SIM_DIR / vcd_override
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{bench.key}_{view}.gtkw"
    vcd_path = vcd_override if vcd_override is not None else DEFAULT_VCD_DIR / bench.vcd

    missing: list[str] = []
    known_signals: set[str] | None = None
    if validate and vcd_path.exists():
        known_signals = read_vcd_signals(vcd_path)

    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        dumpfile = relpath_for_savefile(vcd_path, out_path.parent)
        savefile = out_path.name
        handle.write(f'[dumpfile] "{dumpfile}"\n')
        handle.write(f'[savefile] "{savefile}"\n')
        handle.write("[timestart] 0\n")
        handle.write("[size] 1600 900\n")
        handle.write("[pos] -1 -1\n")
        handle.write("[signals_width] 320\n")
        handle.write("[sst_width] 320\n")
        handle.write(f"[treeopen] {bench.top}.\n")

        for group in groups:
            handle.write("@800200\n")
            handle.write(f"-{group.name}\n")
            for trace in group.traces:
                if known_signals is not None and trace.path not in known_signals:
                    missing.append(trace.path)
                    if strict:
                        continue
                handle.write(f"{trace.flags}\n")
                handle.write(f"{trace.path}\n")
            handle.write("@1000200\n")
            handle.write(f"-{group.name}\n")

    if strict and missing:
        out_path.unlink(missing_ok=True)
        raise ValueError(
            f"{out_path.name}: {len(missing)} trace(s) not found in {vcd_path.name}: "
            + ", ".join(missing[:8])
            + (" ..." if len(missing) > 8 else "")
        )

    return out_path, missing


def print_list() -> None:
    print("Benches and views:")
    for bench_key, bench in BENCHES.items():
        print(f"  {bench_key}: {', '.join(bench.views)}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate parameterized GTKWave .gtkw files for sim/tb_i2c_mpu9250."
    )
    parser.add_argument("--bench", choices=(*BENCHES.keys(), "all"), default="sampler")
    parser.add_argument("--view", default="quick", help="View name, or 'all'.")
    parser.add_argument("--all", action="store_true", help="Generate every bench/view combination.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--vcd", type=Path, help="Override VCD path; valid only with one bench/view.")
    parser.add_argument("--no-validate", action="store_true", help="Do not compare traces with an existing VCD.")
    parser.add_argument("--strict", action="store_true", help="Fail if an existing VCD misses any requested trace.")
    parser.add_argument("--list", action="store_true", help="List benches and views.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.list:
        print_list()
        return 0

    if args.vcd and (args.all or args.bench == "all" or args.view == "all"):
        print("--vcd can only be used with one concrete --bench/--view pair", file=sys.stderr)
        return 2

    jobs: list[tuple[Bench, str]] = []
    if args.all or args.bench == "all":
        for bench in BENCHES.values():
            for view in bench.views:
                jobs.append((bench, view))
    else:
        bench = BENCHES[args.bench]
        if args.view == "all":
            jobs.extend((bench, view) for view in bench.views)
        else:
            jobs.append((bench, args.view))

    try:
        for bench, view in jobs:
            out_path, missing = write_gtkw(
                bench=bench,
                view=view,
                out_dir=args.out_dir,
                vcd_override=args.vcd,
                validate=not args.no_validate,
                strict=args.strict,
            )
            message = f"wrote {out_path.resolve().relative_to(REPO_SIM_DIR)}"
            if missing:
                message += f" ({len(missing)} missing trace warning(s))"
            print(message)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
