# Software Integration Plan

本文档记录 IR 硬件 demo 验证后的 PC/PYNQ 软件集成计划。当前第一版软件已经为课堂 demo 实现：
四消息协议、PYNQ `board_client.py`、PC service/classifier/policy/storage/dashboard、pending-only 手动控制和 display-only desired-state panel。

## 入口门槛

- [x] 当前集成本地板级 demo 对 JY901、DHT11、UART SpO2、TFT LCD 和加湿器保持稳定。
- [x] TX-only Gree IR AC 已加入集成 Vivado overlay。
- [x] 集成 overlay 将匹配 `.bit`、`.hwh` 和板端所需 metadata 导出到 `vivado/gen/`。
- [x] PYNQ 能绑定或静态解析 IR TX IP 地址。
- [x] 已从集成 overlay 发送安全 IR 命令，并观察到实验室 Gree AC 响应。
- [x] PC/PYNQ 四消息协议第一版和 dashboard 入口已实现并自测。

## 已确认决策

| Topic | Decision |
|---|---|
| PYNQ architecture | 构建顶层 `SleepMonitorBoard` / `BoardOrchestrator` class，不把最终逻辑留在 notebook 或单体脚本中。 |
| PC architecture | 可按需重构 `pc_server/`；当前文件是 demo-quality，不约束最终架构。 |
| Policy owner | PC policy 拥有自动 AC 和加湿器决策。 |
| PYNQ role | PYNQ 校验、限频、执行 actuator command，更新本地显示，并上报执行状态。 |
| Classifier path | 当前 `sleep_classifier.py` 加载 `sleep_model.bin` 并执行纯 Python DREAMT GRU 推理；它应通过 classifier adapter 包装，PYNQ hardware driver 不依赖模型内部。 |
| Protocol | `sleep_result` 保持为分类输出；新增 `control_command` 和 `control_status` 用于 actuator control。 |
| Command shape | `control_command` 携带完整 desired actuator target，而不是单个孤立动作。 |
| Execution reporting | PYNQ 必须对 accepted、skipped 和 rejected command 都发送 `control_status`。 |
| Humidifier control | 最终自动加湿器控制属于 PC policy；PYNQ 本地加湿器自动化只用于 fallback/bring-up。 |
| IR protection | PYNQ 执行 IR command validation、hardware minimum interval 和 repeated-command cooldown。 |
| Dashboard control semantics | Dashboard 手动控制使用真实设备语义，创建 pending one-shot `control_command`，不得编码为 fake `sleep_result`。 |
| Message cadence | 对每条 `sensor_data`，PC 严格按顺序发送两条 newline JSON：`sleep_result`，然后 `control_command`，包括 no-action command。 |
| Manual scheduling | Dashboard manual click 设置 `pending_manual_command`；命令随下一条 `sensor_data` 发送，不从 HTTP handler 异步直发。 |
| AC semantics | AC command 是 one-shot IR pulse；`last_commanded_state` 只是 PC 侧 cooldown/display 假设，不是真实 AC feedback。 |
| Humidifier semantics | 加湿器使用 target-state 语义，因为 PYNQ 可以写/读本地 actuator IP。 |
| Desired-state | Dashboard 可显示由 latest/pending command 和 `control_status` 推导的 display-only desired state；不得实现自动 AC replay/reconciliation。 |
| Client count | 第一版只支持一个 active PYNQ client。 |
| Dependencies | 优先使用 Python 标准库加 `openpyxl`；只有显著降低复杂度或提升可靠性时才引入新的 PC-only dependency。PYNQ 保持 Python 3.6/PYNQ-library 兼容。 |

## 范围边界

### 已实现第一版

- PYNQ 侧 board orchestrator：生成 `sensor_data`，更新 display，执行/跳过 actuator target，并生成 `control_status`。
- Board-side socket client：发送 `sensor_data`，接收 `sleep_result` 与 `control_command`，执行 target，并发送 `control_status`。
- PC 侧 protocol、classifier adapter、comfort policy、state store、JSONL storage、service composition、socket loop 和 dashboard entry。
- Dashboard 手动控制：生成真实 `control_command.targets`。
- Display-only desired-state panel。

### 第一版不包含

- 自动 AC desired-state replay。
- 真实 AC 状态反馈或 IR RX 闭环。
- 多 PYNQ client 并发。
- 复杂模型训练或在 PYNQ 上运行 classifier。
- 将旧 Excel-only server 作为最终验收入口。

