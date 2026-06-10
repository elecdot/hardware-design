# Test Plan

Module and system-level test checklist.

## Final Integrated Overlay Acceptance Target

Final course acceptance targets one complete Vivado overlay hardware platform,
one matching `.hwh`, one PYNQ driver suite, and one demonstrable board-side
program. Single-module overlays and direct-MMIO scripts remain validation tools
for isolating bring-up failures, but they are not the preferred final
acceptance path.

Minimum integrated acceptance evidence:

- Vivado Block Design validates with all selected IP present.
- The integrated build exports matching `.bit` and `.hwh` artifacts from the
  same run.
- The integrated XDC uses the planned pin allocation in [wiring.md](wiring.md):
  PMODA for TFT LCD, Arduino `P16/P15` for JY901 I2C, PMODB `W14/Y14` for UART
  SpO2, Arduino IO11 `R17` for DHT11, Arduino `ck_io[0]` / `T14` for Gree IR
  AC TX, and board LEDs for humidifier indication.
- PYNQ loads the integrated overlay and binds IPs through exported metadata
  when available. On older PYNQ images that require same-basename `.tcl`
  metadata, the first board smoke may use the documented Phase4 static address
  map fallback; final metadata acceptance should rerun with
  `--metadata-source overlay` after exporting compatible metadata.
- The acceptance program demonstrates the stable available paths from the
  shared driver suite: JY901 read/status, DHT11 read, UART SpO2 read, TFT update,
  and PS-side humidifier control or status display.

If an integrated platform or driver issue blocks one module, record the blocking
condition and validate that module with the smallest standalone overlay/driver
path before returning to the integrated build.

PC socket/Excel integration is a later-priority final-system layer after the
board-side integrated demo. Validate it in layers:

1. PC-only: run `pc_server.py` and `fake_pynq_client.py` from the socket handoff
   and confirm JSON send/receive plus Excel writes.
2. PYNQ synthetic: run a PYNQ client that sends synthetic `sensor_data` to the
   PC's real IPv4 address and receives `sleep_result`.
3. Integrated driver: replace synthetic values with values from the integrated
   PYNQ driver suite.

Do not let PC firewall, IP address, or `openpyxl` setup block the lower-risk
board-side integrated acceptance path.

## Migrated Handoff Module Regression

These modules have source files migrated from `handoff/` into tracked repo
directories. Their handoff evidence is useful context, but local repo
simulation or board evidence is still required before claiming they work in the
integrated overlay.

### Phase2 Smoke Results

Date: 2026-06-02. Tool: Icarus Verilog (`iverilog` + `vvp`).

The following focused simulations compile and run locally:

```text
tb_humidifier_core PASS
tb_axi_humidifier PASS
tb_spi_lcd_master PASS
tb_tft_lcd_spi_axi PASS
tb_dht11_onewire_smoke PASS data_valid=37001900
tb_spo2_frame_parser PASS
```

Scope of this evidence:

- Humidifier core threshold/manual behavior and AXI register path.
- TFT SPI byte transmitter and AXI wrapper byte-send path.
- DHT11 one-wire valid-frame decode for 55% RH and 25 C using an Icarus `IOBUF`
  stub.
- SpO2 frame parser decode for known 5-byte and 7-byte frames.

This is not Vivado synthesis, IP packaging, integrated BD validation, or board
evidence.

### Phase3 IP Packaging Static Validation

Date: 2026-06-03.

Scope:

- User completed Vivado IP packaging and checked package ports/parameters in
  Vivado.
- Local repo validation checked package files, IP-XACT metadata, source file
  sets, AXI interface metadata, parameter defaults, and accidental generated
  artifact inclusion.
- Vivado CLI is not available in the current shell `PATH`, so this section is
  not a Vivado batch catalog-validation log and is not BD validation,
  synthesis, implementation, bitstream export, or board evidence.

Validated packaged IP directories:

