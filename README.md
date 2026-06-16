# Smart Sleep Monitoring Assistance System

This repository is for a Computer Hardware Comprehensive Course Design project:
a low-cost, non-invasive, home-oriented sleep monitoring and assistance system
built around the PYNQ-Z1 / Zynq-7000 XC7Z020 platform.

The system collects physiological, motion, and environmental data, displays key
runtime values locally, sends structured records to a PC-side service, and may
trigger simple assistance actions such as IR air-conditioner control,
humidifier control, or sleep-aid prompts.

System outputs are auxiliary estimates only. They are not clinical diagnosis
results.

## Project Overview

Core goals:

- Collect sleep-related signals during overnight operation.
- Estimate sleep state and sleep stability from multiple signals.
- Display key values on the board-side display.
- Send runtime data to a PC service for logging, analysis, and visualization.
- Keep the implementation explainable for course assessment and debugging.

Current workspace status:

- The current integrated hardware platform is `system_v0_2`, exported under
  `vivado/gen/` as matching `.bit`, `.hwh`, and `.tcl` artifacts.
- The integrated board demo path has board evidence for JY901, DHT11, UART
  SpO2, TFT LCD, humidifier status/control, and TX-only Gree IR AC.
- TX-only Gree IR AC integration is closed for the hardware scope: source
  migration, regression, IP packaging, Block Design integration, PYNQ smoke,
  and real lab AC response are recorded.
- PC/PYNQ software integration now has a classroom-demo-ready first pass:
  canonical four-message protocol, board-side socket client/orchestrator,
  PC classifier adapter, comfort policy, JSONL storage, dashboard entry,
  pending-only manual controls, and a display-only desired-state panel.

## Hardware Platform

Target board:

- Board: PYNQ-Z1
- Chip: Xilinx Zynq-7000 XC7Z020, `xc7z020clg400-1`
- PS: ARM Cortex-A9 processing system
- PL: FPGA programmable logic
- PS-PL communication: AXI / AXI-Lite

Important constraints:

- Treat PYNQ-Z1 external I/O as 3.3 V logic only.
- Do not hot-plug sensors or wires while the board is powered.
- Keep clock assumptions explicit in RTL parameters, register docs, and XDC.
- The current design assumes a 100 MHz system/AXI clock unless documented
  otherwise.

## Main External Modules

Input sensing modules:

| Module | Data | Planned interface | Status |
|---|---|---|---|
| Heart-rate / SpO2 sensor | BPM, SPO2 | UART custom IP | Integrated local board demo pass; physical RX/TX orientation note recorded |
| JY901 / MPU9250 IMU | Acceleration, gyro, attitude, temperature | I2C custom IP | Integrated local board demo pass |
| DHT11 | Temperature, humidity | One-Wire custom IP | Integrated local board demo pass |

Display and assistance modules:

| Module | Purpose | Planned interface | Status |
|---|---|---|---|
| 1.3-inch TFT display | Board-side real-time display | SPI custom IP | Integrated local board demo pass |
| IR air-conditioner transmitter | Environment assistance | IR custom IP | TX-only integrated hardware scope complete; lab Gree AC response confirmed |
| Humidifier or indicator | Simple actuator control | GPIO / PWM / relay-style output | Integrated local board demo pass |
| Sleep-aid prompt module | Optional audio or prompt output | PDM / PWM / audio | Planned |

## System Architecture

The system is organized into three layers.

1. PL-side custom IP layer
   - Implements timing-sensitive peripheral protocols.
   - Exposes clean AXI-Lite register interfaces to the PS.
   - Keeps board pin assignments in XDC, not RTL.

2. PYNQ board-side client
   - Loads bitstream and overlay metadata.
   - Binds custom IP by overlay name.
   - Reads sensors through MMIO drivers.
   - Runs lightweight local rules such as turning detection and threshold flags.
   - Updates the local display and sends structured samples to the PC.

3. PC-side service and analysis tools
   - Receives samples from PYNQ.
   - Decodes one canonical protocol.
   - Validates values and timestamp order.
   - Saves raw records before any prediction or smoothing.
   - Produces statistics and visualization for the course demo/report.

## Repo Layout

Current and planned repository structure:

| Path | Purpose |
|---|---|
| [.agents/skills/](.agents/skills/) | Repo-local Codex skills. |
| [AGENTS.md](AGENTS.md) | Agent execution rules and Definition of Done. |
| [README.md](README.md) | Stable project overview and navigation. |
| [docs/](docs/) | Engineering docs and work notes. |
| [reports/](reports/) | Course report inputs and diagrams. |
| [rtl/](rtl/) | Synthesizable RTL custom IP. |
| [sim/](sim/) | Behavioral simulations and testbenches. |
| [vivado/](vivado/) | Vivado projects, constraints, and future scripts. |

