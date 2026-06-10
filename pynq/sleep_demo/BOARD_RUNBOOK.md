# Integrated Board Demo Runbook

This runbook describes how to deploy the integrated overlay and PYNQ runtime
files to the PYNQ-Z1 board, then run the first layered board demo.

Current integrated local artifacts:

- `vivado/gen/system_v0_2.bit`
- `vivado/gen/system_v0_2.hwh`
- `vivado/gen/system_v0_2.tcl`

Both files must be copied to the board together with the same base name. Newer
PYNQ images use the `.hwh` metadata to populate `Overlay.ip_dict`. Some older
PYNQ images instead look for a same-basename `.tcl`; `integrated_demo.py`
therefore falls back to the Phase4 static address map when
`system_v0_2.tcl` is absent.

## Target Layout

Use one dedicated directory on the board:

```text
/home/xilinx/jupyter_notebooks/sleep_monitor/
  system_v0_2.bit
  system_v0_2.hwh
  system_v0_2.tcl        # optional, only if exported for old PYNQ metadata
  sleep_demo/
    integrated_demo.py
    display_ui.py
  jy901_demo/
  dht11_demo/
  spo2_demo/
  tft_lcd_demo/
  humidifier_demo/
  ir_ac_demo/
```

Deploy the contents of local `pynq/` into this target directory. Do not deploy
only `pynq/sleep_demo/`, because `integrated_demo.py` imports sibling driver
directories.

Do not deploy the whole repository to the board for the demo path. The Vivado
project, handoff packs, reports, and generated run directories are unnecessary
and slow to copy.

## Deployment

Set the board address first. The hostname `pynq` works only if the PC can
resolve it; otherwise replace it with the board IPv4 address.

### Recommended: rsync

Use rsync when available from WSL, Git Bash, MSYS2, or another shell that has
OpenSSH and rsync.

```bash
BOARD=xilinx@pynq
DEST=/home/xilinx/jupyter_notebooks/sleep_monitor

ssh "$BOARD" "mkdir -p $DEST"
rsync -av --delete \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.ipynb_checkpoints/' \
  pynq/ "$BOARD:$DEST/"

rsync -av \
  vivado/gen/system_v0_2.bit \
  vivado/gen/system_v0_2.hwh \
  vivado/gen/system_v0_2.tcl \
  "$BOARD:$DEST/"
```

Use `--delete` only when `DEST` is dedicated to this demo. If you keep manual
notes or captures in that directory, remove `--delete`.

PowerShell with rsync uses the same idea:

```powershell
$Board = "xilinx@pynq"
$Dest = "/home/xilinx/jupyter_notebooks/sleep_monitor"

ssh $Board "mkdir -p $Dest"
rsync -av --delete --exclude '__pycache__/' --exclude '*.pyc' --exclude '.ipynb_checkpoints/' .\pynq\ "${Board}:${Dest}/"
rsync -av .\vivado\gen\system_v0_2.bit .\vivado\gen\system_v0_2.hwh .\vivado\gen\system_v0_2.tcl "${Board}:${Dest}/"
```

### Fallback: scp

Use this if rsync is unavailable:

```powershell
$Board = "xilinx@pynq"
$Dest = "/home/xilinx/jupyter_notebooks/sleep_monitor"

ssh $Board "mkdir -p $Dest"
scp -r .\pynq\* "${Board}:${Dest}/"
scp .\vivado\gen\system_v0_2.bit .\vivado\gen\system_v0_2.hwh .\vivado\gen\system_v0_2.tcl "${Board}:${Dest}/"
```

The scp path is less clean because it does not delete stale files and may copy
local cache files.

## Board Wiring Preflight

Power the board off before changing wires.

Required integrated pin plan:

