# tb_axi_uart_spo2

UART SpO2 IP 的仿真材料。

交接包没有为 UART SpO2 IP 提供聚焦的模块级回归测试。该目录先放入 parser 级 smoke test，
后续再补齐完整 UART 波形和 AXI wrapper 覆盖。

## 文件

| 文件 | 用途 |
|---|---|
| [tb_spo2_frame_parser.v](tb_spo2_frame_parser.v) | 5 字节和 7 字节帧解析器 smoke test，带显式 PASS/ERROR 输出。 |

## 运行

在本目录下执行：

```powershell
iverilog -g2012 -o build/tb_spo2_frame_parser.vvp tb_spo2_frame_parser.v ../../rtl/axi_uart_spo2/spo2_frame_parser.v
vvp build/tb_spo2_frame_parser.vvp
```

预期 PASS 标记：

```text
tb_spo2_frame_parser PASS
```

建议首先检查：

- UART RX 是否按 9600 baud 时序接收字节。
- `STATUS`、`MEASURE`、`WAVE`、`FLAGS`、`RAW0` 和 `RAW1` 是否按文档更新。