Implemented or active subtrees:

| Path | Purpose |
|---|---|
| [rtl/i2c_mpu9250/](rtl/i2c_mpu9250/) | AXI-Lite I2C/JY901 RTL implementation. |
| [rtl/dht11_axi/](rtl/dht11_axi/) | DHT11 AXI RTL migrated from handoff. |
| [rtl/gree_ir_axi/](rtl/gree_ir_axi/) | TX-only Gree IR AC AXI RTL migrated from handoff. |
| [rtl/axi_humidifier/](rtl/axi_humidifier/) | Humidifier/LED AXI RTL migrated from handoff. |
| [rtl/tft_lcd_spi_axi/](rtl/tft_lcd_spi_axi/) | TFT LCD SPI AXI RTL migrated from handoff. |
| [rtl/axi_uart_spo2/](rtl/axi_uart_spo2/) | UART SpO2 AXI RTL migrated from handoff. |
| [sim/tb_gree_ir_axi/](sim/tb_gree_ir_axi/) | TX-only Gree IR AC AXI preset/start/done/error regression. |
| [sim/tb_i2c_mpu9250/](sim/tb_i2c_mpu9250/) | Behavioral simulation for the JY901 burst-read path. |
| [pynq/jy901_demo/](pynq/jy901_demo/) | Minimal PYNQ-Z1 JY901 bitstream/MMIO demo for classroom presentation. |
| [pynq/dht11_demo/](pynq/dht11_demo/) | DHT11 PYNQ driver/demo migrated from handoff. |
| [pynq/humidifier_demo/](pynq/humidifier_demo/) | Humidifier PYNQ driver/demo migrated from handoff. |
| [pynq/ir_ac_demo/](pynq/ir_ac_demo/) | TX-only Gree IR AC driver/demo migrated from handoff. |
| [pynq/sleep_demo/](pynq/sleep_demo/) | Integrated PYNQ demo, top-level board orchestrator, and socket client. |
| [pynq/tft_lcd_demo/](pynq/tft_lcd_demo/) | TFT LCD PYNQ driver/demo migrated from handoff. |
| [pynq/spo2_demo/](pynq/spo2_demo/) | UART SpO2 PYNQ helper migrated from handoff. |
| [pc_server/](pc_server/) | PC socket service, classifier adapter, comfort policy, storage, fake client, and dashboard entry point. |
| [vivado/constraints/](vivado/constraints/) | Board-level XDC constraints. |
| [vivado/ip_repo/](vivado/ip_repo/) | Shared packaged custom IP repository for Vivado projects. |
| [vivado/ip_repo/ir_ac_axi/](vivado/ip_repo/ir_ac_axi/) | Packaged TX-only Gree IR AC AXI IP. |
| [vivado/project/axi_i2c_jy901_package/](vivado/project/axi_i2c_jy901_package/) | JY901 AXI I2C IP packaging project. |
| [vivado/project/axi_i2c_jy901/](vivado/project/axi_i2c_jy901/) | JY901 AXI/PYNQ overlay project. |
| [vivado/project/ir_axi_package/](vivado/project/ir_axi_package/) | TX-only Gree IR AC AXI IP packaging project. |
| [vivado/project/jy901_hw_debug/](vivado/project/jy901_hw_debug/) | PL-only JY901 hardware debug and ILA bring-up project. |
| [vivado/project/i2c_ip_test/](vivado/project/i2c_ip_test/) | Legacy Vivado project for historical I2C IP testing. |
| [vivado/gen/](vivado/gen/) | Ignored local export folder for temporary `.bit`/`.hwh` files. |
| [docs/JY901/](docs/JY901/) | Vendor reference material for the JY901 module. |

Remaining planned subtrees may be added later:

| Path | Purpose |
|---|---|
| `analysis/` | Feature extraction, smoothing, plots, and model experiments. |
| `tests/` | Python-side tests and reusable fixtures. |
| `data/` | Raw and processed data; normally ignored unless demo samples are needed. |

## Documentations

Read these first:

| Path | Purpose |
|---|---|
| [AGENTS.md](AGENTS.md) | Agent rules, testing expectations, and Definition of Done. |
| [docs/README.md](docs/README.md) | Documentation directory index. |
| [rtl/README.md](rtl/README.md) | RTL directory index. |
| [sim/README.md](sim/README.md) | Simulation directory index. |
| [vivado/README.md](vivado/README.md) | Vivado directory index. |
| [reports/README.md](reports/README.md) | Report material index. |

Engineering references:

