# Integrated Board Demo Runbook

本运行手册说明如何把集成 overlay 和 PYNQ runtime 文件部署到 PYNQ-Z1 板端，
然后运行第一版分层板级 demo。

当前集成本地 artifact：

- `vivado/gen/system_v0_2.bit`
- `vivado/gen/system_v0_2.hwh`
- `vivado/gen/system_v0_2.tcl`

这些文件必须以相同 basename 一起复制到板端。较新的 PYNQ 镜像使用 `.hwh` metadata
填充 `Overlay.ip_dict`。部分较旧 PYNQ 镜像会寻找同 basename 的 `.tcl`；
因此当 `system_v0_2.tcl` 缺失时，`integrated_demo.py` 会回退到 Phase4 静态地址映射。

## 目标布局

板端使用一个专用目录：

```text
/home/xilinx/jupyter_notebooks/sleep_monitor/
  system_v0_2.bit
  system_v0_2.hwh
  system_v0_2.tcl        # 可选，仅在为旧 PYNQ metadata 导出时需要
  sleep_demo/
    integrated_demo.py
    display_ui.py
  jy901_demo/
  dht11_demo/
  spo2_demo/
  tft_lcd_demo/
  humidifier_demo/
  ir_ac_demo/
```

把本地 `pynq/` 的内容部署到该目标目录。不要只部署 `pynq/sleep_demo/`，
因为 `integrated_demo.py` 会导入同级 driver 目录。

demo 路径不要把整个仓库部署到板端。Vivado 工程、handoff 包、报告和生成的 run 目录并不需要，
复制也会很慢。

## 部署

先设置板端地址。只有当 PC 能解析主机名时，`pynq` 才可用；否则替换为板子的 IPv4 地址。

### 推荐：rsync

当 WSL、Git Bash、MSYS2 或其他带 OpenSSH 和 rsync 的 shell 可用时，使用 rsync。

```bash
BOARD=xilinx@pynq
DEST=/home/xilinx/jupyter_notebooks/sleep_monitor

ssh "$BOARD" "mkdir -p $DEST"
rsync -av --delete \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.ipynb_checkpoints/' \
  pynq/ "$BOARD:$DEST/"

rsync -av \
  vivado/gen/system_v0_2.bit \
  vivado/gen/system_v0_2.hwh \
  vivado/gen/system_v0_2.tcl \
  "$BOARD:$DEST/"
```

只有当 `DEST` 专用于本 demo 时才使用 `--delete`。如果该目录里保存了手工笔记或采集结果，
移除 `--delete`。

PowerShell 下使用 rsync 的思路相同：

```powershell
$Board = "xilinx@pynq"
$Dest = "/home/xilinx/jupyter_notebooks/sleep_monitor"

ssh $Board "mkdir -p $Dest"
rsync -av --delete --exclude '__pycache__/' --exclude '*.pyc' --exclude '.ipynb_checkpoints/' .\pynq\ "${Board}:${Dest}/"
rsync -av .\vivado\gen\system_v0_2.bit .\vivado\gen\system_v0_2.hwh .\vivado\gen\system_v0_2.tcl "${Board}:${Dest}/"
```

### 备用：scp

如果 rsync 不可用，使用该方式：

```powershell
$Board = "xilinx@pynq"
$Dest = "/home/xilinx/jupyter_notebooks/sleep_monitor"

ssh $Board "mkdir -p $Dest"
scp -r .\pynq\* "${Board}:${Dest}/"
scp .\vivado\gen\system_v0_2.bit .\vivado\gen\system_v0_2.hwh .\vivado\gen\system_v0_2.tcl "${Board}:${Dest}/"
```

scp 路径不够干净，因为它不会删除 stale 文件，而且可能复制本地 cache 文件。

## 板端接线预检

更改接线前先关闭板子电源。

必需的集成引脚计划：

| 模块 | 信号 |
|---|---|
| TFT LCD | PMODA: `lcd_scl=Y18`, `lcd_sda=Y19`, `lcd_res=Y16`, `lcd_dc=Y17`, `lcd_blk=U18` |
| JY901 | Arduino I2C: `i2c_scl=P16`, `i2c_sda=P15`, 3.3 V pullups |
| UART SpO2 | PMODB: `uart_txd=W14`, `uart_rxd=Y14` |
| DHT11 | Arduino IO11: `dht11_0=R17`, pullup required |
| Humidifier | Board LEDs: `humidifier_leds[3:0]` |
| Gree IR AC TX | Arduino `ck_io[0]`: `ir_pwm=T14` |

