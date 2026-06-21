# ir_ac_demo

从 `handoff/gree_ir_txrx_hardware_package/` 迁移的 PYNQ 侧 TX-only Gree IR AC helper。

## 文件

| 文件 | 用途 |
|---|---|
| [ir_ac.py](ir_ac.py) | `gree_ir_axi_v1_0` 的 TX-only MMIO 驱动。 |
| [demo_ir_ac.py](demo_ir_ac.py) | 用于独立或集成板级 smoke 的小型 CLI。 |
| [gree_yb0f2_command_library_7.json](gree_yb0f2_command_library_7.json) | 七个已验证 preset 的交接命令库。 |

## 命令

第一版支持的命令：

```text
power_on
power_off
temp_24
temp_25
temp_26
temp_27
temp_28
```

该范围不承诺其他 Gree 模式、风速、扫风或 raw command 路径。

## 独立 Smoke

对于交接包独立 overlay，把 `ir_txrx.bit` 部署在本目录旁边，或传入 bitfile 绝对路径，
然后使用 PYNQ Jupyter 等价的 Python 3.6 运行时：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --bitfile /home/xilinx/jupyter_notebooks/ir_txrx.bit \
  --base-addr 0x43C00000 \
  --command temp_26
```

交接包独立 TX base address 为 `0x43C00000`。

## 集成 Smoke

对于 `system_v0_2` 集成 overlay，已确认的 IR AXI base address 为 `0x40005000`。

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --base-addr 0x40005000 \
  --command temp_26
```

距离或对准检查时，在有界时间内重复同一个安全命令：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --base-addr 0x40005000 \
  --command temp_26 \
  --duration 60 \
  --interval 5 \
  --timeout 15.0
```

每次尝试都会打印带时间戳的 `before` 和 `after` status。成功的 driver/IP transaction
应在每次尝试后报告 `done: True`、`error: False` 和 `command: temp_26`。

2026-06-10 的板级验证确认，实验室 Gree AC 会响应集成 `system_v0_2` overlay 发送的
`power_on`、`power_off` 和 `temp_26`。为了可靠响应，IR 发射器需要距离 AC 接收头约 20 cm 以内。

## 安全

- 输入 PYNQ-Z1 PL 引脚的逻辑电平使用 3.3 V。
- 对裸 LED 使用红外发射模块或驱动晶体管/MOSFET。
- 板子上电时不要热插拔 IR 模块。
- 首次集成 smoke 优先使用 `temp_26`，除非团队确认实验室中其他 preset 更安全。
