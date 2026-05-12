# scripts

Vivado Tcl automation, board presets, and reproducible project/build entry
points live here.

## Layout

| Path | Purpose |
|---|---|
| [presets/](presets/) | Board and processing-system presets used by Vivado projects. |

## Registered Scripts

| Path | Purpose |
|---|---|
| [presets/pynq_revC.tcl](presets/pynq_revC.tcl) | PYNQ-Z1 Rev C processing_system7 preset. |

## Rules

- Track Tcl files that are required to recreate or configure a design.
- Keep scripts path-relative to the repo when possible.
- Document the target board, part, and Vivado version when a script depends on
  them.
- Do not commit generated journals, logs, run directories, cache output, or
  machine-specific path dumps as source scripts.
