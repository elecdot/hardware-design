# 智能睡眠监测辅助系统

本仓库用于计算机硬件综合课程设计项目：一个围绕 PYNQ-Z1 / Zynq-7000 XC7Z020 平台构建的低成本、非侵入式、面向家庭场景的睡眠监测与辅助系统。

系统采集生理、运动和环境数据，在板端显示关键运行值，将结构化记录发送到 PC 侧服务，并可触发简单辅助动作，例如红外空调控制、加湿器控制或睡眠辅助提示。

系统输出只作为辅助估计，不是临床诊断结果。

## 项目概述

核心目标：

- 在整夜运行期间采集睡眠相关信号。
- 基于多种信号估计睡眠状态和睡眠稳定性。
- 在板端显示屏显示关键值。
- 将运行数据发送到 PC 服务，用于记录、分析和可视化。
- 保持实现可解释，便于课程考核和调试。

当前工作区状态：

- 当前集成硬件平台为 `system_v0_2`，已在 `vivado/gen/` 下导出匹配的 `.bit`、`.hwh` 和 `.tcl` artifact。
- 集成板级 demo 路径已有 JY901、DHT11、UART SpO2、TFT LCD、加湿器状态/控制和 TX-only Gree IR AC 的板级证据。
- TX-only Gree IR AC 的硬件范围已关闭：源码迁移、回归、IP 打包、Block Design 集成、PYNQ smoke 和真实实验室空调响应均已记录。
- PC/PYNQ 软件集成已有面向课堂 demo 的第一版：规范四消息协议、板端 socket client/orchestrator、PC classifier adapter、舒适策略、JSONL 存储、dashboard 入口、pending-only 手动控制，以及 display-only desired-state panel。

## 硬件平台

目标板卡：

- Board：PYNQ-Z1
- Chip：Xilinx Zynq-7000 XC7Z020，`xc7z020clg400-1`
- PS：ARM Cortex-A9 processing system
- PL：FPGA programmable logic
- PS-PL 通信：AXI / AXI-Lite

重要约束：

- 将 PYNQ-Z1 外部 I/O 视为仅支持 3.3 V logic。
- 板子上电时不要热插拔传感器或导线。
- 在 RTL 参数、寄存器文档和 XDC 中明确时钟假设。
- 除非另有说明，当前设计假设 100 MHz system/AXI clock。

## 主要外部模块

输入传感模块：

| 模块 | 数据 | 计划接口 | 状态 |
|---|---|---|---|
| 心率 / SpO2 传感器 | BPM, SPO2 | UART custom IP | 集成本地板级 demo 通过；已记录物理 RX/TX 方向说明 |
| JY901 / MPU9250 IMU | 加速度、角速度、姿态、温度 | I2C custom IP | 集成本地板级 demo 通过 |
| DHT11 | 温度、湿度 | One-Wire custom IP | 集成本地板级 demo 通过 |

显示和辅助模块：

| 模块 | 用途 | 计划接口 | 状态 |
|---|---|---|---|
| 1.3-inch TFT display | 板端实时显示 | SPI custom IP | 集成本地板级 demo 通过 |
| IR 空调发射器 | 环境辅助 | IR custom IP | TX-only 集成硬件范围完成；实验室 Gree AC 响应已确认 |
| 加湿器或指示器 | 简单执行器控制 | GPIO / PWM / relay-style output | 集成本地板级 demo 通过 |
| 睡眠辅助提示模块 | 可选音频或提示输出 | PDM / PWM / audio | 计划中 |

## 系统架构

系统分为三层。

1. PL 侧自定义 IP 层
   - 实现对时序敏感的外设协议。
   - 向 PS 暴露清晰的 AXI-Lite 寄存器接口。
   - 板级引脚分配保存在 XDC 中，不写入 RTL。

2. PYNQ 板端 client
   - 加载 bitstream 和 overlay metadata。
   - 按 overlay 名称绑定自定义 IP。
   - 通过 MMIO driver 读取传感器。
   - 运行轻量本地规则，例如翻身检测和阈值 flag。
   - 更新本地显示，并向 PC 发送结构化 sample。

3. PC 侧服务和分析工具
   - 接收来自 PYNQ 的 sample。
   - 解码一个规范协议。
   - 校验数值和时间戳顺序。
   - 在任何预测或平滑前保存原始记录。
   - 为课程 demo/report 生成统计和可视化。

## 仓库布局

当前和计划中的仓库结构：

| 路径 | 用途 |
|---|---|
| [.agents/skills/](.agents/skills/) | 仓库本地 Codex skills。 |
| [AGENTS.md](AGENTS.md) | Agent 执行规则和 Definition of Done。 |
| [README.md](README.md) | 稳定项目概览和导航。 |
| [docs/](docs/) | 工程文档和工作笔记。 |
| [reports/](reports/) | 课程报告输入和图表。 |
| [rtl/](rtl/) | 可综合 RTL custom IP。 |
| [sim/](sim/) | 行为仿真和 testbench。 |
| [vivado/](vivado/) | Vivado 工程、约束和未来脚本。 |

