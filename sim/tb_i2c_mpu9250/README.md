# JY901 I2C Sampler Simulation

This testbench verifies the first hardware milestone from [../../docs/i2c_axi_mpu9250.md](../../docs/i2c_axi_mpu9250.md):

- open-drain style I2C master behavior through tri-state SCL/SDA wires;
- `START -> 0xA0 -> 0x34 -> RESTART -> 0xA1` burst read sequence;
- 26 data bytes latched as 13 little-endian 16-bit words;
- `done`, `data_valid`, and `sample_cnt` update after a successful oneshot read.

Run all simulations with `just` when Icarus Verilog is available:

```powershell
cd sim/tb_i2c_mpu9250
just sim
```

This writes generated artifacts under `build/`:

```text
build/bin/*.vvp
build/vcd/*.vcd
build/waves/*.gtkw
```

Direct sampler simulation:

```powershell
cd sim/tb_i2c_mpu9250
just sampler
```

Expected result:

```text
PASS: JY901 burst read simulation completed
PASS: JY901 address NACK simulation completed
```

Top-level AXI4-Lite simulation:

```powershell
cd sim/tb_i2c_mpu9250
just axi
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
just timeout
```

Expected result:

```text
PASS: I2C master timeout path completed
```

Vivado xsim users can add the same files listed in `files.f` to a behavioral simulation set.

Related RTL lives in [../../rtl/i2c_mpu9250/](../../rtl/i2c_mpu9250/). The canonical register-level behavior is documented in [../../docs/register_map.md](../../docs/register_map.md).

Waveform observation:

- [GUIDE.md](GUIDE.md) explains how to run the VCD-producing simulations and how to inspect I2C, sampler, AXI, NACK, and timeout waveforms from first principles.
- [scripts/](scripts/) contains the parameterized GTKWave save-file generator.
- [waves/](waves/) documents the generated `.gtkw` waveform observation presets.

Generate or open waveform presets:

```powershell
just wave-list
just wave-config sampler i2c
just wave axi i2c
```
