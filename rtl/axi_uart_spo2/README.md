# axi_uart_spo2

AXI-Lite UART SpO2/heart-rate receiver migrated from the teammate handoff
package.

## Files

| File | Purpose |
|---|---|
| [axi_uart_spo2_v1_0.v](axi_uart_spo2_v1_0.v) | AXI IP top wrapper. |
| [axi_uart_spo2_v1_0_S00_AXI.v](axi_uart_spo2_v1_0_S00_AXI.v) | AXI4-Lite register wrapper. |
| [uart_rx.v](uart_rx.v) | UART receive core. |
| [uart_tx.v](uart_tx.v) | UART transmit core. |
| [spo2_frame_parser.v](spo2_frame_parser.v) | 5-byte/7-byte SpO2 frame parser. |

## Notes

- Source was copied without RTL behavior changes.
- Integrated target pins are PMODB `uart_txd=W14` and `uart_rxd=Y14`.
- UART defaults to 9600 baud from a 100 MHz clock.
- A module-level regression test still needs to be added.

