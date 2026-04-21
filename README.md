# 智能睡眠监测辅助系统

基于 **PYNQ-Z1 / Zynq-7000 XC7Z020** 的低成本、非侵入式家庭睡眠监测与辅助系统。

本项目面向课程设计场景，目标是在夜间连续采集人体生理、体动与环境数据，并完成本地显示、上位机记录分析，以及基础环境辅助控制。系统输出仅作为辅助性、可解释的估计结果，不用于临床诊断。

## 项目目标

- 连续采集睡眠相关数据
- 基于多模态信号估计睡眠状态与稳定性
- 在板端实时显示关键指标
- 将运行数据发送到 PC 端进行记录、分析与可视化
- 根据简单规则触发空调红外、加湿器等辅助动作

## 硬件平台

- 开发板：PYNQ-Z1
- 芯片：Xilinx Zynq-7000 XC7Z020 (`xc7z020clg400-1`)
- 架构：PS + PL 协同
- 通信方式：AXI

注意事项：

- PYNQ-Z1 外设接口按 **3.3V 逻辑** 处理
- 接线前必须确认模块供电与 IO 电平
- 禁止在开发板上电时热插拔传感器与导线
- 计时敏感模块的时钟来源需在设计与约束中明确记录

## 系统架构

项目按三层结构设计：

1. **PL 侧自定义 IP**
   负责 UART、I2C、One-Wire、SPI、IR 等时序敏感接口，并通过 AXI-Lite 提供寄存器访问。
2. **PYNQ 板端客户端**
   负责加载 overlay、轮询各 IP、刷新显示、执行轻量规则、发送数据到 PC。
3. **PC 端服务与分析层**
   负责接收数据、协议解析、存储、睡眠状态分析、平滑处理与可视化。

## 计划接入的模块

输入采集：

- 心率 / 血氧传感器：UART
- MPU9250 九轴模块：I2C
- DHT11 温湿度传感器：One-Wire

显示与辅助控制：

- 1.3 寸 TFT 彩屏：SPI
- 空调红外控制模块：IR
- 加湿器或简单执行器：GPIO / PWM
- 可选助眠提示模块：PDM / PWM / Audio

## 计划中的自定义 IP

- `spi_tft`
- `uart_hr_spo2`
- `i2c_mpu9250`
- `onewire_dht11`
- `ir_ac`
- `gpio_or_pwm_ctrl`
- `ila_debug`

这些 IP 预期采用“一类协议/模块一个 AXI 从设备”的方式组织，除非后续集成阶段有明确整合需求。

## 仓库导航

当前仓库以设计文档为主，后续将逐步补充 RTL、Vivado 工程、PYNQ 驱动与 PC 端程序。

- [AGENTS.md](/p:/labs/hardware_design/hardware_design/AGENTS.md)
  仓库内工程约束、开发流程、测试要求与协作规则
- [docs/wiring.md](/p:/labs/hardware_design/hardware_design/docs/wiring.md)
  模块接线与电平/供电说明
- [docs/register_map.md](/p:/labs/hardware_design/hardware_design/docs/register_map.md)
  AXI IP 寄存器映射
- [docs/protocol.md](/p:/labs/hardware_design/hardware_design/docs/protocol.md)
  PYNQ 到 PC 的通信协议定义
- [docs/test_plan.md](/p:/labs/hardware_design/hardware_design/docs/test_plan.md)
  模块级与系统级测试计划
- [docs/demo_plan.md](/p:/labs/hardware_design/hardware_design/docs/demo_plan.md)
  课程答辩或演示流程

建议后续按以下结构扩展仓库：

```text
vivado/      # Vivado 工程、IP Repo、约束、BD Tcl
rtl/         # 各协议核心与 AXI 包装
sim/         # 仿真测试平台
pynq/        # Overlay、驱动、notebook、板端客户端
pc_server/   # 上位机接收、存储、协议解析
analysis/    # 数据分析与可视化
tests/       # Python 侧测试与样例
```

## 当前状态

目前仓库处于**工程初始化与文档搭建阶段**：

- 已有项目目标、架构与开发约束说明
- 已建立接线、寄存器、协议、测试、演示等文档占位
- 还未完整提交 RTL、Vivado 工程、PYNQ 驱动和 PC 端实现

因此，现阶段更适合作为课程设计的总体方案仓库，而不是可直接运行的完整成品。

## Open Loops

1. 明确具体传感器与显示模块型号
2. 补全 `docs/wiring.md`、`docs/register_map.md` 与 `docs/protocol.md`
3. 优先完成 `onewire_dht11`、`i2c_mpu9250`、`uart_hr_spo2` 的协议核与仿真
4. 建立基础 PYNQ 驱动与板端采集脚本
5. 建立 PC 端接收、存储和可视化最小可运行链路

## 说明

仓库中的工程规范、协作边界与完成定义以 [AGENTS.md](/p:/labs/hardware_design/hardware_design/AGENTS.md) 为准。README 主要用于项目简介与使用导航，不替代详细设计文档。
