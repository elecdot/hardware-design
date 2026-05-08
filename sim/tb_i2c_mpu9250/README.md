# JY901 I2C Sampler Simulation

This testbench verifies the first hardware milestone from [../../docs/i2c_axi_mpu9250.md](../../docs/i2c_axi_mpu9250.md):

- open-drain style I2C master behavior through tri-state SCL/SDA wires;
- `START -> 0xA0 -> 0x34 -> RESTART -> 0xA1` burst read sequence;
- 26 data bytes latched as 13 little-endian 16-bit words;
- `done`, `data_valid`, and `sample_cnt` update after a successful oneshot read.

Run with Icarus Verilog when available:

```powershell
cd sim/tb_i2c_mpu9250
iverilog -g2012 -o tb_jy901_sampler.vvp -f files.f
vvp tb_jy901_sampler.vvp
```

Expected result:

```text
PASS: JY901 burst read simulation completed
PASS: JY901 address NACK simulation completed
```

Top-level AXI4-Lite simulation:

```powershell
cd sim/tb_i2c_mpu9250
iverilog -g2012 -o tb_axi_i2c_jy901_top.vvp -f files_axi_top.f
vvp tb_axi_i2c_jy901_top.vvp
```

Expected result:

```text
PASS: AXI top burst read register path completed
PASS: AXI top clear_done/clear_error path completed
PASS: AXI top WORD_COUNT boundary paths completed
PASS: AXI top auto_mode path completed
PASS: AXI top cfg_write path completed
PASS: AXI top address NACK register path completed
PASS: AXI top extended NACK paths completed
PASS: AXI top soft_reset path completed
```

Timeout path simulation:

```powershell
cd sim/tb_i2c_mpu9250
iverilog -g2012 -o tb_i2c_master_timeout.vvp -f files_timeout.f
vvp tb_i2c_master_timeout.vvp
```

Expected result:

```text
PASS: I2C master timeout path completed
```

Vivado xsim users can add the same files listed in `files.f` to a behavioral simulation set.

Related RTL lives in [../../rtl/i2c_mpu9250/](../../rtl/i2c_mpu9250/). The canonical register-level behavior is documented in [../../docs/register_map.md](../../docs/register_map.md).
