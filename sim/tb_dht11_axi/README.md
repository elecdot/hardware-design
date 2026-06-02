# tb_dht11_axi

Behavioral simulation material for the DHT11 AXI IP.

## Files

| File | Purpose |
|---|---|
| [tb_dht11.v](tb_dht11.v) | Handoff DHT11 testbench. |
| [tb_dht11_onewire_smoke.v](tb_dht11_onewire_smoke.v) | Icarus-compatible smoke test with an `IOBUF` stub and explicit PASS/ERROR output. |

## Next Step

Run the smoke test before Vivado packaging. From this directory:

```powershell
iverilog -g2012 -o build/tb_dht11_onewire_smoke.vvp tb_dht11_onewire_smoke.v ../../rtl/dht11_axi/dht11_onewire.v
vvp build/tb_dht11_onewire_smoke.vvp
```

Expected PASS marker:

```text
tb_dht11_onewire_smoke PASS
```
