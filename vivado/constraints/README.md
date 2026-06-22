# constraints

这里存放外部 PL 端口的板级 XDC 约束。引脚分配只属于具体板级顶层或 Block Design wrapper，
不要写进可复用 RTL 或 IP package。

## 索引

| 文件 | 用途 |
|---|---|
| [axi_i2c_jy901_package.xdc](axi_i2c_jy901_package.xdc) | 将已打包 AXI/PYNQ I2C IP 映射到 PMODA：`i2c_scl` 为 `Y17`、`i2c_sda` 为 `Y16`，均为 `LVCMOS33`，可选弱内部 pullup。 |
| [dht11_pynq_z1.xdc](dht11_pynq_z1.xdc) | 将 DHT11 `dht11_0` 映射到 Arduino IO11 `R17`，`LVCMOS33`，带 pullup。 |
| [humidifier_leds_pynq_z1.xdc](humidifier_leds_pynq_z1.xdc) | 将 `humidifier_leds[3:0]` 映射到 PYNQ-Z1 板载 LED。 |
| [i2c_jy901_pynq_z1.xdc](i2c_jy901_pynq_z1.xdc) | 将 JY901 I2C `i2c_scl` 映射到 PYNQ-Z1 Arduino SCL `P16`，`i2c_sda` 映射到 Arduino SDA `P15`，均为 `LVCMOS33`。 |
| [integrated/sleep_monitor_pynq_z1.xdc](integrated/sleep_monitor_pynq_z1.xdc) | 当前集成 overlay 引脚分配，覆盖 TFT、JY901、UART SpO2、DHT11、Gree IR AC TX 和加湿器 LED。 |
| [jy901_debug.xdc](jy901_debug.xdc) | `jy901_hw_debug_top.v` 的约束：125 MHz `clk`、SW0 上的 `resetn`、`led[3:0]`，以及位于 PMODA `Y17/Y16` 的 JY901 I2C，均为 `LVCMOS33`。 |
| [spo2_pmodb_pynq_z1.xdc](spo2_pmodb_pynq_z1.xdc) | 将 UART SpO2 `uart_txd` 映射到 PMODB `W14`，`uart_rxd` 映射到 PMODB `Y14`。 |
| [tft_lcd_pynq_z1.xdc](tft_lcd_pynq_z1.xdc) | 将 TFT LCD `lcd_scl/lcd_sda/lcd_res/lcd_dc/lcd_blk` 映射到 PMODA。 |

## 当前集成 Overlay Pin Map

[integrated/sleep_monitor_pynq_z1.xdc](integrated/sleep_monitor_pynq_z1.xdc) 是 `system_v0_2`
课堂集成 overlay 的约束来源。它要求顶层外部端口名与下表一致。

| 模块 | 信号 | Pin/header | 说明 |
|---|---|---|---|
| TFT LCD | `lcd_scl` | PMODA `Y18` | SPI SCL。 |
| TFT LCD | `lcd_sda` | PMODA `Y19` | SPI MOSI。 |
| TFT LCD | `lcd_res` | PMODA `Y16` | Display reset。 |
| TFT LCD | `lcd_dc` | PMODA `Y17` | Command/data select。 |
| TFT LCD | `lcd_blk` | PMODA `U18` | Backlight enable。 |
| JY901 | `i2c_scl` | Arduino SCL `P16` | I2C SCL，带 pullup；真实运行仍建议外部 3.3 V pullup。 |
| JY901 | `i2c_sda` | Arduino SDA `P15` | I2C SDA，带 pullup；真实运行仍建议外部 3.3 V pullup。 |
| UART SpO2 | `uart_txd` | PMODB pin 1 `W14` | FPGA TX。 |
| UART SpO2 | `uart_rxd` | PMODB pin 2 `Y14` | FPGA RX，带 pullup。 |
| DHT11 | `dht11_0` | Arduino IO11 `R17` | One-wire DATA，带 pullup。 |
| Gree IR AC TX | `ir_pwm` | Arduino `ck_io[0]` `T14` | 38 kHz 调制红外输出；使用 IR 发射模块或驱动电路。 |
| Humidifier | `humidifier_leds[0]` | Board LED `R14` | LED 模拟 actuator 状态。 |
| Humidifier | `humidifier_leds[1]` | Board LED `P14` | LED 模拟 actuator 状态。 |
| Humidifier | `humidifier_leds[2]` | Board LED `N16` | LED 模拟 actuator 状态。 |
| Humidifier | `humidifier_leds[3]` | Board LED `M14` | LED 模拟 actuator 状态。 |

## 使用规则

- 同一个顶层构建只能使用一份针对同一信号的 pin-mapping XDC。
- 当前集成 overlay 使用 [integrated/sleep_monitor_pynq_z1.xdc](integrated/sleep_monitor_pynq_z1.xdc)，不要再同时应用冲突的单模块 XDC。
- 单模块 JY901 AXI/PYNQ overlay 工程使用 [axi_i2c_jy901_package.xdc](axi_i2c_jy901_package.xdc)，并保持 debug ILA XDC 禁用。
- `jy901_debug.xdc` 用于 PL-only 硬件调试顶层，并在 SCL/SDA 上包含可选内部弱 pullup。
- 队友原始 zip 中的 pinout 可能不同；迁入集成工程时以本目录和 [../../docs/wiring.md](../../docs/wiring.md) 为准。
- 所有连接到 PL 的外部信号都按 3.3 V logic 处理。新增约束前，确认模块信号电平兼容 PYNQ-Z1。
