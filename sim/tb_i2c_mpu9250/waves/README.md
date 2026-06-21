# Waveform Save File Notes

生成的 GTKWave `.gtkw` save file 会写入 `../build/waves/`，而不是本源码目录。
将生成文件保存在 `build/` 下，可以避免把仿真输出与已审查 testbench 源码混在一起。

生成文件名采用以下形式：

```text
<bench>_<view>.gtkw
```

`../justfile` 中的核心观察 recipe 将波形视图映射到 `GUIDE.md`：

| Recipe | GUIDE 范围 | 生成视图 |
|---|---|---|
| `just observe-sampler-core` | 9.1 最小 sampler/core/status 信号 | `build/waves/sampler_quick.gtkw` |
| `just observe-i2c-bus` | 6.1-6.6 I2C open-drain、START/RESTART/STOP、ACK/NACK | `build/waves/sampler_i2c.gtkw` |
| `just observe-sampler-data` | 6.7-6.8 字节捕获、little-endian word、sample count | `build/waves/sampler_data.gtkw` |
| `just observe-axi-path` | 8.1-8.4 AXI 写、读、STATUS、clear pulse | `build/waves/axi_axi.gtkw` |
| `just observe-axi-data` | 8.3、8.5-8.7 AXI data、WORD_COUNT、auto_mode、soft_reset | `build/waves/axi_data.gtkw` |
| `just observe-nack-errors` | 7.1-7.4 address/register/read/config NACK 路径 | `build/waves/axi_errors.gtkw` |
| `just observe-timeout` | 7.5 timeout 路径 | `build/waves/timeout_errors.gtkw` |

手动示例：

```powershell
cd sim/tb_i2c_mpu9250
just wave-config sampler i2c
gtkwave build/waves/sampler_i2c.gtkw
```

每个 save file 都引用 `../build/vcd/` 下的 VCD，例如相对于 `build/waves/` 的
`../vcd/tb_jy901_sampler.vcd`。修改 RTL 或 testbench 时序后，重新运行对应仿真，
保证 VCD 与源码匹配。
