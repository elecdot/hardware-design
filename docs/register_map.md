# Register Map

All AXI IP register offsets.

## axi_i2c_jy901_v1_0

AXI4-Lite data width is 32 bits. Register offsets follow
[docs/i2c_axi_mpu9250.md](i2c_axi_mpu9250.md).

| Offset | Name | Access | Reset | Description |
|---:|---|---|---:|---|
| `0x00` | `CTRL` | RW | `0x00000000` | bit0 `enable`, bit1 `oneshot_start` pulse, bit2 `auto_mode`, bit3 `clear_done` pulse, bit4 `clear_error` pulse, bit5 `soft_reset` pulse, bit8 `cfg_write_start` pulse |
| `0x04` | `STATUS` | R | `0x000000C0` after pullups | bit0 `busy`, bit1 `done`, bit2 `data_valid`, bit3 `ack_error`, bit4 `timeout`, bit5 `cfg_done`, bit6 `scl_in`, bit7 `sda_in` |
| `0x08` | `DEV_ADDR` | RW | `0x50` | JY901 7-bit I2C address. Do not write `0xA1`; that is the read address byte. |
| `0x0C` | `START_REG` | RW | `0x34` | First JY901 register for burst read. |
| `0x10` | `WORD_COUNT` | RW | `13` | Number of 16-bit words to read. Hardware clamps to 13 words. |
| `0x14` | `SAMPLE_PERIOD` | RW | `10_000_000` | Auto sampling period in AXI clock cycles. With 100 MHz clock, default is 100 ms. |
| `0x18` | `I2C_CLKDIV` | RW | `250` | Quarter-period divider. With 100 MHz clock, 250 gives 100 kHz SCL. |
| `0x1C` | `ERROR_CODE` | R | `0x00` | `0x01` address-write NACK, `0x02` register NACK, `0x03` address-read NACK, `0x04/0x05` config data NACK, `0x10` timeout. |
| `0x20` | `CFG_REG_ADDR` | RW | `0x00` | JY901 config register address for write-word transaction. |
| `0x24` | `CFG_DATA` | RW | `0x0000` | JY901 config 16-bit data, sent low byte first. |
| `0x28` | `VERSION` | R | `0x4A593101` | JY901 IP version marker. |
| `0x40` | `AX_RAW` | R | `0x0000` | Acceleration X raw signed int16. |
| `0x44` | `AY_RAW` | R | `0x0000` | Acceleration Y raw signed int16. |
| `0x48` | `AZ_RAW` | R | `0x0000` | Acceleration Z raw signed int16. |
| `0x4C` | `GX_RAW` | R | `0x0000` | Gyroscope X raw signed int16. |
| `0x50` | `GY_RAW` | R | `0x0000` | Gyroscope Y raw signed int16. |
| `0x54` | `GZ_RAW` | R | `0x0000` | Gyroscope Z raw signed int16. |
| `0x58` | `HX_RAW` | R | `0x0000` | Magnetic X raw signed int16. |
| `0x5C` | `HY_RAW` | R | `0x0000` | Magnetic Y raw signed int16. |
| `0x60` | `HZ_RAW` | R | `0x0000` | Magnetic Z raw signed int16. |
| `0x64` | `ROLL_RAW` | R | `0x0000` | Roll raw signed int16. |
| `0x68` | `PITCH_RAW` | R | `0x0000` | Pitch raw signed int16. |
| `0x6C` | `YAW_RAW` | R | `0x0000` | Yaw raw signed int16. |
| `0x70` | `TEMP_RAW` | R | `0x0000` | Temperature raw signed int16. |
| `0x74` | `SAMPLE_CNT` | R | `0x00000000` | Successful burst-read sample count. |

Current hardware scope:

- supports single-shot reads, auto-period reads, and one 16-bit config write transaction;
- does not implement multi-master arbitration, clock stretching, interrupts, DMA, FIFO buffering, or 10-bit addressing;
- SCL/SDA are open-drain style outputs and require external pullups to 3.3 V.