| Path | Purpose |
|---|---|
| [docs/i2c_axi_mpu9250.md](docs/i2c_axi_mpu9250.md) | Detailed design note for the JY901/MPU9250 I2C AXI IP. |
| [docs/register_map.md](docs/register_map.md) | Canonical AXI-Lite register map. |
| [docs/wiring.md](docs/wiring.md) | Wiring and voltage notes. |
| [docs/test_plan.md](docs/test_plan.md) | Simulation and board-level test checklist. |
| [docs/handoff_and_integration.md](docs/handoff_and_integration.md) | Handoff migration and integration plan for teammate modules. |
| [docs/ir_ac_integration_plan.md](docs/ir_ac_integration_plan.md) | Closed TX-only Gree IR AC hardware integration record and confirmed protocol decisions. |
| [docs/software_integration_plan.md](docs/software_integration_plan.md) | Current PC/PYNQ software integration plan after IR hardware demo validation. |
| [docs/software_integration_runbook.md](docs/software_integration_runbook.md) | Executable PC/PYNQ software integration runbook, including deployment, socket smoke, and evidence capture. |
| [docs/ip_packaging_manual.md](docs/ip_packaging_manual.md) | Phase 3 Vivado IP packaging checklist for migrated RTL modules. |
| [docs/protocol.md](docs/protocol.md) | PYNQ-to-PC newline-delimited JSON protocol. |
| [docs/work_notes.md](docs/work_notes.md) | Human work notes, safety reminders, and common failure modes. |

## Open Loops

Demo readiness:

- [x] Hardware integrated overlay demo path is ready for classroom
  presentation through `system_v0_2`.
- [x] PC/PYNQ four-message software integration first pass is implemented and
  locally self-tested.
- [x] Dashboard entry point is implemented with real protocol/service state,
  pending-only manual controls, and bounded control-history UI.
- [ ] Before formal demo capture, fix PYNQ board time so logs have real
  timestamps.
- [ ] Before formal demo capture, rerun one full `dashboard_server.py` plus
  real PYNQ `board_client.py` session if the lab network and board are
  available.
- [ ] Before showing IR AC in class, position the IR transmitter within about
  20 cm of the lab Gree AC receiver and verify `power_on`, `power_off`, or
  `temp_26`.

Completed:

- [x] Milestone: End-to-end I2C MPU9250 (JY901) integration loop complete: 
including RTL / Sim, Vivado IP hw debug / packaging, PYNQ overlay (bitstream) 
generation, Python driver implementation, and hardware smoke test verification.
- [x] Handoff source/documentation migration skeleton for UART SpO2, DHT11,
SPI TFT LCD, humidifier, and PC socket/Excel demo.
- [x] Integrated local board demo pass for JY901, DHT11, UART SpO2, TFT LCD,
  humidifier status/control, and display update, with documented metadata
  fallback limitations.
- [x] TX-only Gree IR AC integration plan closed and software integration
  entry plan documented; teammate standalone test confirmed lab Gree AC
  response.
- [x] IR-1 source migration skeleton: TX-only Gree IR AC RTL migrated into
  `rtl/gree_ir_axi/`, PYNQ TX demo skeleton added under `pynq/ir_ac_demo/`,
  and local README/register/wiring docs updated.
- [x] IR-2 module regression: focused Icarus simulation for Gree IR TX preset
  selection, start/done/error behavior, and explicit PASS output.
- [x] IR-3 IP packaging: `gree_ir_axi_v1_0` packaged under
  `vivado/ip_repo/ir_ac_axi/` from tracked RTL and statically validated for
  AXI4-Lite metadata, `ir_pwm`, parameters, and file sets.
- [x] IR-4 integrated Vivado overlay: `gree_ir_axi_v1_0_0` added to the
  integrated Block Design, `ir_pwm` exported and placed on `T14`, and
  `system_v0_2.bit/.hwh/.tcl` exported under `vivado/gen/`.
- [x] IR-5 PYNQ board bring-up: integrated overlay driver smoke sent
  `power_on`, `power_off`, and `temp_26`; the lab Gree AC responded when the
  IR transmitter was within approximately 20 cm of the AC receiver.
- [x] Software integration first pass: PYNQ `SleepMonitorBoard` and
  `board_client.py`, PC protocol/classifier/policy/state/storage/service,
  `control_command` / `control_status`, fake client, dashboard server, and
  desired-state panel are implemented with self-test coverage.

Further work after classroom demo:

- Capture a fresh dashboard-plus-real-board evidence run for the final report
  if time allows.
- Improve overlay metadata export for old PYNQ images so static address-map
  fallback is no longer needed.
- Add optional desired-state reconciliation only if future hardware can provide
  reliable actuator feedback; do not add AC replay before the class demo.
- Consider optional sleep-aid prompt/audio module as a later extension.

Keep README files and engineering docs synchronized whenever protocols,
register maps, external ports, wiring, or workflow assumptions change.
