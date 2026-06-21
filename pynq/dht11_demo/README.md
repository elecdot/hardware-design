# dht11_demo

从队友交接包迁移的 PYNQ 侧 DHT11 demo 文件。

## 文件

| 文件 | 用途 |
|---|---|
| [dht11_driver.py](dht11_driver.py) | Direct MMIO DHT11 驱动。 |
| [dht11_test_read.py](dht11_test_read.py) | 简单读数测试脚本。 |

当前驱动默认使用单模块交接地址 `0x43C00000`。集成 overlay 代码应通过 `.hwh` /
`Overlay.ip_dict` 绑定 IP，或显式传入 Vivado 分配的 base address。
