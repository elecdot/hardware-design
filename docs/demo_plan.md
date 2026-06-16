# 演示计划

本文档用于课堂答辩前的最终演示执行。当前推荐演示路径是：

```text
system_v0_2 overlay -> PYNQ board_client.py -> PC dashboard_server.py
```

该路径假设使用一块 PYNQ-Z1、一台 PC 服务器，以及当前已经导出的
`system_v0_2.bit/.hwh/.tcl` 集成硬件平台。

## 演示目标

演示重点不是单独展示零散模块，而是展示一套连贯的睡眠监测与辅助系统：

- PYNQ 加载集成 overlay，并通过 AXI/MMIO 读取硬件模块。
- TFT LCD 在板端实时更新关键状态。
- PYNQ 以 newline-delimited JSON 发送 `sensor_data` 到 PC。
- PC 完成睡眠状态分类、舒适度控制策略、JSONL 记录保存和 dashboard 刷新。
- PC 返回 `sleep_result` 和 `control_command`。
- PYNQ 执行或跳过控制命令，并返回 `control_status`。
- Dashboard 支持手动 pending 控制，用于请求空调 IR 或加湿器动作。

所有睡眠状态输出仅作为课程演示中的辅助估计，不是临床诊断结果。

## 演示优先级

1. 优先展示 dashboard + 真实 PYNQ socket 的完整闭环。
2. 如果网络、防火墙或 PC service 阻塞完整闭环，则退回 PYNQ 本地集成演示。
3. 只有在需要隔离问题或解释硬件证据时，才展示单模块 demo。

不要把旧版 `pc_server.py` 或 Excel-only 逻辑作为当前最终系统的验收证据。
课堂演示的 PC 入口是 `pc_server/dashboard_server.py`。

## 演示前检查清单

课前确认：

- [ ] 本地存在 `vivado/gen/system_v0_2.bit`、`.hwh` 和 `.tcl`。
- [ ] 已将同名 `.bit/.hwh/.tcl` overlay 文件上传到 PYNQ。
- [ ] 已将 `pynq/` runtime 目录上传到 PYNQ。
- [ ] 已校正 PYNQ 板端时间，保证日志时间戳真实。
- [ ] PC 与 PYNQ 位于同一个可达网络。
- [ ] Windows 防火墙允许 Python 在 TCP `9000` 端口接收入站连接。
- [ ] SpO2 UART 物理 RX/TX 方向按记录采用交叉接线。
- [ ] 如果课堂要展示真实空调响应，IR 发射头需距离格力空调接收器约 20 cm
  以内，并对准接收窗口。
- [ ] 同时打开本文档和 `docs/software_integration_runbook.md`。

推荐先在 PYNQ 上校正时间：

```bash
sudo date -s "YYYY-MM-DD HH:MM:SS"
```

请使用演示当天的真实本地时间。

## 启动 PC 端

在 PC 的仓库根目录运行：

```bash
cd pc_server
python dashboard_server.py
```

浏览器打开：

```text
http://127.0.0.1:8080
```

预期状态：

- Web dashboard 正常加载。
- Socket service 监听 `protocol_config.SERVER_PORT`，当前为 `9000`。
- PC 终端没有 traceback。
- PYNQ 启动前，dashboard 显示等待连接或未连接状态。

## PYNQ 本地 sanity check

如果时间允许，先在连接 PC 前做一次本地 overlay 检查。该步骤用于确认集成
overlay 和板端模块可用，不依赖网络。

在 PYNQ 上运行：

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

预期证据：

- PYNQ 终端打印 `sensor_data` JSON 记录。
- TFT 初始化并更新。
- DHT11 温湿度有更新。
- SpO2 模块连接正确时，HR/SpO2 不再是 `null`。
- JY901 通常显示 `jy901_status="OK"`；如果偶发 IMU transient failure，
  但 HR/SpO2 与环境数据仍有效，可以继续完整演示。

## 完整现场演示

先确认 PYNQ 可访问的 PC IPv4 地址。Windows PowerShell 命令：

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -ne 'WellKnown' } | Select-Object IPAddress,InterfaceAlias
```

在 PYNQ 上运行：

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 board_client.py \
  --host 192.168.2.14 \
  --port 9000 \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 300 \
  --interval 1.0 \
  --metadata-source auto \
  --jy901-retries 1 \
  --jy901-retry-delay 0.05 \
  --jy901-max-stale 5.0 \
  --tft-clkdiv 50 \
  --spo2-frame-len 5
```

如果课堂现场 PC IPv4 不是 `192.168.2.14`，只替换 `--host`，其他参数保持不变。

预期证据：

- PYNQ 每个 sample 打印一次四消息闭环：
  `sensor_data -> sleep_result -> control_command -> control_status`。
- Dashboard 显示 live connection 和实时数据。
- PC 在 `pc_server/records/` 下写入 JSONL 记录流。
- Socket loop 运行时，TFT 仍能保持更新。
- 前若干个分类结果可能处于模型 warm-up 阶段，`state_valid=0` 属于正常现象；
  此时策略应保持无自动动作。

## Dashboard 展示重点

