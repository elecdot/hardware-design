# constraints

Board-level XDC constraints for external PL ports live here.

## Index

| File | Purpose |
|---|---|
| [i2c_jy901_pynq_z1.xdc](i2c_jy901_pynq_z1.xdc) | Maps JY901 I2C `i2c_scl` to PYNQ-Z1 Arduino SCL `P16` and `i2c_sda` to Arduino SDA `P15`, both `LVCMOS33`. |

Keep pin assignments out of RTL. Confirm every external signal is compatible with 3.3 V PYNQ-Z1 I/O before adding constraints.
