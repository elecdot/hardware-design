## 125 MHz PL clock on PYNQ-Z1
set_property -dict {PACKAGE_PIN H16 IOSTANDARD LVCMOS33} [get_ports clk]
create_clock -period 8.000 -name clk_125mhz [get_ports clk]

## Reset: connect to SW0, switch up = 1, switch down = 0
set_property -dict {PACKAGE_PIN M20 IOSTANDARD LVCMOS33} [get_ports resetn]

## LEDs
set_property -dict {PACKAGE_PIN R14 IOSTANDARD LVCMOS33} [get_ports {led[0]}]
set_property -dict {PACKAGE_PIN P14 IOSTANDARD LVCMOS33} [get_ports {led[1]}]
set_property -dict {PACKAGE_PIN N16 IOSTANDARD LVCMOS33} [get_ports {led[2]}]
set_property -dict {PACKAGE_PIN M14 IOSTANDARD LVCMOS33} [get_ports {led[3]}]

## PMODA for JY901 I2C
set_property -dict {PACKAGE_PIN Y17 IOSTANDARD LVCMOS33} [get_ports i2c_scl]
set_property -dict {PACKAGE_PIN Y16 IOSTANDARD LVCMOS33} [get_ports i2c_sda]

## Optional internal weak pullups; do not rely on these as the only pullups
set_property PULLTYPE PULLUP [get_ports i2c_scl]
set_property PULLTYPE PULLUP [get_ports i2c_sda]

