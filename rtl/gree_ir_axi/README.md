# gree_ir_axi

从 `handoff/gree_ir_txrx_hardware_package/` 迁移的 TX-only AXI4-Lite Gree IR 空调发射器。

## 范围

首个集成版本只包含发射路径：

- `gree_ir_core.v`
- `gree_ir_axi_v1_0.v`
- `gree_ir_axi_v1_0_S00_AXI.v`

交接包中还包含 `ir_capture_axi` 接收 RTL，但 RX 仍作为独立验证工具保留，
有意不迁入首个集成源码路径。

## 顶层 IP

顶层模块：`gree_ir_axi_v1_0`

外部端口：

| 端口 | 方向 | 说明 |
|---|---|---|
| `ir_pwm` | output | 38 kHz 调制红外发射信号。 |

AXI 接口：

- `s00_axi` AXI4-Lite slave。
- 32-bit data width。
- 5-bit AXI address width。
- 默认时钟假设：100 MHz AXI/system clock。

参数：

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `CORE_CLK_FREQ` | `100_000_000` | 核心时钟频率，单位 Hz。 |
| `CORE_CLK_1US` | `100` | 100 MHz 下 1 微秒 tick 数。 |
| `CORE_CARRIER_HZ` | `38_000` | 红外载波频率。 |

## 命令

RTL 从 ROM 发送 67-bit Gree YB0F2 命令预设。首个集成范围只暴露以下已验证命令：

| Preset | Command |
|---:|---|
| 1 | `power_on` |
| 2 | `power_off` |
| 3 | `temp_24` |
| 4 | `temp_25` |
| 5 | `temp_26` |
| 6 | `temp_27` |
| 7 | `temp_28` |

`CMD_LOW` 和 `CMD_HIGH` 仅用于兼容性/状态可见性，并不是该 RTL 中通用的 raw-command 发送路径。
软件应使用 `PRESET`。

## 寄存器映射

规范寄存器映射见 [../../docs/register_map.md](../../docs/register_map.md)。

## 接线

计划中的集成 overlay 输出为 `ir_pwm`，连接到 PYNQ-Z1 Arduino `ck_io[0]`，封装引脚 `T14`。

使用红外发射模块或晶体管/MOSFET 驱动器。不要从 FPGA 引脚直接驱动裸 IR LED。

## 验证状态

- 队友独立模块测试确认实验室 Gree AC 会响应交接包命令集。
- 本仓库 `IR-2` 仿真已通过：`sim/tb_gree_ir_axi/` 验证 reset 默认值、全部七个 preset shadow、start/done、clear-done/clear-error、重复 start error latch 和 soft reset。
- `IR-3` 已通过 `vivado/ip_repo/ir_ac_axi/` 的 Vivado IP 打包静态验证。
- 集成 Vivado overlay 和板级 smoke 尚未完成。
