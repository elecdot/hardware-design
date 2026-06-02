## clock: PYNQ-Z1 PL clock
##set_property PACKAGE_PIN H16 [get_ports clk_0]
##set_property IOSTANDARD LVCMOS33 [get_ports clk_0]
##create_clock -name sys_clk -period 8.000 [get_ports clk_0]

## DHT11 data pin: Arduino IO11 = R17
set_property PACKAGE_PIN R17 [get_ports dht11_0]
set_property IOSTANDARD LVCMOS33 [get_ports dht11_0]
set_property PULLUP true [get_ports dht11_0]