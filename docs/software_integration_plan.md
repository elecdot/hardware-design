# Software Integration Plan

This document records the confirmed software-integration decisions so future
work can be picked up after the IR hardware platform integration and IR demo
test are complete.

The IR hardware entry gate is now satisfied. TX-only Gree IR AC integration is
closed through `IR-5`, including real lab AC response from the integrated
`system_v0_2` overlay. This software plan is now the next implementation scope.

## Entry Gate

Status: satisfied as of 2026-06-12.

- [x] The current integrated local board demo remains stable with JY901, DHT11,
  UART SpO2, TFT, and humidifier.
- [x] TX-only Gree IR AC is added to the integrated Vivado overlay.
- [x] The integrated overlay exports matching `.bit`, `.hwh`, and board-needed
  metadata into `vivado/gen/`.
- [x] PYNQ can bind or statically resolve the IR TX IP address.
- [x] Safe IR commands were sent from the integrated overlay and produced
  acceptable board/AC evidence: `power_on`, `power_off`, and `temp_26`.

Carry-forward hardware constraint for software integration:

- The IR transmitter must be aimed at the lab Gree AC receiver and kept within
  approximately 20 cm for reliable response. Software should report TX status
  and command history, but it cannot infer successful AC reception from the
  AXI `done` bit alone.

## Confirmed Decisions

| Topic | Decision |
|---|---|
| PYNQ architecture | Build a top-level `SleepMonitorBoard` / `BoardOrchestrator` class instead of keeping final logic inside notebooks or a monolithic script. |
| PC architecture | Refactor `pc_server/` as needed; current files are demo-quality and do not constrain the final architecture. |
| Policy owner | PC policy owns automatic AC and humidifier decisions. |
| PYNQ role | PYNQ validates, rate-limits, executes actuator commands, updates local display, and reports execution status. |
| Neural network path | Future neural-network output plugs into the PC classifier adapter/policy layer, not into PYNQ hardware drivers. |
| Protocol | Keep `sleep_result` as classifier output. Add `control_command` and `control_status` for actuator control. |
| Command shape | `control_command` carries complete desired actuator targets, not one isolated action. |
| Execution reporting | PYNQ must send `control_status` for accepted, skipped, and rejected commands. |
| Humidifier control | Final automatic humidifier control belongs to PC policy; PYNQ local humidifier automation is fallback/bring-up only. |
| IR protection | PYNQ enforces IR command validation, hardware minimum interval, and repeated-command cooldown. |

## Scope Boundary

### In Scope For This Later Phase

- PYNQ top-level class wrapping existing sensor, display, humidifier, and IR
  drivers.
- Board-side socket client that sends `sensor_data`, receives
  `control_command`, applies targets, and sends `control_status`.
- PC service refactor around protocol handling, classifier adapter, comfort
  policy, dashboard state, and storage.
- Dashboard manual controls that emit real `control_command.targets`.
- PC-side automatic policy combining sleep state, temperature, humidity, and
  latest actuator state.
- Logging of raw sensor data, classifier output, policy decision, and PYNQ
  execution result as separate records.

### Out Of Scope Until This Phase Starts

- Replacing the placeholder classifier with a neural network.
- Optimizing dashboard UI beyond what is needed for acceptance.
- Adding new IR commands beyond the seven verified Gree YB0F2 presets.
- Adding IR RX to the final integrated overlay.
- Treating PC socket/Excel/dashboard behavior as accepted without a real PYNQ
  board-originated run.

## PYNQ Top-Level Class Plan

Planned responsibility:

```text
SleepMonitorBoard / BoardOrchestrator
  - load or receive an integrated overlay handle
  - bind IPs by metadata or documented static fallback
  - read JY901, DHT11, and SpO2
  - maintain turnover counter
  - update TFT dashboard
  - apply humidifier target state
  - apply IR AC target command
  - enforce actuator validation and rate limits
  - produce sensor_data and control_status dictionaries
```

Likely first files:

```text
pynq/sleep_demo/board_orchestrator.py
pynq/sleep_demo/board_client.py
```

`integrated_demo.py` can remain a local demo entry point. The mature socket
client should reuse the orchestrator instead of duplicating MMIO and display
logic.

Suggested method boundary:

```python
board = SleepMonitorBoard(...)
sample = board.read_sample()
board.update_display(sample)
status = board.apply_control_command(command)
```

PYNQ execution hard guards:

```text
IR_MIN_INTERVAL_S = 5
IR_REPEAT_COOLDOWN_S = 60  # demo default
```

Same IR command inside repeat cooldown is skipped and reported. Any unknown
target or unknown IR command is rejected and reported.

## PC Service Plan

The current `pc_server/` files can be refactored. Final structure should keep
these concerns separable:

```text
protocol codec
socket service
classifier adapter
comfort policy
dashboard state
storage/logger
```

