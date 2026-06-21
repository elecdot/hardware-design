# Protocol

PC logging/classification 路径使用的 PYNQ 到 PC socket payload 格式。
在集成 `system_v0_2` 板级 demo 和 TX-only IR AC 验证后，该路径是当前软件集成范围。
首个端到端 PC/PYNQ 集成使用这个 newline-delimited JSON 协议。

参考交接包：

```text
handoff/sleep_socket_project/sleep_socket_project/
```

## Transport

- TCP socket。
- PC server 监听 `0.0.0.0:9000`。
- PYNQ client 必须连接 PC 的真实 IPv4 地址，而不是 `127.0.0.1`。
- 每条 message 是一个 UTF-8 编码 JSON object，并以 `\n` 结尾。
- 必须包含 newline terminator，这样接收端才能把 TCP byte stream 分割成完整 message。
- 第一版支持一个 active PYNQ client。第二个 client 应被明确拒绝或关闭。
- 对每条 `sensor_data`，PC 按顺序发送两个 response message：`sleep_result`，然后 `control_command`。
- PYNQ 在处理每个 `control_command` 后发送一个 `control_status`。
- no-action policy decision 仍以 `control_command` 发送，`targets` 为空，并带清晰 `reason`。

第一版 cycle：

```text
PYNQ -> PC: sensor_data
PC -> PYNQ: sleep_result
PC -> PYNQ: control_command
PYNQ -> PC: control_status
```

## PYNQ To PC: sensor_data

板端 client 发送 `sensor_data` packet。

```json
{
  "type": "sensor_data",
  "timestamp": "2026-06-02 14:30:01",
  "sample_id": 1,
  "heart_rate_bpm": 76,
  "spo2_percent": 98,
  "accel_x": 0.12,
  "accel_y": -0.03,
  "accel_z": 0.98,
  "gyro_x": null,
  "gyro_y": null,
  "gyro_z": null,
  "mag_x": null,
  "mag_y": null,
  "mag_z": null,
  "turnover_flag": 0,
  "turnover_count": 3,
  "temperature_c": 26,
  "humidity_percent": 58,
  "data_valid": 1,
  "imu_valid": 1,
  "imu_stale": 0,
  "spo2_valid": 1,
  "env_valid": 1,
  "status_code": 0,
  "checksum_ok": 1,
  "jy901_status": "OK",
  "jy901_attempts": 1,
  "jy901_stale_s": null,
  "remark": "normal"
}
```

第一版最小字段：

| Field | Meaning |
|---|---|
| `type` | 必须为 `sensor_data`。 |
| `timestamp` | 板端或 client 侧 timestamp string。 |
| `sample_id` | 单调递增 sample number。 |
| `heart_rate_bpm` | 来自 UART SpO2 的心率；不可用时使用 `null`。 |
| `spo2_percent` | 来自 UART SpO2 的 SpO2；不可用时使用 `null`。 |
| `accel_x`, `accel_y`, `accel_z` | JY901 加速度值，推荐缩放为 g。 |
| `gyro_x`, `gyro_y`, `gyro_z` | 可选 JY901 gyro 值；可为 `null`。 |
| `mag_x`, `mag_y`, `mag_z` | 可选 JY901 magnetometer 值；可为 `null`。 |
| `turnover_flag` | 当前 sample 表示一次翻身事件时为 `1`，否则为 `0`。 |
| `turnover_count` | 累计翻身次数。 |
| `temperature_c` | DHT11 或可用温度，单位摄氏度。 |
| `humidity_percent` | DHT11 湿度，单位 percent RH。 |
| `data_valid` | packet 可用于 PC classification 时为 `1`。第一版 classifier usability 基于有效 HR/SpO2；仅 JY901 失败不应强制置 `0`。 |
| `imu_valid` | 可选 quality flag：当前 sample 包含新鲜 JY901/IMU read 时为 `1`。 |
| `imu_stale` | 可选 quality flag：retry 失败后复用最近 IMU 值时为 `1`。 |
| `spo2_valid` | 可选 quality flag：HR/SpO2 字段存在且 checksum/sensor flag 可接受时为 `1`。 |
| `env_valid` | 可选 quality flag：温湿度字段为当前值或来自 DHT11 cache 时为 `1`。 |
| `status_code` | 板端 status code；`0` 表示该 packet 无已知错误。 |
| `checksum_ok` | 已解析 sensor payload 通过自身检查时为 `1`。 |
| `jy901_status` | 可选 JY901 status label，例如 `OK`、`ERR` 或 `STALE`。 |
| `jy901_attempts` | 可选字段，本 sample 进行的 JY901 read attempt 数。 |
| `jy901_stale_s` | 可选字段，`imu_stale=1` 时复用 IMU 数据的年龄，单位秒；否则为 `null`。 |
| `remark` | 简短 debug/status 文本。 |

