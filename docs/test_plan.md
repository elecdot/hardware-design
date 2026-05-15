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
