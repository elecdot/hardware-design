# Test Plan

本文档记录仿真、IP 打包、Vivado 集成、板端 smoke 和 PC/PYNQ 端到端测试计划与证据。
在没有对应证据前，不要声称模块或系统“已验证”。

## Final Integrated Overlay Acceptance Target

当前课堂 demo 目标是 `system_v0_2`：

- Vivado 导出匹配的 `system_v0_2.bit`、`system_v0_2.hwh` 和 `system_v0_2.tcl`。
- 集成 pin plan：PMODA 用于 TFT LCD，Arduino `P16/P15` 用于 JY901 I2C，
  PMODB `W14/Y14` 用于 UART SpO2，Arduino IO11 `R17` 用于 DHT11，
  Arduino `ck_io[0]` / `T14` 用于 Gree IR AC TX，板载 LED 用于加湿器状态。
- PYNQ runtime 能用共享 driver suite 读取/更新：JY901 read/status、DHT11 read、UART SpO2 read、TFT update、humidifier status/control、IR AC TX。
- PC/PYNQ 四消息软件闭环可运行：`sensor_data -> sleep_result -> control_command -> control_status`。

正式 demo 前建议重新跑：

1. PC-only self-tests 和 fake client。
2. PYNQ synthetic：`board_client.py --dry-run` 对接 PC service。
3. Integrated driver：`board_client.py` 使用 `system_v0_2.bit/.hwh` 和真实 driver。
4. Dashboard demo：运行 `dashboard_server.py`，打开 Web console，确认四类 record 刷新。

## PC/PYNQ Software Evidence

已有第一版软件证据：

```text
protocol_selftest PASS
classifier_adapter_selftest PASS
sleep_classifier_selftest PASS
comfort_policy_selftest PASS
state_storage_selftest PASS
service_selftest PASS
socket_service_selftest PASS
fake_pynq_client_selftest PASS
dashboard_server_selftest PASS
```

`pc_server/service_selftest.py` 覆盖 PC-side IR cooldown regression：

- cooldown 只在 board 返回 `control_status.applied.ir_ac.sent=true` 后消耗；
- `ir_ac_missing` 或 `ir_ac_error` 不消耗正常 IR cooldown；
- 新 board run 从 `sample_id=1` 开始时重置 policy runtime state。

`pc_server/dashboard_server_selftest.py` 覆盖 dashboard entry bridge：

- static asset serving；
- pending manual command；
- `sensor_data -> sleep_result/control_command -> control_status` 四消息 flow。

已有真实 PYNQ socket evidence：

- 90-sample board run 记录在 `pc_server/records/pynq_integration_smoke/`。
- PC 记录了 board-originated `sensor_data`。
- PC 为每个 sample 发送 `sleep_result` 和 `control_command`。
- PYNQ 返回 `control_status`。
- JY901-only transient failure 不应强制 HR/SpO2 主 `data_valid` 失效。

正式报告截图前，优先刷新一次 `dashboard_server.py` 加真实 PYNQ `board_client.py` 的运行证据。

## Migrated Handoff Module Regression

### Phase2 Smoke Results

Date：2026-06-02。Tool：Icarus Verilog (`iverilog` + `vvp`)。

已观察 PASS：

```text
tb_humidifier_core PASS
tb_axi_humidifier PASS
tb_spi_lcd_master PASS
tb_tft_lcd_spi_axi PASS
tb_dht11_onewire_smoke PASS data_valid=37001900
tb_spo2_frame_parser PASS
```

覆盖：

- Humidifier core threshold/manual behavior 和 AXI register path。
- TFT SPI byte transmitter 和 AXI wrapper byte-send path。
- DHT11 one-wire valid-frame decode：55% RH、25 C，Icarus `IOBUF` stub。
- SpO2 frame parser：已知 5-byte 和 7-byte frame。

### Phase3 IP Packaging Static Validation

已检查 reusable package：