为了可观察性，板端仍可在 `status_code` 中设置 JY901 相关 bit，并保留 `remark="jy901:..."`；
只要 HR/SpO2 有效，就可以保持 `data_valid=1`。PC warm-up 和自动策略不应只因为 JY901
模块瞬时读取失败而重置。

## PC To PYNQ: sleep_result

PC server 在收到每条 `sensor_data` 后发送一条 `sleep_result` packet。
该 message 只表示分类输出，不得编码设备控制动作。

```json
{
  "type": "sleep_result",
  "timestamp": "2026-06-02 14:30:03",
  "sample_id": 1,
  "sleep_state_code": 1,
  "state_valid": 1,
  "remark": "model_dreamt_gru_conf_0.821"
}
```

| Field | Meaning |
|---|---|
| `type` | 必须为 `sleep_result`。 |
| `timestamp` | PC 侧 result timestamp。 |
| `sample_id` | 回显 input sample ID。 |
| `sleep_state_code` | `0` awake/not asleep，`1` light sleep，`2` deep sleep。 |
| `state_valid` | PC classifier result 有效时为 `1`。 |
| `remark` | Classifier/debug status text。 |

如果 `state_valid != 1`，自动策略不得改变 AC 或加湿器状态。
PC 仍会在该 `sleep_result` 之后发送 no-action `control_command`。

## PC To PYNQ: control_command

设备执行使用独立于 `sleep_result` 的 message。PC policy 负责自动 AC 和加湿器决策；
PYNQ 校验并执行期望 actuator target。

```json
{
  "type": "control_command",
  "timestamp": "2026-06-09 21:00:00",
  "sample_id": 123,
  "mode": "auto",
  "policy_id": "comfort_v1",
  "targets": {
    "ir_ac": {
      "command": "temp_26",
      "temperature_setpoint_c": 26
    },
    "humidifier": {
      "enabled": true
    }
  },
  "valid": 1,
  "reason": "light_sleep_temp_high_humidity_low"
}
```

No-action 示例：

```json
{
  "type": "control_command",
  "timestamp": "2026-06-09 21:00:00",
  "sample_id": 123,
  "mode": "auto",
  "policy_id": "comfort_v1",
  "targets": {},
  "valid": 1,
  "reason": "classifier_invalid_model_warmup"
}
```

字段规则：

| Field | Meaning |
|---|---|
| `type` | 必须为 `control_command`。 |
| `timestamp` | PC 侧 command timestamp。 |
| `sample_id` | 匹配触发该命令的 `sensor_data` sample。 |
| `mode` | `auto` 或 `manual`。 |
| `policy_id` | Policy/version identifier，例如 `comfort_v1`。 |
| `targets` | 包含零个或多个 actuator target 的 object。空 object 表示 no action。 |
| `valid` | PC command schema 有效时为 `1`。 |
| `reason` | 简短 policy/manual reason。no-action 必须提供，也便于日志记录。 |

Target 语义：

| Target | Fields | Semantics |
|---|---|---|
| `ir_ac` | `command`，可选 `temperature_setpoint_c` | 一次性 IR pulse command。不证明也不代表真实 AC 状态。 |
| `humidifier` | `enabled` | 本地板端控制 humidifier/LED actuator 的 target state。 |

第一版 `ir_ac.command` 值限制为：

```text
power_on, power_off, temp_24, temp_25, temp_26, temp_27, temp_28
```

Dashboard 手动控制：

