# Wiring

物理模块接线和电压说明。

## 计划中的集成 Overlay 引脚分配

这些分配是最终集成 overlay 的目标。只有当匹配的集成 XDC、`.bit`、`.hwh`
和 PYNQ driver smoke test 证据存在时，才算完成板级验证。

| 模块 | 信号 | PYNQ-Z1 pin/header | 说明 |
|---|---|---|---|
| TFT LCD | `lcd_scl` | PMODA `Y18` | 集成构建中 PMODA 预留给 TFT LCD。 |
| TFT LCD | `lcd_sda` | PMODA `Y19` | SPI MOSI，write-only display path。 |
| TFT LCD | `lcd_res` | PMODA `Y16` | Active-low display reset。 |
| TFT LCD | `lcd_dc` | PMODA `Y17` | `0` command，`1` data。 |
| TFT LCD | `lcd_blk` | PMODA `U18` | Backlight enable。 |
| JY901 | `i2c_scl` | Arduino SCL `P16` | 使用 3.3 V pullup；集成构建中不要使用 PMODA JY901 XDC。 |
| JY901 | `i2c_sda` | Arduino SDA `P15` | Open-drain I2C data。 |
| UART SpO2 | `uart_txd` | PMODB pin 1, `W14` | 课程教学指南列为 `PMODB_1/JB1_P/W14`；板测确认外部模块的 RX/TX 标签需要按交叉接线理解。 |
| UART SpO2 | `uart_rxd` | PMODB pin 2, `Y14` | 课程教学指南列为 `PMODB_2/JB1_N/Y14`；如果 BPM/SpO2 一直为 `NA`，先交换两根 UART 信号线，再考虑修改 RTL。 |
| DHT11 | `dht11_0` | Arduino IO11 `R17` | 带 pullup 的双向 one-wire DATA。 |
| Humidifier | `humidifier_leds[3:0]` | Board LEDs `R14/P14/N16/M14` | LED 输出模拟 actuator；不要直接驱动负载。 |
| Gree IR AC TX | `ir_pwm` | Arduino `ck_io[0]`, `T14` | 首次集成为 TX-only。使用 IR 发射模块或驱动电路；不要从 PL 直接驱动裸 IR LED。 |

所有连接到 PL 的信号都必须是 3.3 V logic。如果模块由 5 V 供电，
需要确认其面向 FPGA 的信号引脚仍为 3.3 V TTL，或增加 level shifting。

UART 链路必须共地。集成板测使用的 SpO2 模块，只有在相对模块标注反接 RX/TX 后才确认工作。

IR 发射模块必须与 PYNQ-Z1 共地。如果发射器由外部电源供电，连接 `ir_pwm` 前必须确认其 `IN/SIG` 引脚接受 3.3 V logic。

## Gree IR AC Transmitter

首个集成目标：

| IR transmitter | PYNQ-Z1 | 说明 |
|---|---|---|
| VCC | 3V3 或外部模块电源 | 如果外部供电，确认模块输入仍兼容 3.3 V。 |
| GND | GND | 必须共地。 |
| IN / SIG | Arduino `ck_io[0]`, `T14` | 由 `gree_ir_axi_v1_0` 的 `ir_pwm` 驱动。 |

交接包的独立测试确认，实验室 Gree AC 会响应七个 Gree YB0F2 preset 命令。
后续集成 overlay 板级 smoke 又确认，真实实验室 AC 会响应 `power_on`、`power_off` 和 `temp_26`。

在实验室搭建中，IR 发射器需要距离 AC 接收头约 20 cm 以内才能可靠响应。
如果 AXI status 报告 `done=true/error=false` 但 AC 没有反应，先把发射器移近接收头并调整角度，
再考虑修改 RTL 或软件。

## JY901 I2C Module

PYNQ-Z1 PL I/O 只使用 3.3 V 接线。

### 当前 AXI/PYNQ Overlay 和 PL Debug 接线

当前 Vivado overlay/debug 工程使用 PMODA 引脚：

| JY901 | PYNQ-Z1 | 说明 |
|---|---|---|
| VCC | 3V3 | 当 SCL/SDA 连接到 PL 引脚时，不要用 5 V 为该 I2C 连接供电。 |
| GND | GND | 必须共地。 |
| SCL | PMODA `Y17` | 增加或确认 4.7 k pullup 到 3.3 V。 |
| SDA | PMODA `Y16` | 增加或确认 4.7 k pullup 到 3.3 V。 |

约束文件：

- AXI/PYNQ overlay：[../vivado/constraints/axi_i2c_jy901_package.xdc](../vivado/constraints/axi_i2c_jy901_package.xdc)。
- PL-only debug top：[../vivado/constraints/jy901_debug.xdc](../vivado/constraints/jy901_debug.xdc)。

### 旧 Arduino Header 映射

[../vivado/constraints/i2c_jy901_pynq_z1.xdc](../vivado/constraints/i2c_jy901_pynq_z1.xdc)
将 `i2c_scl` 映射到 Arduino SCL `P16`，将 `i2c_sda` 映射到 Arduino SDA `P15`。
只有在构建目标明确是 Arduino header 时才使用它，不要与上面的 PMODA 映射同时使用。

PYNQ-Z1 上电时不要热插拔该模块。