| IP package | Package files | AXI metadata | Parameters | External ports |
|---|---|---|---|---|
| `vivado/ip_repo/axi_humidifier/` | `component.xml`, `xgui/`, `src/` present; source files match `rtl/axi_humidifier/` | `aximm/aximm_rtl`, `s00_axi`, `s00_axi_aclk`, `s00_axi_aresetn`, 4096-byte memory range | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5`, `CLK_FREQ_HZ=100000000` | `humidity_hw_valid`, `humidity_hw[7:0]`, `humidifier_led`, `humidifier_leds[3:0]` |
| `vivado/ip_repo/tft_lcd_spi_axi/` | `component.xml`, `xgui/`, `src/` present; source files match `rtl/tft_lcd_spi_axi/` | `aximm/aximm_rtl`, `s00_axi`, `s00_axi_aclk`, `s00_axi_aresetn`, 4096-byte memory range | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5` | `lcd_scl`, `lcd_sda`, `lcd_res`, `lcd_dc`, `lcd_blk` |
| `vivado/ip_repo/dht11_axi/` | `component.xml`, `xgui/`, `src/` present; source files match `rtl/dht11_axi/` | `aximm/aximm_rtl`, `s00_axi`, `s00_axi_aclk`, `s00_axi_aresetn`, 4096-byte memory range | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=4` | RTL/IP port is `dht11`; integrated XDC expects BD external port `dht11_0` |
| `vivado/ip_repo/axi_uart_spo2/` | `component.xml`, `xgui/`, `src/` present; source files match `rtl/axi_uart_spo2/` | `aximm/aximm_rtl`, `s00_axi`, `s00_axi_aclk`, `s00_axi_aresetn`, 4096-byte memory range | `C_BPS=9600`, `C_SYS_CLK_FRE=100000000`, `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5` | `uart_rxd`, `uart_txd`, `irq` |

Additional checks:

- No `top_spi_lcd_test`, testbench, journal, log, run, cache, hardware, or
  `ip_user_files` artifacts were found under the four new package directories.
- The old root-level JY901 IP package remains present in `vivado/ip_repo/` and
  is separate from the four new subdirectory packages.
- DHT11 package source includes the Vivado `IOBUF` primitive in
  `dht11_onewire.v`; this is expected for Vivado packaging. Icarus simulations
  still require their local stub.

Conclusion:

- Phase 3 static package validation is complete for the four migrated IP
  packages.
- The package set can enter Phase 4 Block Design integration, with the remaining
  validation gates being Vivado catalog refresh, BD instantiation, BD validation,
  synthesis/implementation, exported `.bit/.hwh`, and board/PYNQ smoke tests.

### Phase4 Integrated Block Design Validation

Date: 2026-06-03. Project:
`vivado/project/system_v0_1/system_v0_1.xpr`.

Scope:

- User completed the integrated Vivado Block Design and build flow.
- Local validation inspected the Vivado project, BD file, XPR constraints,
  routed reports, IO placement report, and run logs.
- This is not board/PYNQ runtime evidence.

Validated BD content:

| IP instance | Address | Range | Notes |
|---|---:|---:|---|
| `axi_i2c_jy901_v1_0_0` | `0x4000_0000` | 4K | External `i2c_scl/i2c_sda` |
| `axi_humidifier_v1_0_0` | `0x4000_1000` | 4K | `humidity_hw_valid` and `humidity_hw[7:0]` tied from `xlconstant`; external `humidifier_leds[3:0]` |
| `tft_lcd_spi_axi_v1_0_0` | `0x4000_2000` | 4K | External `lcd_scl/lcd_sda/lcd_res/lcd_dc/lcd_blk` |
| `dht11_axi_v1_0_0` | `0x4000_3000` | 4K | IP port `dht11` exported as top-level `dht11_0` |
| `axi_uart_spo2_v1_0_0` | `0x4000_4000` | 4K | External `uart_rxd/uart_txd`; polling-first path |

Validated constraints and IO placement:

| Signal | Package pin | Evidence |
|---|---|---|
| `lcd_scl` | `Y18` | `system_v0_1_wrapper_io_placed.rpt` |
| `lcd_sda` | `Y19` | `system_v0_1_wrapper_io_placed.rpt` |
| `lcd_res` | `Y16` | `system_v0_1_wrapper_io_placed.rpt` |
| `lcd_dc` | `Y17` | `system_v0_1_wrapper_io_placed.rpt` |
| `lcd_blk` | `U18` | `system_v0_1_wrapper_io_placed.rpt` |
| `i2c_scl` | `P16` | `system_v0_1_wrapper_io_placed.rpt` |
| `i2c_sda` | `P15` | `system_v0_1_wrapper_io_placed.rpt` |
| `uart_txd` | `W14` | `system_v0_1_wrapper_io_placed.rpt` |
| `uart_rxd` | `Y14` | `system_v0_1_wrapper_io_placed.rpt` |
| `dht11_0` | `R17` | `system_v0_1_wrapper_io_placed.rpt` |
| `humidifier_leds[3:0]` | `R14/P14/N16/M14` | `system_v0_1_wrapper_io_placed.rpt` |

Build evidence:

- `system_v0_1.xpr` references only
  `vivado/constraints/integrated/sleep_monitor_pynq_z1.xdc` as the project
  target constraints file.
- `ip_upgrade.log` reports successful update of the JY901 custom IP instance.
- `synth_1/__synthesis_is_complete__` exists.
- Routed DRC report has `Violations found: 0`.
- Route status report has `# of nets with routing errors: 0`.
- Routed timing summary reports 0 setup, 0 hold, and 0 pulse-width failing
  endpoints. Worst setup slack is 10.575 ns and worst hold slack is 0.034 ns.
