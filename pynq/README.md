# pynq

PYNQ board-side demo code, drivers, and notebooks live here.

## Index

| Path | Purpose |
|---|---|
| [dht11_demo/](dht11_demo/) | DHT11 direct-MMIO demo and driver migrated from handoff. |
| [humidifier_demo/](humidifier_demo/) | Humidifier/LED AXI demo and driver migrated from handoff. |
| [jy901_demo/](jy901_demo/) | Minimal JY901 AXI I2C demo using bitstream download and direct MMIO on PYNQ-Z1. |
| [sleep_demo/](sleep_demo/) | Integrated overlay demo skeleton that binds all migrated drivers, updates TFT, and drives humidifier registers from PS-side logic. |
| [spo2_demo/](spo2_demo/) | UART SpO2 MMIO helper migrated from handoff. |
| [tft_lcd_demo/](tft_lcd_demo/) | ST7789 TFT LCD AXI SPI display driver and demos migrated from handoff. |

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