## PYNQ 顶层设计

目标对象：

```text
SleepMonitorBoard / BoardOrchestrator
  - load overlay
  - bind JY901, DHT11, SpO2, TFT, humidifier, IR AC drivers
  - sample sensors
  - update local display
  - apply validated control_command targets
  - produce sensor_data and control_status dictionaries
```

典型调用：

```python
sample = board.read_sample()
status = board.apply_control_command(command)
```

socket client 要求：

- 每个 sample 发送一个 `sensor_data`。
- 等待同一 `sample_id` 的 `sleep_result` 和 `control_command`。
- 通过 `SleepMonitorBoard.apply_control_command()` 应用命令。
- 对 accepted、skipped 和 rejected command 都发送一个 `control_status`。
- PC 不可达时每 3 秒重试连接。
- 发送 `sensor_data` 后最多等待 2 秒接收两条 PC message。

第一版 `control_status.status_code`：

| Code | Meaning |
|---:|---|
| `0` | No error. |
| `1` | Rejected invalid command or schema. |
| `2` | Skipped by guard, cooldown, idle, or no-action policy. |
| `3` | Hardware execution error. |

## PC Service 设计

服务组成：

```text
protocol.py
classifier_adapter.py
comfort_policy.py
state_store.py
storage.py
service.py
socket_service.py
dashboard_server.py
```

数据流：

```text
sensor_data -> validate -> classifier adapter -> sleep_result
sensor_data + sleep_result + state -> comfort policy -> control_command
control_status -> state + storage
```

`dashboard_server.py` 可以保持为顶层可运行入口，只要它组合真实 `SleepMonitorPcService`
并使用与 `socket_service.py` 相同的四消息 socket flow。

## Protocol Lifecycle

```text
PYNQ -> PC: sensor_data
PC: classify sensor_data into sleep_result
PC: policy builds control_command from sensor_data + sleep_result + state
PC -> PYNQ: sleep_result
PC -> PYNQ: control_command
PYNQ: apply/skip/reject command
PYNQ -> PC: control_status
PC: logs/displays sensor_data, sleep_result, control_command, control_status
```

每条 `sensor_data` 必须得到两条 PC response，顺序为 `sleep_result` 然后 `control_command`。
no-action 也必须是合法 `control_command`，`targets` 为空并带 `reason`。

规范 message schema 由 [protocol.md](protocol.md) 维护。

计划 target：

```text
targets.ir_ac.command
targets.ir_ac.temperature_setpoint_c
targets.humidifier.enabled
```

手动控制：

- Dashboard click 设置 pending command。
- 下一条 `sensor_data` 将 pending command 转成 `control_command(mode="manual", reason="dashboard_manual")`。
- 如果没有 pending command，manual path 输出 no-action `control_command(reason="manual_idle")`。

## 自动舒适策略

策略输入：

- `sensor_data`
- `sleep_result`
- 当前 PC-side state
- 最近 `control_status`

睡眠状态影响策略强度：

| Sleep state | Meaning | Aggressiveness | Behavior |
|---:|---|---:|---|
| `0` | Not asleep / awake | `1.0` | 更主动调整。 |
| `1` | Light sleep | `0.6` | 中等调整。 |
| `2` | Deep sleep | `0.3` | 更宽舒适区，减少打扰。 |

首版规则：

1. `state_valid != 1` 或传感器数据缺失：no-action。
2. Manual mode：发送 pending manual command，或 no-action `manual_idle`。
3. 湿度低于 40%：`humidifier.enabled=true`。
4. 湿度高于 60%：`humidifier.enabled=false`。
5. 温度明显偏高：默认发送 AC `temp_26`，必要时使用 `temp_25` 或 `temp_24`。
6. 温度明显偏低：发送 AC `temp_27` 或 `temp_28`。
7. 处于舒适区：no-action。

建议温度舒适区：

| Sleep state | Suggested comfortable band |
|---|---|
| `0` not asleep / awake | `24.5..27.0 C` |
| `1` light sleep | `24.0..27.5 C` |
| `2` deep sleep | `23.5..28.0 C` |

IR cooldown：

| Mode | Same IR command repeat | Any IR command minimum interval |
|---|---|---|
| Demo | 30 to 60 s | 5 s |
| Normal | 5 to 10 min | 5 s |

## Storage 和 Dashboard

保留四类 record：

