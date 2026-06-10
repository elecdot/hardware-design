# IR AC Integration Plan

This document freezes the plan for integrating the Gree IR air-conditioner
module into the final sleep-monitor system. It is a planning document; do not
treat the final integrated overlay as verified until the Phase gates below have
board evidence.

Scope boundary:

- Current implementation scope: TX-only IR hardware platform integration and
  board demo validation, through `IR-5`.
- Deferred software scope: PC/PYNQ socket integration, dashboard refactor,
  classifier/policy integration, and end-to-end control loop. Confirmed
  software decisions are recorded in
  [software_integration_plan.md](software_integration_plan.md) so that work can
  be picked up after IR hardware validation.

## Confirmed Decisions

| Topic | Decision |
|---|---|
| Scope | First integrated version is TX-only. `ir_capture_axi` remains a standalone validation tool. |
| Pin | Use `ir_pwm` on Arduino `ck_io[0]`, package pin `T14`, from the handoff XDC. |
| Command set | Only expose the seven verified Gree YB0F2 presets: `power_on`, `power_off`, `temp_24`, `temp_25`, `temp_26`, `temp_27`, `temp_28`. |
| Standalone evidence | The teammate completed standalone module testing and confirmed the lab Gree AC responds. |
| Control ownership | PC policy owns automatic AC and humidifier decisions. PYNQ validates and executes commands. |
| PYNQ fallback | Local PYNQ humidifier automation remains only for bring-up/fallback, not the final automatic policy owner. |
| Protocol | Add `control_command` from PC to PYNQ and `control_status` from PYNQ to PC. |
| Soft architecture | Build a PYNQ top-level orchestrator class and a PC-side integration service/policy layer. |

## Handoff Source Facts

Source package:

```text
handoff/gree_ir_txrx_hardware_package/
```

Relevant files:

```text
synthesis/vivado/rtl/tx/gree_ir_core.v
synthesis/vivado/rtl/tx/gree_ir_axi_v1_0.v
synthesis/vivado/rtl/tx/gree_ir_axi_v1_0_S00_AXI.v
synthesis/vivado/constraints/pynq_z1_ir_txrx.xdc
pynq/ir_txrx.py
pynq/gree_yb0f2_command_library_7.json
docs/register_map.md
docs/wiring.md
```

Standalone TX register map from the handoff package:

| Offset | Name | Description |
|---:|---|---|
| `0x00` | `CONTROL` | bit0 `start`, bit1 `soft_reset`. |
| `0x04` | `STATUS` | bit0 `busy`, bit1 `done`, bit2 `error`. |
| `0x08` | `CMD_LOW` | Low 32 bits of selected compatibility command. |
| `0x0C` | `CMD_HIGH` | High 32 bits of selected compatibility command. |
| `0x10` | `PRESET` | 67-bit waveform preset selector. |
| `0x14` | `DEBUG` | Core state and sample index. |

The TX RTL sends 67-bit Gree YB0F2 commands from preset ROM. It is not a
general Gree protocol encoder, and raw arbitrary command transmission is not
part of the first integrated scope.

## Hardware Safety

- All PYNQ-Z1 PL-facing IR module signals must be 3.3 V logic.
- Do not drive a bare IR LED directly from an FPGA pin.
- Use an IR transmitter module or a transistor/MOSFET driver for a bare IR LED.
- If the IR transmitter has an external supply, connect its ground to PYNQ
  ground and confirm the signal input is 3.3 V-compatible.
- Do not hot-plug modules while the board is powered.

## Proposed Integrated Hardware Plan

Add only the TX IP to the next integrated Vivado overlay.

Planned sources:

```text
rtl/gree_ir_axi/
  gree_ir_core.v
  gree_ir_axi_v1_0.v
  gree_ir_axi_v1_0_S00_AXI.v
```

Planned external port:

```text
ir_pwm
```

Planned constraint:

```tcl
set_property -dict { PACKAGE_PIN T14 IOSTANDARD LVCMOS33 } [get_ports ir_pwm]
```

Recommended integrated address:

| IP instance | Proposed base | Range | Notes |
|---|---:|---:|---|
| `gree_ir_axi_v1_0_0` | `0x4000_5000` | 4K | Final address must be assigned and confirmed in Vivado Address Editor. |

The 4K range matches the existing integrated overlay style. If Vivado package
metadata requires a larger range, record the final assigned range before PYNQ
driver binding.

## Protocol Plan

Keep `sleep_result` as classification output only. Device actuation uses
`control_command`.

PC to PYNQ:

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

PYNQ to PC:

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

Protocol rules:

- `sleep_result` remains PC classifier output.
- `control_command.targets` describes the full desired actuator state for a
  sample, not a single isolated action.
- PYNQ must reject unknown targets and unknown IR commands.
- PYNQ must send `control_status` for accepted, skipped, and rejected commands.

## Automatic Policy Plan

The PC policy combines:

- sleep state classification: `0` awake/not asleep, `1` light sleep, `2` deep
  sleep;
- environment data: temperature and humidity;
- latest known actuator state;
- command cooldown state.

Sleep-state aggressiveness profile:

