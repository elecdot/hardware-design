# Software Integration Runbook

This runbook is the executable checklist for the PC/PYNQ software integration
path after the integrated `system_v0_2` overlay and IR AC TX hardware smoke.
It is separate from `pynq/sleep_demo/BOARD_RUNBOOK.md`, which remains focused
on local board bring-up.

Current integration scope:

- PC runs `dashboard_server.py` for the classroom demo path, or the minimal
  `socket_service.py` for isolated socket debugging.
- PYNQ runs the board socket client.
- PYNQ sends `sensor_data`.
- PC replies with `sleep_result`, then `control_command`.
- PYNQ applies or skips the command and returns `control_status`.
- PC persists four JSONL record streams and the dashboard visualizes sensor,
  classifier, policy, command, status, and desired-state display state.

Do not use legacy `pc_server.py` as acceptance evidence for the new protocol
loop.

## Preconditions

Hardware:

- PYNQ-Z1 boots and is reachable over the lab network.
- `system_v0_2.bit`, `system_v0_2.hwh`, and if needed `system_v0_2.tcl` are
  exported under `vivado/gen/`.
- External modules are wired according to `docs/wiring.md`.
- IR transmitter is aimed at the lab Gree AC receiver and kept within about
  20 cm when validating real AC response.

Software:

- PC can run Python from this repository.
- PYNQ uses the board image's Python 3.6 environment:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 ...
```

Network:

- PC and PYNQ are on the same reachable network.
- PC firewall allows inbound TCP on the selected service port for Python.
  `dashboard_server.py` uses `protocol_config.SERVER_PORT`, currently `9000`;
  the minimal `socket_service.py` examples use `10000` to avoid common Windows
  conflicts around `9000`.
- PYNQ connects to the PC's real IPv4 address, not `127.0.0.1`.
- If another port is used, update every PC and PYNQ command consistently.

## 1. PC Local Self-Tests

Run from the repository root on the PC:

```bash
python -m py_compile pc_server\protocol.py pc_server\protocol_selftest.py pc_server\sleep_classifier.py pc_server\sleep_classifier_selftest.py pc_server\classifier_adapter.py pc_server\classifier_adapter_selftest.py pc_server\comfort_policy.py pc_server\comfort_policy_selftest.py pc_server\state_store.py pc_server\storage.py pc_server\state_storage_selftest.py pc_server\service.py pc_server\service_selftest.py pc_server\socket_service.py pc_server\socket_service_selftest.py pc_server\fake_pynq_client.py pc_server\fake_pynq_client_selftest.py pc_server\dashboard_server.py pc_server\dashboard_server_selftest.py pynq\sleep_demo\board_orchestrator.py pynq\sleep_demo\board_orchestrator_selftest.py pynq\sleep_demo\board_client.py pynq\sleep_demo\board_client_selftest.py
python pc_server\protocol_selftest.py
python pc_server\sleep_classifier_selftest.py
python pc_server\classifier_adapter_selftest.py
python pc_server\comfort_policy_selftest.py
python pc_server\state_storage_selftest.py
python pc_server\service_selftest.py
python pc_server\socket_service_selftest.py
python pc_server\fake_pynq_client_selftest.py
python pc_server\dashboard_server_selftest.py
python pynq\sleep_demo\board_orchestrator_selftest.py
python pynq\sleep_demo\board_client_selftest.py
```

Expected result:

```text
protocol_selftest PASS
sleep_classifier_selftest PASS
classifier_adapter_selftest PASS
comfort_policy_selftest PASS
state_storage_selftest PASS
service_selftest PASS
socket_service_selftest PASS
fake_pynq_client_selftest PASS
dashboard_server_selftest PASS
board_orchestrator_selftest PASS
board_client_selftest PASS
```

These are PC-runnable tests. They validate protocol and socket shape, not real
PYNQ hardware.

## 2. PC-Only Socket Smoke

Terminal A:

```bash
cd pc_server
python socket_service.py --host 127.0.0.1 --port 10000 --record-dir records\pc_only_smoke
```

Terminal B:

```bash
cd pc_server
python fake_pynq_client.py --host 127.0.0.1 --port 10000 --samples 5 --interval 1.0
```

Expected PC-only evidence:

- Fake client prints `SEND sensor_data`, `RECV sleep_result`,
  `RECV control_command`, and `SEND control_status`.
- Socket service records no tracebacks.
- These files exist under `pc_server/records/pc_only_smoke/`:

```text
sensor_data.jsonl
sleep_result.jsonl
control_command.jsonl
control_status.jsonl
```

## 3. Find PC IPv4 Address

On Windows PowerShell:

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -ne 'WellKnown' } | Select-Object IPAddress,InterfaceAlias
```