| Record | Purpose |
|---|---|
| `sensor_data` | 原始板端 measurement。 |
| `sleep_result` | PC classifier output。 |
| `control_command` | PC policy/manual desired actuator target。 |
| `control_status` | PYNQ accepted/skipped/applied execution result。 |

最小 control 字段：

| Record | Fields |
|---|---|
| `control_command` | `timestamp`, `sample_id`, `mode`, `policy_id`, `targets_json`, `valid`, `reason` |
| `control_status` | `timestamp`, `sample_id`, `accepted`, `applied_json`, `status_code`, `remark` |

Dashboard 应显示：

- live connection 状态；
- 当前 sensor values；
- 最新 `sleep_result`；
- 最新 `control_command`；
- PYNQ execution status: `control_status`；
- pending manual command；
- display-only desired-state summary。

## 验证计划

### SW-0: Protocol Contract

- 完成 `docs/protocol.md` 中 `control_command` 和 `control_status` 字段表。
- `pc_server/protocol.py` 覆盖 newline JSON、TCP buffering、四种 message validation、no-action 和 rejected-status encoding。
- self-test：`python pc_server/protocol_selftest.py`。

### SW-1: PC Policy Unit Tests

- `comfort_policy.py` 输出经过 validation 的 `control_command` dictionary。
- 覆盖 classifier invalid、湿度低/高、温度高/低、manual pending、cooldown 和 no-action。
- self-test：`python pc_server/comfort_policy_selftest.py`。

### SW-1b: Classifier Adapter Boundary

- adapter 校验输入 `sensor_data` 和输出 `sleep_result`。
- classifier crash 时返回 `sleep_result(state_valid=0)` 并带清晰 remark。
- JY901-only invalid sample 不应重置 HR/SpO2 主 warm-up。
- self-test：`python pc_server/classifier_adapter_selftest.py` 和 `python pc_server/sleep_classifier_selftest.py`。

### SW-2: PC State And Storage

- `AppState` 管理 latest records、manual pending command、single-client state 和 control history。
- JSONL storage 分别保存四类 record。
- self-test：`python pc_server/state_storage_selftest.py`。

### SW-3a: Service Composition Skeleton

- 对一条 validated `sensor_data`，生成一条 `sleep_result` 和一条 `control_command`，更新 state/storage。
- 接收一条 `control_status` 并记录。
- policy/classifier error 降级为 no-action 或 invalid result，不崩溃。
- self-test：`python pc_server/service_selftest.py`。

### SW-3b: Minimal Socket Loop

- 对每条 incoming `sensor_data`，按顺序发送 `sleep_result` 和 `control_command`。
- 记录 incoming `control_status`。
- self-test：`python pc_server/socket_service_selftest.py`。

### SW-3: Dashboard Service Refactor

- Dashboard 入口使用同一 service/socket flow。
- Manual controls 生成真实 `control_command.targets`。
- self-test：`python pc_server/dashboard_server_selftest.py`。

### SW-4: PC-Only Socket Simulation

- fake PYNQ client 发送 `sensor_data`。
- 接收 `sleep_result` 和 `control_command`。
- 返回 `control_status`。
- self-test：`python pc_server/fake_pynq_client_selftest.py`。

### SW-5: PYNQ Orchestrator Local Smoke

- 确认可生成 `sensor_data`。
- 确认可执行 no-action、humidifier target 和 IR target。
- 确认 IR rate-limit skip 生成合法 `control_status`。
- self-test：`python pynq/sleep_demo/board_orchestrator_selftest.py`。

### SW-6: PYNQ Real Socket Client

验收目标：

- PC 接收 board-originated `sensor_data`。
- PC 发出 `sleep_result` 和 `control_command`。
- PYNQ 执行或跳过命令。
- PYNQ 返回 `control_status`。
- PC 记录四类 message。

### SW-6a: Board Socket Client Skeleton

- `board_client.py` 发送一个 `sensor_data`，等待匹配 `sleep_result` 和 `control_command`，
  应用命令、更新显示并发送一个 `control_status`。
- 板端运行使用 `/opt/python3.6/bin/python3.6`。

## 本阶段剩余事项

- 正式 demo 前修复 PYNQ 板端时间。
- 如果实验室网络和板卡可用，重新运行一次 `dashboard_server.py` 加真实 `board_client.py` 会话。
- 采集 dashboard 截图、PYNQ 输出和 JSONL evidence。
- 仅在后续硬件具备可靠反馈时，考虑 desired-state reconciliation；课堂 demo 前不要添加 AC replay。
