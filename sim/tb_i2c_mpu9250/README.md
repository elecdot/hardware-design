# JY901 I2C Sampler Simulation

This testbench verifies the first hardware milestone from `docs/i2c_axi_mpu9250.md`:

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

Vivado xsim users can add the same files listed in `files.f` to a behavioral simulation set.

Related RTL lives in `../../rtl/i2c_mpu9250/`. The canonical register-level behavior is documented in `../../docs/register_map.md`.
