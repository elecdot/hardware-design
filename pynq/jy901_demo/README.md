# jy901_demo

JY901 AXI I2C bitstream 的最小 PYNQ-Z1 demo。

首个 demo 有意使用已 smoke-tested 的路径：

```python
from pynq import Bitstream, MMIO
Bitstream(bitfile).download()
ip = MMIO(0x43C00000, 0x10000)
```

它不依赖 `.hwh` overlay metadata。

## 目标运行时

bring-up 期间记录的板端环境：

- Jupyter kernel：root，使用 `/opt/python3.6/bin/python3.6`。
- Jupyter PYNQ package 路径：
  `/opt/python3.6/lib/python3.6/site-packages/pynq`。
- SSH CLI 默认 `python3`：`/usr/bin/python3`，版本 3.4.3+，没有完整 Jupyter/PYNQ package 环境。
- SSH CLI 默认 `python`：legacy Python 2.7.10，不是 demo 目标。
- Kernel：`Linux pynq 4.6.0-xilinx ... armv7l`。

demo 代码保持 Python 3.6 兼容。避免使用 Python 3.7+ 语法或 API。

## 文件

| 文件 | 用途 |
|---|---|
| [smoke.ipynb](smoke.ipynb) | 原始手动 smoke test notebook。 |
| [smoke_demo.py](smoke_demo.py) | 短 oneshot demo 的 Jupytext-style py:percent notebook 源文件。 |
| [jy901_driver.py](jy901_driver.py) | Python 3.6 兼容的 bitstream/MMIO 驱动 helper。 |
| [demo_cli.py](demo_cli.py) | 课堂展示用的主自动轮询 demo。 |

## 运行 CLI Demo

把本目录复制到 PYNQ 板端 bitstream 旁边，然后运行：

```bash
cd /home/xilinx/jupyter_notebooks/jy901_test/jy901_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 10
```

默认值：

- bitstream：`/home/xilinx/jupyter_notebooks/jy901_test/jy901_axi_package.bit`
- base address：`0x43C00000`
- address range：`0x10000`
- I2C divider：`500`

可选 JSONL 采集：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 30 --interval 0.5 --jsonl jy901_demo_run.jsonl
```

预期通过证据：

- `VERSION` 打印 `0x4A593101 PASS`；
- 初始 oneshot 使 `SAMPLE_CNT` 增加；
- 表格行持续打印，且没有 `ACK_ERR` 或 `TIMEOUT`；
- 移动或旋转 JY901 会改变加速度和 roll/pitch/yaw 值。

## 可读数据换算

`jy901_driver.py` 暴露 `scale_raw(raw)`、`readable_measurements(raw)` 和
`JY901DemoDriver.read_readable()`，让 CLI、notebook 和 JSONL 输出使用相同换算规则。

| JY901 register | Field | Raw interpretation | Converted unit |
|---:|---|---|---|
| `0x34` | AX | `raw / 32768 * 16` | g |
| `0x35` | AY | `raw / 32768 * 16` | g |
| `0x36` | AZ | `raw / 32768 * 16` | g |
| `0x37` | GX | `raw / 32768 * 2000` | deg/s |
| `0x38` | GY | `raw / 32768 * 2000` | deg/s |
| `0x39` | GZ | `raw / 32768 * 2000` | deg/s |
| `0x3A` | HX | `raw` | magnetic raw count |
| `0x3B` | HY | `raw` | magnetic raw count |
| `0x3C` | HZ | `raw` | magnetic raw count |
| `0x3D` | Roll | `raw / 32768 * 180` | deg |
| `0x3E` | Pitch | `raw / 32768 * 180` | deg |
| `0x3F` | Yaw | `raw / 32768 * 180` | deg |
| `0x40` | TEMP | `raw / 100` | C |

## 运行 Notebook 风格 Demo

`smoke_demo.py` 是 py:percent notebook 源文件。它可以作为脚本打开，
也可以在开发机上用 Jupytext 转换/同步。PYNQ 板端不需要 Jupytext。

notebook 路径有意保持简短：

1. 下载 bitstream；
2. 创建 direct MMIO driver；
3. 检查 `VERSION` 和 `STATUS`；
4. 运行一次 oneshot read；
5. 显示 raw 和 scaled 值。

## 已知失败提示

- `VERSION` 不匹配：确认 `BASE_ADDR=0x43C00000` 仍与 Vivado Address Editor 一致。
- `ACK_ERR` / `ERROR_CODE=0x01`：JY901 没有 ACK write-address byte。
  确认模块供电、PMODA `Y17/Y16`、3.3 V pullup、杜邦线接触以及 `DEV_ADDR=0x50`。
- `TIMEOUT`：确认 I2C 线没有被拉低卡死，且 bitstream 与 RTL/寄存器映射匹配。
- 传感器 payload 全零：把该 sample 视为无效，不要当作静止。
  这通常说明 transaction 被中断、sample 寄存器为 stale/cleared，或出现可见 ACK error 前传感器接线不稳定。
- idle 时 `scl_in=0` 且 `sda_in=0`：检查 pullup、pin mapping 和 IOBUF 三态行为。

## 限制

该 v1 demo 不实现 PC socket 传输、训练好的睡眠阶段预测、临床推断、`.hwh` 自动发现、显示输出或 CSV dashboard。
它演示的是从 bitstream 下载到 AXI 寄存器访问和 JY901 sample read 的最小链路。
