# Handoff And Integration

本文档记录从队友交接包迁移模块到本仓库，并将它们集成进 Vivado/PYNQ 系统的计划和状态。
目标是把零散交接材料收敛为可审查、可仿真、可打包、可上板的工程路径。

## 范围

迁移模块：

- UART SpO2 AXI IP
- DHT11 AXI IP
- TFT LCD SPI AXI IP
- AXI Humidifier/LED IP
- TX-only Gree IR AC AXI IP
- PC socket/Excel demo 参考代码

不直接采用的内容：

- 交接包中的临时工程输出、cache、run directory、机器路径和未验证生成物。
- 与当前硬件范围无关的 IR RX capture，除非后续作为独立验证工具使用。
- 旧 Excel-only PC server 作为最终验收入口。

## 迁移原则

1. 以 `rtl/`、`pynq/`、`pc_server/`、`docs/` 和 `sim/` 中的跟踪文件作为新权威源。
2. 不在 Vivado 生成目录中手改源码。
3. 迁移时先保持行为不变，再用小测试建立证据。
4. 寄存器映射、接线、协议和端口命名发生变化时，同步更新文档。
5. 不声称硬件功能通过，除非有仿真、板测或用户确认的真实测量。

## 当前迁移状态

| 模块 | RTL | 仿真 | IP 打包 | PYNQ/PC | 集成状态 |
|---|---|---|---|---|---|
| JY901 I2C | 已实现 | 已有 JY901 sampler/top/timeout 仿真 | 已有 package/overlay 工程 | `pynq/jy901_demo/` | 集成板端 demo 通过 |
| DHT11 | 已迁入 `rtl/dht11_axi/` | `tb_dht11_onewire_smoke PASS` | 已打包并集成 | `pynq/dht11_demo/` | 集成板端 demo 通过 |
| UART SpO2 | 已迁入 `rtl/axi_uart_spo2/` | `tb_spo2_frame_parser PASS` | 已打包并集成 | `pynq/spo2_demo/` | 集成板端 demo 通过，RX/TX 需交叉 |
| TFT LCD | 已迁入 `rtl/tft_lcd_spi_axi/` | `tb_spi_lcd_master PASS`、`tb_tft_lcd_spi_axi PASS` | 已打包并集成 | `pynq/tft_lcd_demo/` | 集成板端 demo 通过 |
| Humidifier | 已迁入 `rtl/axi_humidifier/` | `tb_humidifier_core PASS`、`tb_axi_humidifier PASS` | 已打包并集成 | `pynq/humidifier_demo/` | PS-controlled 集成 demo 通过 |
| Gree IR AC TX | 已迁入 `rtl/gree_ir_axi/` | `tb_gree_ir_axi PASS` | 已打包并集成 | `pynq/ir_ac_demo/` | `system_v0_2` 中板测通过，真实 AC 响应已确认 |
| PC software | 旧 socket/Excel 作为参考 | PC self-tests | 不适用 | `pc_server/` | 四消息协议和 dashboard 第一版已实现 |

## 目标仓库布局

| 路径 | 内容 |
|---|---|
| `rtl/<ip>/` | 权威 RTL 源码。 |
| `sim/tb_<ip>/` | 模块级 testbench 和运行说明。 |
| `pynq/<module>_demo/` | 板端 driver、helper 和 smoke CLI。 |
| `pc_server/` | PC socket service、classifier adapter、policy、storage、dashboard。 |
| `vivado/ip_repo/` | 可复用已打包 IP。 |
| `vivado/project/` | Vivado 打包、overlay 和 debug 工程。 |
| `vivado/constraints/` | 板级 XDC。 |
| `docs/` | 协议、寄存器、接线、测试计划和集成记录。 |

## 分阶段执行

### Phase 1: Source Migration

每个模块迁移：

1. 将 RTL 放入 `rtl/<ip>/`。
2. 将 testbench 放入 `sim/tb_<ip>/`。
3. 将 PYNQ driver/demo 放入 `pynq/<module>_demo/`。
4. 增加或更新本地 README。
5. 把寄存器映射补入 [register_map.md](register_map.md)。
6. 把接线和电压约束补入 [wiring.md](wiring.md)。

### Phase 2: Module Regression

目标是为每个迁移模块提供至少一个可重复仿真或 smoke test：

```text
tb_humidifier_core PASS
tb_axi_humidifier PASS
tb_spi_lcd_master PASS
tb_tft_lcd_spi_axi PASS
tb_dht11_onewire_smoke PASS
tb_spo2_frame_parser PASS
tb_gree_ir_axi PASS
```

原则：

- testbench 必须输出清晰 PASS/FAIL。
- 对没有完整 AXI testbench 的模块，先补最小 parser/core smoke，再计划完整覆盖。
- 不能用“源码已迁移”替代仿真或板测证据。

### Phase 3: IP Packaging

