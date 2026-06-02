# tb_axi_uart_spo2

Placeholder for UART SpO2 simulation.

The handoff package did not include a focused module-level regression test for
the UART SpO2 IP. Add a byte-stream/frame-parser test before relying on this IP
inside the integrated runtime.

Recommended first checks:

- UART RX receives bytes at 9600 baud timing.
- 5-byte frame mode decodes BPM and SpO2 from known raw bytes.
- 7-byte frame mode remains selectable.
- `STATUS`, `MEASURE`, `WAVE`, `FLAGS`, `RAW0`, and `RAW1` update as documented.