Recommended first-version modules:

```text
pc_server/protocol.py
pc_server/comfort_policy.py
pc_server/service.py
pc_server/dashboard_server.py
```

`dashboard_server.py` may remain the top-level runnable entry if it composes
the service cleanly. It should not permanently own classifier, policy, socket,
storage, and dashboard state as unrelated global logic.

## Protocol Lifecycle

Final intended loop:

```text
PYNQ -> PC: sensor_data
PC: classify sensor_data into sleep_result
PC: policy builds control_command from sensor_data + sleep_result + state
PC -> PYNQ: control_command
PYNQ: applies targets and hardware guards
PYNQ -> PC: control_status
PC: logs/displays sensor_data, sleep_result, control_command, control_status
```

`docs/protocol.md` owns the canonical message schemas.

Planned `control_command` targets:

```text
ir_ac.enabled
ir_ac.command
ir_ac.temperature_setpoint_c
humidifier.enabled
```

First-version `ir_ac.command` values:

```text
power_on
power_off
temp_24
temp_25
temp_26
temp_27
temp_28
```

## Automatic Comfort Policy

Inputs:

- `sleep_state_code`: `0` not asleep/awake, `1` light sleep, `2` deep sleep.
- `temperature_c`.
- `humidity_percent`.
- Latest known AC/humidifier state.
- Last command timestamps.
- Manual/auto mode.

Sleep-state aggressiveness profile:

| Sleep state | Meaning | Aggressiveness | Behavior |
|---:|---|---:|---|
| `0` | Not asleep / awake | `1.0` | More active adjustment. |
| `1` | Light sleep | `0.6` | Moderate adjustment. |
| `2` | Deep sleep | `0.3` | Wider acceptance, less disturbance. |

First-version policy principles:

- Manual mode overrides automatic policy intent.
- Invalid or missing sensor/classifier inputs produce a no-action
  `control_command` with a reason.
- Humidity target is roughly `40..60% RH`.
- Low humidity prioritizes humidifier before AC changes.
- High humidity suppresses humidifier.
- AC setpoints stay in the verified `24..28 C` range.
- Deep sleep widens acceptable environmental range and lengthens cooldowns.
- Policy should output at most one coherent `control_command.targets` state per
  decision cycle.

Cooldown defaults:

| Mode | Same IR command repeat | Any IR command minimum interval |
|---|---:|---:|
| Demo | 30 to 60 s | 5 s |
| Normal | 5 to 10 min | 5 s |

## Storage And Dashboard Plan

Raw and derived records should stay distinguishable:

| Record | Purpose |
|---|---|
| `sensor_data` | Raw board-originated measurements. |
| `sleep_result` | PC classifier output. |
| `control_command` | PC policy/manual desired actuator targets. |
| `control_status` | PYNQ accepted/skipped/applied execution result. |

Excel logging or dashboard history should not overwrite raw sensor data with
classifier or policy outputs. This keeps later neural-network integration and
report analysis clean.

## Validation Plan

### SW-0: Protocol Contract

- Finalize `docs/protocol.md` field tables for `control_command` and
  `control_status`.
- Add small PC-side encode/decode tests or fake message fixtures.

### SW-1: PC Policy Unit Tests

- Test policy outputs for representative sleep states and temperature/humidity
  values.
- Test invalid/null sensor behavior.
- Test manual override.
- Test cooldown behavior and no-action reasons.

### SW-2: PYNQ Orchestrator Local Smoke

- Run orchestrator without socket first.
- Confirm it can produce `sensor_data`.
- Confirm it can apply a synthetic humidifier target.
- Confirm it can reject unknown IR commands.
- Confirm IR rate-limit skip produces a valid `control_status`.

### SW-3: PC-Only Socket Simulation

- Use a fake PYNQ client to send `sensor_data`.
- Confirm PC replies with `sleep_result` and `control_command`.
- Confirm fake client returns `control_status`.
- Confirm storage/dashboard state records all four message types.

### SW-4: PYNQ Synthetic Socket Client

- Run on board with synthetic or fixed sensor data.
- Confirm connection to PC real IPv4 address.
- Confirm command receive and status response without touching hardware.

### SW-5: Real Board End-To-End

- Run the integrated board sensor loop.
- PC receives board-originated `sensor_data`.
- PC emits classifier and control decisions.
- PYNQ applies humidifier and/or IR AC target under safeguards.
- PC dashboard/logs show the complete loop.

## Open Items For This Phase

- Exact Python module names and file split can be refined immediately before
  implementation.
- Final Excel schema can be chosen after deciding whether `dashboard_server.py`
  or a new service entry is the mature PC entry point.
- Neural-network model interface remains future work; first version uses a
  classifier adapter around the existing placeholder rules.
- Board system time must be fixed before timestamp-sensitive logging evidence.
