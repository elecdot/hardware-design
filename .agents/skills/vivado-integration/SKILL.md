---
name: vivado-integration
description: Use when working on Vivado projects, custom IP packaging, IP repositories, Block Design integration, Zynq PS wiring, AXI interconnects, XDC constraints, bitstream generation, or PYNQ overlay export in this PYNQ-Z1 repository.
---

# Vivado Integration

Use this skill for Vivado project, packaging, constraints, and overlay export work.

## First Reads

Read these before editing:

- `README.md` for current project state and target hardware.
- `AGENTS.md` for safety and verification requirements.
- `vivado/README.md`, `vivado/project/README.md`, and `vivado/constraints/README.md`.
- Relevant RTL README files under `rtl/`.
- `docs/wiring.md` and `docs/register_map.md` when exposing ports or integrating AXI IP.

## Target Hardware

- Board/chip target: PYNQ-Z1 / `xc7z020clg400-1`.
- Treat external PL I/O as 3.3 V logic.
- Current design assumption: 100 MHz system/AXI clock unless a specific design document says otherwise.

## Integration Workflow

1. Confirm source RTL lives under `rtl/<ip_name>/`; do not treat Vivado-generated copies as authoritative source.
2. Create or open the Vivado project only after identifying whether the task is project setup, IP packaging, Block Design, constraints, simulation, or export.
3. Add or refresh the custom IP repository when packaging IP under `vivado/ip_repo/`.
4. In Block Design, add Zynq PS, required AXI GP master interface, AXI interconnect or SmartConnect, processor reset, and custom AXI slaves.
5. Connect clocks and resets explicitly through Processor System Reset or the existing project convention.
6. Expose external ports only when required, and document them.
7. Apply XDC constraints from `vivado/constraints/`; do not invent pin assignments.
8. Add ILA probes for hard-to-debug internal signals when useful, and remove or disable debug IP when not needed.
9. Run validation, synthesis, implementation, and bitstream generation when the task requires it.
10. Export `.bit` and `.hwh` together for PYNQ overlay use.

## Source Control Conventions

- Keep XDC source files under `vivado/constraints/`.
- Prefer future Tcl scripts under `vivado/scripts/` for reproducible project creation.
- Generated Vivado cache, run, hardware, IP user files, and simulation output are not design source unless intentionally preserved as evidence.
- If a Vivado project is committed, document its entry point and source ownership in its local README.

## Verification

- Do not claim integrated hardware works from successful synthesis alone.
- For integration-level claims, provide at least Block Design validation, build logs, exported artifacts, ILA evidence, or user-confirmed board results as appropriate.