| Sleep state | Meaning | Aggressiveness | Policy intent |
|---:|---|---:|---|
| `0` | Not asleep / awake | `1.0` | Narrow comfort band, faster correction. |
| `1` | Light sleep | `0.6` | Moderate correction. |
| `2` | Deep sleep | `0.3` | Wider acceptance band, avoid disturbance. |

First-version comfort policy:

- Humidity comfort target: roughly `40..60% RH`.
- If humidity is clearly low, prefer humidifier control before AC changes.
- If humidity is high, suppress humidifier.
- Temperature setpoint should stay within the verified IR command set
  `24..28 C`.
- Deep sleep should avoid frequent or aggressive changes unless temperature or
  humidity is clearly outside the comfort band.
- Manual dashboard mode overrides automatic policy intent, but PYNQ hardware
  safety limits still apply.
- Invalid or missing sensor/classifier data should produce a no-action
  `control_command` with an explanatory `reason`.

Cooldown recommendations:

| Mode | Same IR command repeat | Any IR command minimum interval |
|---|---:|---:|
| Demo | 30 to 60 s | 5 s |
| Normal | 5 to 10 min | 5 s |

PYNQ execution layer hard guards:

- `IR_MIN_INTERVAL_S = 5`
- `IR_REPEAT_COOLDOWN_S = 60` for demo defaults
- Same IR command inside repeat cooldown is skipped and reported.
- Different IR command inside the minimum hardware interval is skipped or
  deferred and reported.

## Deferred Software Architecture Summary

The confirmed software direction is summarized here only to keep the IR
hardware plan aligned with the final system. The executable software plan is
[software_integration_plan.md](software_integration_plan.md).

PYNQ side:

```text
SleepMonitorBoard / BoardOrchestrator
  - binds integrated overlay IPs
  - reads JY901, DHT11, SpO2
  - updates TFT
  - applies humidifier target state
  - applies IR AC command through gree_ir_axi
  - enforces actuator validation and rate limits
  - builds control_status
```

PC side:

```text
PcIntegrationService
  - socket server
  - classifier adapter, later replaceable by neural network output
  - comfort policy engine
  - dashboard state
  - storage/logger
```

`pc_server/` currently contains demo-quality code. It may be refactored to make
the final software integration stable. The final design should preserve the
protocol contract first, then adapt `dashboard_server.py`, `pc_server.py`, and
Excel logging around that contract.

## IR Hardware Execution Plan

### IR-0: Standalone Evidence Capture

- Record the teammate-provided standalone test result in `docs/test_plan.md`.
- Preserve the distinction between standalone AC response and integrated overlay
  response.
- Minimum evidence: lab Gree AC responds to at least one preset command.
- Preferred evidence: `power_on`, one temperature command such as `temp_26`,
  and `power_off` all respond.

### IR-1: Source Migration Skeleton

Status: complete.

- Copy TX-only RTL into `rtl/gree_ir_axi/`.
- Copy or adapt the PYNQ TX driver into `pynq/ir_ac_demo/`.
- Do not migrate RX RTL into the first integrated source path.
- Add local README files for the new RTL and PYNQ subtrees.
- Update `rtl/README.md`, `pynq/README.md`, `docs/wiring.md`, and
  `docs/register_map.md`.

### IR-2: Module Regression

- Add a focused simulation for TX preset selection and done/error behavior.
- Test at least one preset and ideally all seven preset IDs.
- Testbench output must include explicit PASS/FAIL.
- This does not claim real AC behavior; it only validates RTL behavior.

### IR-3: IP Packaging

- Package `gree_ir_axi_v1_0` from tracked `rtl/gree_ir_axi/`.
- Keep RX package out of the first integrated IP repo unless intentionally
  needed for validation.
- Validate AXI4-Lite metadata, external port `ir_pwm`, parameters, and source
  file sets.

### IR-4: Integrated Vivado Overlay

- Add `gree_ir_axi_v1_0_0` as the next AXI slave.
- Proposed address is `0x4000_5000`, final value to be confirmed in Vivado.
- Expose `ir_pwm` and constrain it to `T14`.
- Run BD validation, synthesis, implementation, DRC, route status, timing, and
  bitstream generation.
- Export matching `.bit`, `.hwh`, and any board-needed `.tcl` into `vivado/gen/`.

### IR-5: PYNQ Board Bring-Up

- Extend the integrated static metadata fallback with `gree_ir_axi_v1_0_0`.
- Bind the IR TX driver through the top-level orchestrator.
- Run a TX-only board smoke command that sends a safe command, preferably
  `temp_26` or a mutually agreed non-disruptive preset.
- Record TX status: `done=true`, `error=false`.
- If the lab AC is available, confirm real response again from the integrated
  overlay.

## Deferred Software Execution

After `IR-5` passes, continue with
[software_integration_plan.md](software_integration_plan.md). Target final flow:

```text
PYNQ reads sensors
PC receives sensor_data
PC classifier emits sleep_result
PC policy emits control_command
PYNQ applies humidifier and/or IR AC target
PYNQ sends control_status
PC dashboard/logs show the full loop
```

## Known Open Items

- Final integrated IR address is not assigned until Vivado BD update.
- `control_command` and `control_status` are planned but not implemented.
- The PYNQ top-level orchestrator class is planned but not implemented.
- PC policy defaults need implementation and test fixtures.
- Board system time must be corrected before timestamp-sensitive PC logging.
