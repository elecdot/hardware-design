# tb_tft_lcd_spi_axi

Behavioral simulation material for the TFT LCD SPI AXI IP.

## Files

| File | Purpose |
|---|---|
| [tb_spi_lcd_master.v](tb_spi_lcd_master.v) | SPI byte transmitter testbench. |
| [tb_tft_lcd_spi_axi.v](tb_tft_lcd_spi_axi.v) | AXI wrapper testbench. |

Expected PASS markers:

```text
tb_spi_lcd_master PASS
tb_tft_lcd_spi_axi PASS
```

The handoff package noted that local simulator tools were unavailable on the
packaging machine. Re-run before claiming a simulation pass in this repo.

## Run

From this directory:

```powershell
iverilog -g2012 -o build/tb_spi_lcd_master.vvp tb_spi_lcd_master.v ../../rtl/tft_lcd_spi_axi/spi_lcd_master.v
vvp build/tb_spi_lcd_master.vvp
iverilog -g2012 -o build/tb_tft_lcd_spi_axi.vvp tb_tft_lcd_spi_axi.v ../../rtl/tft_lcd_spi_axi/tft_lcd_spi_axi_v1_0.v ../../rtl/tft_lcd_spi_axi/tft_lcd_spi_axi_v1_0_S00_AXI.v ../../rtl/tft_lcd_spi_axi/spi_lcd_master.v
vvp build/tb_tft_lcd_spi_axi.vvp
```
