# axi_humidifier

AXI-Lite humidifier indicator controller migrated from the teammate handoff
package. The module uses board LEDs to simulate humidifier state.

## Files

| File | Purpose |
|---|---|
| [axi_humidifier_v1_0.v](axi_humidifier_v1_0.v) | AXI IP top wrapper. |
| [axi_humidifier_v1_0_S00_AXI.v](axi_humidifier_v1_0_S00_AXI.v) | AXI4-Lite register wrapper. |
| [humidifier_core.v](humidifier_core.v) | Threshold, hysteresis, manual/software humidity, and LED control core. |

## Notes

- Source was copied without RTL behavior changes.
- First integrated demo path is PS-controlled: PYNQ reads DHT11 humidity and
  writes humidifier AXI registers such as `SW_HUM`.
- Direct PL DHT11-to-humidifier wiring remains optional later validation work.

