## -----------------------------------------------------------------------------
## pynq_tft_lcd_bd.xdc
## PYNQ-Z1 PMODA -> 1.3 inch ST7789 TFT LCD
##
## TFT GND  -> PMODA GND
## TFT VCC  -> PMODA 3V3
## TFT SCL  -> PMODA Pin 1 -> Y18
## TFT SDA  -> PMODA Pin 2 -> Y19
## TFT RES  -> PMODA Pin 3 -> Y16
## TFT DC   -> PMODA Pin 4 -> Y17
## TFT BLK  -> PMODA Pin 7 -> U18
##
## 注意：
## 1. 这里不需要约束 sys_clk，因为正式工程的时钟来自 Zynq PS 的 FCLK_CLK0。
## 2. 外部端口名必须正好叫 lcd_scl/lcd_sda/lcd_res/lcd_dc/lcd_blk。
## -----------------------------------------------------------------------------

set_property -dict { PACKAGE_PIN Y18 IOSTANDARD LVCMOS33 } [get_ports { lcd_scl }]
set_property -dict { PACKAGE_PIN Y19 IOSTANDARD LVCMOS33 } [get_ports { lcd_sda }]
set_property -dict { PACKAGE_PIN Y16 IOSTANDARD LVCMOS33 } [get_ports { lcd_res }]
set_property -dict { PACKAGE_PIN Y17 IOSTANDARD LVCMOS33 } [get_ports { lcd_dc }]
set_property -dict { PACKAGE_PIN U18 IOSTANDARD LVCMOS33 } [get_ports { lcd_blk }]

set_property SLEW SLOW [get_ports { lcd_scl lcd_sda lcd_res lcd_dc lcd_blk }]
set_property DRIVE 8 [get_ports { lcd_scl lcd_sda lcd_res lcd_dc lcd_blk }]