- `impl_1/runme.log` reports `write_bitstream completed successfully`.

Known limitations before Phase 5:

- Methodology report has 17 `TIMING-18` warnings for missing input/output
  delays on external low-speed peripheral ports. These are recorded as
  non-blocking for first board smoke, but the XDC is not a complete external
  timing model.
- A matching local integrated artifact pair exists at
  `vivado/gen/system_v0_1.bit` and `vivado/gen/system_v0_1.hwh`. These files
  are ignored by Git; copy them to the PYNQ board together before driver
  binding.
- Board-side smoke on the recorded PYNQ Python 3.6 image may require
  same-basename `.tcl` metadata. `pynq/sleep_demo/integrated_demo.py` now has an
  `auto` metadata mode that falls back to the Phase4 static address map when
  `system_v0_1.tcl` is absent or when the old PYNQ Tcl parser returns an empty
  `ip_dict`.

Conclusion:

- Phase 4 integrated BD/build validation is sufficient to prepare Phase 5 PYNQ
  runtime smoke planning.
- Phase 5 cannot claim an integrated overlay runtime pass until a matching
  integrated `.bit/.hwh` pair is copied to the board and PYNQ loads it
  successfully.

### Phase5 Integrated Board Runtime Smoke

Date: 2026-06-09. Evidence source: user-confirmed PYNQ-Z1 board run with
`pynq/sleep_demo/integrated_demo.py`, integrated
`vivado/gen/system_v0_1.bit`, matching `.hwh`, and static address-map fallback
because the board's PYNQ Tcl parser returned an empty `ip_dict`.

Command shape:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_1.bit \
  --samples 30 \
  --interval 1.0 \
  --sensor-timeout 0.5 \
  --dht11-period 2.0 \
  --tft-clkdiv 50 \
  --spo2-frame-len 5
