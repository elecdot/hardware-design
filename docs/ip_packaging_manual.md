# IP Packaging Manual

Executable Phase 3 checklist for packaging the migrated RTL modules as reusable
Vivado custom IP.

Scope of this phase:

- Package reusable AXI-Lite IP under `vivado/ip_repo/`.
- Keep authoritative RTL under `rtl/`.
- Prove that each IP is rediscoverable from the shared Vivado IP catalog.
- Stop before final Block Design address assignment, bitstream export, PYNQ
  overlay binding, or board-level claims.

This manual is intentionally conservative. Phase 2 only proved local Icarus
Verilog smoke behavior for selected paths; it did not prove Vivado synthesis,
Block Design integration, or hardware behavior.

## Entry Criteria

Before packaging a module:

1. Start from a clean or intentionally reviewed working tree.
2. Confirm Phase 2 smoke evidence in [test_plan.md](test_plan.md).
3. Confirm the target part is PYNQ-Z1 / `xc7z020clg400-1`.
4. Use a 100 MHz AXI/system clock unless the IP parameter says otherwise.
5. Do not include board pin constraints inside reusable IP packages.
6. Do not edit Vivado-generated HDL copies as source. If an RTL fix is needed,
   edit the tracked file under `rtl/<ip>/`.

Recommended packaging order:

1. `axi_humidifier_v1_0`
2. `tft_lcd_spi_axi_v1_0`
3. `dht11_axi_v1_0`
4. `axi_uart_spo2_v1_0`

The first two have stronger Phase 2 AXI wrapper simulation evidence. DHT11 and
SpO2 are still packageable, but their AXI wrapper behavior needs more
validation after packaging.

## Repository Conventions

Use these paths:

| Purpose | Path |
|---|---|
| Authoritative RTL | `rtl/<ip>/` |
| Temporary packaging project | `vivado/project/<ip>_package/` |
| Shared packaged IP output | `vivado/ip_repo/<ip>/` |
| Final integrated constraints | `vivado/constraints/integrated/` |
| Temporary build/export outputs | `vivado/gen/` |

Track these packaged IP files:

- `vivado/ip_repo/<ip>/component.xml`
- `vivado/ip_repo/<ip>/xgui/*.tcl`
- HDL/data files copied by the packager if the package depends on them

Do not track Vivado cache/run artifacts:

- `.Xil/`
- `*.jou`, `*.log`
- `*.runs/`, `*.cache/`, `*.hw/`, `*.ip_user_files/`
- temporary simulation/build/export output

## IP Inventory

