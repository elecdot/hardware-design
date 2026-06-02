# Handoff And Integration Plan

This document is the working plan for migrating teammate handoff packages from
`handoff/` into the main repository and then integrating them into the PYNQ-Z1
Vivado/PYNQ flow.

The priority for this pass is not to change RTL behavior. The priority is to
create a stable, reviewable migration path that protects the already working
JY901 path, exposes integration blockers early, and makes every later hardware
claim traceable to simulation, board evidence, or user-confirmed measurement.

## Current Baseline

Tracked mainline status:

- `rtl/i2c_mpu9250/` is the only fully integrated source RTL subtree.
- `sim/tb_i2c_mpu9250/` contains the current regression baseline for JY901.
- `pynq/jy901_demo/` contains the smoke-tested direct-MMIO PYNQ demo.
- `vivado/ip_repo/` currently holds the packaged JY901 IP metadata.
- `handoff/` is intentionally ignored by Git through `handoff/.gitignore`.

The migration must treat `handoff/` as untracked input material. Copy only the
selected source, docs, constraints, and small driver files into tracked repo
locations. Do not treat generated Vivado cache/output directories as source.

## Handoff Package Inventory

| Module | Handoff source | Expected tracked source target | Verification status from handoff |
|---|---|---|---|
| DHT11 | `handoff/DHT11_.../DHT11_.../` | `rtl/dht11_axi/`, `sim/tb_dht11_axi/`, `pynq/dht11_demo/`, `vivado/constraints/dht11_pynq_z1.xdc` | PYNQ single-module test plan and exported `.bit/.hwh`; no complete standalone `dht11_axi` packaged IP metadata was found. |
| Humidifier | `handoff/humidifier_handoff_pack_20260601(1)/humidifier_handoff_pack_20260601/` | `rtl/axi_humidifier/`, `sim/tb_axi_humidifier/`, `pynq/humidifier_demo/`, optional LED XDC | Handoff records Vivado packaging integrity pass and two simulation PASS markers. |
| TFT LCD | `handoff/tft_lcd_handoff_pack_20260601/tft_lcd_handoff_pack_20260601/` | `rtl/tft_lcd_spi_axi/`, `sim/tb_tft_lcd_spi_axi/`, `pynq/tft_lcd_demo/`, `vivado/constraints/tft_lcd_pynq_z1.xdc` | Testbenches include PASS markers; handoff notes say local machine lacked simulator tools. PYNQ/Jupyter code is reported as board-tested. |
| UART SpO2 | `handoff/uart_spo2_pynq_handoff_20260601_portable/handoff_uart_spo2_pynq_20260601/` | `rtl/axi_uart_spo2/`, `sim/tb_axi_uart_spo2/`, `pynq/spo2_demo/`, `vivado/constraints/spo2_pmodb_pynq_z1.xdc` | PYNQ overlay artifacts and runtime helper exist; no module-level regression test was found in the handoff scan. |
| PC socket/Excel demo | `handoff/sleep_socket_project/sleep_socket_project/` | `pc_server/`, optional `pynq/sleep_demo/` client, and [protocol.md](protocol.md) | Handoff records a working PC-side TCP newline-JSON server, fake client, Excel writer, and rule-based classifier demo. |

Target paths are planned names. Create or adjust local README files when the
source is actually migrated.

## Migration Rules

1. Import one module at a time.
2. Preserve source behavior on the first copy. Do formatting or cleanup only in
   later commits or clearly separated patches.
3. Prefer authoritative RTL under each package's `rtl/` or `src/` directories.
   Avoid generated netlists, stubs, `.dcp`, `.xsa`, `.bit`, and `.hwh` as source.
4. Add a local README for every new `rtl/`, `sim/`, and `pynq/` subtree.
5. Keep canonical docs synchronized only after the tracked source exists:
   `docs/register_map.md`, `docs/wiring.md`, and `docs/test_plan.md`.
6. Keep every testbench emitting explicit PASS/FAIL console output.
7. Keep PYNQ code compatible with the board's Python 3.6 runtime.
8. Do not commit generated overlay artifacts unless they are intentionally kept
   as release evidence and documented as matching `.bit/.hwh` pairs.

