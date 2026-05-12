# vivado

Vivado project material, constraints, block-design exports, packaged IP output, and automation scripts belong here.

## Index

| Path | Purpose |
|---|---|
| [constraints/](constraints/) | Board-level XDC constraints for external IP ports. |
| [ip_repo/](ip_repo/) | Shared repository for packaged reusable custom AXI IP. |
| [project/](project/) | Local Vivado project directories. |
| [scripts/](scripts/) | Tcl automation, board presets, and reproducible project/build entry points. |

Planned directories from the project convention may be added as needed:

| Path | Purpose |
|---|---|
| [bd/](bd/) | Block Design exports or Tcl regeneration scripts. |

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
