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
| Classifier path | Current `sleep_classifier.py` loads `sleep_model.bin` and performs pure-Python DREAMT GRU inference. It should be wrapped by a classifier adapter; PYNQ hardware drivers must not depend on model internals. |
| Protocol | Keep `sleep_result` as classifier output. Add `control_command` and `control_status` for actuator control. |
| Command shape | `control_command` carries complete desired actuator targets, not one isolated action. |
| Execution reporting | PYNQ must send `control_status` for accepted, skipped, and rejected commands. |
| Humidifier control | Final automatic humidifier control belongs to PC policy; PYNQ local humidifier automation is fallback/bring-up only. |
| IR protection | PYNQ enforces IR command validation, hardware minimum interval, and repeated-command cooldown. |
| Dashboard control semantics | Manual dashboard controls use real device semantics and create pending one-shot `control_command` messages; they must not be encoded as fake `sleep_result` values. |
| Message cadence | For each `sensor_data`, PC sends exactly two newline JSON messages in order: `sleep_result`, then `control_command`, including no-action commands. |
| Manual scheduling | Dashboard manual clicks set `pending_manual_command`; the command is sent with the next `sensor_data`, not asynchronously from the HTTP handler. |
| AC semantics | AC commands are one-shot IR pulses. `last_commanded_state` is a PC-side assumption for cooldown/display only, not real AC feedback. |
| Humidifier semantics | Humidifier uses target-state semantics because PYNQ can write/read the local actuator IP. |
| Desired-state | Desired-state is reserved for a later feature. First version may show or store it, but must not implement automatic desired-state replay/reconciliation. |
| Client count | First version supports one active PYNQ client only. |
| Dependencies | Prefer Python standard library plus `openpyxl`; new PC-only dependencies are allowed only when they materially reduce complexity or improve reliability. PYNQ stays Python 3.6/PYNQ-library compatible. |

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

### Out Of Scope For The First Software Integration Pass

- Training or replacing the current `sleep_model.bin` classifier.
- Optimizing dashboard UI beyond what is needed for acceptance.
- Adding new IR commands beyond the seven verified Gree YB0F2 presets.
- Adding IR RX to the final integrated overlay.
- Treating PC socket/Excel/dashboard behavior as accepted without a real PYNQ
  board-originated run.
- Automatic desired-state replay for AC.
- Multi-PYNQ client support.
- Dashboard immediate-send control bypasses.

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

First-version PYNQ client behavior:

- Keep `integrated_demo.py` as the local hardware smoke/fallback entry point.
- Add `board_orchestrator.py` for reusable hardware binding, sampling,
  display updates, humidifier control, and IR execution.
- Add `board_client.py` for socket transport only.
- Send one `sensor_data` per sample.
- Wait for the matching `sleep_result` and `control_command` for the same
  `sample_id`.
- Apply the command through `SleepMonitorBoard.apply_control_command()`.
- Send one `control_status` for accepted, skipped, and rejected commands.
- Print every received command and generated status to stdout.
- Add only a small TFT status line for recent control status, for example
  `AC: temp_26 sent` or `AC: skip cooldown`; do not build a local control UI.

Network behavior:

- PYNQ connects to the PC's real IPv4 address.
- Connection failure retries every 3 seconds.
- After sending `sensor_data`, wait up to 2 seconds for the two PC messages.
- On timeout or malformed messages, skip control for that sample, keep local
  display/sampling alive, and reconnect if the socket is broken.
- Close the socket cleanly on Ctrl+C.

PYNQ execution hard guards:

```text
IR_MIN_INTERVAL_S = 5
IR_REPEAT_COOLDOWN_S = 60  # demo default
```

Same IR command inside repeat cooldown is skipped and reported. Any unknown
target or unknown IR command is rejected and reported.

First-version `control_status.status_code` values:

| Code | Meaning |
|---:|---|
| `0` | No error. |
| `1` | Rejected invalid command or schema. |
| `2` | Skipped by guard, cooldown, idle, or no-action policy. |
| `3` | Hardware execution error. |

