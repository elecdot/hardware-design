# Waveform Save File Notes

Generated GTKWave `.gtkw` save files are written to `../build/waves/`, not this
source directory. Keeping generated files under `build/` avoids mixing
simulation outputs with reviewed testbench sources.

Generated names use this form:

```text
<bench>_<view>.gtkw
```

Core observation recipes in `../justfile` map the waveform views to
`GUIDE.md`:

| Recipe | GUIDE scope | Generated view |
|---|---|---|
| `just observe-sampler-core` | 9.1 minimal sampler/core/status signals | `build/waves/sampler_quick.gtkw` |
| `just observe-i2c-bus` | 6.1-6.6 I2C open-drain, START/RESTART/STOP, ACK/NACK | `build/waves/sampler_i2c.gtkw` |
| `just observe-sampler-data` | 6.7-6.8 byte capture, little-endian words, sample count | `build/waves/sampler_data.gtkw` |
| `just observe-axi-path` | 8.1-8.4 AXI writes, reads, STATUS, clear pulses | `build/waves/axi_axi.gtkw` |
| `just observe-axi-data` | 8.3, 8.5-8.7 AXI data, WORD_COUNT, auto_mode, soft_reset | `build/waves/axi_data.gtkw` |
| `just observe-nack-errors` | 7.1-7.4 address/register/read/config NACK paths | `build/waves/axi_errors.gtkw` |
| `just observe-timeout` | 7.5 timeout path | `build/waves/timeout_errors.gtkw` |

Manual example:

```powershell
cd sim/tb_i2c_mpu9250
just wave-config sampler i2c
gtkwave build/waves/sampler_i2c.gtkw
```

Each save file references the VCD under `../build/vcd/`, such as
`../vcd/tb_jy901_sampler.vcd` relative to `build/waves/`. Re-run the matching
simulation after changing RTL or testbench timing so the VCD matches the
source.
