## PMODA index 3 as SCL, index 2 as SDA
set_property -dict { PACKAGE_PIN Y17 IOSTANDARD LVCMOS33 } [get_ports i2c_scl]
set_property -dict { PACKAGE_PIN Y16 IOSTANDARD LVCMOS33 } [get_ports i2c_sda]

## Optional weak internal pullups; real external 4.7k pullups are still recommended
set_property PULLUP true [get_ports i2c_scl]
set_property PULLUP true [get_ports i2c_sda]