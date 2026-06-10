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

- The implemented hardware path is centered on `i2c_mpu9250`, an AXI-Lite I2C
  IP for JY901/MPU9250 motion data sampling.
- Behavioral simulation exists for the JY901 burst-read path.
- Vivado packaging, PL-only debug, and PYNQ overlay projects now exist for the
  JY901 I2C path, but exported PYNQ artifacts still need matching `.bit` and
  `.hwh` evidence before being treated as an end-to-end overlay release.
- A minimal PYNQ-side JY901 demo now exists under `pynq/jy901_demo/`. It uses
  `Bitstream.download()` plus direct MMIO for the first classroom demo.
- PC socket/Excel demo code has been migrated under `pc_server/` for the later
  integration layer. Analysis tools and IR AC remain future work.

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
| Heart-rate / SpO2 sensor | BPM, SPO2 | UART custom IP | RTL/PYNQ migrated; integration pending |
| JY901 / MPU9250 IMU | Acceleration, gyro, attitude, temperature | I2C custom IP | RTL, simulation, Vivado packaging, and overlay bring-up in progress |
| DHT11 | Temperature, humidity | One-Wire custom IP | RTL/PYNQ migrated; integration pending |

Display and assistance modules:

| Module | Purpose | Planned interface | Status |
|---|---|---|---|
| 1.3-inch TFT display | Board-side real-time display | SPI custom IP | RTL/PYNQ migrated; integration pending |
| IR air-conditioner transmitter | Environment assistance | IR custom IP | Planned |
| Humidifier or indicator | Simple actuator control | GPIO / PWM / relay-style output | RTL/PYNQ migrated; integration pending |
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
| [pynq/sleep_demo/](pynq/sleep_demo/) | Integrated PYNQ demo skeleton for the final overlay. |
| [pynq/tft_lcd_demo/](pynq/tft_lcd_demo/) | TFT LCD PYNQ driver/demo migrated from handoff. |
| [pynq/spo2_demo/](pynq/spo2_demo/) | UART SpO2 PYNQ helper migrated from handoff. |
| [pc_server/](pc_server/) | PC socket/Excel demo migrated from handoff for the deferred PC integration layer. |
| [vivado/constraints/](vivado/constraints/) | Board-level XDC constraints. |
| [vivado/ip_repo/](vivado/ip_repo/) | Shared packaged custom IP repository for Vivado projects. |
| [vivado/project/axi_i2c_jy901_package/](vivado/project/axi_i2c_jy901_package/) | JY901 AXI I2C IP packaging project. |
| [vivado/project/axi_i2c_jy901/](vivado/project/axi_i2c_jy901/) | JY901 AXI/PYNQ overlay project. |
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
| [docs/ir_ac_integration_plan.md](docs/ir_ac_integration_plan.md) | TX-only Gree IR AC hardware integration plan and confirmed protocol decisions. |
| [docs/software_integration_plan.md](docs/software_integration_plan.md) | Deferred PC/PYNQ software integration plan after IR hardware demo validation. |
| [docs/ip_packaging_manual.md](docs/ip_packaging_manual.md) | Phase 3 Vivado IP packaging checklist for migrated RTL modules. |
| [docs/protocol.md](docs/protocol.md) | PYNQ-to-PC newline-delimited JSON protocol. |
| [docs/work_notes.md](docs/work_notes.md) | Human work notes, safety reminders, and common failure modes. |

## Open Loops

Current open work:

- [ ] IR-3 IP packaging: package `gree_ir_axi_v1_0` from tracked RTL and
  validate AXI4-Lite metadata, `ir_pwm` external port, parameters, and file
  sets.
- [ ] IR-4 integrated Vivado overlay: add TX-only `gree_ir_axi_v1_0_0` to the
  current integrated Block Design, expose `ir_pwm`, constrain it to
  `T14 / Arduino ck_io[0]`, rebuild, and export matching PYNQ artifacts.
- [ ] IR-5 PYNQ board bring-up: bind the integrated IR TX IP, send a safe
  verified preset such as `temp_26`, record TX status, and confirm lab Gree AC
  response from the integrated overlay.
- [ ] After IR hardware validation, resume
  [docs/software_integration_plan.md](docs/software_integration_plan.md):
  implement the PYNQ top-level orchestrator, PC policy/service refactor,
  `control_command`, and `control_status` flow.

Completed:

- [x] Milestone: End-to-end I2C MPU9250 (JY901) integration loop complete: 
including RTL / Sim, Vivado IP hw debug / packaging, PYNQ overlay (bitstream) 
generation, Python driver implementation, and hardware smoke test verification.
- [x] Handoff source/documentation migration skeleton for UART SpO2, DHT11,
SPI TFT LCD, humidifier, and PC socket/Excel demo.
- [x] Integrated local board demo pass for JY901, DHT11, UART SpO2, TFT LCD,
  humidifier status/control, and display update, with documented metadata
  fallback limitations.
- [x] TX-only Gree IR AC integration plan and deferred software integration
  plan documented; teammate standalone test confirmed lab Gree AC response.
- [x] IR-1 source migration skeleton: TX-only Gree IR AC RTL migrated into
  `rtl/gree_ir_axi/`, PYNQ TX demo skeleton added under `pynq/ir_ac_demo/`,
  and local README/register/wiring docs updated.
- [x] IR-2 module regression: focused Icarus simulation for Gree IR TX preset
  selection, start/done/error behavior, and explicit PASS output.

Further work:

- Integrate the PYNQ board-side socket client with the PC service/dashboard
  after IR hardware integration passes.
- Replace or wrap the placeholder sleep classifier with the future neural
  network classifier through the PC classifier adapter.

Keep README files and engineering docs synchronized whenever protocols,
register maps, external ports, wiring, or workflow assumptions change.
