# axi_uart_spo2

从队友交接包迁移的 AXI-Lite UART SpO2/心率接收器。

## 文件

| 文件 | 用途 |
|---|---|
| [axi_uart_spo2_v1_0.v](axi_uart_spo2_v1_0.v) | AXI IP 顶层 wrapper。 |
| [axi_uart_spo2_v1_0_S00_AXI.v](axi_uart_spo2_v1_0_S00_AXI.v) | AXI4-Lite 寄存器 wrapper。 |
| [uart_rx.v](uart_rx.v) | UART 接收核心。 |
| [uart_tx.v](uart_tx.v) | UART 发送核心。 |
| [spo2_frame_parser.v](spo2_frame_parser.v) | 5 字节/7 字节 SpO2 帧解析器。 |

## 说明

- 源码迁移时未修改 RTL 行为。
- 集成目标引脚为 PMODB `uart_txd=W14` 和 `uart_rxd=Y14`。
- UART 默认使用 100 MHz 时钟生成 9600 baud。
- 仍需补充模块级回归测试。
