## Example constraints for PYNQ-Z1 on-board LEDs.
## Use only when you make humidifier_leds[3:0] external ports in your own demo project.
## If the final group project already has pin constraints, let the integration teammate merge these carefully.

set_property -dict { PACKAGE_PIN R14 IOSTANDARD LVCMOS33 } [get_ports { humidifier_leds[0] }];
set_property -dict { PACKAGE_PIN P14 IOSTANDARD LVCMOS33 } [get_ports { humidifier_leds[1] }];
set_property -dict { PACKAGE_PIN N16 IOSTANDARD LVCMOS33 } [get_ports { humidifier_leds[2] }];
set_property -dict { PACKAGE_PIN M14 IOSTANDARD LVCMOS33 } [get_ports { humidifier_leds[3] }];
