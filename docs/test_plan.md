# Test Plan

Module and system-level test checklist.

## Final Integrated Overlay Acceptance Target

Final course acceptance targets one complete Vivado overlay hardware platform,
one matching `.hwh`, one PYNQ driver suite, and one demonstrable board-side
program. Single-module overlays and direct-MMIO scripts remain validation tools
for isolating bring-up failures, but they are not the preferred final
acceptance path.

Minimum integrated acceptance evidence:

- Vivado Block Design validates with all selected IP present.
- The integrated build exports matching `.bit` and `.hwh` artifacts from the
  same run.
- The integrated XDC uses the planned pin allocation in [wiring.md](wiring.md):
  PMODA for TFT LCD, Arduino `P16/P15` for JY901 I2C, PMODB `W14/Y14` for UART
  SpO2, Arduino IO11 `R17` for DHT11, and board LEDs for humidifier indication.
- PYNQ loads the integrated overlay and binds IPs through `.hwh`/`Overlay.ip_dict`
  rather than single-module hard-coded base addresses.
- The acceptance program demonstrates the stable available paths from the
  shared driver suite: JY901 read/status, DHT11 read, UART SpO2 read, TFT update,
  and PS-side humidifier control or status display.

If an integrated platform or driver issue blocks one module, record the blocking
condition and validate that module with the smallest standalone overlay/driver
path before returning to the integrated build.

PC socket/Excel integration is a later-priority final-system layer after the
board-side integrated demo. Validate it in layers:

1. PC-only: run `pc_server.py` and `fake_pynq_client.py` from the socket handoff
   and confirm JSON send/receive plus Excel writes.
2. PYNQ synthetic: run a PYNQ client that sends synthetic `sensor_data` to the
   PC's real IPv4 address and receives `sleep_result`.
3. Integrated driver: replace synthetic values with values from the integrated
   PYNQ driver suite.

Do not let PC firewall, IP address, or `openpyxl` setup block the lower-risk
board-side integrated acceptance path.

## Migrated Handoff Module Regression

These modules have source files migrated from `handoff/` into tracked repo
directories. Their handoff evidence is useful context, but local repo
simulation or board evidence is still required before claiming they work in the
integrated overlay.

### Phase2 Smoke Results

Date: 2026-06-02. Tool: Icarus Verilog (`iverilog` + `vvp`).

The following focused simulations compile and run locally:

```text
tb_humidifier_core PASS
tb_axi_humidifier PASS
tb_spi_lcd_master PASS
tb_tft_lcd_spi_axi PASS
tb_dht11_onewire_smoke PASS data_valid=37001900
tb_spo2_frame_parser PASS
```

Scope of this evidence:

- Humidifier core threshold/manual behavior and AXI register path.
- TFT SPI byte transmitter and AXI wrapper byte-send path.
- DHT11 one-wire valid-frame decode for 55% RH and 25 C using an Icarus `IOBUF`
  stub.
- SpO2 frame parser decode for known 5-byte and 7-byte frames.

This is not Vivado synthesis, IP packaging, integrated BD validation, or board
evidence.

### DHT11 AXI IP

Source:

- [../rtl/dht11_axi/](../rtl/dht11_axi/)
- [../sim/tb_dht11_axi/](../sim/tb_dht11_axi/)
- [../pynq/dht11_demo/](../pynq/dht11_demo/)

Expected first checks:

- DHT11 frame simulation emits explicit PASS/FAIL.
- `DHT11_DATA` decodes humidity and temperature bytes in the documented order.
- Board test reads nonzero data at intervals of at least 1 to 2 seconds.
- Integrated overlay uses Arduino IO11 `R17` with 3.3 V logic and pullup.

### AXI Humidifier IP

Source:

- [../rtl/axi_humidifier/](../rtl/axi_humidifier/)
- [../sim/tb_axi_humidifier/](../sim/tb_axi_humidifier/)
- [../pynq/humidifier_demo/](../pynq/humidifier_demo/)

Expected handoff PASS markers to reproduce:

```text
tb_humidifier_core PASS
tb_axi_humidifier PASS
```

First integrated demo path:

- PYNQ reads DHT11 humidity.
- PYNQ writes humidifier `SW_HUM`.
- Board LEDs reflect humidifier state.
- [../pynq/sleep_demo/integrated_demo.py](../pynq/sleep_demo/integrated_demo.py)
  prints `temperature_c`, `humidity_percent`, and `humidifier_on` from the
  integrated overlay run.

### TFT LCD SPI AXI IP

Source:

- [../rtl/tft_lcd_spi_axi/](../rtl/tft_lcd_spi_axi/)
- [../sim/tb_tft_lcd_spi_axi/](../sim/tb_tft_lcd_spi_axi/)
- [../pynq/tft_lcd_demo/](../pynq/tft_lcd_demo/)

Expected first checks:

- SPI byte transmitter and AXI wrapper simulations emit PASS/FAIL.
- Board test initializes ST7789 with `CLKDIV=50`.
- Initial UI draws full `SLEEP MONITOR` dashboard once.
- Runtime loop updates only numeric/status regions at 1 Hz, then up to 2 Hz if
  stable.

