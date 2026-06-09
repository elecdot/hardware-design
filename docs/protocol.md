# Protocol

PYNQ-to-PC socket payload format for the PC logging/classification path. This
path is part of the final system architecture, but it is a later priority than
the local integrated overlay and driver demo. When socket is included, use this
newline-delimited JSON protocol.

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
  "status_code": 0,
  "checksum_ok": 1,
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
| `data_valid` | `1` when the packet contains usable sensor data. |
| `status_code` | Board-side status code; `0` means no known error for the packet. |
| `checksum_ok` | `1` when parsed sensor payloads passed their own checks. |
| `remark` | Short debug/status text. |

## PC To PYNQ: sleep_result

The PC server replies with one `sleep_result` packet after receiving a
`sensor_data` packet.

```json
{
  "type": "sleep_result",
  "timestamp": "2026-06-02 14:30:03",
  "sample_id": 1,
  "sleep_state_code": 1,
  "state_valid": 1,
  "remark": "rule_light_sleep"
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

## Planned PC To PYNQ: control_command

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
      "enabled": true,
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

First-version `ir_ac.command` values are limited to:

```text
power_on, power_off, temp_24, temp_25, temp_26, temp_27, temp_28
```

## Planned PYNQ To PC: control_status

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
      "command": "temp_26",
      "sent": true,
      "skipped": false,
      "skip_reason": null
    },
    "humidifier": {
      "enabled": true,
      "applied": true
    }
  },
  "status_code": 0,
  "remark": "control_applied"
}
```

The complete IR AC integration plan is in
[ir_ac_integration_plan.md](ir_ac_integration_plan.md).

## PC-Side Storage

The handoff PC server writes `sleep_monitor_data.xlsx` with two sheets:

| Sheet | Purpose |
|---|---|
| `sensor_data` | Raw board-side packets. |
| `sleep_result` | PC classification results. |

PC dependency:

```bash
pip install openpyxl
```

Do not keep the Excel file open while the server writes to it.

## Validation Steps

1. Run `pc_server.py` on the PC.
2. Run `fake_pynq_client.py` on the same PC and confirm JSON send/receive,
   Excel append, and `sleep_result` response.
3. Replace the fake client with a PYNQ client that sends synthetic data to the
   PC's real IPv4 address.
4. Replace synthetic PYNQ values with values read from the integrated driver
   suite.

Do not claim PC-integrated operation until a real PYNQ client connects to the
PC server and the PC records at least one board-originated packet.