已实现或活跃的子树：

| 路径 | 用途 |
|---|---|
| [rtl/i2c_mpu9250/](rtl/i2c_mpu9250/) | AXI-Lite I2C/JY901 RTL 实现。 |
| [rtl/dht11_axi/](rtl/dht11_axi/) | 从交接包迁移的 DHT11 AXI RTL。 |
| [rtl/gree_ir_axi/](rtl/gree_ir_axi/) | 从交接包迁移的 TX-only Gree IR AC AXI RTL。 |
| [rtl/axi_humidifier/](rtl/axi_humidifier/) | 从交接包迁移的加湿器/LED AXI RTL。 |
| [rtl/tft_lcd_spi_axi/](rtl/tft_lcd_spi_axi/) | 从交接包迁移的 TFT LCD SPI AXI RTL。 |
| [rtl/axi_uart_spo2/](rtl/axi_uart_spo2/) | 从交接包迁移的 UART SpO2 AXI RTL。 |
| [sim/tb_gree_ir_axi/](sim/tb_gree_ir_axi/) | TX-only Gree IR AC AXI preset/start/done/error 回归。 |
| [sim/tb_i2c_mpu9250/](sim/tb_i2c_mpu9250/) | JY901 burst-read 路径的行为仿真。 |
| [pynq/jy901_demo/](pynq/jy901_demo/) | 用于课堂展示的最小 PYNQ-Z1 JY901 bitstream/MMIO demo。 |
| [pynq/dht11_demo/](pynq/dht11_demo/) | 从交接包迁移的 DHT11 PYNQ driver/demo。 |
| [pynq/humidifier_demo/](pynq/humidifier_demo/) | 从交接包迁移的加湿器 PYNQ driver/demo。 |
| [pynq/ir_ac_demo/](pynq/ir_ac_demo/) | 从交接包迁移的 TX-only Gree IR AC driver/demo。 |
| [pynq/sleep_demo/](pynq/sleep_demo/) | 集成 PYNQ demo、顶层板端 orchestrator 和 socket client。 |
| [pynq/tft_lcd_demo/](pynq/tft_lcd_demo/) | 从交接包迁移的 TFT LCD PYNQ driver/demo。 |
| [pynq/spo2_demo/](pynq/spo2_demo/) | 从交接包迁移的 UART SpO2 PYNQ helper。 |
| [pc_server/](pc_server/) | PC socket service、classifier adapter、comfort policy、storage、fake client 和 dashboard 入口。 |
| [vivado/constraints/](vivado/constraints/) | 板级 XDC 约束。 |
| [vivado/ip_repo/](vivado/ip_repo/) | Vivado 工程共享的已打包 custom IP 仓库。 |
| [vivado/ip_repo/ir_ac_axi/](vivado/ip_repo/ir_ac_axi/) | 已打包 TX-only Gree IR AC AXI IP。 |
| [vivado/project/axi_i2c_jy901_package/](vivado/project/axi_i2c_jy901_package/) | JY901 AXI I2C IP 打包工程。 |
| [vivado/project/axi_i2c_jy901/](vivado/project/axi_i2c_jy901/) | JY901 AXI/PYNQ overlay 工程。 |
| [vivado/project/ir_axi_package/](vivado/project/ir_axi_package/) | TX-only Gree IR AC AXI IP 打包工程。 |
| [vivado/project/jy901_hw_debug/](vivado/project/jy901_hw_debug/) | PL-only JY901 硬件调试和 ILA bring-up 工程。 |
| [vivado/project/i2c_ip_test/](vivado/project/i2c_ip_test/) | 历史 I2C IP 测试的 legacy Vivado 工程。 |
| [vivado/gen/](vivado/gen/) | 被忽略的本地导出目录，用于临时 `.bit`/`.hwh` 文件。 |
| [docs/JY901/](docs/JY901/) | JY901 模块厂商参考资料。 |

后续可能新增的计划子树：

| 路径 | 用途 |
|---|---|
| `analysis/` | 特征提取、平滑、绘图和模型实验。 |
| `tests/` | Python 侧测试和可复用 fixture。 |
| `data/` | 原始和处理后数据；除非需要 demo sample，通常忽略。 |

## 文档

优先阅读：

| 路径 | 用途 |
|---|---|
| [AGENTS.md](AGENTS.md) | Agent 规则、测试要求和 Definition of Done。 |
| [docs/README.md](docs/README.md) | 文档目录索引。 |
| [rtl/README.md](rtl/README.md) | RTL 目录索引。 |
| [sim/README.md](sim/README.md) | 仿真目录索引。 |
| [vivado/README.md](vivado/README.md) | Vivado 目录索引。 |
| [reports/README.md](reports/README.md) | 报告材料索引。 |

工程参考：

