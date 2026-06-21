# sim

这里存放 RTL 模块的行为仿真和 testbench。

## 索引

| 路径 | 用途 |
|---|---|
| [tb_axi_humidifier/](tb_axi_humidifier/) | 从交接包迁移的加湿器核心和 AXI 寄存器路径仿真。 |
| [tb_axi_uart_spo2/](tb_axi_uart_spo2/) | UART SpO2 回归测试占位，等待源码导入后补齐。 |
| [tb_dht11_axi/](tb_dht11_axi/) | 从交接包迁移的 DHT11 单总线/AXI 仿真材料。 |
| [tb_gree_ir_axi/](tb_gree_ir_axi/) | TX-only Gree IR AC AXI 预设/start/done/error 回归。 |
| [tb_i2c_mpu9250/](tb_i2c_mpu9250/) | I2C/JY901 sampler 仿真，覆盖正常 burst-read 和 address-NACK 场景。 |
| [tb_tft_lcd_spi_axi/](tb_tft_lcd_spi_axi/) | 从交接包迁移的 TFT LCD SPI 核心和 AXI wrapper 仿真。 |

在把 RTL 打包进 Vivado IP 之前，优先补齐小型模块级仿真。
