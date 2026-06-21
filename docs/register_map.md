# Register Map

所有 AXI IP 寄存器 offset。

## axi_i2c_jy901_v1_0

AXI4-Lite data width 为 32 bit。寄存器 offset 遵循
[docs/i2c_axi_mpu9250.md](i2c_axi_mpu9250.md)。

| Offset | Name | Access | Reset | Description |
|---:|---|---|---:|---|
| `0x00` | `CTRL` | RW | `0x00000000` | bit0 `enable`，bit1 `oneshot_start` pulse，bit2 `auto_mode`，bit3 `clear_done` pulse，bit4 `clear_error` pulse，bit5 `soft_reset` pulse，bit8 `cfg_write_start` pulse |
| `0x04` | `STATUS` | R | `0x000000C0` after pullups | bit0 `busy`，bit1 `done`，bit2 `data_valid`，bit3 `ack_error`，bit4 `timeout`，bit5 `cfg_done`，bit6 `scl_in`，bit7 `sda_in` |
| `0x08` | `DEV_ADDR` | RW | `0x50` | JY901 7-bit I2C address。不要写 `0xA1`；那是 read address byte。 |
| `0x0C` | `START_REG` | RW | `0x34` | burst read 的第一个 JY901 register。 |
| `0x10` | `WORD_COUNT` | RW | `13` | 读取的 16-bit word 数量。硬件钳制到最多 13 word。 |
| `0x14` | `SAMPLE_PERIOD` | RW | `10_000_000` | Auto sampling period，单位为 AXI clock cycle。100 MHz 时默认 100 ms。 |
| `0x18` | `I2C_CLKDIV` | RW | `250` | quarter-period divider。100 MHz 时 `250` 得到 100 kHz SCL。 |
| `0x1C` | `ERROR_CODE` | R | `0x00` | `0x01` address-write NACK，`0x02` register NACK，`0x03` address-read NACK，`0x04/0x05` config data NACK，`0x10` timeout。 |
| `0x20` | `CFG_REG_ADDR` | RW | `0x00` | write-word transaction 的 JY901 config register address。 |
| `0x24` | `CFG_DATA` | RW | `0x0000` | JY901 config 16-bit data，低字节先发送。 |
| `0x28` | `VERSION` | R | `0x4A593101` | JY901 IP version marker。 |
| `0x40` | `AX_RAW` | R | `0x0000` | Acceleration X raw signed int16。 |
| `0x44` | `AY_RAW` | R | `0x0000` | Acceleration Y raw signed int16。 |
| `0x48` | `AZ_RAW` | R | `0x0000` | Acceleration Z raw signed int16。 |
| `0x4C` | `GX_RAW` | R | `0x0000` | Gyroscope X raw signed int16。 |
| `0x50` | `GY_RAW` | R | `0x0000` | Gyroscope Y raw signed int16。 |
| `0x54` | `GZ_RAW` | R | `0x0000` | Gyroscope Z raw signed int16。 |
| `0x58` | `HX_RAW` | R | `0x0000` | Magnetic X raw signed int16。 |
| `0x5C` | `HY_RAW` | R | `0x0000` | Magnetic Y raw signed int16。 |
| `0x60` | `HZ_RAW` | R | `0x0000` | Magnetic Z raw signed int16。 |
| `0x64` | `ROLL_RAW` | R | `0x0000` | Roll raw signed int16。 |
| `0x68` | `PITCH_RAW` | R | `0x0000` | Pitch raw signed int16。 |
| `0x6C` | `YAW_RAW` | R | `0x0000` | Yaw raw signed int16。 |
| `0x70` | `TEMP_RAW` | R | `0x0000` | Temperature raw signed int16。 |
| `0x74` | `SAMPLE_CNT` | R | `0x00000000` | 成功 burst-read sample count。 |

当前硬件范围：

- 支持 single-shot read、auto-period read 和一次 16-bit config write transaction；
- 不实现 multi-master arbitration、clock stretching、interrupt、DMA、FIFO buffering 或 10-bit addressing；
- SCL/SDA 为 open-drain 风格输出，需要外部 pullup 到 3.3 V。

## 已迁移交接 IP 寄存器映射

以下寄存器映射来自队友交接包，源码已迁入 `rtl/`。各 IP 的验证状态在
[test_plan.md](test_plan.md) 中单独跟踪；不要只凭该寄存器表推断系统级验收通过。

### dht11_axi_v1_0

| Offset | Name | Access | Description |
|---:|---|---|---|
| `0x00` | `DHT11_DATA` | R | `[31:24] humidity_int`，`[23:16] humidity_dec`，`[15:8] temperature_int`，`[7:0] temperature_dec`。 |
| `0x04` | `STATUS_DEBUG` | R | Debug/status bit，包括 current state、bit count、raw/synchronized data line、output enable/value 和 receive phase。 |
| `0x08` | `COUNT_1US_DBG` | R | 当前微秒 counter debug value。 |
| `0x0C` | `RESERVED` | RW | 预留可写寄存器，当前未使用。 |

### axi_humidifier_v1_0