把可复用 IP 打包到 `vivado/ip_repo/`，详细流程见 [ip_packaging_manual.md](ip_packaging_manual.md)。

检查点：

- `component.xml` 和 `xgui/` 存在。
- AXI4-Lite interface、clock、reset 和 memory map 可见。
- 外部物理端口未被误归类。
- package 内不包含板级 XDC。
- source ownership 可追溯到 `rtl/<ip>/`。

### Phase 4: Integrated Vivado Overlay

目标 overlay：`system_v0_2`。

预期 IP address map：

| IP instance | Base | Notes |
|---|---:|---|
| `axi_i2c_jy901_v1_0_0` | `0x4000_0000` | JY901 I2C |
| `axi_humidifier_v1_0_0` | `0x4000_1000` | Humidifier/LED |
| `tft_lcd_spi_axi_v1_0_0` | `0x4000_2000` | TFT LCD |
| `dht11_axi_v1_0_0` | `0x4000_3000` | DHT11 |
| `axi_uart_spo2_v1_0_0` | `0x4000_4000` | UART SpO2 |
| `gree_ir_axi_v1_0_0` | `0x4000_5000` | Gree IR AC TX |

集成 XDC：

- TFT LCD：PMODA
- JY901：Arduino `P16/P15`
- UART SpO2：PMODB `W14/Y14`
- DHT11：Arduino IO11 `R17`
- Humidifier：板载 LED
- Gree IR AC TX：Arduino `ck_io[0]` / `T14`

导出 artifact：

```text
vivado/gen/system_v0_2.bit
vivado/gen/system_v0_2.hwh
vivado/gen/system_v0_2.tcl
```

### Phase 5: PYNQ Board Bring-Up

本地集成 smoke 入口：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 30 \
  --interval 1.0
```

检查：

- PYNQ 能加载 bitstream。
- 可通过 `.hwh` 或 static fallback 绑定 IP。
- JY901、DHT11、SpO2、TFT、加湿器和 IR driver 不因 import 或地址问题崩溃。
- TFT 能显示 dashboard。
- 加湿器 LED/status 路径可被 PS 控制。
- IR AC TX 能返回 `done=true/error=false`；真实 AC 响应需人工观察。

### Phase 6: PC/PYNQ Software Integration

最终软件路径：

```text
PYNQ board_client.py -> PC dashboard_server.py
```

协议 cycle：

```text
sensor_data -> sleep_result -> control_command -> control_status
```

详细计划和运行步骤见：

- [protocol.md](protocol.md)
- [software_integration_plan.md](software_integration_plan.md)
- [software_integration_runbook.md](software_integration_runbook.md)

## 交接包注意事项

### DHT11

- DATA 是 bidirectional one-wire，需要 pullup。
- 集成 XDC 期望外部 BD port 为 `dht11_0`。
- Icarus 仿真使用 `IOBUF` stub，Vivado 综合使用 primitive。

### UART SpO2

- 默认 9600 baud。
- 板测确认模块侧 RX/TX 标注需要按交叉接线处理。
- 默认先使用 5-byte frame mode，7-byte mode 需实物确认。

### TFT LCD

- 当前 RTL 没有 `CS` 或 `MISO`。
- 如果显示屏带 `CS`，需要硬件拉到有效态或后续扩展 RTL。
- 首版 UI 由 PYNQ 绘制完整 dashboard 后只更新数值区域。

### Humidifier

- 首版集成使用 PS-controlled path：PYNQ 读取 DHT11 湿度后写加湿器 AXI register。
- 直接 PL DHT11-to-humidifier 接线是后续可选验证，不是当前课堂 demo 必需项。

### Gree IR AC

- 首版为 TX-only。
- 支持七个已验证 preset。
- 真实 AC 响应与距离/角度强相关；实验室确认约 20 cm 内更可靠。
- `sent=true` 不是 AC 状态反馈。

## 验收边界

可以声称：

- 某模块有仿真通过：只有 testbench 输出 PASS 时。
- 某模块有板级通过：只有实际板测或用户确认测量时。
- `system_v0_2` 集成 overlay 可用于课堂 demo：已有匹配 bit/hwh/tcl、板端 demo 和 IR 真实响应证据。
- PC/PYNQ software first pass 可用于课堂 demo：已有 self-tests、fake client 和真实 board socket evidence。

不能声称：

- 睡眠状态是临床诊断。
- `sent=true` 等于空调真实状态改变。
- 未运行真实 board client 时，PC-integrated operation 已完成。
- 旧 handoff 工程输出是权威设计源。

## 后续工作

- 课堂正式采集前校正 PYNQ 系统时间。
- 在实验室条件允许时重新运行 dashboard + real board client 完整闭环。
- 为最终报告保存 dashboard 截图、PYNQ 输出和四类 JSONL。
- 后续可考虑 IR RX 或执行器反馈，但课堂 demo 前不加入 AC replay。
