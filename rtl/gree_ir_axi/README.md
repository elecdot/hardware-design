# gree_ir_axi

TX-only AXI4-Lite Gree IR air-conditioner transmitter migrated from
`handoff/gree_ir_txrx_hardware_package/`.

## Scope

This first integrated version includes only the transmitter path:

- `gree_ir_core.v`
- `gree_ir_axi_v1_0.v`
- `gree_ir_axi_v1_0_S00_AXI.v`

The handoff package also includes `ir_capture_axi` receiver RTL, but RX remains
a standalone validation tool and is intentionally not migrated into this first
integrated source path.

## Top-Level IP

Top module: `gree_ir_axi_v1_0`

External port:

| Port | Direction | Description |
|---|---|---|
| `ir_pwm` | output | 38 kHz modulated IR transmitter signal. |

AXI interface:

- `s00_axi` AXI4-Lite slave.
- 32-bit data width.
- 5-bit AXI address width.
- Default clock assumption: 100 MHz AXI/system clock.

Parameters:

| Parameter | Default | Description |
|---|---:|---|
| `CORE_CLK_FREQ` | `100_000_000` | Core clock frequency in Hz. |
| `CORE_CLK_1US` | `100` | One-microsecond tick count at 100 MHz. |
| `CORE_CARRIER_HZ` | `38_000` | IR carrier frequency. |

## Commands

The RTL sends 67-bit Gree YB0F2 command presets from ROM. The first integrated
scope exposes only these verified commands:

| Preset | Command |
|---:|---|
| 1 | `power_on` |
| 2 | `power_off` |
| 3 | `temp_24` |
| 4 | `temp_25` |
| 5 | `temp_26` |
| 6 | `temp_27` |
| 7 | `temp_28` |

`CMD_LOW` and `CMD_HIGH` exist for compatibility/status visibility but are not
a general raw-command transmit path in this RTL. Use `PRESET`.

## Register Map

The canonical register map is documented in
[../../docs/register_map.md](../../docs/register_map.md).

## Wiring

The planned integrated overlay output is `ir_pwm` on PYNQ-Z1 Arduino
`ck_io[0]`, package pin `T14`.

Use an IR transmitter module or a transistor/MOSFET driver. Do not drive a bare
IR LED directly from an FPGA pin.

## Verification Status

- Teammate standalone module test confirmed the lab Gree AC responds to the
  handoff command set.
- Local repo simulation for this migrated RTL is planned in `IR-2`.
- Integrated Vivado packaging and board smoke are not complete yet.
