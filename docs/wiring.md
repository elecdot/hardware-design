# Wiring

Physical module wiring and voltage notes.

## Planned Integrated Overlay Pin Allocation

These assignments are the target for the final integrated overlay. They are
not board-verified until the matching integrated XDC, `.bit`, `.hwh`, and PYNQ
driver smoke test evidence exist.

| Module | Signal | PYNQ-Z1 pin/header | Notes |
|---|---|---|---|
| TFT LCD | `lcd_scl` | PMODA `Y18` | PMODA is reserved for TFT LCD in the integrated build. |
| TFT LCD | `lcd_sda` | PMODA `Y19` | SPI MOSI, write-only display path. |
| TFT LCD | `lcd_res` | PMODA `Y16` | Active-low display reset. |
| TFT LCD | `lcd_dc` | PMODA `Y17` | `0` command, `1` data. |
| TFT LCD | `lcd_blk` | PMODA `U18` | Backlight enable. |
| JY901 | `i2c_scl` | Arduino SCL `P16` | Use 3.3 V pullups; do not use the PMODA JY901 XDC in the integrated build. |
| JY901 | `i2c_sda` | Arduino SDA `P15` | Open-drain I2C data. |
| UART SpO2 | `uart_txd` | PMODB pin 1, `W14` | Course teaching guide lists `PMODB_1/JB1_P/W14`; board test confirmed the external module's RX/TX labels must be treated as crossed. |
| UART SpO2 | `uart_rxd` | PMODB pin 2, `Y14` | Course teaching guide lists `PMODB_2/JB1_N/Y14`; if BPM/SpO2 stay `NA`, swap the two UART signal wires before changing RTL. |
| DHT11 | `dht11_0` | Arduino IO11 `R17` | Bidirectional one-wire DATA with pullup. |
| Humidifier | `humidifier_leds[3:0]` | Board LEDs `R14/P14/N16/M14` | LED output simulates an actuator; do not drive loads directly. |
| Gree IR AC TX | `ir_pwm` | Arduino `ck_io[0]`, `T14` | TX-only first integration. Use an IR transmitter module or driver circuit; do not drive a bare IR LED directly from PL. |

All PL-connected signals must be 3.3 V logic. If a module is powered from 5 V,
verify that its FPGA-facing signal pins are still 3.3 V TTL or add level
shifting.

UART links must share ground. For the SpO2 module used in the integrated board
test, the working orientation was confirmed only after reversing the module-side
RX/TX wiring relative to its labels.

IR transmitter modules must share ground with the PYNQ-Z1. If a transmitter is
powered from an external supply, verify that its `IN/SIG` pin accepts 3.3 V
logic before connecting `ir_pwm`.

## Gree IR AC Transmitter

First integrated target:

| IR transmitter | PYNQ-Z1 | Notes |
|---|---|---|
| VCC | 3V3 or external module supply | Confirm module input remains 3.3 V-compatible if powered externally. |
| GND | GND | Shared ground is required. |
| IN / SIG | Arduino `ck_io[0]`, `T14` | Driven by `ir_pwm` from `gree_ir_axi_v1_0`. |

The handoff package's standalone test confirmed the lab Gree AC responds to the
seven Gree YB0F2 preset commands. Integrated overlay response is still pending.

## JY901 I2C Module

Use 3.3 V wiring only with PYNQ-Z1 PL I/O.

### Current AXI/PYNQ Overlay And PL Debug Wiring

The current Vivado overlay/debug projects use PMODA pins:

| JY901 | PYNQ-Z1 | Notes |
|---|---|---|
| VCC | 3V3 | Do not power this I2C connection from 5 V when SCL/SDA connect to PL pins. |
| GND | GND | Shared ground is required. |
| SCL | PMODA `Y17` | Add or confirm 4.7 k pullup to 3.3 V. |
| SDA | PMODA `Y16` | Add or confirm 4.7 k pullup to 3.3 V. |

Constraint files:

- AXI/PYNQ overlay: [../vivado/constraints/axi_i2c_jy901_package.xdc](../vivado/constraints/axi_i2c_jy901_package.xdc).
- PL-only debug top: [../vivado/constraints/jy901_debug.xdc](../vivado/constraints/jy901_debug.xdc).

### Older Arduino Header Mapping

[../vivado/constraints/i2c_jy901_pynq_z1.xdc](../vivado/constraints/i2c_jy901_pynq_z1.xdc)
maps `i2c_scl` to Arduino SCL `P16` and `i2c_sda` to Arduino SDA `P15`. Use it
only for a build that intentionally targets the Arduino header, not together
with the PMODA mapping above.

Do not hot-plug the module while PYNQ-Z1 is powered.
