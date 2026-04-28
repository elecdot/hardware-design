# Test Plan

Module and system-level test checklist.

## I2C JY901 / MPU9250 AXI IP

### Behavioral simulation

Location:

```text
sim/tb_i2c_mpu9250/
```

Files:

```text
rtl/i2c_mpu9250/i2c_master_core.v
rtl/i2c_mpu9250/jy901_sampler.v
sim/tb_i2c_mpu9250/tb_jy901_sampler.v
```

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