安全检查：

- 所有连接到 PL 的信号都必须是 3.3 V logic。
- 板子上电时不要热插拔模块。
- 每个模块都必须与 PYNQ-Z1 共地。
- 不要从 FPGA 引脚驱动真实负载；板载 LED 只是 actuator indicator。

## 板端环境检查

SSH 登录板子：

```bash
ssh xilinx@pynq
```

检查 PYNQ Python 环境：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 -c "import pynq; print(pynq.__version__)"
```

检查已部署文件：

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor
ls -lh system_v0_2.bit system_v0_2.hwh sleep_demo/integrated_demo.py
```

## Overlay Metadata Smoke

先运行该步骤。它会烧录 overlay，打印 IP 名称和地址，然后退出。
在较新的 PYNQ 镜像上，它使用导出 handoff 中的 `Overlay.ip_dict` metadata。
在较旧镜像上，如果因 `system_v0_2.tcl` 抛出 `FileNotFoundError`，或 Tcl 被解析成空的 `ip_dict`，
脚本会打印 warning 并使用 Phase4 静态地址映射。

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --list-ips
```

预期 custom IP entry：

| IP | 预期地址 |
|---|---:|
| `axi_i2c_jy901_v1_0_0` | `0x40000000` |
| `axi_humidifier_v1_0_0` | `0x40001000` |
| `tft_lcd_spi_axi_v1_0_0` | `0x40002000` |
| `dht11_axi_v1_0_0` | `0x40003000` |
| `axi_uart_spo2_v1_0_0` | `0x40004000` |
| `gree_ir_axi_v1_0_0` | `0x40005000` |

如果输出包含该 warning，首轮板级 smoke 可接受：

```text
WARNING: Overlay metadata TCL is missing; falling back to the Phase4 static address map.
```

该 warning 在首轮板级 smoke 中也可接受：

```text
WARNING: Overlay metadata produced an empty ip_dict; falling back to the Phase4 static address map.
```

如果要强制使用 Vivado/PYNQ metadata 而不是 fallback，传入 `--metadata-source overlay`。
bring-up 期间如需强制静态路径，传入 `--metadata-source static`。

如果这一步失败，不要继续完整 demo。先修复 bit/hwh 配对、driver 文件部署或 IP instance name。

## 分层 Smoke 顺序

### 1. 不启用显示的 Driver Bind 和 Sensor Loop

在初始化 TFT 前，用该步骤确认 Python import、overlay metadata、MMIO binding 和 sensor polling 不会崩溃。

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 5 \
  --interval 1.0 \
  --sensor-timeout 0.5 \
  --dht11-period 2.0 \
  --no-display \
  --no-humidifier
```

预期结果：

- 程序打印 JSON-like sample 行。
- 如果硬件未连接或无响应，JY901、DHT11 或 SpO2 可能报告模块专用错误。
- 进程不应因缺少 IP metadata 或 import 而崩溃。

### 2. Humidifier Register Smoke

该步骤保持显示关闭，并验证 PS-controlled 加湿器路径。

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 5 \
  --interval 1.0 \
  --no-display
```

预期结果：

- 板载 LED 反映加湿器 IP status path。
- 打印 sample 中出现 `humidifier_on`。

### 3. Display Smoke

仅在 TFT 正确接线并供电后运行。

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 3 \
  --interval 1.0 \
  --tft-clkdiv 50
```

预期结果：

- TFT 初始化并绘制 dashboard。
- 数值/状态区域每个 sample 更新一次。

如果显示初始化失败，用 `--no-display` 重新运行，让其他模块 smoke test 继续推进。

### 4. Gree IR AC TX Smoke

仅当 IR 发射器已接线、实验室 Gree AC 能接收命令，并且发送 `temp_26` 可接受时运行。

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/ir_ac_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --base-addr 0x40005000 \
  --command temp_26 \
  --timeout 15.0