| Module | Signals |
|---|---|
| TFT LCD | PMODA: `lcd_scl=Y18`, `lcd_sda=Y19`, `lcd_res=Y16`, `lcd_dc=Y17`, `lcd_blk=U18` |
| JY901 | Arduino I2C: `i2c_scl=P16`, `i2c_sda=P15`, 3.3 V pullups |
| UART SpO2 | PMODB: `uart_txd=W14`, `uart_rxd=Y14` |
| DHT11 | Arduino IO11: `dht11_0=R17`, pullup required |
| Humidifier | Board LEDs: `humidifier_leds[3:0]` |
| Gree IR AC TX | Arduino `ck_io[0]`: `ir_pwm=T14` |

Safety checks:

- All PL-connected signals must be 3.3 V logic.
- Do not hot-plug modules while the board is powered.
- Share ground between every module and the PYNQ-Z1.
- Do not drive real loads from FPGA pins; board LEDs are only an actuator
  indicator.

## Board Environment Check

SSH into the board:

```bash
ssh xilinx@pynq
```

Check the PYNQ Python environment:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 -c "import pynq; print(pynq.__version__)"
```

Check deployed files:

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor
ls -lh system_v0_2.bit system_v0_2.hwh sleep_demo/integrated_demo.py
```

## Overlay Metadata Smoke

Run this first. It programs the overlay, prints IP names and addresses, then
exits. On newer PYNQ images this uses `Overlay.ip_dict` metadata from the
exported handoff. On older images that either raise `FileNotFoundError` for
`system_v0_2.tcl` or parse the Tcl into an empty `ip_dict`, the script prints a
warning and uses the Phase4 static address map.

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --list-ips
```

Expected custom IP entries:

| IP | Expected address |
|---|---:|
| `axi_i2c_jy901_v1_0_0` | `0x40000000` |
| `axi_humidifier_v1_0_0` | `0x40001000` |
| `tft_lcd_spi_axi_v1_0_0` | `0x40002000` |
| `dht11_axi_v1_0_0` | `0x40003000` |
| `axi_uart_spo2_v1_0_0` | `0x40004000` |
| `gree_ir_axi_v1_0_0` | `0x40005000` |

If the output includes this warning, it is acceptable for first board smoke:

```text
WARNING: Overlay metadata TCL is missing; falling back to the Phase4 static address map.
```

This warning is also acceptable for first board smoke:

```text
WARNING: Overlay metadata produced an empty ip_dict; falling back to the Phase4 static address map.
```

To require Vivado/PYNQ metadata instead of the fallback, pass
`--metadata-source overlay`. To force the static path during bring-up, pass
`--metadata-source static`.

If this step fails, do not continue to the full demo. Fix the bit/hwh pair,
driver file deployment, or IP instance names first.

## Layered Smoke Order

### 1. Driver Bind And Sensor Loop Without Display

Use this to confirm Python imports, overlay metadata, MMIO binding, and sensor
polling do not crash before initializing the TFT.

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/sleep_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 5 \
  --interval 1.0 \
  --sensor-timeout 0.5 \
  --dht11-period 2.0 \
  --no-display \
  --no-humidifier
```

Expected result:

- The program prints JSON-like sample lines.
- JY901, DHT11, or SpO2 may report module-specific errors if hardware is not
  connected or not responding.
- The process should not crash due to missing IP metadata or imports.

### 2. Humidifier Register Smoke

This keeps display off and exercises the PS-controlled humidifier path.

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 5 \
  --interval 1.0 \
  --no-display
```

Expected result:

- Board LEDs reflect the humidifier IP status path.
- `humidifier_on` appears in printed samples.

### 3. Display Smoke

Run only after the TFT is wired and powered correctly.

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 3 \
  --interval 1.0 \
  --tft-clkdiv 50
```

Expected result:

- TFT initializes and draws the dashboard.
- Numeric/status regions update once per sample.

If display initialization fails, rerun with `--no-display` to keep other module
smoke tests moving.

### 4. Gree IR AC TX Smoke

Run this only when the IR transmitter is wired, the lab Gree AC can receive
the command, and sending `temp_26` is acceptable.

```bash
cd /home/xilinx/jupyter_notebooks/sleep_monitor/ir_ac_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --base-addr 0x40005000 \
  --command temp_26 \
  --timeout 15.0
```

Expected result:

