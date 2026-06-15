# Protocol

PYNQ-to-PC socket payload format for the PC logging/classification path. This
path is now the current software-integration scope after the integrated
`system_v0_2` board demo and TX-only IR AC validation. Use this
newline-delimited JSON protocol for the first end-to-end PC/PYNQ integration.

Reference handoff:

```text
handoff/sleep_socket_project/sleep_socket_project/
```

## Transport

- TCP socket.
- PC server listens on `0.0.0.0:9000`.
- PYNQ client must connect to the PC's real IPv4 address, not `127.0.0.1`.
- Each message is one JSON object encoded as UTF-8 and terminated by `\n`.
- The newline terminator is required so the receiver can split TCP byte streams
  into complete messages.
- First version supports one active PYNQ client. A second client should be
  rejected or closed clearly.
- For each `sensor_data`, PC sends exactly two response messages in order:
  `sleep_result`, then `control_command`.
- PYNQ sends one `control_status` after handling each `control_command`.
- A no-action policy decision is still sent as a `control_command` with empty
  `targets` and a clear `reason`.

First-version cycle:

```text
PYNQ -> PC: sensor_data
PC -> PYNQ: sleep_result
PC -> PYNQ: control_command
PYNQ -> PC: control_status
```

## PYNQ To PC: sensor_data

The board-side client sends `sensor_data` packets.

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

Minimum first-version fields:

| Field | Meaning |
|---|---|
| `type` | Must be `sensor_data`. |
| `timestamp` | Board-side or client-side timestamp string. |
| `sample_id` | Monotonic sample number. |
| `heart_rate_bpm` | Heart rate from UART SpO2; use `null` if unavailable. |
| `spo2_percent` | SpO2 from UART SpO2; use `null` if unavailable. |
| `accel_x`, `accel_y`, `accel_z` | JY901 acceleration values, preferably scaled in g. |
| `gyro_x`, `gyro_y`, `gyro_z` | Optional JY901 gyro values; may be `null`. |
| `mag_x`, `mag_y`, `mag_z` | Optional JY901 magnetometer values; may be `null`. |
| `turnover_flag` | `1` when the current sample indicates a turnover event, otherwise `0`. |
| `turnover_count` | Cumulative turnover count. |
| `temperature_c` | DHT11 or available temperature in degrees C. |
| `humidity_percent` | DHT11 humidity in percent RH. |
| `data_valid` | `1` when the packet is usable for PC classification. First-version classifier usability is based on valid HR/SpO2; a JY901-only failure should not force this to `0`. |
| `imu_valid` | Optional quality flag: `1` when the current sample contains a fresh JY901/IMU read. |
| `imu_stale` | Optional quality flag: `1` when IMU values were carried forward from a recent previous read after a retry failure. |
| `spo2_valid` | Optional quality flag: `1` when HR/SpO2 fields are present and checksum/sensor flags are acceptable. |
| `env_valid` | Optional quality flag: `1` when temperature/humidity fields are current or from the DHT11 cache. |
| `status_code` | Board-side status code; `0` means no known error for the packet. |
| `checksum_ok` | `1` when parsed sensor payloads passed their own checks. |
| `jy901_status` | Optional JY901 status label such as `OK`, `ERR`, or `STALE`. |
| `jy901_attempts` | Optional number of JY901 read attempts made for this sample. |
| `jy901_stale_s` | Optional age in seconds of reused IMU data when `imu_stale=1`; otherwise `null`. |
| `remark` | Short debug/status text. |

The board may still set JY901-related bits in `status_code` and preserve
`remark="jy901:..."` for observability while keeping `data_valid=1` if HR/SpO2
are valid. PC warm-up and automatic policy must not reset only because the
JY901 module had a transient read failure.

## PC To PYNQ: sleep_result

The PC server sends one `sleep_result` packet after receiving each
`sensor_data` packet. This message is classification output only; it must not
encode device-control actions.

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
| `type` | Must be `sleep_result`. |
| `timestamp` | PC-side result timestamp. |
| `sample_id` | Echoes the input sample ID. |
| `sleep_state_code` | `0` awake/not asleep, `1` light sleep, `2` deep sleep. |
| `state_valid` | `1` when the PC classifier result is valid. |
| `remark` | Classifier/debug status text. |

If `state_valid != 1`, automatic policy must not change AC or humidifier state.
PC still sends a no-action `control_command` after this `sleep_result`.