```

Observed pass evidence:

- Display smoke passed by human observation: TFT initialized correctly and
  updated during the demo.
- JY901 returned valid samples with `jy901_status="OK"` and `data_valid=1`.
- DHT11 returned temperature/humidity values, for example approximately
  `26.0 C` and `22..24% RH` during the recorded run.
- UART SpO2 returned valid 5-byte/polling samples after correcting the physical
  RX/TX orientation: `heart_rate_bpm=86..87`, `spo2_percent=99`,
  `checksum_ok=1`, and `status_code=0`.
- PS-side humidifier control/status participated in the loop and reported
  `humidifier_on=true` under low humidity.
- The integrated loop produced JSON-compatible `sensor_data` records without
  module exceptions in the provided sample.

Important wiring note:

- The SpO2 module's RX/TX labels were confirmed with the responsible teammate
  to require crossed signal wiring for this board setup. If HR/SpO2 stay `NA`,
  swap the UART signal wires before changing the RTL, register map, or parser.

Known remaining limitations:

- Board system time was still incorrect in the captured log
  (`2017-08-16 ...`). Correct board time before PC socket/Excel logging or any
  timestamp-based acceptance capture.
- Turnover count remained `0` in the shared logs. JY901 data was valid, but
  turnover trigger behavior should be validated separately with a deliberate
  roll/pitch motion test or temporary angle debug output.
- Strict `Overlay.ip_dict` metadata parsing is still not accepted on the old
  board image; the current integrated board smoke uses the documented static
  address-map fallback.

### Gree IR AC TX

Source:

- [../rtl/gree_ir_axi/](../rtl/gree_ir_axi/)
- [../pynq/ir_ac_demo/](../pynq/ir_ac_demo/)
- Handoff source:
  `../handoff/gree_ir_txrx_hardware_package/`

Current status:

- IR-1 source migration skeleton is complete for TX-only scope.
- IR-2 focused module regression passes locally with Icarus Verilog.
- IR-3 packaged IP static validation is complete for
  `vivado/ip_repo/ir_ac_axi/`.
- IR-4 integrated overlay build/export validation is complete for
  `vivado/gen/system_v0_2.bit/.hwh/.tcl`.
- The handoff RX capture IP remains standalone validation tooling and is not in
  the first integrated source path.
- Teammate standalone module testing confirmed the lab Gree AC responds to the
  handoff command set. This is standalone evidence, not integrated overlay
  evidence.

IR-2 simulation evidence:

Date: 2026-06-10. Tool: Icarus Verilog (`iverilog` + `vvp`).

Command:

```powershell
iverilog -g2012 -o E:\tmp\tb_gree_ir_axi.vvp `
  sim\tb_gree_ir_axi\tb_gree_ir_axi.v `
  rtl\gree_ir_axi\gree_ir_core.v `
  rtl\gree_ir_axi\gree_ir_axi_v1_0_S00_AXI.v `
  rtl\gree_ir_axi\gree_ir_axi_v1_0.v
vvp E:\tmp\tb_gree_ir_axi.vvp
```

Observed PASS marker:

```text
tb_gree_ir_axi PASS
```

Scope of this evidence:

- Reset defaults for `PRESET`, `CMD_LOW`, `CMD_HIGH`, and `STATUS`.
- All seven committed preset IDs and command-shadow register values.
- Normal `CONTROL.start` to `STATUS.done` behavior.
- Write-1-to-clear behavior for `STATUS.done` and `STATUS.error`.
- Repeated start while busy latches `STATUS.error`.
- `CONTROL.soft_reset` clears active/latch status.

The testbench shortens internal ROM durations through simulation-only
hierarchical assignment. This is not Vivado synthesis, IP packaging, integrated
BD validation, or board evidence.

IR-3 IP packaging static validation:

Date: 2026-06-10. Package project:
`vivado/project/ir_axi_package/ir_axi_package.xpr`. Packaged IP:
`vivado/ip_repo/ir_ac_axi/`.

Scope:

- User completed packaging in Vivado.
- Local validation inspected `component.xml`, `xgui/`, copied `src/` files,
  AXI4-Lite metadata, 4096-byte memory map, parameter defaults, and external
  port metadata.
- Vivado CLI is not available in the current shell `PATH`, so this is not a
  Vivado batch catalog-validation or `ipx::check_integrity` log.
- This is not BD validation, synthesis, implementation, bitstream export, or
  board evidence.

Validated package facts:

| Item | Evidence |
|---|---|
| VLNV | `xilinx.com:user:gree_ir_axi_v1_0:1.0` |
| Packaged files | `component.xml`, `xgui/gree_ir_axi_v1_0_v1_0.tcl`, and `src/` RTL files present |
| Source ownership | Packaged HDL SHA256 values match `rtl/gree_ir_axi/` for `gree_ir_core.v`, `gree_ir_axi_v1_0_S00_AXI.v`, and `gree_ir_axi_v1_0.v` |
| AXI metadata | `s00_axi` `aximm/aximm_rtl` slave, associated `s00_axi_aclk`, associated active-low `s00_axi_aresetn` |
| Memory map | `reg0` base `0x0`, range `4096`, width `32` |
| Parameters | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5`, `CORE_CLK_FREQ=100000000`, `CORE_CLK_1US=100`, `CORE_CARRIER_HZ=38000` |
| External port | `ir_pwm` output is present; no board pin constraint is embedded in the IP package |
| Project metadata | `ir_axi_package.xpr` references tracked RTL and `vivado/ip_repo/ir_ac_axi/component.xml`; `IPRepoPath` is aligned to `../../ip_repo/ir_ac_axi` |

