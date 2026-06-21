# humidifier_demo

从队友交接包迁移的 PYNQ 侧加湿器指示 demo 文件。

## 文件

| 文件 | 用途 |
|---|---|
| [humidifier_driver.py](humidifier_driver.py) | 加湿器 AXI 寄存器的 MMIO 驱动。 |
| [demo_humidifier.py](demo_humidifier.py) | 软件湿度 demo。 |

首个集成路径使用 PS 侧控制：在 PYNQ 中读取 DHT11 湿度，然后写入 `SW_HUM` 等加湿器寄存器。
