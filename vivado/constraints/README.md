# constraints

Board-level XDC constraints for external PL ports live here.

## Index

| File | Purpose |
|---|---|
| [i2c_jy901_pynq_z1.xdc](i2c_jy901_pynq_z1.xdc) | Maps JY901 I2C `i2c_scl` to PYNQ-Z1 Arduino SCL `P16` and `i2c_sda` to Arduino SDA `P15`, both `LVCMOS33`. |
| [jy901_debug.xdc](jy901_debug.xdc) | Constraints for `jy901_hw_debug_top.v`: 125 MHz `clk`, `resetn` on SW0, `led[3:0]`, and JY901 I2C on PMODA `Y17/Y16`, all `LVCMOS33`. |

Use only one I2C pin-mapping XDC for a given top-level build. `jy901_debug.xdc` is intended for the PL-only hardware debug top and includes optional internal weak pullups on SCL/SDA; external 3.3 V pullups are still recommended for real I2C operation.

Keep pin assignments out of RTL. Confirm every external signal is compatible with 3.3 V PYNQ-Z1 I/O before adding constraints.