| IP | Top Module | RTL Files To Add | External Ports | Parameters | Phase 2 Evidence |
|---|---|---|---|---|---|
| Humidifier | `axi_humidifier_v1_0` | `axi_humidifier_v1_0.v`, `axi_humidifier_v1_0_S00_AXI.v`, `humidifier_core.v` | `humidity_hw_valid`, `humidity_hw[7:0]`, `humidifier_led`, `humidifier_leds[3:0]` | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5`, `CLK_FREQ_HZ=100000000` | `tb_humidifier_core PASS`, `tb_axi_humidifier PASS` |
| TFT LCD SPI | `tft_lcd_spi_axi_v1_0` | `tft_lcd_spi_axi_v1_0.v`, `tft_lcd_spi_axi_v1_0_S00_AXI.v`, `spi_lcd_master.v` | `lcd_scl`, `lcd_sda`, `lcd_res`, `lcd_dc`, `lcd_blk` | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5` | `tb_spi_lcd_master PASS`, `tb_tft_lcd_spi_axi PASS` |
| DHT11 | `dht11_axi_v1_0` | `dht11_axi_v1_0.v`, `dht11_axi_v1_0_S00_AXI.v`, `dht11_onewire.v` | `dht11` in RTL; integrated BD external port should be named or mapped to `dht11_0` for the current XDC | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=4` | `tb_dht11_onewire_smoke PASS`; AXI top elaborates |
| UART SpO2 | `axi_uart_spo2_v1_0` | `axi_uart_spo2_v1_0.v`, `axi_uart_spo2_v1_0_S00_AXI.v`, `uart_rx.v`, `uart_tx.v`, `spo2_frame_parser.v` | `uart_rxd`, `uart_txd`, `irq` | `C_BPS=9600`, `C_SYS_CLK_FRE=100000000`, `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5` | `tb_spo2_frame_parser PASS`; AXI top elaborates |

Do not include `rtl/tft_lcd_spi_axi/top_spi_lcd_test.v` in the TFT package. It
is a standalone PL test top, not the reusable AXI IP.

## GUI Packaging Flow

Repeat this section once per IP.

### 1. Create A Temporary RTL Project

In Vivado:

1. `File -> Project -> New`
2. Project name: `<ip>_package`
3. Project location: `vivado/project/`
4. Project type: `RTL Project`
5. Add sources from the matching `rtl/<ip>/` directory.
6. Do not add constraints.
7. Select part `xc7z020clg400-1`.
8. Finish project creation.

Set the top module explicitly:

1. In `Sources`, right-click the top module.
2. Select `Set as Top`.
3. Confirm the top module matches the inventory table above.

### 2. Elaborate Before Packaging

Run:

1. `Flow Navigator -> RTL Analysis -> Open Elaborated Design`
2. Fix any missing module, parameter, or primitive errors before continuing.
3. Check the top-level ports are exactly the ports expected for the IP.

Expected special cases:

- DHT11 may rely on Vivado primitive inference for the bidirectional inout path.
  Do not package the Icarus simulation `IOBUF` stub.
- TFT should expose only write-side LCD pins. There is no `CS` or `MISO` in the
  current RTL.
- Humidifier has optional direct PL humidity inputs. In the first integrated
  PS-controlled path, tie `humidity_hw_valid` low in BD and write `SW_HUM` from
  PYNQ.
- SpO2 should expose `irq`; the first BD may leave it unconnected if PYNQ polls
  status registers.

### 3. Start IP Packager

Use:

1. `Tools -> Create and Package New IP`
2. Select `Package your current project`
3. IP location: `vivado/ip_repo/<ip>/`
4. Continue into the IP Packager view.

Set identification metadata:

| Field | Value |
|---|---|
| Vendor | `xilinx.com` |
| Library | `user` |
| Name | top module name, for example `axi_humidifier_v1_0` |
| Version | `1.0` |
| Display name | human-readable module name |
| Description | one-line role and interface summary |

Keep the IP name stable. Changing it later changes BD cell names, PYNQ
`Overlay.ip_dict` keys, and packaging diffs.

### 4. Check File Groups

In `Package IP -> File Groups`:

1. Confirm all required RTL files from the inventory table are included.
2. Confirm testbenches are not included in synthesis file groups.
3. Confirm standalone demo tops are not included.
4. If the packager copied sources into the package, check that the copied file
   list matches the inventory.

### 5. Check Ports And Interfaces

In `Package IP -> Ports and Interfaces`:

1. Confirm Vivado inferred one AXI4-Lite slave interface from `s00_axi_*`.
2. Interface mode should be slave.
3. Interface type should be AXI4-Lite, not full AXI memory-mapped with burst
   expectations.
4. Associate the AXI interface with `s00_axi_aclk`.
5. Associate reset with `s00_axi_aresetn`, active low.
6. Leave physical peripheral ports as plain external ports.

Typical AXI interface naming can be `S00_AXI`, `s00_axi`, or a Vivado-generated
variant. The exact name is less important than correct protocol type, clock
association, reset association, and address map.

If AXI is not inferred:

1. Check that all AXI signals exist at the top level.
2. Check `C_S00_AXI_DATA_WIDTH` and `C_S00_AXI_ADDR_WIDTH` are visible
   parameters.
3. Use `Infer Bus Interface` manually and select AXI memory mapped slave.
4. Re-run `Package IP -> Review and Package -> Check Integrity`.

### 6. Check Addressing And Memory

In `Package IP -> Addressing and Memory`:

1. Confirm there is one memory map for the AXI-Lite slave.
2. Use a conservative aperture such as `4K` or `64K`.
3. Do not assign final integrated base addresses here.

Final base addresses belong to the integrated Block Design address editor and
the PYNQ driver binding layer.

Expected register footprint:

| IP | Address Width | Used Register Range |
|---|---:|---:|
| DHT11 | 4 | `0x00` to `0x0C` |
| Humidifier | 5 | `0x00` to `0x18` |
| TFT LCD SPI | 5 | `0x00` to `0x0C` |
| UART SpO2 | 5 | `0x00` to `0x1C` |

### 7. Check Parameters

Expose only parameters that are meaningful at integration time:

- Always keep `C_S00_AXI_DATA_WIDTH`.
- Always keep `C_S00_AXI_ADDR_WIDTH`.
- Humidifier: keep `CLK_FREQ_HZ`.
- UART SpO2: keep `C_BPS` and `C_SYS_CLK_FRE`.
- TFT: keep the AXI parameters; runtime SPI divider is register-controlled.
- DHT11: keep the AXI parameters. Timing parameters are currently internal to
  `dht11_onewire.v`; do not invent new top-level package parameters during
  packaging.

For final integrated use, keep clock-related defaults aligned with 100 MHz.

### 8. Review And Re-Package

In `Package IP -> Review and Package`:

1. Click `Run IP Checks` or `Check Integrity`.
2. Review all warnings.
3. Fix blocking interface, file group, or memory map issues.
4. Click `Re-Package IP`.
5. Close the temporary packaging project only after confirming
   `component.xml` exists.

Warnings that affect AXI inference, missing files, missing top modules, or
unassociated clocks are blocking for Phase 3.

## Optional Tcl Skeleton

Use the GUI flow for the first IP so the metadata is visible. After that, the
following Tcl skeleton can help make repeated packaging less manual. Run it from
inside a Vivado Tcl Console after creating a temporary RTL project and setting
the correct top module.

Replace `<ip>` and `<display_name>` before running.

```tcl
set ip_name <ip>
set ip_root [file normalize "../../ip_repo/$ip_name"]

