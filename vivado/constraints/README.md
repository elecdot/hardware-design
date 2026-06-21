# constraints

这里存放外部 PL 端口的板级 XDC 约束。

## 索引

| 文件 | 用途 |
|---|---|
| [axi_i2c_jy901_package.xdc](axi_i2c_jy901_package.xdc) | 将已打包 AXI/PYNQ I2C IP 映射到 PMODA：`i2c_scl` 为 `Y17`、`i2c_sda` 为 `Y16`，均为 `LVCMOS33`，可选弱内部 pullup。 |
| [dht11_pynq_z1.xdc](dht11_pynq_z1.xdc) | 将 DHT11 `dht11_0` 映射到 Arduino IO11 `R17`，`LVCMOS33`，带 pullup。 |
| [humidifier_leds_pynq_z1.xdc](humidifier_leds_pynq_z1.xdc) | 将 `humidifier_leds[3:0]` 映射到 PYNQ-Z1 板载 LED。 |
| [i2c_jy901_pynq_z1.xdc](i2c_jy901_pynq_z1.xdc) | 将 JY901 I2C `i2c_scl` 映射到 PYNQ-Z1 Arduino SCL `P16`，`i2c_sda` 映射到 Arduino SDA `P15`，均为 `LVCMOS33`。 |
| [integrated/sleep_monitor_pynq_z1.xdc](integrated/sleep_monitor_pynq_z1.xdc) | 计划中的集成 overlay 引脚分配，覆盖 TFT、JY901、UART SpO2、DHT11、Gree IR AC TX 和加湿器 LED。 |
| [jy901_debug.xdc](jy901_debug.xdc) | `jy901_hw_debug_top.v` 的约束：125 MHz `clk`、SW0 上的 `resetn`、`led[3:0]`，以及位于 PMODA `Y17/Y16` 的 JY901 I2C，均为 `LVCMOS33`。 |
| [spo2_pmodb_pynq_z1.xdc](spo2_pmodb_pynq_z1.xdc) | 将 UART SpO2 `uart_txd` 映射到 PMODB `W14`，`uart_rxd` 映射到 PMODB `Y14`。 |
| [tft_lcd_pynq_z1.xdc](tft_lcd_pynq_z1.xdc) | 将 TFT LCD `lcd_scl/lcd_sda/lcd_res/lcd_dc/lcd_blk` 映射到 PMODA。 |

同一个顶层构建只能使用一份针对同一信号的 pin-mapping XDC。计划中的集成 overlay 使用
[integrated/sleep_monitor_pynq_z1.xdc](integrated/sleep_monitor_pynq_z1.xdc)，不要再同时应用冲突的单模块 XDC。
现有单模块 JY901 AXI/PYNQ overlay 工程使用 `axi_i2c_jy901_package.xdc`，并保持 debug ILA XDC 禁用。
`jy901_debug.xdc` 用于 PL-only 硬件调试顶层，并在 SCL/SDA 上包含可选内部弱 pullup；
真实 I2C 运行仍建议使用外部 3.3 V pullup。

引脚分配不要写进 RTL。新增约束前，确认每个外部信号都兼容 PYNQ-Z1 的 3.3 V I/O。
