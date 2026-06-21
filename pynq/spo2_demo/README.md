# spo2_demo

从队友交接包迁移的 PYNQ 侧 UART SpO2 helper。

## 文件

| 文件 | 用途 |
|---|---|
| [spo2_mmio.py](spo2_mmio.py) | UART SpO2 IP 的 MMIO helper。 |

## 说明

- `Spo2Sample` 实现为普通 Python 类，使 helper 与已记录的 PYNQ Python 3.6 环境兼容。
- 集成 overlay 目标引脚为 PMODB `uart_txd=W14` 和 `uart_rxd=Y14`。