ipx::package_project \
  -root_dir $ip_root \
  -vendor xilinx.com \
  -library user \
  -taxonomy /UserIP \
  -import_files \
  -force

set core [ipx::current_core]
set_property name $ip_name $core
set_property display_name "<display_name>" $core
set_property description "<display_name> AXI4-Lite custom IP" $core

ipx::infer_bus_interfaces xilinx.com:interface:aximm_rtl:1.0 $core

# Check the inferred bus interface name in the IP Packager GUI.
# It is usually S00_AXI or s00_axi.
ipx::associate_bus_interfaces -busif S00_AXI -clock s00_axi_aclk $core

ipx::check_integrity $core
ipx::save_core $core
```

If the inferred bus interface is not named `S00_AXI`, replace that argument with
the name shown in `Ports and Interfaces`.

After packaging, refresh any consumer project:

```tcl
set_property ip_repo_paths [file normalize "../../ip_repo"] [current_project]
update_ip_catalog
```

## Per-IP Packaging Notes

### Humidifier

Package:

- `rtl/axi_humidifier/axi_humidifier_v1_0.v`
- `rtl/axi_humidifier/axi_humidifier_v1_0_S00_AXI.v`
- `rtl/axi_humidifier/humidifier_core.v`

Checks:

- `humidity_hw_valid` and `humidity_hw[7:0]` remain external input ports.
- `humidifier_led` and `humidifier_leds[3:0]` remain external output ports.
- `CLK_FREQ_HZ` default is `100000000`.
- AXI address width is `5`.

First integrated BD decision:

- Use PS-controlled mode first.
- Tie `humidity_hw_valid` to constant `0`.
- Tie `humidity_hw[7:0]` to constant `0` unless direct PL wiring is being
  tested.
- Let PYNQ write `SW_HUM` after reading DHT11.

### TFT LCD SPI

Package:

- `rtl/tft_lcd_spi_axi/tft_lcd_spi_axi_v1_0.v`
- `rtl/tft_lcd_spi_axi/tft_lcd_spi_axi_v1_0_S00_AXI.v`
- `rtl/tft_lcd_spi_axi/spi_lcd_master.v`

Do not package:

- `rtl/tft_lcd_spi_axi/top_spi_lcd_test.v`

Checks:

- LCD external ports are `lcd_scl`, `lcd_sda`, `lcd_res`, `lcd_dc`,
  `lcd_blk`.
- AXI address width is `5`.
- Runtime SPI divider remains controlled by the `CLKDIV` register.

First integrated BD decision:

- Keep PMODA reserved for TFT.
- Do not reuse older JY901 PMODA constraints in the integrated build.

### DHT11

Package:

- `rtl/dht11_axi/dht11_axi_v1_0.v`
- `rtl/dht11_axi/dht11_axi_v1_0_S00_AXI.v`
- `rtl/dht11_axi/dht11_onewire.v`

Checks:

- RTL top-level physical port is `dht11`.
- The integrated XDC currently documents `dht11_0`; therefore the BD external
  port must be named `dht11_0`, or the XDC must be updated in the same reviewed
  scope.
- AXI address width is `4`.
- Do not include the Icarus-only `IOBUF` simulation stub.

First integrated BD decision:

- Expose the bidirectional DATA line to Arduino IO11 `R17`.
- Ensure a 3.3 V pullup exists.
- Do not claim DHT11 hardware behavior until board reads produce stable
  temperature/humidity values at DHT11-safe intervals.

### UART SpO2

Package:

- `rtl/axi_uart_spo2/axi_uart_spo2_v1_0.v`
- `rtl/axi_uart_spo2/axi_uart_spo2_v1_0_S00_AXI.v`
- `rtl/axi_uart_spo2/uart_rx.v`
- `rtl/axi_uart_spo2/uart_tx.v`
- `rtl/axi_uart_spo2/spo2_frame_parser.v`

Checks:

- `C_BPS` default is `9600`.
- `C_SYS_CLK_FRE` default is `100000000`.
- AXI address width is `5`.
- External ports are `uart_rxd`, `uart_txd`, and `irq`.

First integrated BD decision:

- Route `uart_txd` to PMODB `W14`.
- Route `uart_rxd` to PMODB `Y14`.
- Leave `irq` unconnected for the first polling-based PYNQ demo unless the BD
  already has an interrupt integration plan.

## Post-Package Checks

Run these checks after each IP is packaged.

From PowerShell:

```powershell
Test-Path vivado\ip_repo\<ip>\component.xml
Get-ChildItem vivado\ip_repo\<ip>\xgui
rg -n "<ip>|busInterface|memoryMap|addressBlock" vivado\ip_repo\<ip>
git status --short
```

From a Vivado consumer project Tcl Console:

```tcl
set_property ip_repo_paths [file normalize "../../ip_repo"] [current_project]
update_ip_catalog
```

Then check:

1. The IP appears in the Vivado IP Catalog under User Repository.
2. The IP can be added to a blank Block Design.
3. The AXI interface can connect to AXI Interconnect or SmartConnect.
4. `Validate Design` reports no missing clock/reset/interface connections after
   minimal wiring.
5. External ports match [wiring.md](wiring.md) and the integrated XDC naming.

## Phase 3 Exit Criteria

Phase 3 is complete for an IP only when all of these are true:

1. `component.xml` and `xgui/` exist under `vivado/ip_repo/<ip>/`.
2. Vivado IP integrity check has no blocking errors.
3. The shared `vivado/ip_repo/` path rediscovers the IP in a separate project.
4. AXI4-Lite slave interface, clock, reset, and memory map are visible in BD.
5. Non-AXI physical ports match the planned integrated wiring.
6. Any IP-specific warning is documented before entering BD integration.

Phase 3 is complete for the migrated module set only when all four target IPs
meet the criteria above.

Passing Phase 3 means the IPs are packageable and BD-ready. It does not mean the
final overlay, PYNQ drivers, or physical modules are verified.

## Common Failures

| Symptom | Likely Cause | Fix |
|---|---|---|
| AXI interface not inferred | Port naming or parameter metadata not recognized | Manually infer AXI4-Lite slave interface and associate `s00_axi_aclk` / `s00_axi_aresetn` |
| IP appears but cannot connect to AXI interconnect | Interface inferred as wrong protocol or missing address map | Recheck `Ports and Interfaces` and `Addressing and Memory` |
| DHT11 port constraint fails | BD external port name does not match XDC | Rename BD external port to `dht11_0` or update the integrated XDC in the same scope |
| TFT package includes unexpected top | `top_spi_lcd_test.v` was included as source top | Remove it from packaging file groups and set `tft_lcd_spi_axi_v1_0` as top |
| Humidifier input ports block validation | Optional PL humidity inputs are floating | Tie them to constants for the first PS-controlled build |
| SpO2 timing wrong after integration | Clock parameter does not match AXI clock | Keep `C_SYS_CLK_FRE=100000000` for the planned 100 MHz clock or update both BD and docs |
| Pin conflicts after BD export | Old single-module XDC mixed with integrated XDC | Use the integrated XDC only for the final overlay |
| PYNQ driver cannot find IP by name | IP or BD cell name changed | Keep package names stable and document final BD instance names before driver binding |

## Handoff To Phase 4

After Phase 3, enter Block Design integration with these inputs:

- Four reusable IP packages under `vivado/ip_repo/`.
- Confirmed package names and BD-visible interface names.
- Planned external ports and constraints from [wiring.md](wiring.md).
- Register maps from [register_map.md](register_map.md).
- Known Phase 2 limitations from [test_plan.md](test_plan.md).

Do not start PYNQ driver acceptance until the integrated BD validates, the build
exports matching `.bit` and `.hwh`, and the final BD instance names are known.
