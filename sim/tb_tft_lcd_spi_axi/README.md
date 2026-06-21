# tb_tft_lcd_spi_axi

TFT LCD SPI AXI IP 的行为仿真材料。

## 文件

| 文件 | 用途 |
|---|---|
| [tb_spi_lcd_master.v](tb_spi_lcd_master.v) | SPI 字节发送器 testbench。 |
| [tb_tft_lcd_spi_axi.v](tb_tft_lcd_spi_axi.v) | AXI wrapper testbench。 |

预期 PASS 标记：

```text
tb_spi_lcd_master PASS
tb_tft_lcd_spi_axi PASS
```

交接包记录：打包机器上没有可用的本地仿真工具。在本仓库声称 simulation pass 前需要重新运行。

## 运行

在本目录下执行：

```powershell
iverilog -g2012 -o build/tb_spi_lcd_master.vvp tb_spi_lcd_master.v ../../rtl/tft_lcd_spi_axi/spi_lcd_master.v
vvp build/tb_spi_lcd_master.vvp
iverilog -g2012 -o build/tb_tft_lcd_spi_axi.vvp tb_tft_lcd_spi_axi.v ../../rtl/tft_lcd_spi_axi/tft_lcd_spi_axi_v1_0.v ../../rtl/tft_lcd_spi_axi/tft_lcd_spi_axi_v1_0_S00_AXI.v ../../rtl/tft_lcd_spi_axi/spi_lcd_master.v
vvp build/tb_tft_lcd_spi_axi.vvp
```