### UART SpO2 AXI IP

Source:

- [../rtl/axi_uart_spo2/](../rtl/axi_uart_spo2/)
- [../sim/tb_axi_uart_spo2/](../sim/tb_axi_uart_spo2/)
- [../pynq/spo2_demo/](../pynq/spo2_demo/)

Expected first checks:

- Add a byte-stream/frame-parser simulation for 5-byte mode.
- Verify 9600 baud timing at the integrated AXI clock.
- Keep the PYNQ helper Python 3.6-compatible; `Spo2Sample` is intentionally a
  plain class instead of a `dataclass`.
- Board test confirms BPM/SpO2 update from the physical module.

## I2C JY901 / MPU9250 AXI IP

### Behavioral simulation

Location: [../sim/tb_i2c_mpu9250/](../sim/tb_i2c_mpu9250/).

Files:

- [../rtl/i2c_mpu9250/i2c_master_core.v](../rtl/i2c_mpu9250/i2c_master_core.v)
- [../rtl/i2c_mpu9250/jy901_sampler.v](../rtl/i2c_mpu9250/jy901_sampler.v)
- [../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v](../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v)
- [../sim/tb_i2c_mpu9250/tb_jy901_sampler.v](../sim/tb_i2c_mpu9250/tb_jy901_sampler.v)

Command when `just` and Icarus Verilog are installed:

```powershell
cd sim/tb_i2c_mpu9250
just sampler
```

Generated artifacts are written under `sim/tb_i2c_mpu9250/build/`.

Expected checks:

- I2C transaction is `START, 0xA0, 0x34, RESTART, 0xA1, 26 data bytes, NACK, STOP`.
- `ack_error == 0`.
- `timeout == 0`.
- `data_valid == 1`.
- `sample_cnt == 1`.
- `AX_RAW == 0x1234`, `AY_RAW == 0x5678`, `TEMP_RAW == 0x0D0C` for the included slave model.

### Error-path simulation

The same testbench then runs an address-error case:

- set `dev_addr = 0x51`;
- expect `ack_error == 1`;
- expect `ERROR_CODE == 0x01`.

### AXI top-level simulation

Location: [../sim/tb_i2c_mpu9250/](../sim/tb_i2c_mpu9250/).

Files:

- [../rtl/i2c_mpu9250/i2c_open_drain_io.v](../rtl/i2c_mpu9250/i2c_open_drain_io.v)
- [../rtl/i2c_mpu9250/i2c_master_core.v](../rtl/i2c_mpu9250/i2c_master_core.v)
- [../rtl/i2c_mpu9250/jy901_sampler.v](../rtl/i2c_mpu9250/jy901_sampler.v)
- [../rtl/i2c_mpu9250/axi_lite_regs.v](../rtl/i2c_mpu9250/axi_lite_regs.v)
- [../rtl/i2c_mpu9250/axi_i2c_jy901_v1_0.v](../rtl/i2c_mpu9250/axi_i2c_jy901_v1_0.v)
- [../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v](../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v)
- [../sim/tb_i2c_mpu9250/tb_axi_i2c_jy901_top.v](../sim/tb_i2c_mpu9250/tb_axi_i2c_jy901_top.v)

Command:

```powershell
cd sim/tb_i2c_mpu9250
just axi
```

Expected checks:

- AXI reads `VERSION == 0x4A593101`.
- AXI reads reset `DEV_ADDR == 0x50`.
- AXI writes `I2C_CLKDIV`, `START_REG`, `WORD_COUNT`, `DEV_ADDR`, and `CTRL`.
- AXI polls `STATUS.done`.
- Normal path returns `STATUS.data_valid == 1`, `STATUS.ack_error == 0`, and `STATUS.timeout == 0`.
- AXI reads `AX_RAW == 0x1234`, `AY_RAW == 0x5678`, `TEMP_RAW == 0x0D0C`, and `SAMPLE_CNT == 1`.
- `clear_done` and `clear_error` clear sticky done/error flags.
- `WORD_COUNT` boundary cases `1`, `0`, and `20` complete without error. Hardware treats `0` as one word and clamps values above 13 words.
- `auto_mode` increments `SAMPLE_CNT` across periodic transactions.
- `cfg_write_start` sends a config write and sets `STATUS.cfg_done`.
- Address NACK path returns `STATUS.ack_error == 1` and `ERROR_CODE == 0x01`.
- Register-address NACK returns `ERROR_CODE == 0x02`.
- Read-address NACK returns `ERROR_CODE == 0x03`.
- Config low-byte NACK returns `ERROR_CODE == 0x04`.
- Config high-byte NACK returns `ERROR_CODE == 0x05`.
- `soft_reset` clears sampled data and status flags.

### Timeout simulation

Location: [../sim/tb_i2c_mpu9250/](../sim/tb_i2c_mpu9250/).

Files:

