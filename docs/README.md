# docs

这里存放项目设计说明、硬件参考、寄存器映射、接线说明和测试计划。

## 索引

| 路径 | 用途 |
|---|---|
| [i2c_axi_mpu9250.md](i2c_axi_mpu9250.md) | JY901/MPU9250 I2C AXI IP 的详细设计说明。 |
| [register_map.md](register_map.md) | 已实现自定义 IP 的规范 AXI-Lite 寄存器映射。 |
| [wiring.md](wiring.md) | 外部模块的物理接线和电压注意事项。 |
| [test_plan.md](test_plan.md) | 仿真和板级测试检查清单。 |
| [handoff_and_integration.md](handoff_and_integration.md) | 队友模块的交接迁移与 Vivado/PYNQ 集成计划。 |
| [ir_ac_integration_plan.md](ir_ac_integration_plan.md) | 已关闭的 TX-only Gree IR AC 集成计划、证据、协议决策和执行阶段。 |
| [software_integration_plan.md](software_integration_plan.md) | IR 硬件演示验证后的当前 PC/PYNQ 软件集成计划。 |
| [software_integration_runbook.md](software_integration_runbook.md) | 可执行的 PC/PYNQ 软件集成运行手册，包括 rsync 部署和 socket smoke 步骤。 |
| [ip_packaging_manual.md](ip_packaging_manual.md) | 迁移 RTL 模块的第 3 阶段 Vivado IP 打包可执行检查清单。 |
| [protocol.md](protocol.md) | PYNQ 到 PC 的换行分隔 JSON 协议。 |
| [demo_plan.md](demo_plan.md) | 课程演示或汇报流程说明。 |
| [work_notes.md](work_notes.md) | 面向人的工作笔记、安全提醒和常见故障模式。 |
| [JY901/](JY901/) | JY901 模块的厂商文档、工具和示例代码。 |

当实现细节变多时，把它们放到模块专用文档中；只要 RTL 可见寄存器发生变化，就同步更新 [register_map.md](register_map.md)。
