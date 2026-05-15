# i2c_mpu9250

AXI-Lite custom IP that reads JY901/MPU9250 motion data over an open-drain I2C bus and exposes raw samples to the PS.

## Files

| File | Purpose |
|---|---|
| [axi_i2c_jy901_v1_0.v](axi_i2c_jy901_v1_0.v) | Top-level AXI IP wrapper with external `i2c_scl` and `i2c_sda` ports. |
| [axi_lite_regs.v](axi_lite_regs.v) | AXI4-Lite register bank and software-visible register defaults. |
| [jy901_hw_debug_top.v](jy901_hw_debug_top.v) | Non-AXI Vivado hardware-debug top for direct auto-sampling and ILA bring-up. |
| [jy901_sampler.v](jy901_sampler.v) | Sampling scheduler for oneshot, auto sampling, and config-write transactions. |
| [i2c_master_core.v](i2c_master_core.v) | Bit-level I2C master state machine for burst reads and 16-bit config writes. |
| [i2c_open_drain_io.v](i2c_open_drain_io.v) | Open-drain style SCL/SDA tri-state adapter. |

## Quick Facts

- Target clock assumption: 100 MHz AXI clock unless configured otherwise.
- Default JY901 7-bit I2C address: `0x50`; do not use read byte `0xA1` as the register value.
- Default sample window: 13 little-endian 16-bit words from JY901 register `0x34`.
- Default `I2C_CLKDIV`: `250`, giving about 100 kHz SCL from a 100 MHz clock.
- SCL/SDA must be pulled up to 3.3 V, not 5 V.

## Related Files

| Path | Purpose |
|---|---|
| [../../docs/i2c_axi_mpu9250.md](../../docs/i2c_axi_mpu9250.md) | Full design note and rationale. |
| [../../docs/register_map.md](../../docs/register_map.md) | Software-visible register map. |
| [../../docs/wiring.md](../../docs/wiring.md) | PYNQ-Z1 wiring and voltage constraints. |
| [../../sim/tb_i2c_mpu9250/](../../sim/tb_i2c_mpu9250/) | Behavioral simulation for the sampler/core path. |
| [../../vivado/constraints/i2c_jy901_pynq_z1.xdc](../../vivado/constraints/i2c_jy901_pynq_z1.xdc) | Current PYNQ-Z1 external pin constraints. |
| [../../vivado/constraints/jy901_debug.xdc](../../vivado/constraints/jy901_debug.xdc) | Full constraints for the PL-only hardware debug top. |

Before changing register offsets or status bits, update [../../docs/register_map.md](../../docs/register_map.md) in the same change.

## Hardware Debug Top

[jy901_hw_debug_top.v](jy901_hw_debug_top.v) is an optional non-AXI Vivado bring-up top. It directly instantiates `jy901_sampler` with fixed `DEV_ADDR=0x50`, `START_REG=0x34`, and `WORD_COUNT=13`, marks first-level I2C/status/data signals for ILA, and maps `i2c_busy`, `done`, `data_valid`, and `ack_error | timeout` to `led[3:0]`. It also exposes core-level debug probes such as `core_state_dbg`, `core_step_dbg`, `core_tx_byte_dbg`, and `core_sda_in_dbg` so hardware NACKs can be diagnosed from ILA. It synchronizes the SW0 reset input, launches one debug oneshot after reset release, and then continues auto-sampling at `SAMPLE_PERIOD_CYCLES` intervals. It is for PL-only hardware debug, not a replacement for the AXI/PYNQ wrapper. Use [../../vivado/constraints/jy901_debug.xdc](../../vivado/constraints/jy901_debug.xdc) for its 125 MHz clock, SW0 reset, LEDs, and PMODA I2C pinout, and keep `CLK_HZ` matched to the actual fabric clock.
