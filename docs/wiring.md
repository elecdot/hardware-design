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

Do not hot-plug the module while PYNQ-Z1 is powered.
