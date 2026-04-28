# AGENTS.md

## Project Overview

This repository is for a **Computer Hardware Comprehensive Course Design** project named **智能睡眠监测辅助系统**.

The system is a low-cost, non-invasive, home-oriented sleep monitoring and assistance system built around the **PYNQ-Z1 / Zynq-7000 XC7Z020** platform. It collects physiological, motion, and environmental data, then displays, records, analyzes, and optionally reacts to sleep-related conditions.

Core goals:

- Continuously collect sleep-related data at night.
- Estimate sleep state and sleep stability using multimodal signals.
- Display key values locally on the board-side display.
- Send runtime data to a PC-side service for logging, analysis, and visualization.
- Trigger simple environment-assistance actions such as air-conditioner IR control, humidifier control, or sleep-aid prompts.

This is **not** intended to be a clinical sleep diagnosis system. Treat all sleep-stage or abnormality outputs as auxiliary, interpretable estimates.

## Hardware Platform

Target board:

- **PYNQ-Z1**
- Chip: **Xilinx Zynq-7000 XC7Z020 / xc7z020clg400-1**
- PS: ARM Cortex-A9 processing system
- PL: FPGA programmable logic
- PS-PL communication: **AXI bus**

Important board constraints:

- PYNQ-Z1 external I/O should be treated as **3.3 V only**. Do not assume APduino-style 5 V compatibility.
- Check every sensor/module voltage before wiring.
- Do not hot-plug wires while the board is powered.
- The PL clock may use the PYNQ-Z1 Ethernet PHY 125 MHz clock on **H16**, or a PS-generated FCLK depending on the Vivado block design. Keep clock assumptions explicit in HDL parameters and constraints. NOTE: the system clock are all setup as 100 MHz.

## Main External Modules

Input sensing modules:

- Heart-rate / SpO2 sensor
  - Data: BPM, SPO2
  - Planned interface: **UART IP**
- MPU9250 (JY-901 specific) 9-axis accelerometer / gyroscope
  - Data: accel_x, accel_y, accel_z, possible gyro data
  - Planned interface: **I2C IP**
  - Used for body motion and turning detection
- DHT11 temperature / humidity sensor
  - Data: temperature, humidity
  - Planned interface: **One-Wire IP**

Display module:

- 1.3-inch TFT color display
  - Planned interface: **SPI IP**
  - Used for board-side real-time display

Control / assistance modules:

- IR air-conditioner remote control module
  - Planned interface: **IR_AC custom IP**
- Humidifier or humidifier indicator/control module
  - Usually GPIO/PWM/relay-style control depending on actual hardware
- Optional sleep-aid audio / prompt module
  - May use PDM/PWM/audio output depending on implementation

## System Architecture

The system is divided into three layers:

1. **PL-side custom IP layer**
   - Implements low-level timing-sensitive interfaces.
   - Each peripheral protocol should be wrapped as an AXI-accessible custom IP.
   - PS-side software should interact through memory-mapped registers, not by bit-banging timing-critical protocols in Python.

2. **PYNQ board-side client**
   - Runs in PYNQ Jupyter Notebook / Python environment.
   - Loads the bitstream / overlay.
   - Initializes custom IP drivers.
   - Reads sensor data periodically.
   - Updates local display.
   - Performs lightweight local decisions.
   - Sends structured data to the PC-side server through TCP socket.

3. **PC-side server and analysis tools**
   - Runs in Python / Jupyter / PyQt environment on the host PC.
   - Receives data from PYNQ.
   - Parses and validates frames.
   - Saves records to Excel or another structured file.
   - Runs sleep-stage prediction, smoothing, statistics, and visualization.

## Planned Custom IP Blocks

Use one AXI slave IP per protocol or module unless integration pressure forces consolidation.

Expected IP blocks:

| IP | Purpose | External Signals | Notes |
|---|---|---|---|
| `spi_tft` | TFT display data/command transfer | SCLK, MOSI, CS, DC, RST, optional BL | SPI mode and max clock must match display datasheet |
| `uart_hr_spo2` | Heart-rate / SpO2 sensor receiver | RX, optional TX | Confirm baud rate and frame format from sensor datasheet |
| `i2c_mpu9250` | MPU9250 register access | SCL, SDA | Prefer open-drain style behavior and pull-up awareness |
| `onewire_dht11` | DHT11 timing protocol | single bidirectional DATA | Needs microsecond timing and checksum validation |
| `ir_ac` | IR remote signal generation | IR LED drive signal | Carrier frequency, encoding, and timing must be documented |
| `gpio_or_pwm_ctrl` | Humidifier/fan/simple actuator control | GPIO/PWM outputs | Keep safety and voltage isolation in mind |
| `ila_debug` | Debug only | internal probes | Remove or disable when not needed |

## Suggested Repository Layout

Use this layout unless the existing repository already has a clear structure:

