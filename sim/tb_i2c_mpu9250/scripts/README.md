# Waveform Scripts

This directory contains helper entry points for the I2C/JY901 behavioral
simulation waveform workflow.

## GTKWave Config Generator

`wave_config.py` generates parameterized GTKWave save files under
`../build/waves/` by default. It expects VCD files under `../build/vcd/`,
matching the parent `justfile` recipes.

The parent `justfile` uses uv by default and places the uv cache under
`build/uv-cache`:

```powershell
cd sim/tb_i2c_mpu9250
just wave-config sampler quick
```

No third-party Python packages are required, so plain Python is also valid:

```powershell
cd sim/tb_i2c_mpu9250
python scripts/wave_config.py --bench axi --view i2c --strict
```

List available bench/view combinations:

```powershell
python scripts/wave_config.py --list
```

Generate every configured GTKWave save file:

```powershell
python scripts/wave_config.py --all --strict
```

The generator validates requested signal names against an existing VCD when
that VCD is present. Use `--no-validate` only when preparing a save file before
running the simulation.

## just Entry Points

From `sim/tb_i2c_mpu9250/`:

```powershell
just sim
just wave-config sampler quick
just wave-configs
just wave axi i2c
just observe-list
just observe-i2c-bus
```

To override the Python runner from just:

```powershell
just --set py_run python wave-config timeout errors
```

Direct uv invocation should also keep its cache in `build/` on locked-down
Windows environments:

```powershell
$env:UV_CACHE_DIR = "build/uv-cache"
uv run --script scripts/wave_config.py --bench timeout --view errors --strict
```
