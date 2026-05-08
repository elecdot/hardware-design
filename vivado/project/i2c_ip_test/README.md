# i2c_ip_test

Vivado project used to exercise the JY901/MPU9250 I2C custom IP.

## Entry Points

| Path | Purpose |
|---|---|
| `i2c_ip_test.xpr` | Vivado project file. |
| `../../../rtl/i2c_mpu9250/` | RTL source for the IP under test. |
| `../../../sim/tb_i2c_mpu9250/` | Behavioral testbench source. |
| `../../constraints/i2c_jy901_pynq_z1.xdc` | PYNQ-Z1 I2C pin constraints. |

Open the `.xpr` in Vivado when a GUI project is needed. Prefer documenting reproducible build steps in `../README.md` or future Tcl scripts.
