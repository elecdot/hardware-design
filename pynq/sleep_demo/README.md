# sleep_demo

Integrated PYNQ demo skeleton for the final sleep-monitor overlay.

## Files

| File | Purpose |
|---|---|
| [integrated_demo.py](integrated_demo.py) | Loads one integrated overlay, binds sensor/display/humidifier IPs, samples at a fixed interval, updates TFT, and prints canonical JSON-like records. |
| [display_ui.py](display_ui.py) | ST7789 dashboard drawing helpers with full initial draw and fixed-region updates. |
| [BOARD_RUNBOOK.md](BOARD_RUNBOOK.md) | Step-by-step board deployment and integrated demo runbook. |

## Run

Use the PYNQ Jupyter-equivalent Python 3.6 environment:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_1.bit --samples 30
```

Keep the matching `.hwh` beside the `.bit` with the same base name. For
example, `system_v0_1.bit` must be next to `system_v0_1.hwh`.
If the board's PYNQ image expects a same-basename `.tcl`, the default
`--metadata-source auto` mode falls back to the Phase4 static address map.

First inspect the integrated overlay metadata:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_1.bit --list-ips
```

The default IP names are:

| Module | IP name |
|---|---|
| JY901 | `axi_i2c_jy901_v1_0_0` |
| DHT11 | `dht11_axi_v1_0_0` |
| UART SpO2 | `axi_uart_spo2_v1_0_0` |
| TFT LCD | `tft_lcd_spi_axi_v1_0_0` |
| Humidifier | `axi_humidifier_v1_0_0` |

Use `--allow-missing` only for bring-up isolation. Final demo should run
without missing required IPs.