| IP package | Package files | AXI metadata | Parameters | External ports |
|---|---|---|---|---|
| `vivado/ip_repo/axi_humidifier/` | `component.xml`, `xgui/`, `src/` 存在；source 匹配 `rtl/axi_humidifier/` | `aximm/aximm_rtl`, `s00_axi`, `s00_axi_aclk`, `s00_axi_aresetn`, 4096-byte range | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5`, `CLK_FREQ_HZ=100000000` | `humidity_hw_valid`, `humidity_hw[7:0]`, `humidifier_led`, `humidifier_leds[3:0]` |
| `vivado/ip_repo/tft_lcd_spi_axi/` | `component.xml`, `xgui/`, `src/` 存在；source 匹配 `rtl/tft_lcd_spi_axi/` | `aximm/aximm_rtl`, `s00_axi`, `s00_axi_aclk`, `s00_axi_aresetn`, 4096-byte range | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5` | `lcd_scl`, `lcd_sda`, `lcd_res`, `lcd_dc`, `lcd_blk` |
| `vivado/ip_repo/dht11_axi/` | `component.xml`, `xgui/`, `src/` 存在；source 匹配 `rtl/dht11_axi/` | `aximm/aximm_rtl`, `s00_axi`, `s00_axi_aclk`, `s00_axi_aresetn`, 4096-byte range | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=4` | RTL/IP port 为 `dht11`；集成 XDC 期望 BD external port `dht11_0` |
| `vivado/ip_repo/axi_uart_spo2/` | `component.xml`, `xgui/`, `src/` 存在；source 匹配 `rtl/axi_uart_spo2/` | `aximm/aximm_rtl`, `s00_axi`, `s00_axi_aclk`, `s00_axi_aresetn`, 4096-byte range | `C_BPS=9600`, `C_SYS_CLK_FRE=100000000`, `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5` | `uart_rxd`, `uart_txd`, `irq` |

说明：

- 旧 root-level JY901 IP package 仍存在于 `vivado/ip_repo/`，由现有 JY901 overlay/debug flow 使用。
- DHT11 package source 包含 Vivado `IOBUF` primitive。
- board-level XDC 不应被包含在 reusable IP synthesis file set 中。

## Phase4 Integrated Block Design Validation

原始集成工程：`vivado/project/system_v0_1/system_v0_1.xpr`。

`system_v0_1` address map：

| IP instance | Address | Range | Notes |
|---|---:|---:|---|
| `axi_i2c_jy901_v1_0_0` | `0x4000_0000` | 4K | External `i2c_scl/i2c_sda` |
| `axi_humidifier_v1_0_0` | `0x4000_1000` | 4K | `humidity_hw_valid` 和 `humidity_hw[7:0]` 由 `xlconstant` 绑定；external `humidifier_leds[3:0]` |
| `tft_lcd_spi_axi_v1_0_0` | `0x4000_2000` | 4K | External `lcd_scl/lcd_sda/lcd_res/lcd_dc/lcd_blk` |
| `dht11_axi_v1_0_0` | `0x4000_3000` | 4K | IP port `dht11` 导出为 top-level `dht11_0` |
| `axi_uart_spo2_v1_0_0` | `0x4000_4000` | 4K | External `uart_rxd/uart_txd`；polling-first path |

`system_v0_2` 进一步加入 IR AC：

| IP instance | Address | Range | Notes |
|---|---:|---:|---|
| `gree_ir_axi_v1_0_0` | `0x4000_5000` | 4K | External `ir_pwm` on `T14` |

重要 pin placement evidence：

| Signal | Package pin | Evidence |
|---|---|---|
| `lcd_scl` | `Y18` | `system_v0_1_wrapper_io_placed.rpt` |
| `lcd_sda` | `Y19` | `system_v0_1_wrapper_io_placed.rpt` |
| `lcd_res` | `Y16` | `system_v0_1_wrapper_io_placed.rpt` |
| `lcd_dc` | `Y17` | `system_v0_1_wrapper_io_placed.rpt` |
| `lcd_blk` | `U18` | `system_v0_1_wrapper_io_placed.rpt` |
| `i2c_scl` | `P16` | `system_v0_1_wrapper_io_placed.rpt` |
| `i2c_sda` | `P15` | `system_v0_1_wrapper_io_placed.rpt` |
| `uart_txd` | `W14` | `system_v0_1_wrapper_io_placed.rpt` |
| `uart_rxd` | `Y14` | `system_v0_1_wrapper_io_placed.rpt` |
| `dht11_0` | `R17` | `system_v0_1_wrapper_io_placed.rpt` |
| `humidifier_leds[3:0]` | `R14/P14/N16/M14` | `system_v0_1_wrapper_io_placed.rpt` |
| `ir_pwm` | `T14` | `system_v0_1_wrapper_io_placed.rpt` for `system_v0_2` |

导出 artifact：

```text
vivado/gen/system_v0_1.bit
vivado/gen/system_v0_1.hwh
vivado/gen/system_v0_2.bit
vivado/gen/system_v0_2.hwh
vivado/gen/system_v0_2.tcl
```

## Phase5 Integrated Board Runtime Smoke

本地板端 smoke 使用 `pynq/sleep_demo/integrated_demo.py`、集成 bit/hwh 和 static address-map fallback。

典型命令：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 30 \
  --interval 1.0 \
  --metadata-source auto \
  --tft-clkdiv 50 \
  --spo2-frame-len 5
```

已观察：