For IR AC, `sent=true` means PYNQ sent the IR waveform and the IP completed; it
does not prove the air conditioner received the command.

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
pc_server/classifier_adapter.py
pc_server/comfort_policy.py
pc_server/state_store.py
pc_server/storage.py
pc_server/service.py
pc_server/dashboard_server.py
pc_server/static/dashboard.html
pc_server/static/dashboard.css
pc_server/static/dashboard.js
```

`dashboard_server.py` may remain the top-level runnable entry if it composes
the service cleanly. It should not permanently own classifier, policy, socket,
storage, and dashboard state as unrelated global logic.

Legacy file policy:

- `pc_server.py` is legacy/minimal smoke only and does not constrain the final
  architecture.
- `fake_pynq_client.py` should be rewritten as a new-protocol simulator that
  sends `sensor_data`, receives `sleep_result` plus `control_command`, and
  returns `control_status`.
- `excel_utils.py` may remain an implementation detail behind `storage.py`.
- `dashboard_server.py` is the final PC entry point, but its static HTML/CSS/JS
  should be moved into `pc_server/static/`.

PC service state should live in a lightweight `AppState` object rather than
module-level globals. It should track one active client, latest records,
pending manual command, last commanded state, histories, and snapshots for the
dashboard. No database or event bus is needed for the first pass.

## Protocol Lifecycle

Final intended loop:

```text
PYNQ -> PC: sensor_data
PC: classify sensor_data into sleep_result
PC: policy builds control_command from sensor_data + sleep_result + state
PC -> PYNQ: sleep_result
PC -> PYNQ: control_command
PYNQ: applies targets and hardware guards
PYNQ -> PC: control_status
PC: logs/displays sensor_data, sleep_result, control_command, control_status
```

For every `sensor_data`, PC must send exactly two response messages in this
order: `sleep_result`, then `control_command`. A no-action decision is still a
valid `control_command` with empty `targets` and a reason.

`docs/protocol.md` owns the canonical message schemas.

Planned `control_command` targets:

```text
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

Dashboard manual mode:

- `/api/control` validates the requested real device action and stores it as
  `pending_manual_command`.
- It does not send directly on the socket.
- The next `sensor_data` turns the pending command into
  `control_command(mode="manual", reason="dashboard_manual")`.
- Manual commands are one-shot and clear after sending.
- When manual mode is active and no command is pending, PC sends no-action
  `control_command(reason="manual_idle")`.

## Automatic Comfort Policy

Inputs:

- `sleep_state_code`: `0` not asleep/awake, `1` light sleep, `2` deep sleep.
- `state_valid`.
- `temperature_c`.
- `humidity_percent`.
- Last commanded AC state and latest humidifier target/status.
- Cooldown state.
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
- AC automation outputs one-shot commands only; it does not maintain or replay
  an AC desired-state loop.
- Humidifier automation outputs target state because it is a local actuator.
- One `control_command` may contain both AC and humidifier targets, but the
  policy should generate combined actions conservatively.

Temperature tolerance bands:

| Sleep state | Suggested comfortable band |
|---:|---|
| `0` not asleep / awake | `24.5..27.0 C` |
| `1` light sleep | `24.0..27.5 C` |
| `2` deep sleep | `23.5..28.0 C` |

First-version action priority:

1. `state_valid != 1` or missing sensor data: no-action.
2. Manual mode: emit pending manual command or no-action `manual_idle`.
3. Humidity below 40%: `humidifier.enabled=true`.
4. Humidity above 60%: `humidifier.enabled=false`.
5. Temperature clearly high: send AC `temp_26` by default, using `temp_25` or
   `temp_24` only for stronger high-temperature cases after cooldown checks.
6. Temperature clearly low: send AC `temp_27` or `temp_28`.
7. Comfortable band: no-action.

Do not automatically send `power_off` in first-version policy; keep `power_off`
as a manual command unless a later validation pass explicitly changes this.

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

First-version persistent storage should contain four sheets or equivalent
record streams:

```text
sensor_data
sleep_result
control_command
control_status
```

Minimum extra storage fields:

| Record | Fields |
|---|---|
| `control_command` | `timestamp`, `sample_id`, `mode`, `policy_id`, `targets_json`, `valid`, `reason` |
| `control_status` | `timestamp`, `sample_id`, `accepted`, `applied_json`, `status_code`, `remark` |

Dashboard labels must distinguish:

- desired state: future UI concept, not automatically replayed in first pass;
- last commanded state: PC inference from recent commands;
- PYNQ execution status: `control_status`;
- real AC state: unknown without IR RX or AC feedback.

## Validation Plan

### SW-0: Protocol Contract

- Finalize `docs/protocol.md` field tables for `control_command` and
  `control_status`.
- Add `pc_server/protocol.py`.
- Add small PC-side encode/decode tests or fake message fixtures for all four
  message types.

