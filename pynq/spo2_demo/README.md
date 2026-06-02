# spo2_demo

PYNQ-side UART SpO2 helper migrated from the teammate handoff package.

## Files

| File | Purpose |
|---|---|
| [spo2_mmio.py](spo2_mmio.py) | MMIO helper for the UART SpO2 IP. |

## Notes

- `Spo2Sample` is implemented as a plain Python class so the helper stays
  compatible with the recorded PYNQ Python 3.6 environment.
- Integrated overlay target pins are PMODB `uart_txd=W14` and `uart_rxd=Y14`.