## Integrated Overlay Decisions

The final course-demo target is one complete Vivado overlay hardware platform,
one matching `.hwh`, one PYNQ driver suite, and one demonstrable program built
on that driver suite. Separate single-module overlays remain useful as fallback
validation artifacts if the integrated platform or driver bring-up exposes a
blocking issue.

Accepted pin-allocation decisions for the integrated overlay:

| Module | Integrated overlay pins | Notes |
|---|---|---|
| TFT LCD | Reserve full PMODA: `lcd_scl=Y18`, `lcd_sda=Y19`, `lcd_res=Y16`, `lcd_dc=Y17`, `lcd_blk=U18` | PMODA is dedicated to the display in the integrated build. |
| JY901 | Arduino I2C: `i2c_scl=P16`, `i2c_sda=P15` | Uses the existing Arduino-header XDC variant. Keep the PMODA JY901 overlay as a single-module fallback only. |
| UART SpO2 | PMODB pin 1/2: `uart_txd=W14`, `uart_rxd=Y14` | Pin source is the course teaching guide table: `PMODB_1/JB1_P/W14`, `PMODB_2/JB1_N/Y14`. Still verify physical connector orientation before wiring. |
| DHT11 | Arduino IO11: `dht11_0=R17` | No conflict with the selected PMODA/PMODB plan. |
| Humidifier | Board LEDs: `humidifier_leds[0]=R14`, `[1]=P14`, `[2]=N16`, `[3]=M14` | LED output simulates the actuator; do not drive a load directly from PL pins. |

Accepted acceptance standard:

- The final acceptance path is the integrated overlay plus the corresponding
  driver suite and a demonstrable program.
- Module-specific overlays and direct-MMIO scripts are validation tools, not
  the final acceptance target unless integrated bring-up is blocked.
- If integrated platform or driver work fails, record the blocking point and
  validate the affected module with the smallest meaningful standalone path.

Demo priority:

1. Board-side integrated overlay + PYNQ driver suite + demonstrable local
   program.
2. Add PC socket/Excel flow from `handoff/sleep_socket_project/...` after the
   board-side integrated demo is stable. This is part of the final system
   architecture, but it is a later priority than local overlay/driver bring-up.
3. If PC networking or Excel dependencies consume time, defer socket/Excel
   validation rather than blocking the lower-risk board-side acceptance.

## Integration Order

### Phase 0: Freeze The Working Baseline

- Record the current JY901 regression command and expected PASS output before
  touching shared Vivado or Python integration files.
- Do not change `rtl/i2c_mpu9250/` while importing other modules.
- Keep the current JY901 PMODA overlay as a known-good single-module reference.
- If a future integrated overlay moves JY901 pins, document that as a new
  wiring variant instead of editing away the current proven wiring.

### Phase 1: Source And Documentation Import

- Copy selected RTL, simulation, constraints, and PYNQ drivers into planned
  tracked locations.
- Add module README files that identify top modules, external ports, clock
  assumptions, reset polarity, register offsets, and known limitations.
- Add module entries to `rtl/README.md`, `sim/README.md`, `pynq/README.md`, and
  `vivado/constraints/README.md` as files are created.
- Update this document after each module import with actual target paths.

### Phase 2: Module Regression

- Run existing JY901 simulation first to establish the baseline when tools are
  available.
- Run the imported module's smallest testbench before packaging or BD work.
- For handoff testbenches without clear PASS/FAIL, add simple fatal checks and
  final PASS output.
- If a simulator is unavailable, document the exact command that should be run
  and do not claim simulation pass.

### Phase 3: IP Packaging

- Package only from tracked `rtl/<ip_name>/` source.
- DHT11 should be repackaged from RTL because the handoff package does not
  contain a complete standalone `dht11_axi` packaged IP directory.
- Humidifier, TFT LCD, and UART SpO2 packaged metadata can be used as references,
  but source ownership should still point back to tracked RTL.
