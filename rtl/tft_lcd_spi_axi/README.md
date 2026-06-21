# tft_lcd_spi_axi

用于 240x240 ST7789 TFT LCD 的 AXI-Lite 单字节 SPI 发送器。

## 文件

| 文件 | 用途 |
|---|---|
| [tft_lcd_spi_axi_v1_0.v](tft_lcd_spi_axi_v1_0.v) | 带 LCD 输出引脚的 AXI IP 顶层 wrapper。 |
| [tft_lcd_spi_axi_v1_0_S00_AXI.v](tft_lcd_spi_axi_v1_0_S00_AXI.v) | AXI4-Lite 寄存器 wrapper。 |
| [spi_lcd_master.v](spi_lcd_master.v) | SPI 字节发送器。 |
| [top_spi_lcd_test.v](top_spi_lcd_test.v) | 交接包中的独立 PL 测试顶层。 |

## 说明

- 源码迁移时未修改 RTL 行为。
- 集成目标为 `lcd_scl/lcd_sda/lcd_res/lcd_dc/lcd_blk` 预留 PMODA。
- 当前 RTL 没有 `CS` 或 `MISO`；带 `CS` 的显示屏需要将该引脚保持有效，或后续扩展 RTL。
