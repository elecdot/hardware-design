# i2c_mpu9250

AXI-Lite 自定义 IP，通过 open-drain I2C 总线读取 JY901/MPU9250 运动数据，并向 PS 暴露原始采样。

## 文件

| 文件 | 用途 |
|---|---|
| [axi_i2c_jy901_v1_0.v](axi_i2c_jy901_v1_0.v) | 带外部 `i2c_scl` 和 `i2c_sda` 端口的顶层 AXI IP wrapper。 |
| [axi_lite_regs.v](axi_lite_regs.v) | AXI4-Lite 寄存器组和软件可见寄存器默认值。 |
| [jy901_hw_debug_top.v](jy901_hw_debug_top.v) | 非 AXI 的 Vivado 硬件调试顶层，用于直接 auto-sampling 和 ILA bring-up。 |
| [jy901_sampler.v](jy901_sampler.v) | oneshot、auto sampling 和 config-write transaction 的采样调度器。 |
| [i2c_master_core.v](i2c_master_core.v) | 用于 burst read 和 16-bit config write 的 bit-level I2C master 状态机。 |
| [i2c_open_drain_io.v](i2c_open_drain_io.v) | open-drain 风格 SCL/SDA 三态适配器。 |

## 快速事实

- 目标时钟假设：除非另有配置，否则为 100 MHz AXI clock。
- 默认 JY901 7-bit I2C 地址：`0x50`；不要把读字节 `0xA1` 当成寄存器值使用。
- 默认采样窗口：从 JY901 register `0x34` 开始读取 13 个 little-endian 16-bit word。
- 默认 `I2C_CLKDIV`：`250`，在 100 MHz 时钟下得到约 100 kHz SCL。
- SCL/SDA 必须上拉到 3.3 V，不能上拉到 5 V。

## 相关文件

| 路径 | 用途 |
|---|---|
| [../../docs/i2c_axi_mpu9250.md](../../docs/i2c_axi_mpu9250.md) | 完整设计说明和依据。 |
| [../../docs/register_map.md](../../docs/register_map.md) | 软件可见寄存器映射。 |
| [../../docs/wiring.md](../../docs/wiring.md) | PYNQ-Z1 接线和电压约束。 |
| [../../sim/tb_i2c_mpu9250/](../../sim/tb_i2c_mpu9250/) | sampler/core 路径的行为仿真。 |
| [../../vivado/constraints/axi_i2c_jy901_package.xdc](../../vivado/constraints/axi_i2c_jy901_package.xdc) | 当前 AXI/PYNQ overlay 的 PMODA `Y17/Y16` 引脚约束。 |
| [../../vivado/constraints/i2c_jy901_pynq_z1.xdc](../../vivado/constraints/i2c_jy901_pynq_z1.xdc) | `P16/P15` 的备用 Arduino 排针引脚约束。 |
| [../../vivado/constraints/jy901_debug.xdc](../../vivado/constraints/jy901_debug.xdc) | PL-only 硬件调试顶层的完整约束。 |

修改寄存器 offset 或 status bit 之前，必须在同一个变更中更新 [../../docs/register_map.md](../../docs/register_map.md)。

## 硬件调试顶层

[jy901_hw_debug_top.v](jy901_hw_debug_top.v) 是可选的非 AXI Vivado bring-up 顶层。
它用固定 `DEV_ADDR=0x50`、`START_REG=0x34` 和 `WORD_COUNT=13` 直接例化 `jy901_sampler`，
为 ILA 标记一层 I2C/status/data 信号，并把 `i2c_busy`、`done`、`data_valid`
以及 `ack_error | timeout` 映射到 `led[3:0]`。它还暴露 `core_state_dbg`、
`core_step_dbg`、`core_tx_byte_dbg` 和 `core_sda_in_dbg` 等 core-level debug probe，
便于从 ILA 诊断硬件 NACK。它会同步 SW0 reset 输入，在 reset 释放后发起一次 debug oneshot，
随后按 `SAMPLE_PERIOD_CYCLES` 间隔继续 auto-sampling。该文件用于 PL-only 硬件调试，
不是 AXI/PYNQ wrapper 的替代品。使用 [../../vivado/constraints/jy901_debug.xdc](../../vivado/constraints/jy901_debug.xdc)
约束其 125 MHz 时钟、SW0 reset、LED 和 PMODA I2C pinout，并保持 `CLK_HZ` 与实际 fabric clock 匹配。