```text
.
├── AGENTS.md
├── README.md
├── docs/
│   ├── design_notes.md
│   ├── register_map.md
│   ├── wiring.md
│   └── test_plan.md
├── vivado/
│   ├── project/              # Vivado project files, if committed
│   ├── ip_repo/              # Packaged custom AXI IPs
│   ├── constraints/          # XDC files
│   ├── bd/                   # Block Design exports / Tcl scripts
│   └── scripts/              # Tcl automation
├── rtl/
│   ├── spi_tft/
│   ├── uart_hr_spo2/
│   ├── i2c_mpu9250/
│   ├── onewire_dht11/
│   ├── ir_ac/
│   └── common/
├── sim/
│   ├── tb_spi_tft/
│   ├── tb_uart_hr_spo2/
│   ├── tb_i2c_mpu9250/
│   ├── tb_onewire_dht11/
│   └── tb_ir_ac/
├── pynq/
│   ├── overlays/             # .bit, .hwh, optional .tcl
│   ├── drivers/              # Python MMIO driver wrappers
│   ├── notebooks/            # Board-side Jupyter notebooks
│   └── client/               # Board-side runtime client code
├── pc_server/
│   ├── server.py             # TCP receive and save
│   ├── protocol.py           # frame format encode/decode
│   ├── storage.py            # Excel/CSV writing
│   └── config.example.py
├── analysis/
│   ├── data_analyzer.py      # PyQt or notebook visualization entry
│   ├── model/                # trained model files, if allowed
│   ├── features.py
│   ├── smoothing.py
│   └── plots.py
├── data/
│   ├── raw/                  # ignored by git unless demo samples
│   └── processed/            # ignored by git unless demo samples
└── tests/
    ├── python/
    └── fixtures/
```

## Development Workflow

### Hardware IP workflow

For each custom IP:

1. Read the module datasheet and record the protocol timing in `docs/design_notes.md`.
2. Write or update RTL in `rtl/<ip_name>/`.
3. Write a simulation testbench in `sim/tb_<ip_name>/`.
4. Run behavioral simulation before packaging.
5. Define a clean AXI-Lite register map.
6. Document the register map in `docs/register_map.md`.
7. Package the IP into `vivado/ip_repo/`.
8. Integrate it into Vivado Block Design.
9. Add constraints in `vivado/constraints/`.
10. Generate bitstream and export `.hwh` for PYNQ.
11. Test the IP alone before whole-system integration.

Do not modify a working IP and the whole-system Block Design at the same time unless the change is small and reversible.

### Vivado integration workflow

Expected integration steps:

1. Create Vivado project for **xc7z020clg400-1** or the PYNQ-Z1 board file.
2. Add custom IP repository.
3. Create Block Design.
4. Add Zynq PS.
5. Enable required AXI GP master interface.
6. Add custom AXI slave IPs.
7. Connect AXI interconnect / smartconnect.
8. Connect clocks and resets through Processor System Reset.
9. Expose external ports.
10. Apply XDC constraints.
11. Add ILA probes for hard-to-debug signals.
12. Run synthesis, implementation, bitstream generation.
13. Export `.bit` and `.hwh` to `pynq/overlays/`.

### PYNQ-side software workflow

Board-side code should:

1. Load the overlay.
2. Bind each IP by name from the overlay object.
3. Wrap raw MMIO accesses in driver functions/classes.
4. Initialize display and sensors.
5. Poll sensors at a readable sampling period, typically around **1 second** for UI-level display.
6. Run lightweight local logic:
   - turning detection from MPU9250 data;
   - temperature/humidity threshold decisions;
   - local abnormal-state flags;
   - display refresh.
7. Send a structured data frame to the PC server.
8. Cleanly close socket and files when an end condition occurs.

Suggested Python driver function names, based on the project plan:

```python
def get_mpu9250(): ...       # returns accel_x, accel_y, accel_z, optional gyro data
def get_hr_spo2(): ...       # returns bpm, spo2
def get_dht11(): ...         # returns temperature, humidity
def detect_turning(window): ...
def set_ir_ac_mode(mode): ...
def set_humidifier(enabled): ...
def update_display(sample): ...
def send_sample(sock, sample): ...
```

Prefer clear function names over inherited unclear names such as `gettty()` or `getxxy()` in new code. If old names are kept for compatibility, wrap them with clearer aliases.

### PC-side software workflow

PC-side code should:

1. Start a TCP server and wait for PYNQ connection.
2. Decode incoming frames using one canonical protocol definition.
3. Validate field count, value ranges, and timestamp order.
4. Save records to Excel or CSV with stable column names.
5. Run sleep-stage prediction only after raw data is saved.
6. Apply smoothing to reduce noisy stage transitions.
7. Visualize BPM, SPO2, temperature, humidity, and sleep-stage timeline.

Recommended canonical columns:

```text
Time, BPM, SPO2, Temperature, Humidity, accel_x, accel_y, accel_z, turn_count, sleep_stage, flags
```

## Communication Protocol

Define the board-to-PC payload in exactly one file, preferably `pc_server/protocol.py`, and mirror it on the PYNQ side.

Recommended first version:

- Use newline-delimited JSON during development because it is debuggable.
- Move to binary frames only after the system is stable.

