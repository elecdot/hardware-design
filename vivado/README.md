# vivado

Vivado project material, constraints, block-design exports, packaged IP output, and automation scripts belong here.

## Index

| Path | Purpose |
|---|---|
| [constraints/](constraints/) | Board-level XDC constraints for external IP ports. |
| [gen/](gen/) | Local temporary `.bit`/`.hwh` export location; ignored by Git. |
| [ip_repo/](ip_repo/) | Shared repository for packaged reusable custom AXI IP. |
| [project/](project/) | Vivado project directories for IP packaging, PYNQ overlay builds, PL-only debug, and legacy references. |
| [scripts/](scripts/) | Tcl automation, board presets, and reproducible project/build entry points. |

## IP Repository Convention

Use one shared repository at [ip_repo/](ip_repo/) for packaged custom IP.
Individual Vivado projects under [project/](project/) should reference this
directory through their IP repository path instead of keeping private packaged
IP copies.

Source RTL remains authoritative under [../rtl/](../rtl/). Packaged IP metadata
and files that Vivado needs to rediscover the IP may be tracked in Git, but
generated Vivado cache, run, hardware, IP user files, and simulation output
should not become design source unless intentionally preserved as evidence.

## Tcl Script Convention

Keep hand-maintained or exported Tcl that affects project reproducibility under
[scripts/](scripts/). This includes PYNQ-Z1 board or PS presets, project
creation scripts, IP packaging scripts, Block Design regeneration scripts, and
overlay export helpers.

Tcl scripts committed here should avoid machine-specific absolute paths. Keep
Vivado-generated journals, logs, run scripts, and project cache output out of
Git unless they are intentionally preserved as build evidence.

## Export Convention

Use [gen/](gen/) for local overlay artifacts copied out of Vivado, such as
`.bit` and `.hwh` files. PYNQ overlays need matching `.bit` and `.hwh` files
from the same build; a bitstream alone is not enough for reliable MMIO driver
binding.