- JY901 返回有效 sample，`jy901_status="OK"` 且 `data_valid=1`。
- DHT11 返回温湿度值，例如约 `27 C`、`15-16% RH`。
- UART SpO2 在修正 RX/TX 物理方向后返回有效 5-byte/polling sample。
- TFT 初始化并更新 dashboard。
- 加湿器 status/control 路径参与循环。
- 翻身 count 在共享日志中保持 `0`；JY901 数据有效，但尚未做专门翻身动作验证。

## Gree IR AC TX

相关路径：

- [../rtl/gree_ir_axi/](../rtl/gree_ir_axi/)
- [../sim/tb_gree_ir_axi/](../sim/tb_gree_ir_axi/)
- [../pynq/ir_ac_demo/](../pynq/ir_ac_demo/)
- `vivado/ip_repo/ir_ac_axi/`
- `vivado/gen/system_v0_2.bit/.hwh/.tcl`

模块回归：

```powershell
iverilog -g2012 -o E:\tmp\tb_gree_ir_axi.vvp `
  sim\tb_gree_ir_axi\tb_gree_ir_axi.v `
  rtl\gree_ir_axi\gree_ir_core.v `
  rtl\gree_ir_axi\gree_ir_axi_v1_0_S00_AXI.v `
  rtl\gree_ir_axi\gree_ir_axi_v1_0.v
vvp E:\tmp\tb_gree_ir_axi.vvp
```

观察 PASS：

```text
tb_gree_ir_axi PASS
```

IP packaging evidence：

| Item | Evidence |
|---|---|
| VLNV | `xilinx.com:user:gree_ir_axi_v1_0:1.0` |
| Packaged files | `component.xml`, `xgui/gree_ir_axi_v1_0_v1_0.tcl`, `src/` RTL files present |
| Source ownership | Packaged HDL SHA256 匹配 `rtl/gree_ir_axi/` 中 `gree_ir_core.v`、`gree_ir_axi_v1_0_S00_AXI.v` 和 `gree_ir_axi_v1_0.v` |
| AXI metadata | `s00_axi` `aximm/aximm_rtl` slave，关联 `s00_axi_aclk` 和 active-low `s00_axi_aresetn` |
| Memory map | `reg0` base `0x0`，range `4096`，width `32` |
| Parameters | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5`, `CORE_CLK_FREQ=100000000`, `CORE_CLK_1US=100`, `CORE_CARRIER_HZ=38000` |
| External port | `ir_pwm` output 存在；IP package 内未嵌入 board pin constraint |

集成 overlay evidence：

| Item | Evidence |
|---|---|
| BD Tcl IP catalog | `system_v0_2.tcl` 包含 `xilinx.com:user:gree_ir_axi_v1_0:1.0` |
| New IP instance | `.hwh` 中存在 `gree_ir_axi_v1_0_0`，VLNV 为 `xilinx.com:user:gree_ir_axi_v1_0:1.0` |
| Address map | `.hwh` range `0x40005000..0x40005FFF`；Tcl 分配 `0x40005000` range `0x1000` |
| AXI connection | Tcl 将 `gree_ir_axi_v1_0_0/s00_axi` 连接到 `ps7_0_axi_periph/M05_AXI` |
| Clock/reset | Tcl 将 IR IP 连接到 `processing_system7_0/FCLK_CLK0` 和 `rst_ps7_0_50M/peripheral_aresetn` |
| External port | `.hwh` 和 wrapper 暴露 output `ir_pwm` 并连接到 `gree_ir_axi_v1_0_0/ir_pwm` |
| IO placement | `ir_pwm` 放在 `T14`，`LVCMOS33`，drive `8`，slew `SLOW` |
| DRC/route/timing | routed DRC 0 violations，route errors 0，timing met |
| Bitstream | `write_bitstream completed successfully`，`system_v0_2.bit` 非空 |

板端 smoke：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --base-addr 0x40005000 \
  --command temp_26 \
  --timeout 15.0
```

关键字段：

| Phase | Key fields |
|---|---|
| Before | `busy=false`, `done=false`, `error=false`, `preset=1`, `command=power_on`, `raw_status=0` |
| After | `busy=false`, `done=true`, `error=false`, `preset=5`, `command=temp_26`, `raw_status=2` |

结论：TX-only Gree IR AC 硬件集成对 `system_v0_2` 已接受并关闭。

## 单模块后续测试项

### DHT11 AXI IP

目标：

- DHT11 frame simulation 输出显式 PASS/FAIL。
- `DHT11_DATA` 按文档顺序解码 humidity 和 temperature byte。
- 板端读数在 1 到 2 秒间隔下稳定更新。

### AXI Humidifier IP

目标：

