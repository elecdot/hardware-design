# rtl

这里存放 PL 侧自定义协议 IP 的可综合 RTL。

## 索引

| 路径 | 用途 |
|---|---|
| [axi_humidifier/](axi_humidifier/) | 从交接包迁移的 AXI-Lite 加湿器/LED 指示控制器。 |
| [axi_uart_spo2/](axi_uart_spo2/) | 从交接包迁移的 AXI-Lite UART SpO2/心率接收器。 |
| [dht11_axi/](dht11_axi/) | 从交接包迁移的 AXI-Lite DHT11 单总线温湿度 IP。 |
| [gree_ir_axi/](gree_ir_axi/) | 从交接包迁移的 TX-only AXI-Lite Gree IR AC 发射器。 |
| [i2c_mpu9250/](i2c_mpu9250/) | 用于 JY901/MPU9250 运动数据采样的 AXI-Lite I2C master IP。 |
| [tft_lcd_spi_axi/](tft_lcd_spi_axi/) | 从交接包迁移的 ST7789 TFT LCD AXI-Lite SPI 字节发送器。 |

每个自定义 IP 使用一个子目录。可行时，将协议核心、AXI wrapper 和共享辅助逻辑分开维护。