- Run Vivado IP integrity checks and record warnings that affect integration.

### Phase 4: Block Design Integration

- Build the integrated overlay from the shared `vivado/ip_repo/`; this is the
  primary final acceptance hardware platform.
- Add one new AXI slave at a time and run BD validation after each addition.
- Assign non-overlapping AXI address windows in Vivado Address Editor.
- Export matching `.bit` and `.hwh` from the same build into `vivado/gen/`.
- Use `.hwh`/`Overlay.ip_dict` for integrated PYNQ binding. Hard-coded
  `0x43C00000` is acceptable only in single-module legacy demos.
- Apply one integrated XDC set that matches the accepted pin-allocation table.
  Do not apply the old JY901 PMODA XDC in the same integrated build.

### Phase 5: PYNQ Runtime Integration

- Keep reusable drivers in `.py` modules, not only notebooks.
- Provide one small CLI or notebook-style smoke demo per module during bring-up.
- Add the final combined acceptance program only after individual module demos
  work against the integrated overlay.
- Prefer PS-side control for humidifier integration: PYNQ reads DHT11 humidity,
  then writes humidifier AXI registers. Direct PL-to-PL DHT11 valid/humidity
  wiring is optional later validation work.
- Keep board-side scripts compatible with
  `/opt/python3.6/bin/python3.6`; avoid dependencies that are unavailable in
  the recorded board runtime.

### Phase 6: Deferred PC Socket Integration

- Use the handoff architecture under `handoff/sleep_socket_project/...` as the
  reference PC demo: TCP socket, newline-delimited JSON, Excel logging, and
  `sleep_result` response.
- Migrate PC files after the board-side integrated demo is stable enough to
  provide real sensor values.
- Keep the PC protocol mirrored in [protocol.md](protocol.md).
- On PYNQ, implement a real client that reuses the integrated driver suite and
  sends `sensor_data` packets. Do not keep fake sensor generation in the final
  board client.
- Treat Windows firewall, PC IP address, and `openpyxl` installation as demo
  environment prerequisites.

## Main Integration Risks

### Pin Conflicts

Original handoff/default pin maps cannot all coexist, but the integrated
overlay pin plan now resolves the known PMODA/PMODB conflicts:

| Signal group | Pins currently used | Conflict |
|---|---|---|
| JY901 current PMODA overlay | `i2c_scl=Y17`, `i2c_sda=Y16` | Conflicts with TFT `lcd_dc=Y17` and `lcd_res=Y16`. |
| TFT LCD | `lcd_scl=Y18`, `lcd_sda=Y19`, `lcd_res=Y16`, `lcd_dc=Y17`, `lcd_blk=U18` | Conflicts with JY901 PMODA pins and UART SpO2 `Y18/Y19`. |
| UART SpO2 | `uart_txd=Y18`, `uart_rxd=Y19` | Conflicts with TFT `lcd_scl/lcd_sda`. |
| DHT11 | `dht11_0=R17` | No conflict found in the current scan. |
| Humidifier LEDs | `R14/P14/N16/M14` | Uses PYNQ-Z1 board LEDs; verify they are not already reserved by the top design. |

Integrated plan:

- PMODA is reserved for TFT LCD.
- JY901 moves to Arduino `P16/P15`.
- UART SpO2 moves to PMODB `W14/Y14`.
- DHT11 remains on Arduino IO11 `R17`.
- Humidifier remains on board LEDs unless the final demo needs a different
  visible indicator.

Remaining checks:

- PMODB `W14/Y14` has been confirmed from the course teaching guide table; still
  confirm connector orientation before wiring sensor `RX(IN)` and `TX(OUT)`.
- Confirm all selected pins are accessible with the physical wiring layout.
- Confirm every external signal uses `LVCMOS33`; do not connect 5 V logic to PL
  pins.

### AXI Address Collisions

The handoff single-module overlays commonly use `0x43C00000`. In the integrated
overlay, every AXI-Lite slave must receive a unique address range. Do not bake
single-module addresses into shared drivers. Use one of these patterns:

