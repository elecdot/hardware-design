# project

这里存放用于打包、集成和本地硬件 bring-up 的 Vivado 工程目录，也保留队友交接的原始 `.zip`
设计包。源 RTL 仍保存在 [../../rtl/](../../rtl/) 下；`.srcs` 中的工程副本、生成的 HDL wrapper、run 目录、
cache 输出和仿真产物都是 Vivado 状态，不是权威设计源文件。

## 当前入口选择

| 目标 | 首选入口 | 说明 |
|---|---|---|
| 课堂集成 overlay | [system_v0_1/](system_v0_1/) | 当前集成 Vivado 工程目录；导出到 [../gen/system_v0_2.bit](../gen/system_v0_2.bit) 和匹配 `.hwh/.tcl`。 |
| JY901 AXI/PYNQ 单模块 overlay | [axi_i2c_jy901/](axi_i2c_jy901/) | Block Design `jy901_axi_system`，使用 PMODA `Y17/Y16` 约束。 |
| 自定义 IP 打包 | `*_package/` 或对应单 IP 工程 | 从 [../../rtl/](../../rtl/) 读取源码，输出到 [../ip_repo/](../ip_repo/)。 |
| JY901 PL-only 调试 | [jy901_hw_debug/](jy901_hw_debug/) | 直接调试 I2C、pullup、ACK/NACK 和 ILA bring-up。 |
| 历史状态查阅 | [i2c_ip_test/](i2c_ip_test/) | legacy 混合工程，不作为新 overlay 或 IP package 入口。 |
| 队友原始交接追溯 | `*.zip` | 原始设计包和提交材料；不要把 zip 内生成文件当作当前权威源码。 |

## Vivado 工程索引

| 路径 | 工程类型 | 顶层/BD | 权威源码或约束 | 状态 |
|---|---|---|---|---|
| [axi_humidifier_package/](axi_humidifier_package/) | IP 打包工程 | `axi_humidifier_v1_0` | [../../rtl/axi_humidifier/](../../rtl/axi_humidifier/)，输出 [../ip_repo/axi_humidifier/](../ip_repo/axi_humidifier/) | 从队友交接包迁移后已打包。 |
| [axi_i2c_jy901_package/](axi_i2c_jy901_package/) | IP 打包工程 | `axi_i2c_jy901_v1_0` | [../../rtl/i2c_mpu9250/](../../rtl/i2c_mpu9250/)，输出根级 [../ip_repo/component.xml](../ip_repo/component.xml) | JY901 AXI I2C IP 打包入口。 |
| [axi_uart_spo2/](axi_uart_spo2/) | IP 打包工程 | `axi_uart_spo2_v1_0` | [../../rtl/axi_uart_spo2/](../../rtl/axi_uart_spo2/)，输出 [../ip_repo/axi_uart_spo2/](../ip_repo/axi_uart_spo2/) | 从队友交接包迁移后已打包。 |
| [dht11_axi/](dht11_axi/) | IP 打包工程 | `dht11_axi_v1_0` | [../../rtl/dht11_axi/](../../rtl/dht11_axi/)，输出 [../ip_repo/dht11_axi/](../ip_repo/dht11_axi/) | 从队友交接包迁移后已打包。 |
| [ir_axi_package/](ir_axi_package/) | IP 打包工程 | `gree_ir_axi_v1_0` | [../../rtl/gree_ir_axi/](../../rtl/gree_ir_axi/)，输出 [../ip_repo/ir_ac_axi/](../ip_repo/ir_ac_axi/) | TX-only Gree IR AC AXI IP 打包入口。 |
| [tft_lcd_spi_axi_package/](tft_lcd_spi_axi_package/) | IP 打包工程 | `tft_lcd_spi_axi_v1_0` | [../../rtl/tft_lcd_spi_axi/](../../rtl/tft_lcd_spi_axi/)，输出 [../ip_repo/tft_lcd_spi_axi/](../ip_repo/tft_lcd_spi_axi/) | 从队友交接包迁移后已打包。 |
| [axi_i2c_jy901/](axi_i2c_jy901/) | 单模块 PYNQ overlay | BD `jy901_axi_system`，wrapper `jy901_axi_system_wrapper` | [../constraints/axi_i2c_jy901_package.xdc](../constraints/axi_i2c_jy901_package.xdc) | JY901 单模块 overlay 工程。 |
| [jy901_hw_debug/](jy901_hw_debug/) | PL-only 硬件调试 | `jy901_hw_debug_top` | [../../rtl/i2c_mpu9250/jy901_hw_debug_top.v](../../rtl/i2c_mpu9250/jy901_hw_debug_top.v)，[../constraints/jy901_debug.xdc](../constraints/jy901_debug.xdc) | 用于直接 JY901 I2C bring-up 和 ILA 调试。 |
| [system_v0_1/](system_v0_1/) | 集成 PYNQ overlay | BD `system_v0_1`，wrapper `system_v0_1_wrapper` | [../constraints/integrated/sleep_monitor_pynq_z1.xdc](../constraints/integrated/sleep_monitor_pynq_z1.xdc)，共享 [../ip_repo/](../ip_repo/) | 当前集成工程目录；最新导出名为 `system_v0_2`。 |
| [i2c_ip_test/](i2c_ip_test/) | Legacy 混合工程 | BD `system_experimental` / `jy901_hw_debug` | 详见 [i2c_ip_test/README.md](i2c_ip_test/README.md) 和 [i2c_ip_test/LEGACY.md](i2c_ip_test/LEGACY.md) | 仅供历史查阅。 |