- The command prints `before` and `after` status dictionaries.
- `after` should report `done: True`, `error: False`, `preset: 5`, and
  `command: temp_26`.
- If the lab AC is available and aimed correctly, confirm real response by
  observation before claiming IR-5 board evidence.

For distance or aiming checks, keep the same command and repeat it for a
bounded period:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_ir_ac.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --base-addr 0x40005000 \
  --command temp_26 \
  --duration 60 \
  --interval 5 \
  --timeout 15.0
```

Move the transmitter closer to the AC receiver or adjust the angle during this
run. Do not use an unbounded repeat loop for the lab demo.

### 5. Full Local Demo

Run after the previous layers are stable:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 integrated_demo.py \
  --bitfile /home/xilinx/jupyter_notebooks/sleep_monitor/system_v0_2.bit \
  --samples 30 \
  --interval 1.0 \
  --sensor-timeout 0.5 \
  --dht11-period 2.0 \
  --tft-clkdiv 50 \
  --spo2-frame-len 5
```

This is still a board-side local demo. PC socket/Excel integration remains a
later layer.

## Result Interpretation

The printed sample uses the protocol fields documented in `docs/protocol.md`.

Important status bits from `integrated_demo.py`:

| Bit | Meaning |
|---:|---|
| `0x01` | JY901 read/config path reported an exception |
| `0x02` | DHT11 read path reported an exception |
| `0x04` | SpO2 path reported sensor/frame/error condition |
| `0x08` | Humidifier register path reported an exception |

Useful fields:

- `jy901_status`: JY901 status summary.
- `temperature_c`, `humidity_percent`: DHT11-derived environment values.
- `heart_rate_bpm`, `spo2_percent`: UART SpO2 values when frames are received.
- `turnover_flag`, `turnover_count`: local movement logic from JY901 roll/pitch.
- `humidifier_on`: PS-controlled humidifier IP state.

## Common Failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Missing `.hwh` error | `.bit` was copied without same-basename `.hwh` | Copy `system_v0_2.bit` and `system_v0_2.hwh` together |
| Missing `.tcl` error from `pynq.pl._TCL` | Older PYNQ image expects TCL metadata | Update `integrated_demo.py`; default `--metadata-source auto` falls back to the Phase4 static address map |
| `--metadata-source overlay` prints `(none)` or no IP entries | Tcl exists but this PYNQ parser did not extract IP metadata | Use default `auto` or explicit `static` for first board smoke; do not treat this as a hardware failure |
| `Cannot find IP ...` | Wrong `.hwh`, stale overlay, or old default IP names | Run `--list-ips`; compare instance names with this runbook |
| `ImportError` for driver modules | Only `sleep_demo/` was copied | Deploy local `pynq/` contents so sibling driver directories exist |
| JY901 timeout/NACK | Wiring, pullups, address, or module power issue | Check `P16/P15`, 3.3 V pullups, GND, and `DEV_ADDR=0x50` |
| TFT blank | Wiring, backlight, reset/DC pins, or SPI speed issue | Confirm PMODA wiring and retry with `--tft-clkdiv 50` |
| DHT11 always zero | Sensor timing, pullup, or data pin issue | Use 1 to 2 second read interval and confirm `R17` DATA pullup |
| SpO2 never updates | UART signal direction or frame mode issue | Start with default 5-byte mode; board test confirmed the module-side RX/TX labels may need crossed wiring on `W14/Y14` |
| Board-side Python cannot import `pynq` | Wrong Python interpreter | Use `sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6` |

## When Updating Files

For Python-only changes:

```bash
rsync -av --delete --exclude '__pycache__/' --exclude '*.pyc' pynq/ xilinx@pynq:/home/xilinx/jupyter_notebooks/sleep_monitor/
```

For a regenerated overlay:

```bash
rsync -av vivado/gen/system_v0_2.bit vivado/gen/system_v0_2.hwh vivado/gen/system_v0_2.tcl xilinx@pynq:/home/xilinx/jupyter_notebooks/sleep_monitor/
```

Use both commands when code and hardware artifacts changed.
