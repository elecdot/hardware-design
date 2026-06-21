# pc_server

最终软件集成阶段的 PC 侧 socket service、睡眠分类、舒适策略、持久化存储和 dashboard 入口。

原始 socket/Excel 文件来自 `handoff/sleep_socket_project/sleep_socket_project/`，
应作为想法级参考代码，而不是最终架构约束。

## 文件

| 文件 | 用途 |
|---|---|
| [protocol_config.py](protocol_config.py) | Socket、Excel、字段和 state-code 配置。 |
| [excel_utils.py](excel_utils.py) | Legacy Excel workbook helper；后续可成为存储实现细节。 |
| [sleep_classifier.py](sleep_classifier.py) | 纯 Python DREAMT GRU classifier，加载 `sleep_model.bin` 并输出 `sleep_result`。 |
| [sleep_model.bin](sleep_model.bin) | `sleep_classifier.py` 使用的轻量 classifier weights。 |
| [dashboard_server.py](dashboard_server.py) | Dashboard PC 入口，组合 `SleepMonitorPcService`、Web state/SSE、四消息 socket handling 和 pending-only manual controls。 |
| [dashboard_server_selftest.py](dashboard_server_selftest.py) | Dashboard 入口、pending manual command 和四消息 socket flow 的 loopback self-test。 |
| [static/](static/) | `dashboard_server.py` 服务的 dashboard HTML、CSS 和 JavaScript asset。 |
| [protocol.py](protocol.py) | 四种 message type 的规范 newline JSON protocol helper 和 validation。 |
| [protocol_selftest.py](protocol_selftest.py) | 无 dependency 的 SW-0 protocol self-test。 |
| [classifier_adapter.py](classifier_adapter.py) | 围绕 `sleep_classifier.py` 的稳定 wrapper，提供经过验证的 `sleep_result` 输出和失败 fallback。 |
| [classifier_adapter_selftest.py](classifier_adapter_selftest.py) | 使用 fake classifier function 的无 dependency classifier adapter self-test。 |
| [sleep_classifier_selftest.py](sleep_classifier_selftest.py) | JY901-only invalid sample 和真实 HR/SpO2 invalid sample 的 classifier warm-up regression。 |
| [comfort_policy.py](comfort_policy.py) | 纯第一版舒适策略，输出经过验证的 `control_command` 消息。 |
| [comfort_policy_selftest.py](comfort_policy_selftest.py) | 无 dependency 的 SW-1 policy self-test。 |
| [state_store.py](state_store.py) | 面向单 client dashboard/service state 和 pending manual command 的线程安全 `AppState`。 |
| [storage.py](storage.py) | 用于 `sensor_data`、`sleep_result`、`control_command` 和 `control_status` 的 JSONL four-record storage backend。 |
| [state_storage_selftest.py](state_storage_selftest.py) | 无 dependency 的 SW-2 AppState/storage self-test。 |
| [service.py](service.py) | 单次 `sensor_data` cycle 和 `control_status` 记录的无 socket PC service 组合。 |
| [service_selftest.py](service_selftest.py) | 无 dependency 的 service composition self-test。 |
| [socket_service.py](socket_service.py) | 新四消息协议的最小顺序 TCP loop。 |
| [socket_service_selftest.py](socket_service_selftest.py) | `sensor_data -> sleep_result/control_command -> control_status` 的 loopback TCP self-test。 |
| [pc_server.py](pc_server.py) | Legacy/minimal socket smoke；不是最终验收入口。 |
| [fake_pynq_client.py](fake_pynq_client.py) | 新协议的 PC-only fake PYNQ client。 |
| [fake_pynq_client_selftest.py](fake_pynq_client_selftest.py) | fake client 与最小 socket service 的 loopback self-test。 |

## 运行顺序

安装 PC dependency：

```bash
pip install -r requirements.txt
```

课堂 demo 的 PC 入口：

```bash
python dashboard_server.py
```

这会在 `http://127.0.0.1:8080` 启动 Web dashboard，并在 `protocol_config.SERVER_PORT`
上启动 PYNQ socket listener，当前端口为 `9000`。

最小新协议 socket service：

```bash
python socket_service.py --host 0.0.0.0 --port 9000
```

Legacy 最小 server，不作为最终验收证据：

```bash
python pc_server.py
```

新协议 PC-only socket smoke：

```bash
python socket_service.py --host 127.0.0.1 --port 9000
python fake_pynq_client.py --host 127.0.0.1 --port 9000 --samples 5 --interval 1.0
```

Dashboard 加 fake-client smoke：

```bash
python dashboard_server.py
python fake_pynq_client.py --host 127.0.0.1 --port 9000 --samples 10 --interval 1.0
```

Protocol self-test：

```bash
python protocol_selftest.py
```

Classifier adapter self-test：

```bash
python classifier_adapter_selftest.py
```

Classifier warm-up/JY901 robustness self-test：

```bash
python sleep_classifier_selftest.py
```

Comfort policy self-test：

```bash
python comfort_policy_selftest.py
```

State/storage self-test：

```bash
python state_storage_selftest.py
```

Service composition self-test：

```bash
python service_selftest.py
```

Socket loopback self-test：

```bash
python socket_service_selftest.py
```

Fake PYNQ client self-test：

```bash
python fake_pynq_client_selftest.py
```

Dashboard entry self-test：

```bash
python dashboard_server_selftest.py
```

真实 PYNQ 集成时，board client 必须连接 PC 的真实 IPv4 地址，而不是 `127.0.0.1`。

完整 PC/PYNQ 集成流程见 [../docs/software_integration_runbook.md](../docs/software_integration_runbook.md)，
包括 PYNQ 文件部署、dry-run socket smoke、真实 board client 运行和 evidence capture。

## 协议方向

对于每个板端发出的 `sensor_data`，最终 PC service 按顺序发送两个 newline JSON message：

```text
sleep_result
control_command
```

随后 PYNQ client 回复：

```text
control_status
```

Dashboard 手动控制会设置一个 pending real device command，并等待下一个 `sensor_data`；
它们不会绕过主 socket loop。AC command 是一次性 IR action。加湿器控制是 target state。
Dashboard desired-state panel 仅用于显示，由 latest/pending command 加 `control_status` 推导；
它不得自动重放 AC desired state。Dashboard 入口使用与 `socket_service.py` 相同的四消息协议。

IR AC cooldown 基于 PC 侧 monotonic runtime，并且只在 board 返回
`control_status.applied.ir_ac.sent=true` 后开始。`ir_ac_missing` 或 `ir_ac_error` 等板端 skip
会记录为 failure/skip，但不消耗正常 IR cooldown。当新的 board run 以 `sample_id=1` 开始时，
service 会重置 policy runtime state，避免上一次 smoke run 的 stale cooldown 影响新运行。

见 [../docs/protocol.md](../docs/protocol.md) 和 [../docs/software_integration_plan.md](../docs/software_integration_plan.md)。
