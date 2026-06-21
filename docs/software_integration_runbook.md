# Software Integration Runbook

本文档是 PC/PYNQ 软件集成的可执行运行手册，覆盖本地自测、PYNQ 部署、socket smoke、
真实 board client 运行和证据采集。

当前推荐课堂路径：

```text
PYNQ board_client.py -> PC dashboard_server.py
```

## 1. PC 本地自测

在仓库根目录运行：

```bash
python pc_server/protocol_selftest.py
python pc_server/classifier_adapter_selftest.py
python pc_server/sleep_classifier_selftest.py
python pc_server/comfort_policy_selftest.py
python pc_server/state_storage_selftest.py
python pc_server/service_selftest.py
python pc_server/socket_service_selftest.py
python pc_server/fake_pynq_client_selftest.py
python pc_server/dashboard_server_selftest.py
```

预期：所有 self-test 正常退出，没有 traceback。

## 2. PC-Only Fake Client Smoke

终端 1：

```bash
cd pc_server
python socket_service.py --host 127.0.0.1 --port 9000 --record-dir records\fake_client_smoke
```

终端 2：

```bash
cd pc_server
python fake_pynq_client.py --host 127.0.0.1 --port 9000 --samples 5 --interval 1.0
```

预期：

- fake client 每个 sample 收到 `sleep_result` 和 `control_command`。
- fake client 返回 `control_status`。
- `records/fake_client_smoke/` 下生成四类 JSONL。

## 3. Dashboard Fake Client Smoke

终端 1：

```bash
cd pc_server
python dashboard_server.py
```

浏览器打开：

```text
http://127.0.0.1:8080
```

终端 2：

```bash
cd pc_server
python fake_pynq_client.py --host 127.0.0.1 --port 9000 --samples 10 --interval 1.0
```

预期：

- dashboard 页面加载成功。
- 页面显示 live data、latest result、latest command 和 control status。
- manual pending control 能在下一条 `sensor_data` 中被发送。

## 4. 部署 PYNQ 文件

目标目录：

```text
/home/xilinx/jupyter_notebooks/sleep_monitor/
```

推荐使用 rsync：

```bash
rsync -av --delete \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.ipynb_checkpoints/' \
  pynq/ xilinx@pynq:/home/xilinx/jupyter_notebooks/sleep_monitor/
```

上传 overlay artifact：

```bash
rsync -av vivado/gen/system_v0_2.bit vivado/gen/system_v0_2.hwh vivado/gen/system_v0_2.tcl xilinx@pynq:/home/xilinx/jupyter_notebooks/sleep_monitor/
```

如果本地没有 `system_v0_2.tcl`，只上传 `.bit` 和 `.hwh`：

```bash
rsync -av vivado/gen/system_v0_2.bit vivado/gen/system_v0_2.hwh xilinx@pynq:/home/xilinx/jupyter_notebooks/sleep_monitor/
```

## 5. 为 PYNQ 启动 PC Dashboard

在 PC 端：

```bash
cd pc_server
python dashboard_server.py
```

dashboard URL：

```text
http://127.0.0.1:8080
```

socket listener 使用 `protocol_config.SERVER_PORT`，当前为 `9000`；PYNQ 端使用相同端口。

如果只测试 socket service，也可运行：

```bash
cd pc_server
python socket_service.py --host 0.0.0.0 --port 10000 --record-dir records\pynq_integration_smoke
```

## 6. PYNQ Dry-Run Client

先用 synthetic sample 测试网络和协议：

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 board_client.py \
  --host <PC_IPV4> \
  --port 9000 \
  --dry-run \
  --samples 5 \
  --interval 1.0
```

预期：

- PYNQ 打印 `SEND sensor_data`、`RECV sleep_result`、`RECV control_command` 和 `SEND control_status`。
- PC 记录四类 message。
- `sleep_result.state_valid` 可能为 `0`，因为 dry-run sample 不包含真实 warm-up 数据；这是正常现象。

## 7. 可选本地 Overlay Sanity Check

不依赖 PC 网络，先确认集成 overlay 和驱动绑定：

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 5 \
  --interval 1.0 \
  --metadata-source auto \
  --jy901-retries 1 \
  --jy901-retry-delay 0.05 \
  --jy901-max-stale 5.0 \
  --tft-clkdiv 50 \
  --spo2-frame-len 5
```

预期：

- 打印 record 的 `type="sensor_data"`。
- TFT 能初始化并更新。
- DHT11、SpO2 和 JY901 根据实际接线返回值或清晰错误。

## 8. 真实 PYNQ Socket Client

把 `<PC_IPV4>` 替换成 PC 的真实 IPv4 地址：

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 board_client.py \
  --host <PC_IPV4> \
  --port 9000 \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 90 \
  --interval 1.0 \
  --metadata-source auto \
  --jy901-retries 1 \
  --jy901-retry-delay 0.05 \
  --jy901-max-stale 5.0 \
  --tft-clkdiv 50 \
  --spo2-frame-len 5
```

预期：

- PC 记录 board-originated `sensor_data`。
- PC 对每个 sample 发送 `sleep_result` 和 `control_command`。
- PYNQ 对每个 command 返回一个 `control_status`。
- TFT 保持更新。
- 如果偶发 JY901-only transient failure，HR/SpO2 有效时 classifier warm-up 不应被重置。

## 9. 需要采集的证据

保存：

- PC 终端输出。
- PYNQ 终端输出。
- `pc_server/records/` 下本次 run 的四类 JSONL：
  `sensor_data`、`sleep_result`、`control_command`、`control_status`。
- Dashboard 截图。
- 如展示 IR AC，保存人工观察记录：命令、距离、是否响应。

## 10. 故障排查

PC IPv4 不确定：

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -ne 'WellKnown' } | Select-Object IPAddress,InterfaceAlias
```

端口被防火墙阻止：

```powershell
Test-NetConnection <PC_IPV4> -Port 9000
```

`Overlay.ip_dict` 为空或 `.tcl` 缺失：

- 使用默认 `--metadata-source auto`。
- 确保 `.bit` 和 `.hwh` 同 basename 且在同一目录。
- 当前脚本会回退到 Phase4 静态地址映射。

PYNQ 无法 import `pynq`：

- 使用 `/opt/python3.6/bin/python3.6`：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 board_client.py --help
```

PYNQ 返回 `control_status.remark=ir_ac_missing`：

- 确认部署了完整 `pynq/` 目录，而不是只部署 `sleep_demo/`。
- 运行 `integrated_demo.py --list-ips`，确认存在 `gree_ir_axi_v1_0_0`。
- 确认 `system_v0_2.bit/.hwh` 是最新集成 artifact。

HR/SpO2 一直为 `NA` 或 `null`：

- 检查 UART RX/TX 交叉接线。
- 保持 `--spo2-frame-len 5`。
- 在排除接线前不要修改 RTL 或 parser。

IR TX status done 但空调不响应：

- 把 IR 发射器移到距离 AC 接收头约 20 cm 以内。
- 对准接收窗口。
- 使用已确认命令，例如 `temp_26`。
- 不要用 `sent=true` 单独声称真实 AC 响应。

## 11. 运行结束后

检查 JSONL 记录数量是否匹配：

```bash
python -m json.tool pc_server/records/<run>/sensor_data.jsonl
```

如果使用的是正式 demo run，将输出、截图和人工观察记录同步到报告材料中。
