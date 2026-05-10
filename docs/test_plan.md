# Test Plan

Module and system-level test checklist.

## I2C JY901 / MPU9250 AXI IP

### Behavioral simulation

Location: [../sim/tb_i2c_mpu9250/](../sim/tb_i2c_mpu9250/).

Files:

- [../rtl/i2c_mpu9250/i2c_master_core.v](../rtl/i2c_mpu9250/i2c_master_core.v)
- [../rtl/i2c_mpu9250/jy901_sampler.v](../rtl/i2c_mpu9250/jy901_sampler.v)
- [../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v](../sim/tb_i2c_mpu9250/jy901_i2c_slave_model.v)
- [../sim/tb_i2c_mpu9250/tb_jy901_sampler.v](../sim/tb_i2c_mpu9250/tb_jy901_sampler.v)

Command when Icarus Verilog is installed:

```powershell
cd sim/tb_i2c_mpu9250
iverilog -g2012 -o tb_jy901_sampler.vvp -f files.f
vvp tb_jy901_sampler.vvp
```

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
iverilog -g2012 -o tb_axi_i2c_jy901_top.vvp -f files_axi_top.f
vvp tb_axi_i2c_jy901_top.vvp
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
iverilog -g2012 -o tb_i2c_master_timeout.vvp -f files_timeout.f
vvp tb_i2c_master_timeout.vvp
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

## Waveform signals to observe

### Behavioral simulation (`tb_jy901_sampler`)

- **I2C bus signals:** `i2c_scl`, `i2c_sda`. Verify start condition (SDA low while SCL high), device address (`0xA0`), register address (`0x34`), repeat start, read address (`0xA1`), 26 data bytes, NACK, stop condition.
- **I2C master signals:** `scl_drive_low`, `sda_drive_low` to see when the master pulls lines low.
- **Master state machine:** `dut.i2c_master_core_i.state` (states 0-16 as defined) shows sequence of operations.
- **Tx/Rx data:** `tx_byte`, `rx_data`, `rx_valid`, `rx_index`, `byte_cnt`, `bit_cnt`. Confirm that each byte is sent/received correctly.
- **Control outputs:** `busy`, `done`, `data_valid`, `ack_error`, `timeout`, `error_code`. Check that `done` rises briefly at end, `ack_error` and `timeout` stay low.
- **Data outputs:** `data0`..`data12`, `sample_cnt`. Verify expected values for normal pass.

### Address NACK path

Same signals as above. Watch `ack_error` go high and `error_code` become `0x01`, and that the sequence stops after sending device address without ack.

### AXI top-level simulation (`tb_axi_i2c_jy901_top`)

- **I2C bus and internal master signals** as listed above.
- **AXI control:** (optional) look at `S_AXI_AWVALID`, `S_AXI_ARVALID`, etc. for completeness.
- **Register interface outputs:** `data0`..`data12`, `sample_cnt`, `data_valid`, `ack_error`, `timeout`, `error_code`, `done`, `cfg_done`.
- **Auto-mode signals:** observe `sample_cnt` incrementing over multiple transactions; `busy` pulses.
- **Error codes per step:** confirm `error_code` values `0x01`..`0x05` for corresponding NACK scenarios.
- **Soft reset:** after `soft_reset`, all data outputs and status flags return to zero.

### Timeout simulation (`tb_i2c_master_timeout`)

- **Master state machine:** verify state never leaves `ST_IDLE` or hangs in middle.
- **Timeout counter:** `timeout_cnt` (internal) increments; `timeout` asserts before any I2C phase completes.
- **Flags:** `timeout` = `1`, `ack_error` = `0`, `error_code` = `0x10`.
- **Tick divider:** `div_cnt` and `tick` may help check speed.