IR-4 integrated overlay validation:

Date: 2026-06-10. Project:
`vivado/project/system_v0_1/system_v0_1.xpr`. Exported artifacts:
`vivado/gen/system_v0_2.bit`, `vivado/gen/system_v0_2.hwh`, and
`vivado/gen/system_v0_2.tcl`.

Validated integration evidence:

| Item | Evidence |
|---|---|
| BD Tcl IP catalog | `system_v0_2.tcl` includes `xilinx.com:user:gree_ir_axi_v1_0:1.0` |
| New IP instance | `gree_ir_axi_v1_0_0` exists in `.hwh` with VLNV `xilinx.com:user:gree_ir_axi_v1_0:1.0` |
| Address map | `.hwh` memory range is `0x40005000..0x40005FFF`; Tcl assigns `0x40005000` range `0x1000` |
| AXI connection | Tcl connects `gree_ir_axi_v1_0_0/s00_axi` to `ps7_0_axi_periph/M05_AXI` |
| Clock/reset | Tcl connects IR IP to `processing_system7_0/FCLK_CLK0` and `rst_ps7_0_50M/peripheral_aresetn` |
| External port | `.hwh` and wrapper expose output `ir_pwm` connected to `gree_ir_axi_v1_0_0/ir_pwm` |
| IO placement | `system_v0_1_wrapper_io_placed.rpt` places `ir_pwm` on `T14`, `LVCMOS33`, drive `8`, slew `SLOW` |
| DRC | Routed DRC reports `Violations found: 0` |
| Route | Route status reports `# of nets with routing errors: 0` |
| Timing | Routed timing summary reports WNS `10.274 ns`, WHS `0.040 ns`, no failing endpoints, and all user specified timing constraints met |
| Bitstream | `impl_1/runme.log` reports `write_bitstream completed successfully`; `system_v0_2.bit` is non-empty and matches the run output size |

Known limitations before IR-5:

- Methodology report has 19 warnings: 18 `TIMING-18` missing input/output delay
  warnings for low-speed external ports, plus one `LUTAR-1` warning where the
  IR core's locally generated soft-reset path drives asynchronous clear pins.
  The build still routes, meets timing, and writes a bitstream. If IR TX shows
  unstable behavior on board, prioritize replacing the IR core soft reset with
  a synchronous reset implementation.
- This is not PYNQ runtime evidence and does not yet confirm real lab AC
  response from the integrated overlay.

Expected next checks:

- IR-5 PYNQ board smoke sends a safe verified preset, records TX
  `done=true/error=false`, and confirms lab Gree AC response from the
  integrated overlay.

IR-5 partial PYNQ board smoke:

Date: 2026-06-10. Overlay artifact:
`/home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit`. IP base:
`0x40005000`.

Command:

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/ir_ac_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --base-addr 0x40005000 \
  --command temp_26 \
  --timeout 15.0
