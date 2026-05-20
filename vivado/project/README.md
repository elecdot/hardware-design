# project

Vivado project directories for packaging, integration, and local hardware
bring-up live here. Source RTL remains under [../../rtl/](../../rtl/); project
copies under `.srcs`, generated HDL wrappers, run directories, cache output, and
simulation products are Vivado state rather than authoritative design source.

## Index

| Path | Purpose |
|---|---|
| [axi_i2c_jy901_package/](axi_i2c_jy901_package/) | IP packaging project for `axi_i2c_jy901_v1_0`; uses RTL from `rtl/i2c_mpu9250/` and updates the shared [../ip_repo/](../ip_repo/). |
| [axi_i2c_jy901/](axi_i2c_jy901/) | PYNQ/Zynq overlay project. Instantiates the packaged AXI I2C IP in Block Design `jy901_axi_system`, top `jy901_axi_system_wrapper`, and applies [../constraints/axi_i2c_jy901_package.xdc](../constraints/axi_i2c_jy901_package.xdc). |
| [jy901_hw_debug/](jy901_hw_debug/) | PL-only hardware debug project for `jy901_hw_debug_top`; uses [../constraints/jy901_debug.xdc](../constraints/jy901_debug.xdc), optional ILA, and direct PMODA I2C bring-up. |
| [i2c_ip_test/](i2c_ip_test/) | Legacy reference project. It mixes packaging, Block Design, and debug flows; do not use it as the clean entry point for new work. |

## Current JY901 Flows

Keep these flows separate:

1. **Package IP** in [axi_i2c_jy901_package/](axi_i2c_jy901_package/).
   - Main top: `axi_i2c_jy901_v1_0`.
   - Input source: [../../rtl/i2c_mpu9250/](../../rtl/i2c_mpu9250/).
   - Output metadata: [../ip_repo/component.xml](../ip_repo/component.xml) and [../ip_repo/](../ip_repo/) support files.
   - Do not treat this as the board bitstream project.

2. **Build PYNQ overlay** in [axi_i2c_jy901/](axi_i2c_jy901/).
   - Block Design: `jy901_axi_system`.
   - Top wrapper: `jy901_axi_system_wrapper`.
   - External PL ports should be only the real JY901 I2C pins, `i2c_scl` and `i2c_sda`.
   - Constraint file: [../constraints/axi_i2c_jy901_package.xdc](../constraints/axi_i2c_jy901_package.xdc), PMODA `Y17/Y16`, `LVCMOS33`.
   - Export `.bit` and `.hwh` together for PYNQ use. Temporary exports belong in [../gen/](../gen/), which is ignored by Git.

3. **Run PL-only hardware debug** in [jy901_hw_debug/](jy901_hw_debug/).
   - Top: `jy901_hw_debug_top`.
   - Constraint file: [../constraints/jy901_debug.xdc](../constraints/jy901_debug.xdc).
   - Use this for sensor wiring, pullup, ACK/NACK, and ILA bring-up before relying on AXI/PYNQ software.

## Notes

- When a project uses custom IP, set `ip_repo_paths` to the shared [../ip_repo/](../ip_repo/) directory and refresh the IP catalog.
- Do not keep private packaged IP copies inside each project unless the copy is explicitly documented as a throwaway experiment.
- If Vivado reports `NSTD-1`/`UCIO-1` on `USBIND_0_0_*` in the overlay project, the PS7 USB control interface was accidentally made external. Remove that external BD interface rather than assigning arbitrary PL pins or downgrading DRC severity.
