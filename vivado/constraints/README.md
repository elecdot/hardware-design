# constraints

Board-level XDC constraints for external PL ports live here.

## Index

| File | Purpose |
|---|---|
| [axi_i2c_jy901_package.xdc](axi_i2c_jy901_package.xdc) | Maps the packaged AXI/PYNQ I2C IP to PMODA `Y17` for `i2c_scl` and `Y16` for `i2c_sda`, both `LVCMOS33`, with optional weak internal pullups. |
| [dht11_pynq_z1.xdc](dht11_pynq_z1.xdc) | Maps DHT11 `dht11_0` to Arduino IO11 `R17`, `LVCMOS33`, with pullup. |
| [humidifier_leds_pynq_z1.xdc](humidifier_leds_pynq_z1.xdc) | Maps `humidifier_leds[3:0]` to PYNQ-Z1 board LEDs. |
| [i2c_jy901_pynq_z1.xdc](i2c_jy901_pynq_z1.xdc) | Maps JY901 I2C `i2c_scl` to PYNQ-Z1 Arduino SCL `P16` and `i2c_sda` to Arduino SDA `P15`, both `LVCMOS33`. |
| [integrated/sleep_monitor_pynq_z1.xdc](integrated/sleep_monitor_pynq_z1.xdc) | Planned integrated overlay pin allocation for TFT, JY901, UART SpO2, DHT11, Gree IR AC TX, and humidifier LEDs. |
| [jy901_debug.xdc](jy901_debug.xdc) | Constraints for `jy901_hw_debug_top.v`: 125 MHz `clk`, `resetn` on SW0, `led[3:0]`, and JY901 I2C on PMODA `Y17/Y16`, all `LVCMOS33`. |
| [spo2_pmodb_pynq_z1.xdc](spo2_pmodb_pynq_z1.xdc) | Maps UART SpO2 `uart_txd` to PMODB `W14` and `uart_rxd` to PMODB `Y14`. |
| [tft_lcd_pynq_z1.xdc](tft_lcd_pynq_z1.xdc) | Maps TFT LCD `lcd_scl/lcd_sda/lcd_res/lcd_dc/lcd_blk` to PMODA. |

Use only one pin-mapping XDC for a given top-level build. For the planned
integrated overlay, use [integrated/sleep_monitor_pynq_z1.xdc](integrated/sleep_monitor_pynq_z1.xdc)
and do not also apply conflicting single-module XDC files. For the existing
single-module JY901 AXI/PYNQ overlay project, use `axi_i2c_jy901_package.xdc`
and keep debug ILA XDC files disabled. `jy901_debug.xdc` is intended for the
PL-only hardware debug top and includes optional internal weak pullups on
SCL/SDA; external 3.3 V pullups are still recommended for real I2C operation.

Keep pin assignments out of RTL. Confirm every external signal is compatible with 3.3 V PYNQ-Z1 I/O before adding constraints.