演示时重点指出：

- 当前传感器值：HR、SpO2、温度、湿度、IMU/status、turnover。
- 睡眠状态分类结果与 warm-up 过程。
- 最近控制命令与对应 `control_status`。
- Dashboard 手动 pending 控制：空调 IR 与加湿器。
- Desired-state 面板：当前请求目标与最近执行/观察结果摘要。
- Debug JSON 面板仅在需要解释协议或排查问题时展示。

Desired-state 面板不会自动重放 AC 命令，也不能替代 `control_status` 作为硬件执行证据。

## 可选：IR 空调真实响应展示

只有在能接近空调接收器、且允许发送空调命令时才做该演示。

集成 overlay 已确认的命令：

```text
power_on
power_off
temp_26
```

IR 硬件集成已经有板端证据：

- `power_on`、`power_off` 和 `temp_26` 均已让实验室格力空调响应。
- 实验室环境中，IR 发射头需要距离空调接收器约 20 cm 以内才可靠。

课堂演示建议只选择一个安全、可见的命令，例如 `temp_26` 或 `power_on`，避免频繁开关空调。

不要仅根据 `ir_ac.sent=true` 宣称空调真实响应。该状态只表示 PYNQ 端 IR IP
完成了发射；真实空调是否响应仍需要人工观察确认。

## Fallback 路径

如果 PC 网络或防火墙阻塞完整演示：

- 在 PYNQ 上运行 `integrated_demo.py` 本地演示。
- 展示 TFT 更新和 PYNQ JSON 输出。
- 说明 PC 路径已有 fake-client 和真实板端 socket run 证据，记录在
  `docs/test_plan.md` 和 `docs/software_integration_runbook.md`。

如果 HR/SpO2 一直是 `NA` 或 `null`：

- 优先检查 UART RX/TX 是否按记录交叉接线。
- 保持 `--spo2-frame-len 5`。
- 在排除接线问题前，不要修改 RTL 或 parser。

如果 JY901 偶发 invalid sample：

- 只要 HR/SpO2 和环境数据仍有效，可以继续演示。
- 当前软件把 IMU 质量与 HR/SpO2 主数据有效性分开处理，单独的 JY901
  不稳定不会重置 classifier warm-up。

如果 IR AC 不响应：

- 将 IR 发射头移到距离空调接收器约 20 cm 以内。
- 对准接收窗口。
- 使用已确认命令。
- 如果 PYNQ 返回 `ir_ac_missing`，重新同步最新 `pynq/` 到板端，并确认
  `integrated_demo.py --list-ips` 中存在 `gree_ir_axi_v1_0_0`；该 remark
  表示板端 IR driver 未绑定，不表示空调忽略了 IR 脉冲。
- 如果仍然阻塞，展示 PYNQ TX status，并引用已有真实空调响应证据，不要在课堂现场长时间调试距离或角度。

如果 `Overlay.ip_dict` 为空或 `.tcl` metadata 被旧 PYNQ image 拒绝：

- 使用 `--metadata-source auto`。
- 保持同名 `.bit`、`.hwh` 和 `.tcl` 放在同一目录。
- 当前板端 image 可以使用已记录的 static address-map fallback。

## 已有证据

硬件与板端证据：

- `system_v0_2` 集成 overlay 已导出到 `vivado/gen/`。
- JY901、DHT11、UART SpO2、TFT LCD、加湿器、Gree IR AC TX 都已有集成板端 demo 证据。
- 实验室格力空调已确认响应 `power_on`、`power_off` 和 `temp_26`。

软件证据：

- PC/PYNQ 协议和 service self-tests 已通过。
- Board orchestrator 和 board client 的 PC fake-driver self-tests 已通过。
- 90-sample 真实 PYNQ socket run 已产生匹配的 `sensor_data`、`sleep_result`、
  `control_command` 和 `control_status` JSONL streams。
- Dashboard + fake-client smoke 已产生 10 次完整四消息闭环，并成功加载
  `/`、`/static/dashboard.css` 和 `/static/dashboard.js`。

最终报告截图或视频前，优先刷新一次真实演示路径证据：

```text
pc_server/dashboard_server.py + pynq/sleep_demo/board_client.py
```

## 简短讲解顺序

1. 硬件平台：PYNQ-Z1、自定义 AXI-Lite IP、集成 `system_v0_2`。
2. 传感器与执行器：SpO2、JY901、DHT11、TFT、加湿器、IR AC TX。
3. 板端软件：orchestrator 读取传感器、更新显示、执行 PC 返回的控制命令。
4. PC 软件：四消息协议、classifier adapter、comfort policy、JSONL storage、dashboard。
5. 安全边界：睡眠状态是辅助估计，不做临床声明；IR AC 没有硬件反馈接收链路；
   执行策略保持保守。

## 演示后保存材料

演示后保留：

- PC 终端输出。
- PYNQ 终端输出。
- 本次 `pc_server/records/` 下的 JSONL 文件。
- Dashboard 截图。
- 硬件人工观察记录：TFT、HR/SpO2、湿度、加湿器、IR 空调响应情况。
