# i2c_ip_test Legacy Status

This Vivado project is retained as historical reference only.

Do not use this project as the clean entry point for new IP packaging,
Block Design integration, or PYNQ overlay bitstream builds. It has mixed several
different Vivado workflows in one `.xpr`:

- custom AXI IP packaging files;
- full `system_experimental` Block Design integration;
- optional PL-only `jy901_hw_debug_top` bring-up logic;
- debug ILA XDC files and board-level pin XDC files;
- generated IP/output products from multiple experiments.

That mixture makes Vivado state easy to corrupt. One common failure mode is
setting `axi_i2c_jy901_v1_0` as the top module and then running implementation;
all AXI-Lite ports become top-level FPGA IO, leading to IO placement errors such
as `[Place 30-58] Number of unplaced IO Ports is greater than number of
available pins`.

## Recommended Split

Use separate Vivado entry points for future work:

1. **IP packaging project**
   - Packages `axi_i2c_jy901_v1_0` into `vivado/ip_repo/`.
   - Does not run full-board implementation or bitstream generation.
   - Does not include board pin constraints or debug ILA XDC files inside the
     packaged IP.

2. **AXI/PYNQ overlay project**
   - Instantiates the packaged IP in a Zynq Block Design.
   - Uses a BD wrapper, such as `system_experimental_wrapper`, as the top.
   - Exposes only real external PL ports, currently `i2c_scl` and `i2c_sda`.
   - Uses `vivado/constraints/axi_i2c_jy901_package.xdc` for PMODA `Y17/Y16`.
   - Generates the `.bit` and `.hwh` files for PYNQ together.

3. **Optional PL-only hardware debug project**
   - Uses `jy901_hw_debug_top.v` and debug-specific constraints.
   - May include ILA probes during bring-up.
   - Stays separate from the packaged AXI IP and PYNQ overlay build.

Current files under this directory can still be inspected for reference, but
new reproducible build flows should be documented as Tcl scripts or separate
Vivado projects under `vivado/project/`.