- `Overlay.ip_dict[ip_name]["phys_addr"]` for integrated overlays;
- explicit `base_addr` only for direct-MMIO debug scripts;
- a documented address table only after the Vivado BD has been validated.

### Clock And Timing Assumptions

- Current mainline assumes a 100 MHz AXI/system clock unless documented.
- DHT11 timing depends on microsecond counters; confirm its clock parameter or
  counter math before board testing.
- TFT SPI speed is controlled by `CLKDIV`; preserve the driver's control-bit
  shadowing so byte sends do not accidentally drop reset or backlight bits.
- UART SpO2 assumes 9600 baud from a 100 MHz clock; confirm the divider if
  FCLK changes.
- Humidifier timing uses seconds derived from `CLK_FREQ_HZ`; confirm packaging
  parameter values in Vivado.

### Protocol And Data Semantics

- DHT11 read intervals should stay at or above the sensor's practical update
  period, usually around 1 to 2 seconds.
- Humidifier `humidity_hw_valid` should be a one-cycle pulse. If DHT11 exposes
  a level instead, add a pulse adapter or document the repeated-sample behavior.
- Low-risk humidifier integration uses PS control first: read humidity in PYNQ,
  then write `SW_HUM` or control registers. Direct hardware humidity wiring is a
  later optimization, not the first acceptance path.
- UART SpO2 defaults to the observed 5-byte frame mode. Enable 7-byte mode only
  when the physical sensor output is confirmed to match that format.
- The SpO2 module may use 5 V power, but UART signals connected to PL pins must
  be verified as 3.3 V TTL.
- JY901 remains 3.3 V I2C with open-drain SCL/SDA and valid pullups.
- PC socket integration uses newline-delimited JSON. The PYNQ client must send
  the PC's real IPv4 address, not `127.0.0.1`.

### AXI And Driver Semantics

- Preserve write-one-pulse bits such as `clear_counter`, `start`, and
  `clear_done`; drivers should not hold pulse bits high.
- Check every reset value from PYNQ before relying on a module in the combined
  runtime.
- For generated AXI template wrappers, verify AW/W handshake assumptions against
  PYNQ MMIO and the selected interconnect.
- Avoid exposing raw magic offsets in notebooks; wrap MMIO access in driver
  classes with named constants.

## Behavior Regression Strategy

Minimum regression set before any integrated overlay claim:

| Level | Required evidence |
|---|---|
| Source import | Tracked source paths exist, README files name top modules and external ports, and source files match selected handoff inputs except documented changes. |
| Existing JY901 regression | Current JY901 simulations still produce the documented PASS output, or the missing-tool reason is recorded. |
| Imported module simulation | Each imported testbench emits PASS/FAIL and covers at least reset/default behavior plus one useful active transaction. |
| IP packaging | Vivado IP integrity check passes or has only documented non-blocking warnings. |
| BD integration | Vivado validates the block design after each IP addition, and external ports match the selected XDC. |
| PYNQ driver smoke | Driver can find the IP from `.hwh` or explicit base address, read a version/status/data register, and report errors clearly. |
| Board smoke | Physical module wiring, voltage, and a successful sample/control action are recorded. |
| Integrated acceptance program | One program running on the integrated overlay uses the shared driver suite to demonstrate the required sensor/display/control behavior. |

Do not claim an integrated system pass until multiple IPs operate together on
one exported overlay and the board-side code reads or controls them through the
same runtime.

The final acceptance program should, at minimum, show that the integrated driver
suite can:

- read JY901 sample/status without breaking the known I2C path;
- read DHT11 temperature/humidity when the sensor is connected;
- read UART SpO2 BPM/SpO2 frames in the confirmed frame mode;
- update the TFT LCD through the AXI SPI display driver;
- control or display humidifier state through PS-side AXI writes, preferably
  using the DHT11 value read by the PYNQ driver.

Deferred final-system socket extension:

- send a `sensor_data` newline-JSON packet to the PC server;
- save data to Excel through the PC handoff server;
- receive a `sleep_result` packet and show or print the returned state.

