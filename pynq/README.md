# pynq

这里存放 PYNQ 板端 demo 代码、驱动和 notebook。

## 索引

| 路径 | 用途 |
|---|---|
| [dht11_demo/](dht11_demo/) | 从交接包迁移的 DHT11 direct-MMIO demo 和驱动。 |
| [humidifier_demo/](humidifier_demo/) | 从交接包迁移的加湿器/LED AXI demo 和驱动。 |
| [ir_ac_demo/](ir_ac_demo/) | 从交接包迁移的 TX-only Gree IR AC MMIO 驱动和板级 smoke CLI。 |
| [jy901_demo/](jy901_demo/) | 在 PYNQ-Z1 上下载 bitstream 并 direct-MMIO 的最小 JY901 AXI I2C demo。 |
| [sleep_demo/](sleep_demo/) | 集成 overlay demo 骨架，绑定所有迁移驱动、更新 TFT，并由 PS 侧逻辑驱动加湿器寄存器。 |
| [spo2_demo/](spo2_demo/) | 从交接包迁移的 UART SpO2 MMIO helper。 |
| [tft_lcd_demo/](tft_lcd_demo/) | 从交接包迁移的 ST7789 TFT LCD AXI SPI 显示驱动和 demo。 |

当前 PYNQ-Z1 软件环境：

- Jupyter kernel：root 下的 `/opt/python3.6/bin/python3.6`，包含位于
  `/opt/python3.6/lib/python3.6/site-packages` 的 PYNQ Python package。
- SSH CLI 默认 `python3`：`/usr/bin/python3`，版本 3.4.3+，没有 Jupyter 使用的完整
  PYNQ package 环境。
- 旧版默认 `python`：Python 2.7.10。本 demo 路径不要使用它。

用与 Jupyter 等价的解释器运行板端 CLI demo：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 10
```
