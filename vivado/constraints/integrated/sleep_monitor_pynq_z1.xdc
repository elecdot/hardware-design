## Integrated PYNQ-Z1 pin allocation for the sleep monitor overlay.
## Apply this only to the integrated overlay top whose external port names match
## these signals. Do not also apply conflicting single-module XDC files.

## TFT LCD on PMODA
set_property -dict { PACKAGE_PIN Y18 IOSTANDARD LVCMOS33 } [get_ports lcd_scl]
set_property -dict { PACKAGE_PIN Y19 IOSTANDARD LVCMOS33 } [get_ports lcd_sda]
set_property -dict { PACKAGE_PIN Y16 IOSTANDARD LVCMOS33 } [get_ports lcd_res]
set_property -dict { PACKAGE_PIN Y17 IOSTANDARD LVCMOS33 } [get_ports lcd_dc]
set_property -dict { PACKAGE_PIN U18 IOSTANDARD LVCMOS33 } [get_ports lcd_blk]
set_property SLEW SLOW [get_ports { lcd_scl lcd_sda lcd_res lcd_dc lcd_blk }]
set_property DRIVE 8 [get_ports { lcd_scl lcd_sda lcd_res lcd_dc lcd_blk }]

## JY901 I2C on Arduino SCL/SDA
set_property -dict { PACKAGE_PIN P16 IOSTANDARD LVCMOS33 } [get_ports i2c_scl]
set_property -dict { PACKAGE_PIN P15 IOSTANDARD LVCMOS33 } [get_ports i2c_sda]
set_property PULLUP true [get_ports i2c_scl]
set_property PULLUP true [get_ports i2c_sda]

## UART SpO2 on PMODB pin 1/2
set_property -dict { PACKAGE_PIN W14 IOSTANDARD LVCMOS33 } [get_ports uart_txd]
set_property -dict { PACKAGE_PIN Y14 IOSTANDARD LVCMOS33 } [get_ports uart_rxd]
set_property PULLUP true [get_ports uart_rxd]

## DHT11 on Arduino IO11
set_property -dict { PACKAGE_PIN R17 IOSTANDARD LVCMOS33 } [get_ports dht11_0]
set_property PULLUP true [get_ports dht11_0]

## Board LEDs for humidifier indicator
set_property -dict { PACKAGE_PIN R14 IOSTANDARD LVCMOS33 } [get_ports { humidifier_leds[0] }]
set_property -dict { PACKAGE_PIN P14 IOSTANDARD LVCMOS33 } [get_ports { humidifier_leds[1] }]
set_property -dict { PACKAGE_PIN N16 IOSTANDARD LVCMOS33 } [get_ports { humidifier_leds[2] }]
set_property -dict { PACKAGE_PIN M14 IOSTANDARD LVCMOS33 } [get_ports { humidifier_leds[3] }]
