# project

Vivado project directories for integration and local hardware build experiments live here.

## Index

| Path | Purpose |
|---|---|
| [i2c_ip_test/](i2c_ip_test/) | Legacy Vivado project kept for reference; it mixes IP packaging, Block Design integration, and debug/overlay constraints. |

Source RTL should remain under [../../rtl/](../../rtl/); project-generated cache and simulation products are not authoritative design files.

When a project uses packaged custom IP, set its IP repository path to the shared
[../ip_repo/](../ip_repo/) directory. Do not keep separate packaged IP copies
inside each project unless the copy is explicitly documented as a throwaway
experiment.

For new JY901/I2C work, keep three flows separate: an IP packaging project that
updates [../ip_repo/](../ip_repo/), a PYNQ overlay project that instantiates the
packaged IP in a Zynq Block Design and generates `.bit`/`.hwh`, and an optional
PL-only hardware debug project for ILA bring-up.
