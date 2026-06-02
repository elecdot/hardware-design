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
| UART SpO2 | `handoff/uart_spo2_pynq_handoff_20260601_portable/handoff_uart_spo2_pynq_20260601/` | `rtl/axi_uart_spo2/`, `sim/tb_axi_uart_spo2/`, `pynq/spo2_demo/`, `vivado/constraints/spo2_pynq_z1.xdc` | PYNQ overlay artifacts and runtime helper exist; no module-level regression test was found in the handoff scan. |

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

- Build the integrated overlay from the shared `vivado/ip_repo/`.
- Add one new AXI slave at a time and run BD validation after each addition.
- Assign non-overlapping AXI address windows in Vivado Address Editor.
- Export matching `.bit` and `.hwh` from the same build into `vivado/gen/`.
- Use `.hwh`/`Overlay.ip_dict` for integrated PYNQ binding. Hard-coded
  `0x43C00000` is acceptable only in single-module legacy demos.

### Phase 5: PYNQ Runtime Integration

- Keep reusable drivers in `.py` modules, not only notebooks.
- Provide one small CLI or notebook-style smoke demo per module.
- Add a later combined runtime only after individual module demos work.
- Keep board-side scripts compatible with
  `/opt/python3.6/bin/python3.6`; do not use standard-library `dataclasses`.

## Main Integration Risks

### Pin Conflicts

Current handoff/default pin maps cannot all coexist:

| Signal group | Pins currently used | Conflict |
|---|---|---|
| JY901 current PMODA overlay | `i2c_scl=Y17`, `i2c_sda=Y16` | Conflicts with TFT `lcd_dc=Y17` and `lcd_res=Y16`. |
| TFT LCD | `lcd_scl=Y18`, `lcd_sda=Y19`, `lcd_res=Y16`, `lcd_dc=Y17`, `lcd_blk=U18` | Conflicts with JY901 PMODA pins and UART SpO2 `Y18/Y19`. |
| UART SpO2 | `uart_txd=Y18`, `uart_rxd=Y19` | Conflicts with TFT `lcd_scl/lcd_sda`. |
| DHT11 | `dht11_0=R17` | No conflict found in the current scan. |
| Humidifier LEDs | `R14/P14/N16/M14` | Uses PYNQ-Z1 board LEDs; verify they are not already reserved by the top design. |

Do not resolve these conflicts by assigning random pins. Candidate approaches:

- keep separate single-module overlays for demo fallback;
- move JY901 to the existing Arduino-header mapping `P16/P15` in the integrated
  overlay, after confirming pullups and wiring;
- reserve PMODA for the TFT LCD if the display must be shown in the final demo;
- choose and document a new UART SpO2 pin pair only after checking PYNQ-Z1 pin
  availability, voltage level, and wiring access.

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
- UART SpO2 defaults to the observed 5-byte frame mode. Enable 7-byte mode only
  when the physical sensor output is confirmed to match that format.
- The SpO2 module may use 5 V power, but UART signals connected to PL pins must
  be verified as 3.3 V TTL.
- JY901 remains 3.3 V I2C with open-drain SCL/SDA and valid pullups.

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

Do not claim an integrated system pass until multiple IPs operate together on
one exported overlay and the board-side code reads or controls them through the
same runtime.

## Module-Specific Notes

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
- Keep software-humidity mode as the independent demo path.
- In integrated mode, connect DHT11 humidity integer and a valid pulse only
  after the DHT11 output timing is confirmed.
- Treat board LEDs as an actuator simulation, not a direct load driver.

### TFT LCD

- Preserve the driver's CTRL shadow register behavior.
- Keep `CLKDIV=50` as the conservative first board-test value.
- Current RTL has no CS or MISO. If the display has a CS pin, tie it low only
  if the module documentation and wiring are confirmed.
- A byte-at-a-time AXI path is slow but acceptable for stable classroom display;
  do not add FIFO/DMA until the current path is stable.

### UART SpO2

- Replace `dataclasses` usage before targeting the recorded Python 3.6 PYNQ
  runtime, or explicitly install and document a backport.
- Add a frame-parser simulation or UART byte-stream test before relying on the
  driver in the combined runtime.
- Keep both 5-byte and 7-byte modes documented; default to the observed 5-byte
  mode.
- Verify signal voltage before connecting to PL pins, especially if the module
  is powered from 5 V.

## Open Decisions

- Final integrated pin assignment for JY901, TFT LCD, and UART SpO2.
- Whether the course demo requires one all-in overlay or allows separate
  module-specific fallback overlays.
- Final integrated AXI address map from Vivado Address Editor.
- Whether DHT11 exposes a reliable `data_valid` pulse usable by humidifier.
- Whether UART SpO2 needs interrupt wiring or polling is sufficient.

## Completion Criteria For This Migration Step

- This plan is tracked in `docs/`.
- Documentation indexes reference this plan.
- No RTL behavior is changed by documentation-only edits.
- Future source migration has explicit target paths, risk gates, and
  regression requirements.
