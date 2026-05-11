# i2c_ip_test

Vivado project used to exercise the JY901/MPU9250 I2C custom IP.

## Entry Points

| Path | Purpose |
|---|---|
| [i2c_ip_test.xpr](i2c_ip_test.xpr) | Vivado project file. |
| [../../../rtl/i2c_mpu9250/](../../../rtl/i2c_mpu9250/) | RTL source for the IP under test. |
| [../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v](../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v) | Optional PL-only top for direct JY901 hardware debug and ILA probing. |
| [../../../sim/tb_i2c_mpu9250/](../../../sim/tb_i2c_mpu9250/) | Behavioral testbench source. |
| [../../constraints/i2c_jy901_pynq_z1.xdc](../../constraints/i2c_jy901_pynq_z1.xdc) | PYNQ-Z1 I2C pin constraints. |
| [../../constraints/jy901_debug.xdc](../../constraints/jy901_debug.xdc) | Full debug-top constraints for `jy901_hw_debug_top.v`, including clock, reset, LEDs, and PMODA I2C. |

Open [i2c_ip_test.xpr](i2c_ip_test.xpr) in Vivado when a GUI project is needed. Use [../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v](../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v) with [../../constraints/jy901_debug.xdc](../../constraints/jy901_debug.xdc) for direct PL hardware bring-up; use [../../../rtl/i2c_mpu9250/axi_i2c_jy901_v1_0.v](../../../rtl/i2c_mpu9250/axi_i2c_jy901_v1_0.v) and the appropriate I2C-only constraints for AXI/PYNQ integration. Prefer documenting reproducible build steps in [../README.md](../README.md) or future Tcl scripts.