| Offset | Name | Access | Description |
|---:|---|---|---|
| `0x00` | `CTRL` | RW/W1P | bit0 `enable`，bit1 `manual_mode`，bit2 `manual_on`，bit3 `use_sw_humidity`，bit4 `clear_counter` write-one-pulse。 |
| `0x04` | `SW_HUM` | RW | 软件湿度输入，0 到 100 percent。 |
| `0x08` | `THRESH` | RW | `[7:0] threshold_low`，`[15:8] hysteresis`，`[31:16] dry_alert_s`。 |
| `0x0C` | `TIMING` | RW | `[15:0] min_on_s`，`[31:16] min_off_s`。 |
| `0x10` | `STATUS` | R | `[7:0] humidity`，bit8 `humidifier_on`，`[10:9] dry_level`，`[15:12] humidifier_leds`，`[31:16] debug/status`。 |
| `0x14` | `DRY_SEC` | R | 累计 humidifier-on 秒数。 |
| `0x18` | `VERSION` | R | `0x20260601`。 |

交接默认值：`CTRL=0x00000009`，`SW_HUM=50`，
`THRESH=0x000A052D`，`TIMING=0x00000000`。

### tft_lcd_spi_axi_v1_0

| Offset | Name | Access | Reset | Description |
|---:|---|---|---:|---|
| `0x00` | `CTRL` | RW/pulse | `0x0000000C` | bit0 `start`，bit1 `dc`，bit2 `lcd_res`，bit3 `lcd_blk`，bit4 `clear_done`。 |
| `0x04` | `DATA` | RW | `0x00000000` | `[7:0]` 中的下一个 SPI byte。 |
| `0x08` | `CLKDIV` | RW | `0x00000019` | SPI half-period divider；`SCL = S_AXI_ACLK / (2 * CLKDIV)`。 |
| `0x0C` | `STATUS` | R | dynamic | bit0 `busy`，bit1 `done_latched`，bit2 `done_pulse`，bit3 `lcd_res`，bit4 `lcd_blk`，bit5 `dc`。 |

软件在 pulse `start` 时必须保留 `CTRL[3:1]`；否则 reset 或 backlight 可能被意外拉低。

### axi_uart_spo2_v1_0

| Offset | Name | Access | Description |
|---:|---|---|---|
| `0x00` | `CTRL` | RW/W1P | bit0 `enable`，bit1 `clear`，bit2 `irq_enable`，bit4 `frame_7byte_mode`。 |
| `0x04` | `TXDATA` | W | `[7:0]` TX byte，写 bit8 发送一个 byte。 |
| `0x08` | `STATUS` | R | bit0 frame seen，bit1 frame error，bit2 CRC OK，bit3 sensor off，bit4 sensor error，bit5 searching，bit6 search timeout，`[10:7] frame_len`。 |
| `0x0C` | `MEASURE` | R | `[7:0] BPM`，`[15:8] SpO2`。 |
| `0x10` | `WAVE` | R | `[7:0] pleth`，`[15:8] bar graph`，`[23:16] perfusion index`。 |
| `0x14` | `FLAGS` | R | `[31:16] frame_counter`、CRC fields、pulse/mode flags。 |
| `0x18` | `RAW0` | R | Raw bytes 0 到 3。 |
| `0x1C` | `RAW1` | R | Raw bytes 4 到 6。 |

该 IP 默认使用 5-byte frame mode。只有确认物理传感器输出 7-byte frame format 后，才使用 `CTRL[4]`。

### gree_ir_axi_v1_0

从 `handoff/gree_ir_txrx_hardware_package/` 迁移的 TX-only AXI-Lite Gree YB0F2 IR AC transmitter。
首个集成范围只暴露七个已验证 preset 命令，不包含交接包 RX capture IP。

验证状态：`system_v0_2` 的 TX-only 集成硬件范围已关闭；module regression、IP packaging、
integrated BD/build export、PYNQ board smoke 和用户确认的实验室 AC 响应都记录在 [test_plan.md](test_plan.md)。

| Offset | Name | Access | Reset | Description |
|---:|---|---|---:|---|
| `0x00` | `CONTROL` | RW/pulse | `0x00000000` | bit0 `start` pulse，bit1 `soft_reset` pulse。core busy 时 `start` 会 latch `STATUS.error`。 |
| `0x04` | `STATUS` | R/W1C | dynamic | bit0 `busy`，bit1 `done`，bit2 `error`。写 `1` 到 bit1 或 bit2 清除对应 latched status。 |
| `0x08` | `CMD_LOW` | RW | `0x00080016` | compatibility command shadow 的低 32 bit。首版中不是 raw transmit path。 |
| `0x0C` | `CMD_HIGH` | RW | `0x090040A4` | compatibility command shadow 的高 32 bit。首版中不是 raw transmit path。 |
| `0x10` | `PRESET` | RW | `0x00000001` | 选择 67-bit command ROM preset。有效 preset 为 1 到 7。 |
| `0x14` | `DEBUG` | R | dynamic | `[3:0] core state`，`[17:8] debug bit/sample index`。 |

首版支持的 preset：

| Preset | Command | 67-bit command |
|---:|---|---|
| 1 | `power_on` | `0x1090040A400080016` |
| 2 | `power_off` | `0x8050040A40008001C` |
| 3 | `temp_24` | `0x9010040A400080016` |
| 4 | `temp_25` | `0x9090040A40008000E` |
| 5 | `temp_26` | `0x9050040A40008001E` |
| 6 | `temp_27` | `0x90D0040A400080000` |
| 7 | `temp_28` | `0x9030040A400080010` |

`system_v0_2.hwh` 中已确认的集成 base address 为 `0x4000_5000`，
范围 4K（`0x4000_5000..0x4000_5FFF`）。
