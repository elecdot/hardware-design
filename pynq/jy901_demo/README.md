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

- Jupyter kernel: root with `/opt/python3.6/bin/python3.6`.
- Jupyter PYNQ package path:
  `/opt/python3.6/lib/python3.6/site-packages/pynq`.
- SSH CLI default `python3`: `/usr/bin/python3`, version 3.4.3+, without the
  complete Jupyter/PYNQ package environment.
- SSH CLI default `python`: legacy Python 2.7.10, not the demo target.
- Kernel: `Linux pynq 4.6.0-xilinx ... armv7l`.

Keep demo code Python 3.6 compatible. Avoid Python 3.7+ syntax or APIs.

## Files

| File | Purpose |
|---|---|
| [smoke.ipynb](smoke.ipynb) | Original manual smoke test notebook. |
| [smoke_demo.py](smoke_demo.py) | Jupytext-style py:percent notebook source for a short oneshot demo. |
| [jy901_driver.py](jy901_driver.py) | Python 3.6-compatible bitstream/MMIO driver helpers. |
| [demo_cli.py](demo_cli.py) | Main automatic polling demo for classroom presentation. |

## Run CLI Demo

Copy this directory to the PYNQ board next to the bitstream, then run:

```bash
cd /home/xilinx/jupyter_notebooks/jy901_test/jy901_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 10
```

Defaults:

- bitstream: `/home/xilinx/jupyter_notebooks/jy901_test/jy901_axi_package.bit`
- base address: `0x43C00000`
- address range: `0x10000`
- I2C divider: `500`

Optional JSONL capture:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 30 --interval 0.5 --jsonl jy901_demo_run.jsonl
```

Expected pass evidence:

- `VERSION` prints `0x4A593101 PASS`;
- initial oneshot increments `SAMPLE_CNT`;
- table rows continue printing without `ACK_ERR` or `TIMEOUT`;
- moving or rotating the JY901 changes acceleration and roll/pitch/yaw values.

## Readable Data Conversion

`jy901_driver.py` exposes `scale_raw(raw)`, `readable_measurements(raw)`, and
`JY901DemoDriver.read_readable()` so the CLI, notebook, and JSONL output use
the same conversion rules.

| JY901 register | Field | Raw interpretation | Converted unit |
|---:|---|---|---|
| `0x34` | AX | `raw / 32768 * 16` | g |
| `0x35` | AY | `raw / 32768 * 16` | g |
| `0x36` | AZ | `raw / 32768 * 16` | g |
| `0x37` | GX | `raw / 32768 * 2000` | deg/s |
| `0x38` | GY | `raw / 32768 * 2000` | deg/s |
| `0x39` | GZ | `raw / 32768 * 2000` | deg/s |
| `0x3A` | HX | `raw` | magnetic raw count |
| `0x3B` | HY | `raw` | magnetic raw count |
| `0x3C` | HZ | `raw` | magnetic raw count |
| `0x3D` | Roll | `raw / 32768 * 180` | deg |
| `0x3E` | Pitch | `raw / 32768 * 180` | deg |
| `0x3F` | Yaw | `raw / 32768 * 180` | deg |
| `0x40` | TEMP | `raw / 100` | C |

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
- `ACK_ERR` / `ERROR_CODE=0x01`: the JY901 did not ACK the write-address byte.
  Confirm module power, PMODA `Y17/Y16`, 3.3 V pullups, Dupont jumper contact,
  and `DEV_ADDR=0x50`.
- `TIMEOUT`: confirm I2C lines are not stuck low and the bitstream matches the RTL/register map.
- all-zero sensor payload: treat the sample as invalid, not as motion. This is
  usually a sign of an interrupted transaction, stale/cleared sample registers,
  or unstable sensor wiring before a visible ACK error.
- `scl_in=0` and `sda_in=0` at idle: check pullups, pin mapping, and IOBUF tri-state behavior.

## Limitations

This v1 demo does not implement PC socket transfer, trained sleep-stage
prediction, clinical inference, `.hwh` auto discovery, display output, or CSV
dashboards. It demonstrates the minimal chain from bitstream download to AXI
register access and JY901 sample reads.
