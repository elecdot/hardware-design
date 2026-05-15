# Wiring

Physical module wiring and voltage notes.

## JY901 I2C Module

Use 3.3 V wiring only with PYNQ-Z1 PL I/O.

| JY901 | PYNQ-Z1 | Notes |
|---|---|---|
| VCC | 3V3 | Do not power this I2C connection from 5 V when SCL/SDA connect to PL pins. |
| GND | GND | Shared ground is required. |
| SCL | Arduino SCL / `P16` | Add or confirm 4.7 k pullup to 3.3 V. |
| SDA | Arduino SDA / `P15` | Add or confirm 4.7 k pullup to 3.3 V. |

Constraint file: [../vivado/constraints/i2c_jy901_pynq_z1.xdc](../vivado/constraints/i2c_jy901_pynq_z1.xdc).

The PL-only `jy901_hw_debug_top` flow instead uses PMODA pins from
[../vivado/constraints/jy901_debug.xdc](../vivado/constraints/jy901_debug.xdc):
`i2c_scl` on `Y17` and `i2c_sda` on `Y16`. Do not apply both I2C pin-mapping
constraints in the same build.

Do not hot-plug the module while PYNQ-Z1 is powered.