- [../rtl/i2c_mpu9250/i2c_master_core.v](../rtl/i2c_mpu9250/i2c_master_core.v)
- [../sim/tb_i2c_mpu9250/tb_i2c_master_timeout.v](../sim/tb_i2c_mpu9250/tb_i2c_master_timeout.v)

Command:

```powershell
cd sim/tb_i2c_mpu9250
just timeout
```

Expected checks:

- `i2c_master_core` is instantiated with a reduced `TIMEOUT_CYCLES`.
- The transaction times out before the first I2C phase completes.
- `timeout == 1`.
- `ack_error == 0`.
- `ERROR_CODE == 0x10`.

### Single-module board test

Minimum first board test:

1. Wire JY901 VCC to 3.3 V, GND to GND, SCL/SDA to the constrained PYNQ-Z1 pins.
2. Confirm SCL/SDA pull up to 3.3 V, not 5 V.
3. Program the bitstream and set:
   - `DEV_ADDR = 0x50`
   - `START_REG = 0x34`
   - `WORD_COUNT = 1`
   - `I2C_CLKDIV = 250`
4. Write `CTRL = enable | oneshot_start`.
5. Read `STATUS`, `ERROR_CODE`, `AX_RAW`, and `SAMPLE_CNT`.

Passing criteria:

- `STATUS.done == 1`;
- `STATUS.ack_error == 0`;
- `SAMPLE_CNT` increments;
- logic analyzer or ILA shows `0xA0 0x34 0xA1`.

### PYNQ AXI driver demo

Location: [../pynq/jy901_demo/](../pynq/jy901_demo/).

Use this when demonstrating the minimal PS-side path to an assessor. The v1
demo intentionally uses bitstream download and direct MMIO instead of `.hwh`
overlay discovery because this matches the current smoke-tested board flow.

Board runtime:

- Jupyter kernel uses `/opt/python3.6/bin/python3.6` as root with PYNQ
  packages under `/opt/python3.6/lib/python3.6/site-packages`;
- SSH CLI default `/usr/bin/python3` is version 3.4.3+ and does not match the
  complete Jupyter/PYNQ environment;
- legacy CLI `python` may report 2.7.10 but is not the demo target;
- Linux 4.6.0-xilinx on PYNQ-Z1.

Command on the board:

```bash
cd /home/xilinx/jupyter_notebooks/jy901_test/jy901_demo
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 10
```

Default demo parameters:

- bitstream `/home/xilinx/jupyter_notebooks/jy901_test/jy901_axi_package.bit`;
- base address `0x43C00000`;
- address range `0x10000`;
- `I2C_CLKDIV = 500`;
- `DEV_ADDR = 0x50`, `START_REG = 0x34`, `WORD_COUNT = 13`.

Passing criteria:

- `VERSION == 0x4A593101`;
- initial oneshot increments `SAMPLE_CNT`;
- no `ack_error` or `timeout`;
- repeated table rows show increasing `SAMPLE_CNT`;
- raw/scaled values change when the physical JY901 is moved.

Do not mark this as a PC-integrated or end-to-end pass; v1 does not send data
to a PC server or run a sleep-stage model.

### PL-only hardware debug top

Optional direct Vivado bring-up top: [../rtl/i2c_mpu9250/jy901_hw_debug_top.v](../rtl/i2c_mpu9250/jy901_hw_debug_top.v).

Use this when the goal is to test the sampler/I2C path before relying on AXI/PYNQ software. The top fixes:

- `enable = 1`;
- `auto_mode = 1`;
- `DEV_ADDR = 0x50`;
- `START_REG = 0x34`;
- `WORD_COUNT = 13`;
- one debug oneshot after reset release;
- sample period to roughly 0.5 s using its `CLK_HZ` parameter.

Vivado integration requirements:

- include `jy901_hw_debug_top.v`, `i2c_open_drain_io.v`, `jy901_sampler.v`, and `i2c_master_core.v`;
- apply [../vivado/constraints/jy901_debug.xdc](../vivado/constraints/jy901_debug.xdc) for the debug top clock, reset, LEDs, and PMODA I2C pins;
- do not also apply another XDC that maps `i2c_scl` or `i2c_sda` to different pins in the same build;
- confirm `CLK_HZ` matches the actual fabric clock used by the project.
- arm ILA first, then toggle SW0 from reset asserted to released if triggering on the reset-release debug oneshot.

Passing criteria:

- ILA shows `ack_error == 0` and `timeout == 0`;
- `sample_cnt` increments over repeated auto samples;
- `data_valid == 1` after the first successful sample;
- ILA or logic analyzer shows `START, 0xA0, 0x34, RESTART, 0xA1`;
- at least one raw data word changes when the physical JY901 orientation changes.

If `ERROR_CODE == 0x01`, the master reached the write-address ACK bit and saw
SDA high. In ILA, check `core_tx_byte_dbg == 0xA0`, `core_step_dbg == 0`, and
`core_sda_in_dbg == 1` near the ACK state. If these are true, debug wiring,
pullups, module power, PMODA pin selection, or the actual JY901 I2C address
before changing RTL timing.

Do not mark this as a hardware pass until ILA, logic analyzer, or user-confirmed board evidence is available.
