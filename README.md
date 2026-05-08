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
- PYNQ-side runtime code, PC server code, analysis tools, and most other
  planned IPs are still future work unless added later.

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
| Heart-rate / SpO2 sensor | BPM, SPO2 | UART custom IP | Planned |
| JY901 / MPU9250 IMU | Acceleration, gyro, attitude, temperature | I2C custom IP | RTL and simulation in progress |
| DHT11 | Temperature, humidity | One-Wire custom IP | Planned |

Display and assistance modules:

| Module | Purpose | Planned interface | Status |
|---|---|---|---|
| 1.3-inch TFT display | Board-side real-time display | SPI custom IP | Planned |
| IR air-conditioner transmitter | Environment assistance | IR custom IP | Planned |
| Humidifier or indicator | Simple actuator control | GPIO / PWM / relay-style output | Planned |
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

```text
.
|-- .agent/skills/            # Repo-local Codex skills
|-- AGENTS.md                 # Agent execution rules and Definition of Done
|-- README.md                 # Stable project overview and navigation
|-- docs/                     # Engineering docs and work notes
|-- reports/                  # Course report inputs and diagrams
|-- rtl/                      # Synthesizable RTL custom IP
|-- sim/                      # Behavioral simulations and testbenches
`-- vivado/                   # Vivado projects, constraints, and future scripts
```

Implemented or active subtrees:

| Path | Purpose |
|---|---|
| `rtl/i2c_mpu9250/` | AXI-Lite I2C/JY901 RTL implementation. |
| `sim/tb_i2c_mpu9250/` | Behavioral simulation for the JY901 burst-read path. |
| `vivado/constraints/` | Board-level XDC constraints. |
| `vivado/project/i2c_ip_test/` | Local Vivado project for I2C IP testing. |
| `docs/JY901/` | Vendor reference material for the JY901 module. |

Planned subtrees may be added later:

| Path | Purpose |
|---|---|
| `pynq/` | Overlay files, Python drivers, notebooks, and board-side client code. |
| `pc_server/` | TCP receive service, protocol parsing, and storage code. |
| `analysis/` | Feature extraction, smoothing, plots, and model experiments. |
| `tests/` | Python-side tests and reusable fixtures. |
| `data/` | Raw and processed data; normally ignored unless demo samples are needed. |

## Documentations

Read these first:

| Path | Purpose |
|---|---|
| `AGENTS.md` | Agent rules, testing expectations, and Definition of Done. |
| `docs/README.md` | Documentation directory index. |
| `rtl/README.md` | RTL directory index. |
| `sim/README.md` | Simulation directory index. |
| `vivado/README.md` | Vivado directory index. |
| `reports/README.md` | Report material index. |

Engineering references:

| Path | Purpose |
|---|---|
| `docs/i2c_axi_mpu9250.md` | Detailed design note for the JY901/MPU9250 I2C AXI IP. |
| `docs/register_map.md` | Canonical AXI-Lite register map. |
| `docs/wiring.md` | Wiring and voltage notes. |
| `docs/test_plan.md` | Simulation and board-level test checklist. |
| `docs/protocol.md` | PYNQ-to-PC protocol definition placeholder. |
| `docs/work_notes.md` | Human work notes, safety reminders, and common failure modes. |

## Open Loops

Current open work:

- Finish or formalize the PYNQ Python driver for `i2c_mpu9250`.
- Decide whether `vivado/project/i2c_ip_test/` should be committed as source or
  regenerated from scripts.
- Complete the board-level I2C/JY901 test evidence.
- Define the PYNQ-to-PC JSON protocol in `docs/protocol.md`.
- Add the PC receive/storage path.
- Add or scope the remaining planned IPs: UART heart-rate/SpO2, DHT11,
  SPI TFT, IR AC, and GPIO/PWM actuator control.
- Refine repo-local skills under `.agent/skills/` as the workflow stabilizes.

Keep README files and engineering docs synchronized whenever protocols,
register maps, external ports, wiring, or workflow assumptions change.