## Module-Specific Notes

### JY901

- Integrated overlay uses Arduino `P16/P15`, not the current PMODA `Y17/Y16`
  overlay pinout.
- Keep the existing PMODA JY901 overlay/debug flow documented as fallback
  evidence and wiring reference.
- Re-run the JY901 PYNQ smoke test after moving to `P16/P15`; a successful
  PMODA board test does not prove the Arduino-header wiring.

### DHT11

- Repackage from RTL rather than relying on generated module-reference metadata.
- Confirm the top-level bidirectional DATA port remains an inout at the top
  level and is constrained with `PULLUP true` or an external pullup.
- Add or preserve a testbench that emits PASS/FAIL for a valid DHT11 frame.
- The canonical data register is `{humidity_int, humidity_dec,
  temperature_int, temperature_dec}`.

### Humidifier

- Preserve the corrected LED behavior from the handoff: LEDs mirror
  `humidifier_on`.
- Keep PS/software-humidity mode as the first integrated demo path.
- In the low-risk integrated program, PYNQ reads DHT11 humidity and writes
  humidifier `SW_HUM` or related control registers.
- Directly connecting DHT11 humidity integer and a valid pulse in PL is optional
  later validation work after the DHT11 output timing is confirmed.
- Treat board LEDs as an actuator simulation, not a direct load driver.

### TFT LCD

- Preserve the driver's CTRL shadow register behavior.
- Keep `CLKDIV=50` as the conservative first board-test value.
- Use the current stable display style as the first integrated UI: initialize a
  full `SLEEP MONITOR` dashboard once, then update only numeric/status regions.
- First refresh target is 1 Hz local UI updates. After board smoke testing,
  attempt up to 2 Hz for faster-changing values while keeping DHT11 on its
  slower valid sample cadence.
- Display priority: HR, SpO2, turnover count, temperature, humidity, JY901/data
  status, humidifier state, and PC sleep result if socket is active.
- Avoid full-screen redraw in the periodic loop; use full redraw only during
  initialization or error recovery.
- Current RTL has no CS or MISO. If the display has a CS pin, tie it low only
  if the module documentation and wiring are confirmed.
- A byte-at-a-time AXI path is slow but acceptable for stable classroom display;
  do not add FIFO/DMA until the current path is stable.

### UART SpO2

- `Spo2Sample` is kept as a plain class for the recorded Python 3.6 PYNQ
  runtime.
- Add a frame-parser simulation or UART byte-stream test before relying on the
  driver in the combined runtime.
- Keep both 5-byte and 7-byte modes documented; default to the observed 5-byte
  mode.
- Verify signal voltage before connecting to PL pins, especially if the module
  is powered from 5 V.
- Integrated overlay targets PMODB pin 1/2 as `uart_txd=W14` and
  `uart_rxd=Y14`, based on the course teaching guide table. Verify direction at
  the connector before wiring sensor `RX(IN)` and `TX(OUT)`.

### PC Socket/Excel Demo

- Handoff files define a candidate PC integration path:
  `protocol_config.py`, `excel_utils.py`, `sleep_classifier.py`,
  `pc_server.py`, and `fake_pynq_client.py`.
- Protocol is TCP with one JSON object per line.
- PC server listens on `0.0.0.0:9000`; local fake client uses `127.0.0.1`.
- PYNQ must connect to the PC's real IPv4 address.
- `openpyxl` is required on the PC side.
- Do not open `sleep_monitor_data.xlsx` while the server is writing it.
- Current classifier is a rule placeholder, not a trained model.

## Open Decisions

- Final integrated AXI address map from Vivado Address Editor.
- Whether UART SpO2 needs interrupt wiring or polling is sufficient.
- Whether PC socket/Excel is included in the live classroom run or demonstrated
  after the local overlay demo as a second-stage final-system feature.

## Completion Criteria For This Migration Step

- This plan is tracked in `docs/`.
- Documentation indexes reference this plan.
- No RTL behavior is changed by documentation-only edits.
- Future source migration has explicit target paths, risk gates, and
  regression requirements.
