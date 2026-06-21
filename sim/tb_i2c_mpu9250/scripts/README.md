# Waveform Scripts

本目录包含 I2C/JY901 行为仿真波形工作流的辅助入口。

## GTKWave 配置生成器

`wave_config.py` 默认在 `../build/waves/` 下生成参数化 GTKWave save file。
它期望 VCD 文件位于 `../build/vcd/`，与父级 `justfile` recipe 匹配。

父级 `justfile` 默认使用 uv，并把 uv cache 放在 `build/uv-cache` 下：

```powershell
cd sim/tb_i2c_mpu9250
just wave-config sampler quick
```

不需要第三方 Python package，因此普通 Python 也可使用：

```powershell
cd sim/tb_i2c_mpu9250
python scripts/wave_config.py --bench axi --view i2c --strict
```

列出可用的 bench/view 组合：

```powershell
python scripts/wave_config.py --list
```

生成所有已配置的 GTKWave save file：

```powershell
python scripts/wave_config.py --all --strict
```

当对应 VCD 已存在时，生成器会根据该 VCD 校验请求的信号名。
仅在运行仿真前预先准备 save file 时使用 `--no-validate`。

## just 入口

从 `sim/tb_i2c_mpu9250/` 执行：

```powershell
just sim
just wave-config sampler quick
just wave-configs
just wave axi i2c
just observe-list
just observe-i2c-bus
```

从 just 覆盖 Python runner：

```powershell
just --set py_run python wave-config timeout errors
```

在受限 Windows 环境中，直接调用 uv 时也应把 cache 放到 `build/` 下：

```powershell
$env:UV_CACHE_DIR = "build/uv-cache"
uv run --script scripts/wave_config.py --bench timeout --view errors --strict
```
