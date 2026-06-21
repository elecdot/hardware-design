# IR AC Integration Plan

本文档记录 TX-only Gree IR AC 的集成决策、证据和执行阶段。当前硬件集成范围已经对
`system_v0_2` overlay 关闭：源码迁移、模块回归、IP 打包、集成 BD、PYNQ 板端 smoke
和真实实验室空调响应均已完成。

## 关闭状态摘要

| Phase | 必需证据 | 结果 |
|---|---|---|
| IR-0 standalone evidence | 队友独立测试确认实验室 Gree AC 响应交接命令集 | Complete |
| IR-1 source migration | TX-only RTL、PYNQ helper 和本地文档迁入跟踪路径 | Complete |
| IR-2 module regression | Icarus regression 对 preset/start/done/error 行为输出 `tb_gree_ir_axi PASS` | Complete |
| IR-3 IP packaging | `gree_ir_axi_v1_0` 已打包到 `vivado/ip_repo/ir_ac_axi/`，包含 AXI metadata 和 `ir_pwm` | Complete |
| IR-4 integrated overlay | 导出 `system_v0_2.bit/.hwh/.tcl`；地址 `0x40005000`；`ir_pwm=T14`；DRC/route/timing 通过 | Complete |
| IR-5 board bring-up | PYNQ TX status 为 `done=true/error=false`；真实 AC 响应 `power_on`、`power_off`、`temp_26` | Complete |

## 已确认决策

| Topic | Decision |
|---|---|
| Scope | 首个集成版本为 TX-only。`ir_capture_axi` 保留为独立验证工具。 |
| Pin | 使用交接 XDC 中的 Arduino `ck_io[0]` / package pin `T14` 输出 `ir_pwm`。 |
| Command set | 只暴露七个已验证 Gree YB0F2 preset：`power_on`、`power_off`、`temp_24`、`temp_25`、`temp_26`、`temp_27`、`temp_28`。 |
| Standalone evidence | 队友已完成独立模块测试，并确认实验室 Gree AC 响应。 |
| Control ownership | PC policy 拥有自动 AC 和加湿器决策；PYNQ 负责校验和执行命令。 |
| PYNQ fallback | 本地 PYNQ 加湿器自动化只保留为 bring-up/fallback，不是最终自动策略 owner。 |
| Protocol | 增加 PC 到 PYNQ 的 `control_command`，以及 PYNQ 到 PC 的 `control_status`。 |
| Soft architecture | 构建 PYNQ 顶层 orchestrator class 和 PC 侧 integration service/policy layer。 |

## 交接源码事实

参考目录：

```text
handoff/gree_ir_txrx_hardware_package/
```

迁移到本仓库的 TX-only 源码：

```text
synthesis/vivado/rtl/tx/gree_ir_core.v
synthesis/vivado/rtl/tx/gree_ir_axi_v1_0.v
synthesis/vivado/rtl/tx/gree_ir_axi_v1_0_S00_AXI.v
synthesis/vivado/constraints/pynq_z1_ir_txrx.xdc
```

首版寄存器：

| Offset | Name | Description |
|---:|---|---|
| `0x00` | `CONTROL` | bit0 `start`，bit1 `soft_reset`。 |
| `0x04` | `STATUS` | bit0 `busy`，bit1 `done`，bit2 `error`。 |
| `0x08` | `CMD_LOW` | selected compatibility command 的低 32 bit。 |
| `0x0C` | `CMD_HIGH` | selected compatibility command 的高 32 bit。 |
| `0x10` | `PRESET` | 67-bit waveform preset selector。 |
| `0x14` | `DEBUG` | core state 和 sample index。 |

## 硬件安全

- PYNQ-Z1 PL 引脚只接受 3.3 V logic。
- 不要从 FPGA 引脚直接驱动裸 IR LED；使用 IR 发射模块或晶体管/MOSFET 驱动。
- 模块必须与 PYNQ-Z1 共地。
- 板子上电时不要热插拔 IR 模块。
- 真实空调响应需要人工观察；`sent=true` 只表示发射完成。

## 集成硬件结果

生成 artifact：

```text
vivado/gen/system_v0_2.bit
vivado/gen/system_v0_2.hwh
vivado/gen/system_v0_2.tcl
```

集成地址：

| IP instance | Base | Range | Notes |
|---|---:|---:|---|
| `gree_ir_axi_v1_0_0` | `0x4000_5000` | 4K | 由 `system_v0_2.hwh` 和 `system_v0_2.tcl` 确认。 |

外部端口：

```text
ir_pwm -> Arduino ck_io[0] -> T14
```

XDC 端口位置：

```tcl
set_property PACKAGE_PIN T14 [get_ports ir_pwm]
```

## 协议计划

`sleep_result` 保持为分类输出。设备执行使用 `control_command`。

PC 到 PYNQ：

```json
{
  "type": "control_command",
  "sample_id": 123,
  "mode": "auto",
  "policy_id": "comfort_v1",
  "targets": {
    "ir_ac": {"command": "temp_26", "temperature_setpoint_c": 26},
    "humidifier": {"enabled": true}
  },
  "valid": 1,
  "reason": "light_sleep_temp_high_humidity_low"
}
```

PYNQ 到 PC：