- 复现 `tb_humidifier_core PASS` 和 `tb_axi_humidifier PASS`。
- PYNQ 读取 DHT11 湿度并写 `SW_HUM`。
- `pynq/sleep_demo/integrated_demo.py` 中 LED/status 反映 humidifier path。

### TFT LCD SPI AXI IP

目标：

- SPI byte transmitter 和 AXI wrapper 仿真输出 PASS/FAIL。
- PYNQ driver 能绘制 dashboard 并更新固定区域。
- `CLKDIV=50` 是首个集成 display target。

### UART SpO2 AXI IP

目标：

- 验证 100 MHz AXI clock 下 9600 baud timing。
- 板测确认物理模块 BPM/SpO2 更新。
- RX/TX 接线方向按已确认的交叉方式处理。

## I2C JY901 / MPU9250 AXI IP

### Behavioral simulation

覆盖文件：

- [../rtl/i2c_mpu9250/i2c_master_core.v](../rtl/i2c_mpu9250/i2c_master_core.v)
- [../rtl/i2c_mpu9250/jy901_sampler.v](../rtl/i2c_mpu9250/jy901_sampler.v)
- [../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v](../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v)
- [../sim/tb_i2c_mpu9250/tb_jy901_sampler.v](../sim/tb_i2c_mpu9250/tb_jy901_sampler.v)

命令：

```powershell
cd sim\tb_i2c_mpu9250
just sampler
```

验收：

- I2C transaction 为 `START, 0xA0, 0x34, RESTART, 0xA1, 26 data bytes, NACK, STOP`。
- `data_valid=1`，`sample_cnt` 增加。
- address NACK path 设置 `ERROR_CODE=0x01`。

### AXI top-level simulation

命令：

```powershell
cd sim\tb_i2c_mpu9250
just axi
```

验收：

- AXI reads `VERSION == 0x4A593101`。
- AXI reads reset `DEV_ADDR == 0x50`。
- AXI writes `I2C_CLKDIV`、`START_REG`、`WORD_COUNT`、`DEV_ADDR` 和 `CTRL`。
- AXI polls `STATUS.done`。
- AXI reads `AX_RAW == 0x1234`、`AY_RAW == 0x5678`、`TEMP_RAW == 0x0D0C`、`SAMPLE_CNT == 1`。
- clear_done/clear_error、WORD_COUNT boundary、auto_mode、cfg_write、NACK 和 soft_reset path 均通过。

### Timeout simulation

```powershell
cd sim\tb_i2c_mpu9250
just timeout
```

验收：transaction 在第一个 I2C phase 完成前 timeout，并设置 timeout/error status。

### Single-module board test

步骤：

1. JY901 VCC 接 3.3 V，GND 接 GND，SCL/SDA 接受约束的 PYNQ-Z1 引脚。
2. 确认 SCL/SDA 上拉到 3.3 V，不是 5 V。
3. 烧录 bitstream，设置 `DEV_ADDR=0x50`、`START_REG=0x34`、`WORD_COUNT=13`、`I2C_CLKDIV=250`。
4. 写 `CTRL = enable | oneshot_start`。
5. 读 `STATUS`、`ERROR_CODE`、`AX_RAW` 和 `SAMPLE_CNT`。

### PYNQ AXI driver demo

板端环境：

- Jupyter kernel 使用 `/opt/python3.6/bin/python3.6`。
- SSH CLI 默认 `/usr/bin/python3` 不是 PYNQ demo 环境。
- legacy `python` 可能是 2.7.10，不使用。

命令：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 10
```

验收：

- `VERSION=0x4A593101`。
- `SAMPLE_CNT` 持续增加。
- 无 `ACK_ERR/TIMEOUT`。
- 移动实物 JY901 时 raw/scaled 值变化。

### PL-only hardware debug top

当目标是在依赖 AXI/PYNQ 软件前测试 sampler/I2C path 时使用。

要点：

- 顶层：`jy901_hw_debug_top`。
- 使用 [../vivado/constraints/jy901_debug.xdc](../vivado/constraints/jy901_debug.xdc)。
- ILA 观察 SCL/SDA、state、step、tx_byte、rx_data、ack_error、timeout、data_valid、sample_cnt。
- 至少一个 raw data word 应在改变 JY901 姿态时变化。

若 `core_sda_in_dbg == 1` 出现在 ACK 状态附近，重点检查 debug 接线、pullup、模块供电、PMODA pin selection 或实际 JY901 I2C address。

## 证据规则

- 仿真通过：必须有明确 PASS marker。
- 板级通过：必须有实际板端输出、截图、日志或用户确认测量。
- 集成通过：必须说明 bit/hwh、IP 地址、端口、XDC 和运行命令。
- 端到端通过：必须保存四类 message record。
- 硬件执行器：不要把软件状态误当成真实物理反馈。