| 路径 | 用途 |
|---|---|
| [docs/i2c_axi_mpu9250.md](docs/i2c_axi_mpu9250.md) | JY901/MPU9250 I2C AXI IP 的详细设计说明。 |
| [docs/register_map.md](docs/register_map.md) | 规范 AXI-Lite 寄存器映射。 |
| [docs/wiring.md](docs/wiring.md) | 接线和电压说明。 |
| [docs/test_plan.md](docs/test_plan.md) | 仿真和板级测试检查清单。 |
| [docs/handoff_and_integration.md](docs/handoff_and_integration.md) | 队友模块交接迁移和集成计划。 |
| [docs/ir_ac_integration_plan.md](docs/ir_ac_integration_plan.md) | 已关闭的 TX-only Gree IR AC 硬件集成记录和已确认协议决策。 |
| [docs/software_integration_plan.md](docs/software_integration_plan.md) | IR 硬件 demo 验证后的当前 PC/PYNQ 软件集成计划。 |
| [docs/software_integration_runbook.md](docs/software_integration_runbook.md) | 可执行 PC/PYNQ 软件集成运行手册，包括部署、socket smoke 和证据采集。 |
| [docs/ip_packaging_manual.md](docs/ip_packaging_manual.md) | 迁移 RTL 模块的第 3 阶段 Vivado IP 打包检查清单。 |
| [docs/protocol.md](docs/protocol.md) | PYNQ 到 PC 的 newline-delimited JSON 协议。 |
| [docs/work_notes.md](docs/work_notes.md) | 人工工作笔记、安全提醒和常见故障模式。 |

## 未闭环事项

Demo 准备度：

- [x] 硬件集成 overlay demo 路径已可通过 `system_v0_2` 进行课堂展示。
- [x] PC/PYNQ 四消息软件集成第一版已实现并完成本地自测。
- [x] Dashboard 入口已实现，使用真实 protocol/service state、pending-only 手动控制和有界 control-history UI。
- [ ] 正式 demo 采集前，修复 PYNQ 板端时间，确保日志包含真实时间戳。
- [ ] 正式 demo 采集前，如果实验室网络和板卡可用，重新运行一次完整 `dashboard_server.py` 加真实 PYNQ `board_client.py` 会话。
- [ ] 课堂展示 IR AC 前，将 IR 发射器放到距离实验室 Gree AC 接收头约 20 cm 以内，并验证 `power_on`、`power_off` 或 `temp_26`。

已完成：

- [x] 里程碑：端到端 I2C MPU9250 (JY901) 集成闭环完成，包括 RTL / Sim、Vivado IP hw debug / packaging、PYNQ overlay (bitstream) 生成、Python driver 实现和硬件 smoke test 验证。
- [x] UART SpO2、DHT11、SPI TFT LCD、加湿器和 PC socket/Excel demo 的交接源码/文档迁移骨架。
- [x] JY901、DHT11、UART SpO2、TFT LCD、加湿器状态/控制和显示更新的集成本地板级 demo 通过，并记录 metadata fallback 限制。
- [x] TX-only Gree IR AC 集成计划关闭，软件集成入口计划已记录；队友独立测试确认实验室 Gree AC 响应。
- [x] IR-1 源码迁移骨架：TX-only Gree IR AC RTL 迁入 `rtl/gree_ir_axi/`，PYNQ TX demo 骨架加入 `pynq/ir_ac_demo/`，并更新本地 README/register/wiring 文档。
- [x] IR-2 模块回归：针对 Gree IR TX preset selection、start/done/error 行为和显式 PASS 输出的聚焦 Icarus 仿真。
- [x] IR-3 IP 打包：从已跟踪 RTL 将 `gree_ir_axi_v1_0` 打包到 `vivado/ip_repo/ir_ac_axi/`，并静态验证 AXI4-Lite metadata、`ir_pwm`、参数和 file set。
- [x] IR-4 集成 Vivado overlay：`gree_ir_axi_v1_0_0` 已加入集成 Block Design，`ir_pwm` 已导出并放置到 `T14`，`system_v0_2.bit/.hwh/.tcl` 已导出到 `vivado/gen/`。
- [x] IR-5 PYNQ 板端 bring-up：集成 overlay driver smoke 已发送 `power_on`、`power_off` 和 `temp_26`；当 IR 发射器距离 AC 接收头约 20 cm 以内时，实验室 Gree AC 有响应。
- [x] 软件集成第一版：PYNQ `SleepMonitorBoard` 和 `board_client.py`，PC protocol/classifier/policy/state/storage/service，`control_command` / `control_status`，fake client，dashboard server 和 desired-state panel 已实现并有自测覆盖。

课堂 demo 后进一步工作：

- 如时间允许，为最终报告采集一轮新的 dashboard 加真实板端证据运行。
- 改进旧 PYNQ 镜像的 overlay metadata 导出，避免继续依赖静态地址映射 fallback。
- 仅当未来硬件能提供可靠 actuator feedback 时，才添加可选 desired-state reconciliation；课堂 demo 前不要添加 AC replay。
- 可考虑把睡眠辅助提示/audio 模块作为后续扩展。

当协议、寄存器映射、外部端口、接线或工作流假设发生变化时，保持 README 文件和工程文档同步。