```

预期结果：

- 命令打印 `before` 和 `after` status dictionary。
- `after` 应报告 `done: True`、`error: False`、`preset: 5` 和 `command: temp_26`。
- 2026-06-10 的板级验证确认，实验室 Gree AC 会响应集成 overlay 发出的
  `power_on`、`power_off` 和 `temp_26`。
- 在实验室搭建中，IR 发射器需要距离 AC 接收头约 20 cm 以内才能可靠响应。

距离或对准检查时，保持同一命令并在有界时间内重复：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --base-addr 0x40005000 \
  --command temp_26 \
  --duration 60 \
  --interval 5 \
  --timeout 15.0
```

运行期间把发射器移近 AC 接收头或调整角度。实验室 demo 不要使用无界 repeat loop。

### 5. 完整本地 Demo

前面各层稳定后运行：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 30 \
  --interval 1.0 \
  --sensor-timeout 0.5 \
  --dht11-period 2.0 \
  --tft-clkdiv 50 \
  --spo2-frame-len 5
```

这仍是板端本地 demo。PC socket/Excel 集成是后续层。

## 结果解释

打印的 sample 使用 `docs/protocol.md` 中定义的 protocol 字段。

`integrated_demo.py` 中的重要 status bit：

| Bit | 含义 |
|---:|---|
| `0x01` | JY901 read/config path reported an exception |
| `0x02` | DHT11 read path reported an exception |
| `0x04` | SpO2 path reported sensor/frame/error condition |
| `0x08` | Humidifier register path reported an exception |

有用字段：

- `jy901_status`：JY901 status summary。
- `temperature_c`、`humidity_percent`：DHT11 派生环境值。
- `heart_rate_bpm`、`spo2_percent`：收到 frame 时的 UART SpO2 值。
- `turnover_flag`、`turnover_count`：来自 JY901 roll/pitch 的本地体动逻辑。
- `humidifier_on`：PS-controlled 加湿器 IP 状态。

## 常见失败

| 现象 | 可能原因 | 修复 |
|---|---|---|
| Missing `.hwh` error | 只复制了 `.bit`，没有同 basename `.hwh` | 同时复制 `system_v0_2.bit` 和 `system_v0_2.hwh` |
| `pynq.pl._TCL` 报 Missing `.tcl` error | 较旧 PYNQ 镜像需要 TCL metadata | 更新 `integrated_demo.py`；默认 `--metadata-source auto` 会回退到 Phase4 静态地址映射 |
| `--metadata-source overlay` 打印 `(none)` 或没有 IP entry | Tcl 存在，但该 PYNQ parser 未提取出 IP metadata | 首轮板级 smoke 使用默认 `auto` 或显式 `static`；不要把它当成硬件失败 |
| `Cannot find IP ...` | `.hwh` 错误、overlay stale 或旧默认 IP 名称 | 运行 `--list-ips`；与本 runbook 中的 instance name 对比 |
| driver module `ImportError` | 只复制了 `sleep_demo/` | 部署本地 `pynq/` 内容，确保同级 driver 目录存在 |
| JY901 timeout/NACK | 接线、pullup、地址或模块供电问题 | 检查 `P16/P15`、3.3 V pullup、GND 和 `DEV_ADDR=0x50` |
| TFT blank | 接线、背光、reset/DC 引脚或 SPI 速度问题 | 确认 PMODA 接线并用 `--tft-clkdiv 50` 重试 |
| DHT11 always zero | 传感器时序、pullup 或 data pin 问题 | 使用 1 到 2 秒读数间隔，并确认 `R17` DATA pullup |
| SpO2 never updates | UART 信号方向或 frame mode 问题 | 先用默认 5-byte mode；板测确认模块侧 RX/TX 标签可能需要在 `W14/Y14` 上交叉接线 |
| IR TX status is done but AC does not react | IR 距离或对准问题 | 修改 RTL/software 前，先把发射器移到 AC 接收头约 20 cm 以内并调整角度 |
| Board-side Python cannot import `pynq` | Python 解释器错误 | 使用 `sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6` |

## 更新文件时

只改 Python 时：

```bash
rsync -av --delete --exclude '__pycache__/' --exclude '*.pyc' pynq/ xilinx@pynq:/home/xilinx/jupyter_notebooks/sleep_monitor/
```

重新生成 overlay 时：

```bash
rsync -av vivado/gen/system_v0_2.bit vivado/gen/system_v0_2.hwh vivado/gen/system_v0_2.tcl xilinx@pynq:/home/xilinx/jupyter_notebooks/sleep_monitor/
```

代码和硬件 artifact 都变化时，两个命令都运行。
