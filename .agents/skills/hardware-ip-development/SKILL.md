---
name: hardware-ip-development
description: Use when working on synthesizable RTL, custom AXI-Lite IP, protocol cores, register maps, hardware-facing Verilog/SystemVerilog changes, or simulation testbenches in this PYNQ-Z1 hardware design repository.
---

# Hardware IP Development

Use this skill for RTL and custom PL IP work.

## First Reads

Read these before editing:

- `README.md` for project status and hardware assumptions.
- `AGENTS.md` for testing, safety, and Definition of Done.
- Relevant directory README files under `rtl/`, `sim/`, `docs/`, and `vivado/`.
- `docs/register_map.md` before changing AXI-visible registers.
- `docs/wiring.md` before changing external signals.
- `docs/test_plan.md` before claiming behavior works.

## Workflow

1. Identify the target IP and whether the change is protocol core, AXI wrapper, register map, testbench, or documentation.
2. Read the module datasheet or existing design note before encoding protocol timing.
3. Put synthesizable RTL in `rtl/<ip_name>/`.
4. Put behavioral simulation in `sim/tb_<ip_name>/`.
5. Keep protocol core logic separate from AXI wrapper logic when practical.
6. Define 32-bit AXI-Lite registers with explicit reset values and access modes.
7. Update `docs/register_map.md` when offsets, bits, reset values, or semantics change.
8. Update `docs/wiring.md` and `vivado/constraints/` docs when external ports or pins change.
9. Run or document a focused simulation before packaging into Vivado.
10. Never claim board verification without simulation output, board evidence, or user-confirmed measurement.

## RTL Rules

- Use synthesizable Verilog/SystemVerilog only unless the Vivado toolchain support is confirmed.
- Use named parameters for clock frequency, baud rate, timing thresholds, and counter widths.
- Synchronize asynchronous external inputs with at least two flip-flops before edge detection.
- Use explicit reset behavior.
- Prefer finite-state machines for timing-sensitive protocols such as DHT11, I2C, SPI, UART, and IR.
- Do not hard-code board-specific pins inside RTL; keep pin assignments in XDC.
- Do not drive open-drain buses high from RTL; release them and rely on valid pullups.

## Test Expectations

- Test protocol cores independently before AXI packaging.
- Make testbenches emit clear PASS/FAIL output.
- Include normal and at least one relevant error path when the protocol has observable failures.
- Keep generated simulation artifacts out of source unless intentionally preserved as evidence.
