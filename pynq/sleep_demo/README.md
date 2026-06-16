# sleep_demo

Integrated PYNQ demo, board orchestrator, and socket client for the final
sleep-monitor overlay.

## Files

| File | Purpose |
|---|---|
| [integrated_demo.py](integrated_demo.py) | Loads one integrated overlay, binds sensor/display/actuator IPs, samples at a fixed interval, updates TFT, and prints canonical JSON-like records. |
| [integrated_demo_selftest.py](integrated_demo_selftest.py) | PC-runnable self-test that checks static integrated metadata binds all expected drivers, including IR AC. |
| [display_ui.py](display_ui.py) | ST7789 dashboard drawing helpers with full initial draw and fixed-region updates. |
| [board_orchestrator.py](board_orchestrator.py) | Reusable top-level board wrapper for sampling, display update, humidifier target execution, IR AC guarded execution, and `control_status` creation. |
| [board_orchestrator_selftest.py](board_orchestrator_selftest.py) | PC-runnable self-test for orchestrator protocol shape and fake actuator behavior. |
| [board_client.py](board_client.py) | PYNQ-side socket client that sends `sensor_data`, receives `sleep_result` plus `control_command`, applies the command, and returns `control_status`. |
| [board_client_selftest.py](board_client_selftest.py) | PC-runnable loopback self-test for board client plus minimal PC socket service. |
| [BOARD_RUNBOOK.md](BOARD_RUNBOOK.md) | Step-by-step board deployment and integrated demo runbook. |

For the PC/PYNQ socket integration procedure, including rsync deployment and
record evidence capture, use
[../../docs/software_integration_runbook.md](../../docs/software_integration_runbook.md).

Keep [integrated_demo.py](integrated_demo.py) as the local hardware
smoke/fallback entry point. Do not turn it into the final socket client.

## Run

Use the PYNQ Jupyter-equivalent Python 3.6 environment:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit --samples 30
```

Keep the matching `.hwh` beside the `.bit` with the same base name. For
example, `system_v0_2.bit` must be next to `system_v0_2.hwh`.
If the board's PYNQ image expects a same-basename `.tcl`, the default
`--metadata-source auto` mode falls back to the Phase4 static address map.

First inspect the integrated overlay metadata:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit --list-ips
```

The default IP names are:

| Module | IP name |
|---|---|
| JY901 | `axi_i2c_jy901_v1_0_0` |
| DHT11 | `dht11_axi_v1_0_0` |
| UART SpO2 | `axi_uart_spo2_v1_0_0` |
| TFT LCD | `tft_lcd_spi_axi_v1_0_0` |
| Humidifier | `axi_humidifier_v1_0_0` |
| Gree IR AC TX | `gree_ir_axi_v1_0_0` |

Use `--allow-missing` only for bring-up isolation. Final demo should run
without missing required IPs.

PC-runnable board-side self-tests:

```bash
python integrated_demo_selftest.py
python board_orchestrator_selftest.py
```

PC-runnable board client loopback self-test:

```bash
python board_client_selftest.py
```

First board-side socket-client shape:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 board_client.py \
  --host <PC_IPV4> \
  --port 9000 \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 30 \
  --jy901-retries 1 \
  --jy901-retry-delay 0.05 \
  --jy901-max-stale 5.0
```

## Socket Integration Direction

The mature PYNQ client should:

- run under `/opt/python3.6/bin/python3.6`;
- avoid PC-only dependencies;
- connect to the PC's real IPv4 address;
- retry connection every 3 seconds if the PC is unavailable;
- send one `sensor_data` per sample;
- retry transient JY901 read failures and mark IMU quality separately from
  HR/SpO2-based `data_valid`;
- wait up to 2 seconds for the matching `sleep_result` and `control_command`;
- skip control for that sample on timeout or malformed messages;
- execute valid commands with local guard/cooldown checks;
- print `control_command` and `control_status` to stdout;
- show only a small local TFT control-status summary.

The PC dashboard remains the complete control and monitoring UI.