```json
{
  "type": "control_status",
  "sample_id": 123,
  "accepted": 1,
  "applied": {
    "ir_ac": {
      "requested": true,
      "command": "temp_26",
      "sent": true,
      "skipped": false,
      "error": null
    }
  },
  "status_code": 0,
  "remark": "control_applied"
}
```

协议边界：

- `sleep_result` 仍是 PC classifier output。
- `control_command.targets` 描述一个 sample 的期望 actuator target。
- PYNQ 必须对 accepted、skipped 和 rejected command 都发送 `control_status`。
- AC command 是一次性 IR pulse，不等于真实 AC 状态反馈。

## 自动策略计划

PC policy 负责自动舒适度策略。首版策略保持保守：

| Sleep state | Meaning | Aggressiveness | Policy intent |
|---:|---|---:|---|
| `0` | Not asleep / awake | `1.0` | 较窄舒适区，较快修正。 |
| `1` | Light sleep | `0.6` | 中等修正。 |
| `2` | Deep sleep | `0.3` | 更宽容，避免打扰。 |

规则：

- `state_valid != 1` 时输出 no-action `control_command` 并说明 `reason`。
- 湿度偏低时请求加湿器打开，湿度偏高时请求关闭。
- 温度明显偏高时可发送 `temp_26`、`temp_25` 或 `temp_24`。
- 温度明显偏低时可发送 `temp_27` 或 `temp_28`。
- IR command 必须有最小间隔和重复命令 cooldown。

建议 cooldown：

| Mode | Same IR command repeat | Any IR command minimum interval |
|---|---|---|
| Demo | 30 to 60 s | 5 s |
| Normal | 5 to 10 min | 5 s |

## 软件架构移交

PYNQ 侧：

```text
SleepMonitorBoard / BoardOrchestrator
  - bind integrated overlay IPs
  - read sensors
  - update TFT
  - validate/rate-limit actuator commands
  - execute humidifier target and IR one-shot command
  - builds control_status
```

PC 侧：

```text
SleepMonitorPcService
  - validates sensor_data
  - runs classifier adapter
  - runs comfort policy
  - stores four record streams
  - updates dashboard state
```

`pc_server/` 中的旧 demo-quality 文件可以重构；它们不是最终架构约束。

## 硬件执行记录

### IR-0: Standalone Evidence Capture

队友独立测试确认实验室 Gree AC 会响应交接命令集。该证据作为迁移入口，但不替代本仓库集成验证。

### IR-1: Source Migration Skeleton

迁移产物：

- [../rtl/gree_ir_axi/](../rtl/gree_ir_axi/)
- [../pynq/ir_ac_demo/](../pynq/ir_ac_demo/)
- [register_map.md](register_map.md)
- [wiring.md](wiring.md)
- [test_plan.md](test_plan.md)

### IR-2: Module Regression

本地证据：2026-06-10 使用 Icarus Verilog 运行，输出 `tb_gree_ir_axi PASS`。

覆盖行为：

- reset 默认值；
- 七个 preset shadow；
- `start` 到 `done`；
- done/error clear；
- busy 期间重复 start 触发 error；
- soft reset。

### IR-3: IP Packaging

`gree_ir_axi_v1_0` 已打包到 `vivado/ip_repo/ir_ac_axi/`。静态验证内容包括：

- `component.xml`、`xgui/` 和 `src/` 存在；
- packaged HDL SHA256 与 `rtl/gree_ir_axi/` 匹配；
- AXI4-Lite metadata、4096-byte memory map、parameter default 正确；
- 外部 `ir_pwm` 存在；
- IP package 内不嵌入板级 pin constraint。

### IR-4: Integrated Vivado Overlay

IR IP 已加入集成 Block Design：

- instance：`gree_ir_axi_v1_0_0`
- address：`0x4000_5000`，range 4K
- AXI port：连接到 `ps7_0_axi_periph/M05_AXI`
- clock/reset：连接到 `processing_system7_0/FCLK_CLK0` 和 `rst_ps7_0_50M/peripheral_aresetn`
- external port：`ir_pwm`
- pin：`T14`
- 导出 artifact：`system_v0_2.bit`、`system_v0_2.hwh`、`system_v0_2.tcl`

路由 DRC、route status、timing summary 和 bitstream 输出均已记录为通过。

### IR-5: PYNQ Board Bring-Up

板端命令：

```bash
demo_ir_ac.py --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit --base-addr 0x40005000 --command temp_26 --timeout 15.0
```

结果：

- PYNQ status 显示 `done=true`、`error=false`。
- `power_on`、`power_off` 和 `temp_26` 均让实验室 Gree AC 响应。
- 可靠响应需要 IR 发射器距离 AC 接收头约 20 cm 以内并对准。

## 软件集成移交

最终软件闭环：

```text
PYNQ sends sensor_data
PC receives sensor_data
PC classifier emits sleep_result
PC policy emits control_command
PYNQ executes/skips/rejects command
PYNQ sends control_status
PC stores and displays all four records
```

后续实现以 [software_integration_plan.md](software_integration_plan.md) 和
[software_integration_runbook.md](software_integration_runbook.md) 为准。

## 已知限制

- 首版 IR AC 是 TX-only，没有 RX capture 或真实 AC 状态反馈。
- `sent=true` 不能单独证明真实空调响应。
- Dashboard desired-state panel 只能显示推导状态，不得自动重放 AC desired state。
- 课堂 demo 前不要添加 AC replay；只保留手动一次性 pending command 和保守自动策略。
