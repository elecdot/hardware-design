# rtl

Synthesizable RTL for custom PL-side protocol IP lives here.

## Index

| Path | Purpose |
|---|---|
| [axi_humidifier/](axi_humidifier/) | AXI-Lite humidifier/LED indicator controller migrated from handoff. |
| [axi_uart_spo2/](axi_uart_spo2/) | AXI-Lite UART SpO2/heart-rate receiver migrated from handoff. |
| [dht11_axi/](dht11_axi/) | AXI-Lite DHT11 one-wire temperature/humidity IP migrated from handoff. |
| [gree_ir_axi/](gree_ir_axi/) | TX-only AXI-Lite Gree IR AC transmitter migrated from handoff. |
| [i2c_mpu9250/](i2c_mpu9250/) | AXI-Lite I2C master IP for JY901/MPU9250 motion data sampling. |
| [tft_lcd_spi_axi/](tft_lcd_spi_axi/) | AXI-Lite SPI byte transmitter for ST7789 TFT LCD migrated from handoff. |

Add one subdirectory per custom IP. Keep protocol cores, AXI wrappers, and shared helper logic separated when practical.
