# Wiring

Physical module wiring and voltage notes.

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
