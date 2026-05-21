# pynq

PYNQ board-side demo code, drivers, and notebooks live here.

## Index

| Path | Purpose |
|---|---|
| [jy901_demo/](jy901_demo/) | Minimal JY901 AXI I2C demo using bitstream download and direct MMIO on PYNQ-Z1. |

Current PYNQ-Z1 software environment:

- Jupyter kernel: root with `/opt/python3.6/bin/python3.6`, including the PYNQ
  Python package under `/opt/python3.6/lib/python3.6/site-packages`.
- SSH CLI default `python3`: `/usr/bin/python3` version 3.4.3+, without the
  complete PYNQ package environment used by Jupyter.
- Legacy default `python`: Python 2.7.10. Do not use it for this demo path.

Run board-side CLI demos with the Jupyter-equivalent interpreter:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 10
```
