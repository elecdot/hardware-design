# vivado/gen

这里存放供本地 PYNQ overlay 使用的临时 Vivado 导出 artifact。

本目录中的构建 artifact 被 Git 忽略。把 `.bit` 复制到这里便于本地测试，
但除非同时导出了匹配的 `.hwh`，否则不要声称 overlay 已可用于 PYNQ。

## Artifact 索引

| 文件 | 状态 | 说明 |
|---|---|---|
| [system_v0_2.bit](system_v0_2.bit) | 当前集成 demo artifact | 加入 TX-only Gree IR AC 后导出的 bitstream。 |
| [system_v0_2.hwh](system_v0_2.hwh) | 当前集成 demo artifact | 与 `system_v0_2.bit` 匹配；PYNQ overlay 绑定 MMIO driver 时应同时使用。 |
| [system_v0_2.tcl](system_v0_2.tcl) | 当前集成 demo artifact | 从 Block Design `system_v0_1` 导出的 Tcl。 |
| [system_v0_1.bit](system_v0_1.bit) | 历史集成 artifact | 加入 IR AC 前的集成导出版本。 |
| [system_v0_1.hwh](system_v0_1.hwh) | 历史集成 artifact | 与 `system_v0_1.bit` 匹配。 |
| [system_v0_1.tcl](system_v0_1.tcl) | 历史集成 artifact | 从 Block Design `system_v0_1` 导出的历史 Tcl。 |
| [jy901_axi_package.bit](jy901_axi_package.bit) | 单模块历史 artifact | 仅有 bitstream；缺少同名 `.hwh` 时不应作为完整 PYNQ overlay 交付。 |

## `system_v0_2` 地址映射

`system_v0_2.hwh` 中确认的 AXI address map：

| Instance | Base | High |
|---|---:|---:|
| `axi_i2c_jy901_v1_0_0` | `0x4000_0000` | `0x4000_0FFF` |
| `axi_humidifier_v1_0_0` | `0x4000_1000` | `0x4000_1FFF` |
| `tft_lcd_spi_axi_v1_0_0` | `0x4000_2000` | `0x4000_2FFF` |
| `dht11_axi_v1_0_0` | `0x4000_3000` | `0x4000_3FFF` |
| `axi_uart_spo2_v1_0_0` | `0x4000_4000` | `0x4000_4FFF` |
| `gree_ir_axi_v1_0_0` | `0x4000_5000` | `0x4000_5FFF` |

## 使用规则

- PYNQ 端加载时，`.bit` 和 `.hwh` 应来自同一次 Vivado 构建，并保持同名或显式传入匹配路径。
- 导出新 overlay 后，同步更新本 README、[../project/README.md](../project/README.md) 和相关 PYNQ driver fallback 地址。
- 不要把只有 `.bit`、没有 `.hwh` 的文件描述成完整 overlay。
