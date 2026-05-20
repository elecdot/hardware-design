# jy901_demo

Minimal PYNQ-Z1 demo for the JY901 AXI I2C bitstream.

This first demo intentionally uses the smoke-tested path:

```python
from pynq import Bitstream, MMIO
Bitstream(bitfile).download()
ip = MMIO(0x43C00000, 0x10000)
```

It does not depend on `.hwh` overlay metadata.

## Target Runtime

Board environment recorded during bring-up:

```bash
xilinx@pynq:~$ python --version
Python 2.7.10
xilinx@pynq:~$ uname -a
Linux pynq 4.6.0-xilinx #1 SMP PREEMPT Tue Aug 15 15:44:37 PDT 2017 armv7l armv7l armv7l GNU/Linux
```

Keep demo code Python 2.7 compatible.

## Files

| File | Purpose |
|---|---|
| [smoke.ipynb](smoke.ipynb) | Original manual smoke test notebook. |
| [smoke_demo.py](smoke_demo.py) | Jupytext-style py:percent notebook source for a short oneshot demo. |
| [jy901_driver.py](jy901_driver.py) | Python 2-compatible bitstream/MMIO driver helpers. |
| [demo_cli.py](demo_cli.py) | Main automatic polling demo for classroom presentation. |

## Run CLI Demo

Copy this directory to the PYNQ board next to the bitstream, then run:

```bash
cd /home/xilinx/jupyter_notebooks/jy901_test/jy901_demo
python demo_cli.py --duration 10
```

Defaults:

- bitstream: `/home/xilinx/jupyter_notebooks/jy901_test/jy901_axi_package.bit`
- base address: `0x43C00000`
- address range: `0x10000`
- I2C divider: `500`

Optional JSONL capture:

```bash
python demo_cli.py --duration 30 --interval 0.5 --jsonl jy901_demo_run.jsonl
```

Expected pass evidence:

- `VERSION` prints `0x4A593101 PASS`;
- initial oneshot increments `SAMPLE_CNT`;
- table rows continue printing without `ACK_ERR` or `TIMEOUT`;
- moving or rotating the JY901 changes acceleration and roll/pitch/yaw values.

## Run Notebook-Style Demo

`smoke_demo.py` is a py:percent notebook source. It can be opened as a script or
converted/synced with Jupytext on a development machine. Jupytext is not
required on the PYNQ board.

The notebook path is intentionally short:

1. download bitstream;
2. create direct MMIO driver;
3. check `VERSION` and `STATUS`;
4. run one oneshot read;
5. display raw and scaled values.

## Known Failure Hints

- `VERSION` mismatch: confirm `BASE_ADDR=0x43C00000` still matches Vivado Address Editor.
- `ACK_ERR`: confirm JY901 power, PMODA `Y17/Y16`, 3.3 V pullups, and `DEV_ADDR=0x50`.
- `TIMEOUT`: confirm I2C lines are not stuck low and the bitstream matches the RTL/register map.
- `scl_in=0` and `sda_in=0` at idle: check pullups, pin mapping, and IOBUF tri-state behavior.

## Limitations

This v1 demo does not implement PC socket transfer, trained sleep-stage
prediction, clinical inference, `.hwh` auto discovery, display output, or CSV
dashboards. It demonstrates the minimal chain from bitstream download to AXI
register access and JY901 sample reads.
