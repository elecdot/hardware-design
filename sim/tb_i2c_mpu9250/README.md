> 这远不只是一个标准的“simulation pass”。
> 它用于支持快速观察波形，帮助我充分准备 I2C IP 期中检查。
>
> 一般仿真也许不需要复杂脚本来构建多个 artifact，
> 但这个仿真环境确实需要。

# JY901 I2C Sampler Simulation

该 testbench 验证 [../../docs/i2c_axi_mpu9250.md](../../docs/i2c_axi_mpu9250.md) 中的首个硬件里程碑：

- 通过三态 SCL/SDA 线实现 open-drain 风格 I2C master 行为；
- `START -> 0xA0 -> 0x34 -> RESTART -> 0xA1` burst read 序列；
- 26 个数据字节锁存为 13 个 little-endian 16-bit word；
- 成功 oneshot read 后更新 `done`、`data_valid` 和 `sample_cnt`。

如果可用 Icarus Verilog，用 `just` 运行全部仿真：

```powershell
cd sim/tb_i2c_mpu9250
just sim
```

这会把生成的 artifact 写到 `build/` 下：

```text
build/bin/*.vvp
build/vcd/*.vcd
build/waves/*.gtkw
```

直接 sampler 仿真：

```powershell
cd sim/tb_i2c_mpu9250
just sampler
```

预期结果：

```text
PASS: JY901 burst read simulation completed
PASS: JY901 address NACK simulation completed
```

顶层 AXI4-Lite 仿真：

```powershell
cd sim/tb_i2c_mpu9250
just axi
```

预期结果：

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

timeout 路径仿真：

```powershell
cd sim/tb_i2c_mpu9250
just timeout
```

预期结果：

```text
PASS: I2C master timeout path completed
```

Vivado xsim 用户可以把 `files.f` 中列出的同一组文件加入 behavioral simulation set。

相关 RTL 位于 [../../rtl/i2c_mpu9250/](../../rtl/i2c_mpu9250/)。
规范寄存器级行为见 [../../docs/register_map.md](../../docs/register_map.md)。

波形观察：

- [GUIDE.md](GUIDE.md) 说明如何运行生成 VCD 的仿真，以及如何从第一性原理检查 I2C、sampler、AXI、NACK 和 timeout 波形。
- [scripts/](scripts/) 包含参数化 GTKWave save-file generator。
- [waves/](waves/) 记录生成的 `.gtkw` 波形观察 preset。

生成或打开波形 preset：

```powershell
just wave-list
just wave-config sampler i2c
just wave axi i2c
```

核心观察 recipe 与 [GUIDE.md](GUIDE.md) 对应：

```powershell
just observe-list
just observe-i2c-bus
just observe-axi-path
just observe-nack-errors
just observe-timeout
```
