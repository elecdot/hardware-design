# dht11_axi

AXI-Lite DHT11 one-wire temperature/humidity IP migrated from the teammate
handoff package.

## Files

| File | Purpose |
|---|---|
| [dht11_axi_v1_0.v](dht11_axi_v1_0.v) | AXI IP top wrapper with external `dht11_0` one-wire port. |
| [dht11_axi_v1_0_S00_AXI.v](dht11_axi_v1_0_S00_AXI.v) | AXI4-Lite register wrapper. |
| [dht11_onewire.v](dht11_onewire.v) | DHT11 one-wire timing core. |

## Notes

- Source was copied without RTL behavior changes.
- The handoff package did not contain a complete standalone packaged
  `dht11_axi` IP directory, so this IP should be repackaged from tracked RTL.
- Integrated target pin is Arduino IO11 `R17`, documented in
  [../../docs/wiring.md](../../docs/wiring.md).
- Keep the bidirectional DATA line as a top-level inout and use a pullup.