## 队友原始 Zip 包

这些 zip 是原始交接或外部完整工程包，保留在本目录用于提交追溯和必要时复查原始 Vivado 状态。
仓库内当前可维护源码以 [../../rtl/](../../rtl/)、[../ip_repo/](../ip_repo/) 和 [../../pynq/](../../pynq/) 为准。

| 文件 | 原始顶层/内容 | 已迁移到仓库的位置 | 备注 |
|---|---|---|---|
| [dht11(1).zip](dht11%281%29.zip) | 原始 `dht11_sim_copy222` Vivado 工程，含 `dht11_test_wrapper.bit`、`dht11_axi.bit/.hwh` 和生成文件 | [../../rtl/dht11_axi/](../../rtl/dht11_axi/)、[../ip_repo/dht11_axi/](../ip_repo/dht11_axi/)、[../../pynq/dht11_demo/](../../pynq/dht11_demo/) | 无根 README；作为原始 DHT11 Vivado 工程证据保留。 |
| [humidifier_handoff_pack_20260601(2).zip](humidifier_handoff_pack_20260601%282%29.zip) | `humidifier_handoff_pack_20260601`，含 RTL、IP repo、sim、PYNQ demo、reg map、wiring 和 bus integration notes | [../../rtl/axi_humidifier/](../../rtl/axi_humidifier/)、[../ip_repo/axi_humidifier/](../ip_repo/axi_humidifier/)、[../../pynq/humidifier_demo/](../../pynq/humidifier_demo/) | 使用板载 LED 模拟加湿器状态；不要直接驱动实际负载。 |
| [pynq_gree_ir_txrx.zip](pynq_gree_ir_txrx.zip) | `pynq_ir_txrx_integrated_full_project`，含 Gree IR TX、IR capture RX、完整 Vivado build 和 PYNQ 示例 | [../../rtl/gree_ir_axi/](../../rtl/gree_ir_axi/)、[../ip_repo/ir_ac_axi/](../ip_repo/ir_ac_axi/)、[../../pynq/ir_ac_demo/](../../pynq/ir_ac_demo/) | 当前系统只迁入 TX-only Gree IR AC；RX capture 未纳入首个集成范围。 |
| [tft_lcd_handoff_pack_20260601(1).zip](tft_lcd_handoff_pack_20260601%281%29.zip) | `tft_lcd_handoff_pack_20260601`，含 RTL、sim、IP repo、PYNQ driver 和 `tft_lcd.bit/.hwh` | [../../rtl/tft_lcd_spi_axi/](../../rtl/tft_lcd_spi_axi/)、[../ip_repo/tft_lcd_spi_axi/](../ip_repo/tft_lcd_spi_axi/)、[../../pynq/tft_lcd_demo/](../../pynq/tft_lcd_demo/) | ST7789 SPI 字节发送器；当前 RTL 无 `CS`/`MISO`。 |
| [uart_spo2_pynq.zip](uart_spo2_pynq.zip) | `uart_spo2_pynq`，含 AXI UART SpO2 IP、Vivado overlay、PYNQ MMIO、Tcl 和调试工程 | [../../rtl/axi_uart_spo2/](../../rtl/axi_uart_spo2/)、[../ip_repo/axi_uart_spo2/](../ip_repo/axi_uart_spo2/)、[../../pynq/spo2_demo/](../../pynq/spo2_demo/) | 原始包使用的独立引脚约束不等同于当前集成 XDC；集成约束以 [../constraints/README.md](../constraints/README.md) 为准。 |

## 当前集成 Overlay

[system_v0_1/](system_v0_1/) 是当前集成 Vivado 工程目录，导出的最新课堂 demo artifact 位于
[../gen/system_v0_2.bit](../gen/system_v0_2.bit)、[../gen/system_v0_2.hwh](../gen/system_v0_2.hwh)
和 [../gen/system_v0_2.tcl](../gen/system_v0_2.tcl)。

`system_v0_2.hwh` 中确认的 AXI address map：

| Instance | Base | High | 说明 |
|---|---:|---:|---|
| `axi_i2c_jy901_v1_0_0` | `0x4000_0000` | `0x4000_0FFF` | JY901 AXI I2C。 |
| `axi_humidifier_v1_0_0` | `0x4000_1000` | `0x4000_1FFF` | 加湿器/LED 指示控制。 |
| `tft_lcd_spi_axi_v1_0_0` | `0x4000_2000` | `0x4000_2FFF` | TFT LCD SPI byte sender。 |
| `dht11_axi_v1_0_0` | `0x4000_3000` | `0x4000_3FFF` | DHT11 one-wire 温湿度。 |
| `axi_uart_spo2_v1_0_0` | `0x4000_4000` | `0x4000_4FFF` | UART SpO2/心率。 |
| `gree_ir_axi_v1_0_0` | `0x4000_5000` | `0x4000_5FFF` | TX-only Gree IR AC。 |

外部端口和 pin mapping 以 [../constraints/integrated/sleep_monitor_pynq_z1.xdc](../constraints/integrated/sleep_monitor_pynq_z1.xdc)
和 [../../docs/wiring.md](../../docs/wiring.md) 为准。不要同时启用会冲突的单模块 XDC。

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