Pick the IPv4 address on the interface reachable from PYNQ. Do not use
`127.0.0.1`.

Optional quick connectivity check from PYNQ:

```bash
ping <PC_IPV4>
```

## 4. Deploy Files To PYNQ

Recommended target:

```text
/home/xilinx/jupyter_notebooks/sleep_monitor/
```

The board-side Python layout must keep demo directories as siblings:

```text
sleep_monitor/
  system_v0_2.bit
  system_v0_2.hwh
  system_v0_2.tcl        # if available/needed by the old PYNQ image
  sleep_demo/
  jy901_demo/
  dht11_demo/
  spo2_demo/
  tft_lcd_demo/
  humidifier_demo/
  ir_ac_demo/
```

Safe upload from the repository root:

```bash
rsync -av --exclude '__pycache__/' --exclude '*.pyc' pynq/ xilinx@pynq:/home/xilinx/jupyter_notebooks/sleep_monitor/
rsync -av vivado/gen/system_v0_2.bit vivado/gen/system_v0_2.hwh vivado/gen/system_v0_2.tcl xilinx@pynq:/home/xilinx/jupyter_notebooks/sleep_monitor/
```

If `system_v0_2.tcl` does not exist locally, upload only `.bit` and `.hwh`:

```bash
rsync -av vivado/gen/system_v0_2.bit vivado/gen/system_v0_2.hwh xilinx@pynq:/home/xilinx/jupyter_notebooks/sleep_monitor/
```

Do not use `--delete` against the whole `sleep_monitor/` target unless you are
sure it contains no board-local artifacts that should be preserved. For a clean
directory-by-directory sync, use `--delete` only on individual demo
subdirectories after checking the destination path.

The PYNQ side should not need `pc_server/`; `board_client.py` intentionally
uses its own lightweight protocol codec to avoid PC-only imports.

## 5. Start PC Dashboard For PYNQ

On the PC:

```bash
cd pc_server
python dashboard_server.py
```

Open the dashboard:

```text
http://127.0.0.1:8080
```

Keep this terminal visible. It should show the Web console, client
connect/disconnect status, and no tracebacks. The socket port is
`protocol_config.SERVER_PORT`, currently `9000`; use that same port in the
PYNQ `board_client.py` command below.

For socket-only debugging without the dashboard, keep the minimal service path:

```bash
cd pc_server
python socket_service.py --host 0.0.0.0 --port 10000 --record-dir records\pynq_integration_smoke
```

## 6. PYNQ Dry-Run Client

Use this before loading the real overlay path. It validates network direction,
message order, and PC storage with a board client that sends synthetic invalid
sensor samples.

On PYNQ:

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 board_client.py \
  --dry-run \
  --host <PC_IPV4> \
  --port 9000 \
  --samples 3 \
  --interval 1.0
```

Expected dry-run evidence:

- PYNQ prints `SEND sensor_data`, `RECV sleep_result`,
  `RECV control_command`, and `SEND control_status`.
- PC `records/` receives all four JSONL files when using `dashboard_server.py`.
  If using `socket_service.py --record-dir records\pynq_integration_smoke`,
  check that directory instead.
- `sleep_result.state_valid` may be `0` because dry-run samples do not contain
  real HR/SpO2.

## 7. Optional Local Overlay Sanity Check

Before the real socket client, run a short local integrated demo on PYNQ:

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 5 \
  --interval 1.0 \
  --metadata-source auto \
  --jy901-retries 1 \
  --jy901-retry-delay 0.05 \
  --jy901-max-stale 5.0 \
  --tft-clkdiv 50 \
  --spo2-frame-len 5
```

Expected overlay evidence:

- Printed records have `type="sensor_data"`.
- JY901 should usually report `jy901_status="OK"` and `imu_valid=1`.
  Occasional JY901-only failures may report `jy901_status="ERR"` or `STALE`
  with `status_code` bit `0x01`; they should not force `data_valid=0` when
  HR/SpO2 are valid.
- DHT11 temperature/humidity should update at its configured period.
- HR/SpO2 should become non-null when the UART module is connected correctly.
- TFT should update if display is enabled.

