# ir_ac_demo

PYNQ-side TX-only Gree IR AC helper migrated from
`handoff/gree_ir_txrx_hardware_package/`.

## Files

| File | Purpose |
|---|---|
| [ir_ac.py](ir_ac.py) | TX-only MMIO driver for `gree_ir_axi_v1_0`. |
| [demo_ir_ac.py](demo_ir_ac.py) | Small CLI for standalone or integrated board smoke. |
| [gree_yb0f2_command_library_7.json](gree_yb0f2_command_library_7.json) | Handoff command library for the seven verified presets. |

## Commands

First-version supported commands:

```text
power_on
power_off
temp_24
temp_25
temp_26
temp_27
temp_28
```

No other Gree mode, fan, swing, or raw command path is promised in this scope.

## Standalone Smoke

For the handoff standalone overlay, deploy `ir_txrx.bit` beside this directory
or pass an absolute bitfile path, then use the PYNQ Jupyter-equivalent Python
3.6 runtime:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --bitfile /home/xilinx/jupyter_notebooks/ir_txrx.bit \
  --base-addr 0x43C00000 \
  --command temp_26
```

The standalone handoff TX base address is `0x43C00000`.

## Integrated Smoke

After IR is added to the integrated overlay, pass the Vivado-assigned base
address or use the future top-level board orchestrator. The planned integrated
address is `0x40005000`, but the final value must be confirmed in Vivado.

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --base-addr 0x40005000 \
  --command temp_26 \
  --no-download
```

## Safety

- Use 3.3 V logic into the PYNQ-Z1 PL pin.
- Use an IR transmitter module or a driver transistor/MOSFET for a bare LED.
- Do not hot-plug the IR module while the board is powered.
- Prefer `temp_26` for first integrated smoke unless the team agrees a
  different preset is safer in the lab.
