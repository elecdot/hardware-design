# sim

Behavioral simulations and testbenches for RTL modules live here.

## Index

| Path | Purpose |
|---|---|
| [tb_axi_humidifier/](tb_axi_humidifier/) | Humidifier core and AXI register-path simulation migrated from handoff. |
| [tb_axi_uart_spo2/](tb_axi_uart_spo2/) | Placeholder for UART SpO2 regression tests to be added after source import. |
| [tb_dht11_axi/](tb_dht11_axi/) | DHT11 one-wire/AXI simulation material migrated from handoff. |
| [tb_i2c_mpu9250/](tb_i2c_mpu9250/) | I2C/JY901 sampler simulation with normal burst-read and address-NACK cases. |
| [tb_tft_lcd_spi_axi/](tb_tft_lcd_spi_axi/) | TFT LCD SPI core and AXI wrapper simulation migrated from handoff. |

Prefer small module-level simulations before packaging RTL into Vivado IP.