Initial implementation:

- `pc_server/protocol.py` provides newline JSON encode/decode, incremental
  TCP message buffering, validation for `sensor_data`, `sleep_result`,
  `control_command`, and `control_status`, plus no-action/rejected-status
  helpers.
- `pc_server/protocol_selftest.py` is a dependency-free smoke test for round
  trips, split TCP chunks, no-action commands, and invalid command/status
  rejection.

### SW-1: PC Policy Unit Tests

- Test policy outputs for representative sleep states and temperature/humidity
  values.
- Test invalid/null sensor behavior.
- Test manual override.
- Test cooldown behavior and no-action reasons.

Initial implementation:

- `pc_server/comfort_policy.py` implements the first-version pure policy with
  no socket/dashboard/storage dependencies.
- It emits validated `control_command` dictionaries.
- It covers classifier warmup/no-action, humidity on/off, high-temperature AC
  command, IR cooldown, manual pending command, manual idle, and missing sensor
  data.
- `pc_server/comfort_policy_selftest.py` is the dependency-free smoke test.

### SW-1b: Classifier Adapter Boundary

- Wrap `sleep_classifier.py` behind a stable adapter before wiring it into
  socket service or dashboard logic.
- Validate incoming `sensor_data` and outgoing `sleep_result` with the
  canonical protocol module.
- On classifier load/runtime/schema errors, return a valid
  `sleep_result(state_valid=0)` with a clear remark instead of crashing the
  service loop.

Initial implementation:

- `pc_server/classifier_adapter.py` provides `SleepClassifierAdapter` and
  `classify_sensor_data()`.
- The adapter lazy-loads the real `sleep_classifier.classify_sleep_state`
  only when no test/fake classifier is injected.
- `pc_server/classifier_adapter_selftest.py` covers valid output, minimal
  output normalization, invalid classifier output, runtime exceptions, and
  invalid input sensor packets.

### SW-2: PC State And Storage

- Add `AppState`.
- Add four-record storage support.
- Confirm dashboard snapshots include sensor, model result, command, status,
  pending manual command, and last commanded state.

Initial implementation:

- `pc_server/state_store.py` provides a thread-safe `AppState` for one active
  client, latest records, bounded histories, pending one-shot manual command,
  control mode, and last-commanded actuator state.
- `pc_server/storage.py` provides the first JSONL storage backend with one
  validated append-only stream per protocol record type. This is an equivalent
  first-version record stream; an Excel backend can still be added behind the
  same boundary later.
- `pc_server/state_storage_selftest.py` covers snapshot copy isolation, pending
  manual command normalization, history bounding, control-state tracking, and
  four-record JSONL validation.

### SW-3: Dashboard Service Refactor

- Keep `dashboard_server.py` as the PC entry point.
- Split static HTML/CSS/JS into `pc_server/static/`.
- Keep `/api/state`, `/events`, `/api/mode`, and `/api/control`.
- Make `/api/control` pending-only; it must not directly send on the socket.

### SW-4: PC-Only Socket Simulation

- Rewrite fake client for the new protocol.
- Send `sensor_data`.
- Receive `sleep_result` then `control_command`.
- Return `control_status`.
- Confirm storage/dashboard state records all four message types.

### SW-5: PYNQ Orchestrator Local Smoke

- Run orchestrator without socket first.
- Confirm it can produce `sensor_data`.
- Confirm it can apply a synthetic humidifier target.
- Confirm it can reject unknown IR commands.
- Confirm IR rate-limit skip produces a valid `control_status`.
- Confirm local TFT/stdout control-status summary is concise and nonblocking.

### SW-6: PYNQ Real Socket Client

- Run the integrated board sensor loop.
- PC receives board-originated `sensor_data`.
- PC emits `sleep_result` and `control_command`.
- PYNQ applies humidifier and/or IR AC target under safeguards.
- PYNQ returns `control_status`.
- PC dashboard/logs show the complete loop.

## Open Items For This Phase

- Exact Python module names and file split can be refined immediately before
  implementation.
- `dashboard_server.py` is the mature PC entry point, but its responsibilities
  should be decomposed into service/state/policy/storage modules.
- Current `sleep_classifier.py` is a real pure-Python model implementation
  backed by `sleep_model.bin`; wrap it with an adapter instead of coupling
  service/dashboard logic to classifier internals.
- Board system time must be fixed before timestamp-sensitive logging evidence.
