# sleep_demo

最终睡眠监测 overlay 的集成 PYNQ demo、板端 orchestrator 和 socket client。

## 文件

| 文件 | 用途 |
|---|---|
| [integrated_demo.py](integrated_demo.py) | 加载一个集成 overlay、绑定 sensor/display/actuator IP、按固定间隔采样、更新 TFT，并打印规范 JSON-like record。 |
| [integrated_demo_selftest.py](integrated_demo_selftest.py) | 可在 PC 上运行的 self-test，检查静态集成 metadata 是否绑定所有预期驱动，包括 IR AC。 |
| [display_ui.py](display_ui.py) | ST7789 dashboard 绘制 helper，支持完整初始绘制和固定区域更新。 |
| [board_orchestrator.py](board_orchestrator.py) | 可复用顶层板端 wrapper，负责采样、显示更新、加湿器目标执行、IR AC guarded execution 和 `control_status` 创建。 |
| [board_orchestrator_selftest.py](board_orchestrator_selftest.py) | orchestrator protocol shape 和 fake actuator 行为的 PC-runnable self-test。 |
| [board_client.py](board_client.py) | PYNQ 侧 socket client，发送 `sensor_data`，接收 `sleep_result` 与 `control_command`，应用命令并返回 `control_status`。 |
| [board_client_selftest.py](board_client_selftest.py) | board client 与最小 PC socket service 的 PC-runnable loopback self-test。 |
| [BOARD_RUNBOOK.md](BOARD_RUNBOOK.md) | 分步骤板端部署和集成 demo 运行手册。 |

PC/PYNQ socket 集成流程，包括 rsync 部署和 record evidence capture，见
[../../docs/software_integration_runbook.md](../../docs/software_integration_runbook.md)。

保留 [integrated_demo.py](integrated_demo.py) 作为本地硬件 smoke/fallback 入口。
不要把它改造成最终 socket client。

## 运行

使用 PYNQ Jupyter 等价的 Python 3.6 环境：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit --samples 30
```

匹配的 `.hwh` 必须与 `.bit` 放在一起，并使用相同 basename。
例如，`system_v0_2.bit` 必须位于 `system_v0_2.hwh` 旁边。
如果板端 PYNQ 镜像需要同 basename 的 `.tcl`，默认 `--metadata-source auto` 模式会回退到 Phase4 静态地址映射。

先检查集成 overlay metadata：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit --list-ips
```

默认 IP 名称：

| 模块 | IP name |
|---|---|
| JY901 | `axi_i2c_jy901_v1_0_0` |
| DHT11 | `dht11_axi_v1_0_0` |
| UART SpO2 | `axi_uart_spo2_v1_0_0` |
| TFT LCD | `tft_lcd_spi_axi_v1_0_0` |
| Humidifier | `axi_humidifier_v1_0_0` |
| Gree IR AC TX | `gree_ir_axi_v1_0_0` |

仅在 bring-up 隔离时使用 `--allow-missing`。最终 demo 应在所有 required IP 不缺失的情况下运行。

可在 PC 上运行的板端 self-test：

```bash
python integrated_demo_selftest.py
python board_orchestrator_selftest.py
```

可在 PC 上运行的 board client loopback self-test：

```bash
python board_client_selftest.py
```

首个板端 socket-client 形态：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 board_client.py \
  --host <PC_IPV4> \
  --port 9000 \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 30 \
  --jy901-retries 1 \
  --jy901-retry-delay 0.05 \
  --jy901-max-stale 5.0
```

## Socket 集成方向

成熟的 PYNQ client 应该：

- 运行在 `/opt/python3.6/bin/python3.6` 下；
- 避免 PC-only dependency；
- 连接 PC 的真实 IPv4 地址；
- PC 不可用时每 3 秒重试连接；
- 每个 sample 发送一个 `sensor_data`；
- 对瞬时 JY901 读取失败进行重试，并把 IMU quality 与基于 HR/SpO2 的 `data_valid` 分开标记；
- 最多等待 2 秒接收匹配的 `sleep_result` 和 `control_command`；
- timeout 或消息格式错误时跳过该 sample 的控制；
- 使用本地 guard/cooldown 检查执行有效命令；
- 将 `control_command` 和 `control_status` 打印到 stdout；
- 本地 TFT 只显示简短的 control-status summary。

PC dashboard 仍是完整的控制与监测 UI。