## PC To PYNQ: control_command

Device actuation uses a separate message from `sleep_result`. The PC policy
owns automatic AC and humidifier decisions; PYNQ validates and executes the
desired actuator targets.

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

No-action example:

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

Field rules:

| Field | Meaning |
|---|---|
| `type` | Must be `control_command`. |
| `timestamp` | PC-side command timestamp. |
| `sample_id` | Matches the triggering `sensor_data` sample. |
| `mode` | `auto` or `manual`. |
| `policy_id` | Policy/version identifier, for example `comfort_v1`. |
| `targets` | Object containing zero or more actuator targets. Empty means no action. |
| `valid` | `1` when the PC command schema is valid. |
| `reason` | Short policy/manual reason. Required for no-action and useful for logs. |

Target semantics:

| Target | Fields | Semantics |
|---|---|---|
| `ir_ac` | `command`, optional `temperature_setpoint_c` | One-shot IR pulse command. It does not prove or represent real AC state. |
| `humidifier` | `enabled` | Target state for the local board-controlled humidifier/LED actuator. |

First-version `ir_ac.command` values are limited to:

```text
power_on, power_off, temp_24, temp_25, temp_26, temp_27, temp_28
```

Manual dashboard controls:

- Dashboard manual buttons use real device semantics.
- `/api/control` stores a pending manual command; it does not send directly on
  the socket.
- The next `sensor_data` causes PC to send
  `control_command(mode="manual", reason="dashboard_manual")`.
- Manual AC commands are one-shot and clear after being sent.
- Desired-state is reserved for future UI work. First version must not
  automatically replay desired-state commands.

## PYNQ To PC: control_status

PYNQ replies with the actual execution result for accepted, skipped, and
rejected actuator commands.

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

Field rules:

| Field | Meaning |
|---|---|
| `type` | Must be `control_status`. |
| `timestamp` | PYNQ-side status timestamp. |
| `sample_id` | Matches the triggering `control_command`. |
| `accepted` | `1` if schema and targets were accepted for handling; `0` if rejected. |
| `applied` | Per-target execution details. |
| `status_code` | Structured status code. |
| `remark` | Short execution/debug reason. |

`status_code` values:

| Code | Meaning |
|---:|---|
| `0` | No error. |
| `1` | Rejected invalid command or schema. |
| `2` | Skipped by guard, cooldown, idle, or no-action policy. |
| `3` | Hardware execution error. |

For IR AC, `sent=true` means PYNQ sent the IR waveform and the IP completed; it
does not prove the lab AC received the command. The lab setup required the IR
transmitter to be within approximately 20 cm of the AC receiver for reliable
response. PC-side IR cooldown should be consumed by confirmed `sent=true`
status, not merely by issuing a `control_command`; skips such as
`ir_ac_missing` remain retryable after the normal policy checks.

The complete IR AC integration plan is in
[ir_ac_integration_plan.md](ir_ac_integration_plan.md).

## PC-Side Storage

First-version storage should preserve raw and derived records separately. Excel
or equivalent persistent storage should contain at least four record streams:

| Sheet | Purpose |
|---|---|
| `sensor_data` | Raw board-side packets. |
| `sleep_result` | PC classification results. |
| `control_command` | PC policy/manual desired actuator targets for a sample. |
| `control_status` | PYNQ accepted/skipped/applied execution result. |

Minimum control storage fields:

| Sheet | Fields |
|---|---|
| `control_command` | `timestamp`, `sample_id`, `mode`, `policy_id`, `targets_json`, `valid`, `reason` |
| `control_status` | `timestamp`, `sample_id`, `accepted`, `applied_json`, `status_code`, `remark` |

PC dependency:

```bash
pip install openpyxl
```

Do not keep the Excel file open while the server writes to it.

## Validation Steps

1. Validate `pc_server/protocol.py` encode/decode for all four message types.
2. Run the PC dashboard/service with a fake PYNQ client that sends
   `sensor_data`, receives `sleep_result` plus `control_command`, and returns
   `control_status`.
3. Confirm storage/dashboard state records all four message types.
4. Replace the fake client with a PYNQ client that sends synthetic data to the
   PC's real IPv4 address.
5. Replace synthetic PYNQ values with values read from the integrated driver
   suite.

Do not claim PC-integrated operation until a real PYNQ client connects to the
PC server and the PC records at least one board-originated packet plus the
matching `sleep_result`, `control_command`, and `control_status`.
