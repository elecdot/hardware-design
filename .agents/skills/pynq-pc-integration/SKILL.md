---
name: pynq-pc-integration
description: Use when working on PYNQ Python overlays, MMIO drivers, board-side runtime clients, notebooks, TCP socket transmission, PC-side receive services, payload protocols, storage, or analysis handoff in this sleep monitoring repository.
---

# PYNQ PC Integration

Use this skill for PS-side Python, PYNQ overlay drivers, board-to-PC transport, PC server, and analysis handoff work.

## First Reads

Read these before editing:

- `README.md` for system architecture and open loops.
- `AGENTS.md` for testing and Definition of Done.
- `docs/register_map.md` before writing MMIO drivers.
- `docs/protocol.md` before changing board-to-PC payloads.
- `docs/test_plan.md` before claiming runtime behavior works.
- Relevant directory README files when `pynq/`, `pc_server/`, `analysis/`, or `tests/` exist.

## PYNQ-Side Workflow

1. Load the overlay and matching `.hwh`.
2. Bind each custom IP by name from the overlay object.
3. Wrap raw MMIO accesses in driver classes or functions; avoid magic offsets in notebooks.
4. Initialize display and sensors through reusable Python modules, not notebook-only code.
5. Poll UI-level values at a readable period, typically around 1 second unless a module needs faster sampling.
6. Run lightweight local logic only: turning detection, threshold decisions, local flags, display refresh, and send scheduling.
7. Close sockets and files cleanly on stop conditions.

Suggested clear function names:

```python
def get_mpu9250(): ...
def get_hr_spo2(): ...
def get_dht11(): ...
def detect_turning(window): ...
def set_ir_ac_mode(mode): ...
def set_humidifier(enabled): ...
def update_display(sample): ...
def send_sample(sock, sample): ...
```

If old unclear names are kept for compatibility, wrap them with clearer aliases.

## PC-Side Workflow

1. Start the TCP server before the PYNQ client connects.
2. Decode incoming frames using one canonical protocol definition.
3. Validate field count, value ranges, and timestamp order.
4. Save raw records before sleep-stage prediction, smoothing, or visualization.
5. Use stable column names:

```text
Time, BPM, SPO2, Temperature, Humidity, accel_x, accel_y, accel_z, turn_count, sleep_stage, flags
```

## Python Rules

- Keep notebooks thin; put reusable logic into `.py` modules.
- Use dataclasses or dictionaries for sensor samples.
- Use clear names such as `bpm`, `spo2`, `temperature`, `humidity`, and `accel_x`.
- Add range checks for sensor data.
- Avoid infinite loops without a clean stop condition.
- Use logging or structured debug output.
- Do not silently swallow socket, file, parsing, or MMIO exceptions.
- Keep raw data immutable; write processed outputs separately.

## Protocol Rules

- Define the board-to-PC payload in exactly one canonical place and mirror it on both sides.
- Prefer newline-delimited JSON during development because it is easy to inspect.
- Move to binary frames only after documenting byte order, signedness, scaling, framing, length/checksum, and end condition.
