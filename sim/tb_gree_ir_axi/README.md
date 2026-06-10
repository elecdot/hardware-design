# tb_gree_ir_axi

Focused module regression for the TX-only Gree IR AC AXI wrapper.

## Scope

This simulation validates the software-visible contract before Vivado IP
packaging:

- reset defaults for `PRESET`, `CMD_LOW`, `CMD_HIGH`, and `STATUS`
- the seven committed preset IDs and command-shadow register values
- normal `CONTROL.start` to `STATUS.done` behavior
- write-1-to-clear behavior for `STATUS.done` and `STATUS.error`
- repeated start while busy latches `STATUS.error`
- `CONTROL.soft_reset` clears active/latch status

The testbench shortens the internal IR sample ROM entries through hierarchical
simulation-only assignment so that the full 140-sample transmit FSM completes
quickly. This does not modify synthesizable RTL or board timing.

## Run

From the repository root:

```powershell
iverilog -g2012 -o E:\tmp\tb_gree_ir_axi.vvp `
  sim\tb_gree_ir_axi\tb_gree_ir_axi.v `
  rtl\gree_ir_axi\gree_ir_core.v `
  rtl\gree_ir_axi\gree_ir_axi_v1_0_S00_AXI.v `
  rtl\gree_ir_axi\gree_ir_axi_v1_0.v
vvp E:\tmp\tb_gree_ir_axi.vvp
```

Expected PASS marker:

```text
tb_gree_ir_axi PASS
```

This is not Vivado synthesis, packaged-IP validation, integrated overlay
evidence, or board evidence.
