# axi_humidifier

从队友交接包迁移的 AXI-Lite 加湿器指示控制器。该模块使用板载 LED 模拟加湿器状态。

## 文件

| 文件 | 用途 |
|---|---|
| [axi_humidifier_v1_0.v](axi_humidifier_v1_0.v) | AXI IP 顶层 wrapper。 |
| [axi_humidifier_v1_0_S00_AXI.v](axi_humidifier_v1_0_S00_AXI.v) | AXI4-Lite 寄存器 wrapper。 |
| [humidifier_core.v](humidifier_core.v) | 阈值、滞回、手动/软件湿度和 LED 控制核心。 |

## 说明

- 源码迁移时未修改 RTL 行为。
- 首个集成 demo 路径由 PS 控制：PYNQ 读取 DHT11 湿度，然后写入 `SW_HUM` 等加湿器 AXI 寄存器。
- 直接把 PL 侧 DHT11 接到加湿器仍属于后续可选验证工作。
