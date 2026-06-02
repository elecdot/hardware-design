# tb_axi_humidifier

Behavioral simulation material for the AXI humidifier controller.

## Files

| File | Purpose |
|---|---|
| [tb_humidifier_core.v](tb_humidifier_core.v) | Core behavior testbench. |
| [tb_axi_humidifier.v](tb_axi_humidifier.v) | AXI register path testbench. |

Expected handoff PASS markers:

```text
tb_humidifier_core PASS
tb_axi_humidifier PASS
```

## Run

From this directory:

```powershell
iverilog -g2012 -o build/tb_humidifier_core.vvp tb_humidifier_core.v ../../rtl/axi_humidifier/humidifier_core.v
vvp build/tb_humidifier_core.vvp
iverilog -g2012 -o build/tb_axi_humidifier.vvp tb_axi_humidifier.v ../../rtl/axi_humidifier/axi_humidifier_v1_0.v ../../rtl/axi_humidifier/axi_humidifier_v1_0_S00_AXI.v ../../rtl/axi_humidifier/humidifier_core.v
vvp build/tb_axi_humidifier.vvp
```
