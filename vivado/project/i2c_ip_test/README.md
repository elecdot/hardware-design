# i2c_ip_test (legacy)

这是早期用于验证 JY901/MPU9250 I2C 自定义 IP 的 legacy Vivado 工程。

该工程把 IP 打包、Block Design 集成、PL-only 调试逻辑、debug ILA 约束和板级 overlay 约束混在同一个 `.xpr` 中。
仅把它保留为历史参考。不要把它作为新 IP 打包或 PYNQ overlay bitstream 构建的干净入口。
推荐拆分方式见 [LEGACY.md](LEGACY.md)。

## 入口

| 路径 | 用途 |
|---|---|
| [i2c_ip_test.xpr](i2c_ip_test.xpr) | Legacy Vivado 工程文件；仅供参考。 |
| [LEGACY.md](LEGACY.md) | legacy 状态原因和推荐的未来工程拆分。 |
| [../../../rtl/i2c_mpu9250/](../../../rtl/i2c_mpu9250/) | 被测 IP 的 RTL 源码。 |
| [../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v](../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v) | 用于直接 JY901 硬件调试和 ILA 探测的可选 PL-only 顶层。 |
| [../../../sim/tb_i2c_mpu9250/](../../../sim/tb_i2c_mpu9250/) | 行为 testbench 源码。 |
| [../../constraints/i2c_jy901_pynq_z1.xdc](../../constraints/i2c_jy901_pynq_z1.xdc) | PYNQ-Z1 I2C 引脚约束。 |
| [../../constraints/axi_i2c_jy901_package.xdc](../../constraints/axi_i2c_jy901_package.xdc) | 当前 AXI/PYNQ overlay 的 PMODA `Y17/Y16` I2C 约束。 |
| [../../constraints/jy901_debug.xdc](../../constraints/jy901_debug.xdc) | `jy901_hw_debug_top.v` 的完整 debug-top 约束，包括时钟、reset、LED 和 PMODA I2C。 |

仅在需要检查或恢复历史工程状态时打开 [i2c_ip_test.xpr](i2c_ip_test.xpr)。
后续工作应保持流程分离：将 [../../../rtl/i2c_mpu9250/axi_i2c_jy901_v1_0.v](../../../rtl/i2c_mpu9250/axi_i2c_jy901_v1_0.v)
打包到 [../../ip_repo/](../../ip_repo/) 且不包含 board/debug XDC；在单独 Block Design 工程中构建 PYNQ overlay，
顶层为 BD wrapper；将 [../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v](../../../rtl/i2c_mpu9250/jy901_hw_debug_top.v)
和 [../../constraints/jy901_debug.xdc](../../constraints/jy901_debug.xdc) 留给 PL-only 硬件 bring-up。