## 8. Real PYNQ Socket Client

On PYNQ:

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 board_client.py \
  --host <PC_IPV4> \
  --port 9000 \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 30 \
  --interval 1.0 \
  --metadata-source auto \
  --jy901-retries 1 \
  --jy901-retry-delay 0.05 \
  --jy901-max-stale 5.0 \
  --tft-clkdiv 50 \
  --spo2-frame-len 5
```

For bring-up isolation, add `--no-display` or `--allow-missing` only when
debugging a specific failing module. Final evidence should run without missing
required IPs.

Expected real-run evidence:

- PC records board-originated `sensor_data`.
- PC sends `sleep_result` and `control_command` for each sample.
- PYNQ returns one `control_status` for each command.
- PC record directory has matching JSONL streams.
- Dashboard shows live connection, sensor values, sleep result, control
  history, desired-state display panel, and recent JSON debug records.
- `sleep_result` warm-up should progress across occasional JY901-only
  `status_code=0x01` samples instead of restarting.
- PYNQ stdout shows command/status lines and no unhandled exceptions.
- TFT remains responsive if display is enabled.

## 9. Evidence To Capture

For review, keep:

- PC command line used for `dashboard_server.py` or `socket_service.py`.
- PYNQ command line used for `board_client.py`.
- First 3 to 5 JSON objects from each JSONL stream:
  `sensor_data`, `sleep_result`, `control_command`, `control_status`.
- PYNQ stdout showing one complete cycle.
- Any human observations:
  TFT updates, humidifier LEDs, IR transmitter position, AC response.

Do not claim real AC acceptance from `ir_ac.sent=true` alone. That bit means
the PYNQ-side IR IP completed transmission; real AC response still requires
human observation.

## 10. Troubleshooting

PC service fails at `server.bind(...)` with WinError `10013` or `10048`:

- `10013` means Windows denied binding that address/port.
- `10048` means the address/port is already in use or not yet reusable.
- For `dashboard_server.py`, either free port `9000` or temporarily change
  `SERVER_PORT` in `pc_server/protocol_config.py`, then update the PYNQ client
  `--port` value consistently. For `socket_service.py`, use `10000` as shown
  above, or choose another high port such as `10001`.
- Check whether a port is already listening:

```powershell
netstat -ano | Select-String ':9000'
```

- Check Windows reserved TCP port ranges:

```powershell
netsh interface ipv4 show excludedportrange protocol=tcp
netsh interface ipv6 show excludedportrange protocol=tcp
```

- If `--host 0.0.0.0` fails but `--host 127.0.0.1` works, local PC-only smoke
  can still run, but PYNQ integration needs a host binding reachable from the
  board and a firewall rule for the chosen port.

PC service gets no connection:

- Check PYNQ is using `<PC_IPV4>`, not `127.0.0.1`.
- Check Windows firewall for TCP `9000` or the chosen port.
- Check both devices are on the same reachable network.

PYNQ times out waiting for responses:

- Confirm PC service is `dashboard_server.py` or `socket_service.py`, not
  legacy `pc_server.py`.
- Confirm PC stdout has no traceback.
- Confirm only one active PYNQ client is connected.

`Overlay.ip_dict` is empty or `.tcl` is missing:

- Use `--metadata-source auto`; current code falls back to the documented
  static address map for old PYNQ images.
- Keep same-basename `.bit` and `.hwh` beside each other.
- If the board image expects `.tcl`, also keep same-basename `.tcl`.

HR/SpO2 stays null:

- Recheck UART physical orientation. The integrated board smoke required
  crossed RX/TX wiring for the SpO2 module.
- Use `--spo2-frame-len 5` unless validating the alternate frame mode.

Classifier returns no-action:

- The model has a warmup window and requires valid HR/SpO2 samples.
- `state_valid=0` must lead to no automatic actuator changes.

IR command sent but AC does not respond:

- Keep the IR transmitter within approximately 20 cm of the AC receiver.
- Aim directly at the receiver window.
- Confirm the command is one of:
  `power_on`, `power_off`, `temp_24`, `temp_25`, `temp_26`, `temp_27`,
  `temp_28`.

Board timestamps are wrong:

- Fix board time before collecting timestamp-sensitive evidence:

```bash
sudo date -s "YYYY-MM-DD HH:MM:SS"
```

Use the actual local wall-clock time for the run.