- Dashboard manual button 使用真实设备语义。
- `/api/control` 存储 pending manual command；它不直接向 socket 发送。
- 下一条 `sensor_data` 触发 PC 发送 `control_command(mode="manual", reason="dashboard_manual")`。
- Manual AC command 是 one-shot，发送后清除。
- Desired-state 保留给未来 UI 工作。第一版不得自动重放 desired-state command。

## PYNQ To PC: control_status

PYNQ 对已接受、跳过和拒绝的 actuator command 返回实际执行结果。

```json
{
  "type": "control_status",
  "timestamp": "2026-06-09 21:00:01",
  "sample_id": 123,
  "accepted": 1,
  "applied": {
    "ir_ac": {
      "requested": true,
      "command": "temp_26",
      "sent": true,
      "skipped": false,
      "skip_reason": null,
      "error": null,
      "status": {
        "done": true,
        "error": false,
        "raw_status": 2
      }
    },
    "humidifier": {
      "requested": true,
      "enabled": true,
      "applied": true,
      "skipped": false,
      "skip_reason": null,
      "error": null,
      "humidifier_on": true
    }
  },
  "status_code": 0,
  "remark": "control_applied"
}
```

字段规则：

| Field | Meaning |
|---|---|
| `type` | 必须为 `control_status`。 |
| `timestamp` | PYNQ 侧 status timestamp。 |
| `sample_id` | 匹配触发的 `control_command`。 |
| `accepted` | schema 和 target 被接受处理时为 `1`；拒绝时为 `0`。 |
| `applied` | 每个 target 的执行细节。 |
| `status_code` | 结构化 status code。 |
| `remark` | 简短 execution/debug reason。 |

`status_code` 值：

| Code | Meaning |
|---:|---|
| `0` | 无错误。 |
| `1` | 拒绝 invalid command 或 schema。 |
| `2` | 因 guard、cooldown、idle 或 no-action policy 被跳过。 |
| `3` | 硬件执行错误。 |

对 IR AC 来说，`sent=true` 表示 PYNQ 已发送 IR waveform 且 IP 完成；
它不证明实验室 AC 收到了命令。实验室搭建需要 IR 发射器距离 AC 接收头约 20 cm 以内才能可靠响应。
PC 侧 IR cooldown 应由确认的 `sent=true` status 消耗，而不是仅由发出 `control_command` 消耗；
`ir_ac_missing` 等 skip 在正常 policy check 后仍可重试。

完整 IR AC 集成计划见 [ir_ac_integration_plan.md](ir_ac_integration_plan.md)。

## PC-Side Storage

第一版存储应分别保留 raw record 和 derived record。Excel 或等价持久化存储至少包含四类 record stream：

| Sheet | Purpose |
|---|---|
| `sensor_data` | 原始板端 packet。 |
| `sleep_result` | PC classification result。 |
| `control_command` | PC policy/manual 为某个 sample 给出的期望 actuator target。 |
| `control_status` | PYNQ accepted/skipped/applied execution result。 |

最小 control storage 字段：

| Sheet | Fields |
|---|---|
| `control_command` | `timestamp`, `sample_id`, `mode`, `policy_id`, `targets_json`, `valid`, `reason` |
| `control_status` | `timestamp`, `sample_id`, `accepted`, `applied_json`, `status_code`, `remark` |

PC dependency：

```bash
pip install openpyxl
```

server 写入时不要打开 Excel 文件。

## Validation Steps

1. 校验 `pc_server/protocol.py` 对四种 message type 的 encode/decode。
2. 使用 fake PYNQ client 运行 PC dashboard/service：发送 `sensor_data`，
   接收 `sleep_result` 加 `control_command`，再返回 `control_status`。
3. 确认 storage/dashboard state 记录所有四种 message type。
4. 将 fake client 替换为 PYNQ client，向 PC 真实 IPv4 地址发送 synthetic data。
5. 将 synthetic PYNQ 值替换为从集成 driver suite 读取的真实值。

在真实 PYNQ client 连接 PC server，且 PC 至少记录一条 board-originated packet
以及匹配的 `sleep_result`、`control_command` 和 `control_status` 之前，不要声称 PC-integrated operation 已完成。
