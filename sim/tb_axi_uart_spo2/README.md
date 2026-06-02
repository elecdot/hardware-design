# tb_axi_uart_spo2

Simulation material for the UART SpO2 IP.

The handoff package did not include a focused module-level regression test for
the UART SpO2 IP. This directory starts with a parser-level smoke test before
full UART waveform and AXI wrapper coverage are added.

## Files

| File | Purpose |
|---|---|
| [tb_spo2_frame_parser.v](tb_spo2_frame_parser.v) | 5-byte and 7-byte frame parser smoke test with explicit PASS/ERROR output. |

## Run

From this directory:

```powershell
iverilog -g2012 -o build/tb_spo2_frame_parser.vvp tb_spo2_frame_parser.v ../../rtl/axi_uart_spo2/spo2_frame_parser.v
vvp build/tb_spo2_frame_parser.vvp
```

Expected PASS marker:

```text
tb_spo2_frame_parser PASS
```

Recommended first checks:

- UART RX receives bytes at 9600 baud timing.
- `STATUS`, `MEASURE`, `WAVE`, `FLAGS`, `RAW0`, and `RAW1` update as documented.