```

Observed status:

| Phase | Key fields |
|---|---|
| Before | `busy=false`, `done=false`, `error=false`, `preset=1`, `command=power_on`, `raw_status=0` |
| After | `busy=false`, `done=true`, `error=false`, `preset=5`, `command=temp_26`, `raw_status=2` |

Scope of this evidence:

- Confirms PYNQ MMIO binding to the integrated IR IP at `0x40005000`.
- Confirms `temp_26` maps to preset `5` and updates the command shadow.
- Confirms one TX transaction completed without the IP error bit.
- This is not yet recorded as real lab AC response evidence unless an operator
  also confirms the AC reacted to the command.

### DHT11 AXI IP

Source:

- [../rtl/dht11_axi/](../rtl/dht11_axi/)
- [../sim/tb_dht11_axi/](../sim/tb_dht11_axi/)
- [../pynq/dht11_demo/](../pynq/dht11_demo/)

Expected first checks:

- DHT11 frame simulation emits explicit PASS/FAIL.
- `DHT11_DATA` decodes humidity and temperature bytes in the documented order.
- Board test reads nonzero data at intervals of at least 1 to 2 seconds.
- Integrated overlay uses Arduino IO11 `R17` with 3.3 V logic and pullup.

### AXI Humidifier IP

Source:

- [../rtl/axi_humidifier/](../rtl/axi_humidifier/)
- [../sim/tb_axi_humidifier/](../sim/tb_axi_humidifier/)
- [../pynq/humidifier_demo/](../pynq/humidifier_demo/)

Expected handoff PASS markers to reproduce:

```text
tb_humidifier_core PASS
tb_axi_humidifier PASS
```

First integrated demo path:

- PYNQ reads DHT11 humidity.
- PYNQ writes humidifier `SW_HUM`.
- Board LEDs reflect humidifier state.
- [../pynq/sleep_demo/integrated_demo.py](../pynq/sleep_demo/integrated_demo.py)
  prints `temperature_c`, `humidity_percent`, and `humidifier_on` from the
  integrated overlay run.

### TFT LCD SPI AXI IP

Source:

- [../rtl/tft_lcd_spi_axi/](../rtl/tft_lcd_spi_axi/)
- [../sim/tb_tft_lcd_spi_axi/](../sim/tb_tft_lcd_spi_axi/)
- [../pynq/tft_lcd_demo/](../pynq/tft_lcd_demo/)

Expected first checks:

- SPI byte transmitter and AXI wrapper simulations emit PASS/FAIL.
- Board test initializes ST7789 with `CLKDIV=50`.
- Initial UI draws full `SLEEP MONITOR` dashboard once.
- Runtime loop updates only numeric/status regions at 1 Hz, then up to 2 Hz if
  stable.

### UART SpO2 AXI IP

Source:

- [../rtl/axi_uart_spo2/](../rtl/axi_uart_spo2/)
- [../sim/tb_axi_uart_spo2/](../sim/tb_axi_uart_spo2/)
- [../pynq/spo2_demo/](../pynq/spo2_demo/)

Expected first checks:

- Add a byte-stream/frame-parser simulation for 5-byte mode.
- Verify 9600 baud timing at the integrated AXI clock.
- Keep the PYNQ helper Python 3.6-compatible; `Spo2Sample` is intentionally a
  plain class instead of a `dataclass`.
- Board test confirms BPM/SpO2 update from the physical module.

## I2C JY901 / MPU9250 AXI IP

### Behavioral simulation

Location: [../sim/tb_i2c_mpu9250/](../sim/tb_i2c_mpu9250/).

Files:

- [../rtl/i2c_mpu9250/i2c_master_core.v](../rtl/i2c_mpu9250/i2c_master_core.v)
- [../rtl/i2c_mpu9250/jy901_sampler.v](../rtl/i2c_mpu9250/jy901_sampler.v)
- [../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v](../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v)
- [../sim/tb_i2c_mpu9250/tb_jy901_sampler.v](../sim/tb_i2c_mpu9250/tb_jy901_sampler.v)

Command when `just` and Icarus Verilog are installed:

```powershell
cd sim/tb_i2c_mpu9250
just sampler
```

Generated artifacts are written under `sim/tb_i2c_mpu9250/build/`.

Expected checks:

- I2C transaction is `START, 0xA0, 0x34, RESTART, 0xA1, 26 data bytes, NACK, STOP`.
- `ack_error == 0`.
- `timeout == 0`.
- `data_valid == 1`.
- `sample_cnt == 1`.
- `AX_RAW == 0x1234`, `AY_RAW == 0x5678`, `TEMP_RAW == 0x0D0C` for the included slave model.

### Error-path simulation

The same testbench then runs an address-error case:

- set `dev_addr = 0x51`;
- expect `ack_error == 1`;
- expect `ERROR_CODE == 0x01`.

### AXI top-level simulation

Location: [../sim/tb_i2c_mpu9250/](../sim/tb_i2c_mpu9250/).

Files:

- [../rtl/i2c_mpu9250/i2c_open_drain_io.v](../rtl/i2c_mpu9250/i2c_open_drain_io.v)
- [../rtl/i2c_mpu9250/i2c_master_core.v](../rtl/i2c_mpu9250/i2c_master_core.v)
- [../rtl/i2c_mpu9250/jy901_sampler.v](../rtl/i2c_mpu9250/jy901_sampler.v)
- [../rtl/i2c_mpu9250/axi_lite_regs.v](../rtl/i2c_mpu9250/axi_lite_regs.v)
- [../rtl/i2c_mpu9250/axi_i2c_jy901_v1_0.v](../rtl/i2c_mpu9250/axi_i2c_jy901_v1_0.v)
- [../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v](../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v)
- [../sim/tb_i2c_mpu9250/tb_axi_i2c_jy901_top.v](../sim/tb_i2c_mpu9250/tb_axi_i2c_jy901_top.v)

Command:

```powershell
cd sim/tb_i2c_mpu9250
just axi
```

Expected checks:

- AXI reads `VERSION == 0x4A593101`.
- AXI reads reset `DEV_ADDR == 0x50`.
- AXI writes `I2C_CLKDIV`, `START_REG`, `WORD_COUNT`, `DEV_ADDR`, and `CTRL`.
- AXI polls `STATUS.done`.
- Normal path returns `STATUS.data_valid == 1`, `STATUS.ack_error == 0`, and `STATUS.timeout == 0`.
- AXI reads `AX_RAW == 0x1234`, `AY_RAW == 0x5678`, `TEMP_RAW == 0x0D0C`, and `SAMPLE_CNT == 1`.
- `clear_done` and `clear_error` clear sticky done/error flags.
- `WORD_COUNT` boundary cases `1`, `0`, and `20` complete without error. Hardware treats `0` as one word and clamps values above 13 words.
- `auto_mode` increments `SAMPLE_CNT` across periodic transactions.
- `cfg_write_start` sends a config write and sets `STATUS.cfg_done`.
- Address NACK path returns `STATUS.ack_error == 1` and `ERROR_CODE == 0x01`.
- Register-address NACK returns `ERROR_CODE == 0x02`.
- Read-address NACK returns `ERROR_CODE == 0x03`.
- Config low-byte NACK returns `ERROR_CODE == 0x04`.
- Config high-byte NACK returns `ERROR_CODE == 0x05`.
- `soft_reset` clears sampled data and status flags.

### Timeout simulation

Location: [../sim/tb_i2c_mpu9250/](../sim/tb_i2c_mpu9250/).

Files:

- [../rtl/i2c_mpu9250/i2c_master_core.v](../rtl/i2c_mpu9250/i2c_master_core.v)
- [../sim/tb_i2c_mpu9250/tb_i2c_master_timeout.v](../sim/tb_i2c_mpu9250/tb_i2c_master_timeout.v)

Command:

```powershell
cd sim/tb_i2c_mpu9250
just timeout
```

Expected checks:

- `i2c_master_core` is instantiated with a reduced `TIMEOUT_CYCLES`.
- The transaction times out before the first I2C phase completes.
- `timeout == 1`.
- `ack_error == 0`.
- `ERROR_CODE == 0x10`.

### Single-module board test

Minimum first board test:

1. Wire JY901 VCC to 3.3 V, GND to GND, SCL/SDA to the constrained PYNQ-Z1 pins.
2. Confirm SCL/SDA pull up to 3.3 V, not 5 V.
3. Program the bitstream and set:
   - `DEV_ADDR = 0x50`
   - `START_REG = 0x34`
   - `WORD_COUNT = 1`
   - `I2C_CLKDIV = 250`
4. Write `CTRL = enable | oneshot_start`.
5. Read `STATUS`, `ERROR_CODE`, `AX_RAW`, and `SAMPLE_CNT`.

Passing criteria:

- `STATUS.done == 1`;
- `STATUS.ack_error == 0`;
- `SAMPLE_CNT` increments;
- logic analyzer or ILA shows `0xA0 0x34 0xA1`.

### PYNQ AXI driver demo

Location: [../pynq/jy901_demo/](../pynq/jy901_demo/).

Use this when demonstrating the minimal PS-side path to an assessor. The v1
demo intentionally uses bitstream download and direct MMIO instead of `.hwh`
overlay discovery because this matches the current smoke-tested board flow.

Board runtime:

- Jupyter kernel uses `/opt/python3.6/bin/python3.6` as root with PYNQ
  packages under `/opt/python3.6/lib/python3.6/site-packages`;
- SSH CLI default `/usr/bin/python3` is version 3.4.3+ and does not match the
  complete Jupyter/PYNQ environment;
- legacy CLI `python` may report 2.7.10 but is not the demo target;
- Linux 4.6.0-xilinx on PYNQ-Z1.

Command on the board:

```bash
cd /home/xilinx/jupyter_notebooks/jy901_test/jy901_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 10
```

Default demo parameters:

- bitstream `/home/xilinx/jupyter_notebooks/jy901_test/jy901_axi_package.bit`;
- base address `0x43C00000`;
- address range `0x10000`;
- `I2C_CLKDIV = 500`;
- `DEV_ADDR = 0x50`, `START_REG = 0x34`, `WORD_COUNT = 13`.

Passing criteria:

- `VERSION == 0x4A593101`;
- initial oneshot increments `SAMPLE_CNT`;
- no `ack_error` or `timeout`;
- repeated table rows show increasing `SAMPLE_CNT`;
- raw/scaled values change when the physical JY901 is moved.

Do not mark this as a PC-integrated or end-to-end pass; v1 does not send data
to a PC server or run a sleep-stage model.

### PL-only hardware debug top

Optional direct Vivado bring-up top: [../rtl/i2c_mpu9250/jy901_hw_debug_top.v](../rtl/i2c_mpu9250/jy901_hw_debug_top.v).

Use this when the goal is to test the sampler/I2C path before relying on AXI/PYNQ software. The top fixes:

- `enable = 1`;
- `auto_mode = 1`;
- `DEV_ADDR = 0x50`;
- `START_REG = 0x34`;
- `WORD_COUNT = 13`;
- one debug oneshot after reset release;
- sample period to roughly 0.5 s using its `CLK_HZ` parameter.

Vivado integration requirements:

- include `jy901_hw_debug_top.v`, `i2c_open_drain_io.v`, `jy901_sampler.v`, and `i2c_master_core.v`;
- apply [../vivado/constraints/jy901_debug.xdc](../vivado/constraints/jy901_debug.xdc) for the debug top clock, reset, LEDs, and PMODA I2C pins;
- do not also apply another XDC that maps `i2c_scl` or `i2c_sda` to different pins in the same build;
- confirm `CLK_HZ` matches the actual fabric clock used by the project.
- arm ILA first, then toggle SW0 from reset asserted to released if triggering on the reset-release debug oneshot.

Passing criteria:

- ILA shows `ack_error == 0` and `timeout == 0`;
- `sample_cnt` increments over repeated auto samples;
- `data_valid == 1` after the first successful sample;
- ILA or logic analyzer shows `START, 0xA0, 0x34, RESTART, 0xA1`;
- at least one raw data word changes when the physical JY901 orientation changes.

If `ERROR_CODE == 0x01`, the master reached the write-address ACK bit and saw
SDA high. In ILA, check `core_tx_byte_dbg == 0xA0`, `core_step_dbg == 0`, and
`core_sda_in_dbg == 1` near the ACK state. If these are true, debug wiring,
pullups, module power, PMODA pin selection, or the actual JY901 I2C address
before changing RTL timing.

Do not mark this as a hardware pass until ILA, logic analyzer, or user-confirmed board evidence is available.
