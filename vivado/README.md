# vivado

Vivado project material, constraints, block-design exports, packaged IP output, and automation scripts belong here.

## Index

| Path | Purpose |
|---|---|
| `constraints/` | Board-level XDC constraints for external IP ports. |
| `project/` | Local Vivado project directories. |

Planned directories from the project convention may be added as needed:

| Path | Purpose |
|---|---|
| `ip_repo/` | Packaged reusable custom AXI IP. |
| `bd/` | Block Design exports or Tcl regeneration scripts. |
| `scripts/` | Tcl automation for project creation, build, and export. |

Generated Vivado cache, run, and simulation output should not become design source unless intentionally preserved as evidence.
