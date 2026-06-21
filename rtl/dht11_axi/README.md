# dht11_axi

从队友交接包迁移的 AXI-Lite DHT11 单总线温湿度 IP。

## 文件

| 文件 | 用途 |
|---|---|
| [dht11_axi_v1_0.v](dht11_axi_v1_0.v) | 带外部 `dht11` 单总线端口的 AXI IP 顶层 wrapper。 |
| [dht11_axi_v1_0_S00_AXI.v](dht11_axi_v1_0_S00_AXI.v) | AXI4-Lite 寄存器 wrapper。 |
| [dht11_onewire.v](dht11_onewire.v) | DHT11 单总线时序核心。 |

## 说明

- 源码迁移时未修改 RTL 行为。
- 交接包未包含完整的独立 `dht11_axi` 已打包 IP 目录，因此该 IP 应从已跟踪 RTL 重新打包。
- 集成目标引脚为 Arduino IO11 `R17`，见 [../../docs/wiring.md](../../docs/wiring.md)。
- 集成 XDC 当前约束的外部 BD 端口名为 `dht11_0`；要么保持该 BD 外部名称，要么在同一审查范围内更新 XDC。
- DATA 双向线应保持为顶层 inout，并使用 pullup。
