# tft_lcd_spi_axi

AXI-Lite byte-at-a-time SPI transmitter for a 240x240 ST7789 TFT LCD.

## Files

| File | Purpose |
|---|---|
| [tft_lcd_spi_axi_v1_0.v](tft_lcd_spi_axi_v1_0.v) | AXI IP top wrapper with LCD output pins. |
| [tft_lcd_spi_axi_v1_0_S00_AXI.v](tft_lcd_spi_axi_v1_0_S00_AXI.v) | AXI4-Lite register wrapper. |
| [spi_lcd_master.v](spi_lcd_master.v) | SPI byte transmitter. |
| [top_spi_lcd_test.v](top_spi_lcd_test.v) | Standalone PL test top from handoff. |

## Notes

- Source was copied without RTL behavior changes.
- Integrated target reserves PMODA for `lcd_scl/lcd_sda/lcd_res/lcd_dc/lcd_blk`.
- Current RTL has no `CS` or `MISO`; a display with `CS` needs that pin held
  active or a later RTL extension.

