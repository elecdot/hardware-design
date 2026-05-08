# AGENTS.md

Read README.md first for the project overview, hardware platform, external
modules, system architecture, repository layout, open loops, and documentation
index. Read relevant directory-level README files for the local conventions.

## Testing Requirements

Before claiming a module works, provide evidence for at least one of these
levels:

1. **Simulation pass**
   - Testbench waveforms match expected protocol timing.
   - Testbenches should emit clear PASS/FAIL output for automated review.
2. **Single-module hardware pass**
   - The module works with the actual sensor/display/actuator.
3. **AXI driver pass**
   - PYNQ-side Python can read/write registers and obtain expected values.
4. **Integrated system pass**
   - Multiple IPs work together in the Block Design.
5. **End-to-end pass**
   - PYNQ reads data, displays it, sends it to PC, and the PC saves or
     visualizes it.

For every fix, prefer adding a small reproducible test over only editing the
final notebook.

## Agent Operating Rules

Act as an expert in PYNQ-Z1 design, integration, and development. If upcoming
work depends on unclear information, search for it or request confirmation from
the human.

When working in this repo:

1. First identify whether the requested change is RTL, Vivado integration,
   PYNQ driver, PC server, analysis, documentation, or report-writing.
2. Do not invent pin assignments, register maps, sensor frame formats, or
   trained model details. Mark unknowns explicitly and leave TODOs.
3. Preserve the current working flow unless the user asks for a refactor.
4. Prefer small, reviewable changes.
5. Keep generated code compatible with Vivado/PYNQ constraints.
6. Update documentation when changing protocols, register maps, frame formats,
   external ports, or wiring.
7. Keep README files up to date when directory purpose, entry points, or
   important status changes.
8. For hardware-facing changes, include a test plan.
9. For notebook changes, move reusable code into modules where possible.
10. For data analysis changes, keep raw data immutable and write processed
    outputs separately.
11. Never claim a hardware feature is verified unless there is simulation
    output, board test evidence, or user-confirmed measurement.

## Hardware Safety

- Treat PYNQ-Z1 Arduino/PMOD I/O as 3.3 V logic.
- Do not hot-plug sensor wires while the board is powered.
- Verify VCC, GND, and signal voltage before connecting modules.
- Use level shifting or isolation when driving modules that require 5 V
  signaling.
- Do not drive loads such as humidifiers, fans, IR LEDs, or speakers directly
  from FPGA pins.

## Definition of Done

Checklist before a feature is done:

- Relevant RTL or Python code is implemented and ready to commit.
- Register map or protocol documentation is updated.
- Constraints are updated if external ports changed.
- Simulation or board-level test evidence exists.
- The feature can be demonstrated or explained for course assessment.
- Any known limitations are documented.

Commit only when the user explicitly requests it.
