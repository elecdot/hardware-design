# project

这里存放用于打包、集成和本地硬件 bring-up 的 Vivado 工程目录。源 RTL 仍保存在
[../../rtl/](../../rtl/) 下；`.srcs` 中的工程副本、生成的 HDL wrapper、run 目录、cache 输出和仿真产物都是 Vivado 状态，
不是权威设计源文件。

## 索引

| 路径 | 用途 |
|---|---|
| [axi_i2c_jy901_package/](axi_i2c_jy901_package/) | `axi_i2c_jy901_v1_0` 的 IP 打包工程；使用 `rtl/i2c_mpu9250/` 中的 RTL，并更新共享 [../ip_repo/](../ip_repo/)。 |
| [axi_i2c_jy901/](axi_i2c_jy901/) | PYNQ/Zynq overlay 工程。在 Block Design `jy901_axi_system` 中例化已打包 AXI I2C IP，顶层为 `jy901_axi_system_wrapper`，并应用 [../constraints/axi_i2c_jy901_package.xdc](../constraints/axi_i2c_jy901_package.xdc)。 |
| [ir_axi_package/](ir_axi_package/) | `gree_ir_axi_v1_0` 的 IP 打包工程；使用 `rtl/gree_ir_axi/` 中的 RTL，并更新 [../ip_repo/ir_ac_axi/](../ip_repo/ir_ac_axi/)。 |
| [jy901_hw_debug/](jy901_hw_debug/) | `jy901_hw_debug_top` 的 PL-only 硬件调试工程；使用 [../constraints/jy901_debug.xdc](../constraints/jy901_debug.xdc)、可选 ILA 和直接 PMODA I2C bring-up。 |
| [i2c_ip_test/](i2c_ip_test/) | legacy 参考工程。它混合了打包、Block Design 和调试流程；新工作不要把它当作干净入口。 |

## 当前 JY901 流程

保持这些流程相互分离：

1. 在 [axi_i2c_jy901_package/](axi_i2c_jy901_package/) 中 **打包 IP**。
   - 主顶层：`axi_i2c_jy901_v1_0`。
   - 输入源码：[../../rtl/i2c_mpu9250/](../../rtl/i2c_mpu9250/)。
   - 输出元数据：[../ip_repo/component.xml](../ip_repo/component.xml) 和 [../ip_repo/](../ip_repo/) 支持文件。
   - 不要把这个工程当作板级 bitstream 工程。

2. 在 [axi_i2c_jy901/](axi_i2c_jy901/) 中 **构建 PYNQ overlay**。
   - Block Design：`jy901_axi_system`。
   - 顶层 wrapper：`jy901_axi_system_wrapper`。
   - 外部 PL 端口应只包含真实 JY901 I2C 引脚：`i2c_scl` 和 `i2c_sda`。
   - 约束文件：[../constraints/axi_i2c_jy901_package.xdc](../constraints/axi_i2c_jy901_package.xdc)，PMODA `Y17/Y16`，`LVCMOS33`。
   - 为 PYNQ 使用同时导出 `.bit` 和 `.hwh`。临时导出放在被 Git 忽略的 [../gen/](../gen/) 中。

3. 在 [jy901_hw_debug/](jy901_hw_debug/) 中 **运行 PL-only 硬件调试**。
   - 顶层：`jy901_hw_debug_top`。
   - 约束文件：[../constraints/jy901_debug.xdc](../constraints/jy901_debug.xdc)。
   - 在依赖 AXI/PYNQ 软件之前，用它验证传感器接线、pullup、ACK/NACK 和 ILA bring-up。

## 说明

- 使用自定义 IP 的工程应把 `ip_repo_paths` 设为共享 [../ip_repo/](../ip_repo/) 目录，并刷新 IP catalog。
- 除非明确记录为一次性实验，否则不要在每个工程内部保留私有已打包 IP 副本。
- 如果 Vivado 在 overlay 工程中对 `USBIND_0_0_*` 报告 `NSTD-1`/`UCIO-1`，
  说明 PS7 USB control interface 被误导出为外部接口。应删除该外部 BD interface，
  不要随意分配 PL 引脚或降低 DRC 严重性。
