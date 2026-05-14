# i2c_ip_test (legacy)

Legacy Vivado project previously used to exercise the JY901/MPU9250 I2C custom
IP.

This project mixes IP packaging, Block Design integration, PL-only debug logic,
debug ILA constraints, and board-level overlay constraints in one `.xpr`. Keep
it as historical reference only. Do not use it as the clean entry point for new
IP packaging or PYNQ overlay bitstream builds. See [LEGACY.md](LEGACY.md) for
the recommended split.

## Entry Points

| Path | Purpose |
|---|---|
| [i2c_ip_test.xpr](i2c_ip_test.xpr) | Legacy Vivado project file; reference only. |
| [LEGACY.md](LEGACY.md) | Rationale for legacy status and recommended future project split. |
| [../../../rtl/i2c_mpu9250/](../../../rtl/i2c_mpu9250/) | RTL source for the IP under test. |
| [../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v](../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v) | Optional PL-only top for direct JY901 hardware debug and ILA probing. |
| [../../../sim/tb_i2c_mpu9250/](../../../sim/tb_i2c_mpu9250/) | Behavioral testbench source. |
| [../../constraints/i2c_jy901_pynq_z1.xdc](../../constraints/i2c_jy901_pynq_z1.xdc) | PYNQ-Z1 I2C pin constraints. |
| [../../constraints/axi_i2c_jy901_package.xdc](../../constraints/axi_i2c_jy901_package.xdc) | Active AXI/PYNQ overlay I2C constraints for PMODA `Y17/Y16`. |
| [../../constraints/jy901_debug.xdc](../../constraints/jy901_debug.xdc) | Full debug-top constraints for `jy901_hw_debug_top.v`, including clock, reset, LEDs, and PMODA I2C. |

Only open [i2c_ip_test.xpr](i2c_ip_test.xpr) when you need to inspect or recover
historical project state. For future work, keep the flows separate: package
[../../../rtl/i2c_mpu9250/axi_i2c_jy901_v1_0.v](../../../rtl/i2c_mpu9250/axi_i2c_jy901_v1_0.v)
into [../../ip_repo/](../../ip_repo/) without board/debug XDC files, build the
PYNQ overlay from a separate Block Design project whose top is the BD wrapper,
and reserve [../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v](../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v)
with [../../constraints/jy901_debug.xdc](../../constraints/jy901_debug.xdc) for
PL-only hardware bring-up.