Example JSON frame:

```json
{"time": 0, "bpm": 72, "spo2": 98, "temperature": 25.0, "humidity": 48.0, "accel_x": 0.01, "accel_y": -0.03, "accel_z": 0.98, "turn_count": 0, "flags": []}
```

If using binary frames, document:

- byte order;
- signedness;
- scale factor for each physical quantity;
- frame header/footer;
- checksum or length field;
- end condition.

## Register Map Rules

Every AXI IP must have a documented register map.

Minimum documentation per register:

```text
Offset: 0x00
Name: CONTROL
Access: RW
Bits:
  [0] enable
  [1] start
  [2] reset
Reset value: 0x00000000
Description: starts one transaction when start has a rising edge
```

Rules:

- Use 32-bit AXI-Lite registers.
- Keep status and control registers separate when possible.
- Use write-one-to-clear for sticky status flags if interrupts are added.
- Avoid magic offsets in Python notebooks; define constants.
- Keep reset values explicit.
- Document whether a start bit is level-sensitive or edge-sensitive.

## Coding Standards

### Verilog / RTL

- Use synthesizable Verilog/SystemVerilog only unless the toolchain is confirmed to support the feature.
- Use named parameters for clock frequency, baud rate, timing thresholds, and counter widths.
- Synchronize asynchronous external inputs with at least two flip-flops before edge detection.
- Use explicit reset behavior.
- Prefer finite-state machines for timing protocols such as DHT11, I2C, and IR.
- Keep AXI wrapper logic separate from protocol core logic when practical.
- Do not hard-code board-specific pins inside RTL; use XDC constraints.
- Test protocol core independently before AXI packaging.

### Python

- Keep notebooks thin. Put reusable logic into `.py` modules.
- Use dataclasses or dictionaries for sensor samples.
- Use clear names: `bpm`, `spo2`, `temperature`, `humidity`, `accel_x`.
- Add range checks for sensor data.
- Avoid infinite loops without a clean stop condition.
- Use logging or structured print output for debug.
- Do not silently swallow socket or MMIO exceptions.

## Testing Requirements

Before claiming a module works, provide evidence for one of these levels:

1. **Simulation pass**
   - Testbench waveforms match expected protocol timing.
2. **Single-module hardware pass**
   - The module works with the actual sensor/display/actuator.
3. **AXI driver pass**
   - PYNQ-side Python can read/write registers and obtain expected values.
4. **Integrated system pass**
   - Multiple IPs work together in the Block Design.
5. **End-to-end pass**
   - PYNQ reads data, displays it, sends it to PC, PC saves and visualizes it.

For every fix, prefer adding a small reproducible test over only editing the final notebook.

## Safety and Hardware Handling

- Do not hot-plug sensor wires while the board is powered.
- Verify VCC, GND, and signal voltage before connecting modules.
- Treat PYNQ-Z1 Arduino/PMOD I/O as 3.3 V logic.
- Use level shifting or isolation when driving modules that require 5 V signaling.
- Be careful with actuators such as humidifiers, fans, IR LEDs, and speakers; do not drive loads directly from FPGA pins.
- Use current-limiting resistors and proper driver circuits where needed.

## Common Failure Modes

Check these first when debugging:

- Wrong board part: use `xc7z020clg400-1` for PYNQ-Z1.
- Missing or mismatched `.hwh` file for PYNQ overlay.
- AXI IP name changed in Vivado, but Python still uses the old name.
- Register offset mismatch between AXI wrapper and Python driver.
- Start bit expected as rising edge, but software holds it high.
- External input not synchronized before edge detection.
- Wrong clock frequency assumption in counters.
- UART baud rate mismatch.
- I2C SDA/SCL pull-up or tri-state mistake.
- DHT11 bidirectional line not released to high-Z at the correct time.
- SPI mode or display reset sequence mismatch.
- PYNQ-Z1 I/O voltage violation.
- Socket server not started before board-side client connects.

## Agent Operating Rules

When working in this repo:

1. First identify whether the requested change is RTL, Vivado integration, PYNQ driver, PC server, analysis, documentation, or report-writing.
2. Do not invent pin assignments, register maps, sensor frame formats, or trained model details. Mark unknowns explicitly and leave TODOs.
3. Preserve the current working flow unless the user asks for a refactor.
4. Prefer small, reviewable changes.
5. Keep generated code compatible with Vivado/PYNQ constraints.
6. Update documentation when changing protocols, register maps, frame formats, or wiring.
7. For hardware-facing changes, include a test plan.
8. For notebook changes, move reusable code into modules where possible.
9. For data analysis changes, keep raw data immutable and write processed outputs separately.
10. Never claim a hardware feature is verified unless there is simulation output, board test evidence, or user-confirmed measurement.

## Definition of Done

A feature is done only when:

- Relevant RTL or Python code is committed.
- Register map or protocol documentation is updated.
- Constraints are updated if external ports changed.
- Simulation or board-level test evidence exists.
- The feature can be demonstrated or explained for course assessment.
- Any known limitations are documented.