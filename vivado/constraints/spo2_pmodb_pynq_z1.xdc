## PYNQ-Z1 PMODB pin plan for the integrated UART SpO2 path.
## Course teaching guide mapping:
##   PMODB_1 / JB1_P -> W14
##   PMODB_2 / JB1_N -> Y14
##
## Module RX(IN) connects to FPGA uart_txd.
## Module TX(OUT) connects to FPGA uart_rxd.

set_property -dict { PACKAGE_PIN W14 IOSTANDARD LVCMOS33 } [get_ports uart_txd]
set_property -dict { PACKAGE_PIN Y14 IOSTANDARD LVCMOS33 } [get_ports uart_rxd]
set_property PULLUP true [get_ports uart_rxd]

