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

## Migrated Handoff IP Register Maps

The following register maps are copied from teammate handoff packages after the
source files were migrated into `rtl/`. They still need local simulation,
Vivado packaging, integrated BD address assignment, and PYNQ smoke evidence
before being treated as verified integrated-system registers.

### dht11_axi_v1_0

| Offset | Name | Access | Description |
|---:|---|---|---|
| `0x00` | `DHT11_DATA` | R | `[31:24] humidity_int`, `[23:16] humidity_dec`, `[15:8] temperature_int`, `[7:0] temperature_dec`. |
| `0x04` | `STATUS_DEBUG` | R | Debug/status bits including current state, bit count, raw/synchronized data line, output enable/value, and receive phase. |
| `0x08` | `COUNT_1US_DBG` | R | Current microsecond counter debug value. |
| `0x0C` | `RESERVED` | RW | Reserved writable register, currently unused. |

### axi_humidifier_v1_0

| Offset | Name | Access | Description |
|---:|---|---|---|
| `0x00` | `CTRL` | RW/W1P | bit0 `enable`, bit1 `manual_mode`, bit2 `manual_on`, bit3 `use_sw_humidity`, bit4 `clear_counter` write-one-pulse. |
| `0x04` | `SW_HUM` | RW | Software humidity input, 0 to 100 percent. |
| `0x08` | `THRESH` | RW | `[7:0] threshold_low`, `[15:8] hysteresis`, `[31:16] dry_alert_s`. |
| `0x0C` | `TIMING` | RW | `[15:0] min_on_s`, `[31:16] min_off_s`. |
| `0x10` | `STATUS` | R | `[7:0] humidity`, bit8 `humidifier_on`, `[10:9] dry_level`, `[15:12] humidifier_leds`, `[31:16] debug/status`. |
| `0x14` | `DRY_SEC` | R | Accumulated humidifier-on seconds. |
| `0x18` | `VERSION` | R | `0x20260601`. |

Default handoff values: `CTRL=0x00000009`, `SW_HUM=50`,
`THRESH=0x000A052D`, `TIMING=0x00000000`.

### tft_lcd_spi_axi_v1_0

| Offset | Name | Access | Reset | Description |
|---:|---|---|---:|---|
| `0x00` | `CTRL` | RW/pulse | `0x0000000C` | bit0 `start`, bit1 `dc`, bit2 `lcd_res`, bit3 `lcd_blk`, bit4 `clear_done`. |
| `0x04` | `DATA` | RW | `0x00000000` | Next SPI byte in `[7:0]`. |
| `0x08` | `CLKDIV` | RW | `0x00000019` | SPI half-period divider; `SCL = S_AXI_ACLK / (2 * CLKDIV)`. |
| `0x0C` | `STATUS` | R | dynamic | bit0 `busy`, bit1 `done_latched`, bit2 `done_pulse`, bit3 `lcd_res`, bit4 `lcd_blk`, bit5 `dc`. |

Software must preserve `CTRL[3:1]` when pulsing `start`; otherwise reset or
backlight can be accidentally deasserted.

### axi_uart_spo2_v1_0

| Offset | Name | Access | Description |
|---:|---|---|---|
| `0x00` | `CTRL` | RW/W1P | bit0 `enable`, bit1 `clear`, bit2 `irq_enable`, bit4 `frame_7byte_mode`. |
| `0x04` | `TXDATA` | W | `[7:0]` TX byte, write bit8 to transmit one byte. |
| `0x08` | `STATUS` | R | bit0 frame seen, bit1 frame error, bit2 CRC OK, bit3 sensor off, bit4 sensor error, bit5 searching, bit6 search timeout, `[10:7] frame_len`. |
| `0x0C` | `MEASURE` | R | `[7:0] BPM`, `[15:8] SpO2`. |
| `0x10` | `WAVE` | R | `[7:0] pleth`, `[15:8] bar graph`, `[23:16] perfusion index`. |
| `0x14` | `FLAGS` | R | `[31:16] frame_counter`, CRC fields, pulse/mode flags. |
| `0x18` | `RAW0` | R | Raw bytes 0 to 3. |
| `0x1C` | `RAW1` | R | Raw bytes 4 to 6. |

The IP defaults to 5-byte frame mode. Use `CTRL[4]` only after confirming the
physical sensor emits the 7-byte frame format.
