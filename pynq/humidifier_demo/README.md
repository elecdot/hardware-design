# humidifier_demo

PYNQ-side humidifier indicator demo files migrated from the teammate handoff
package.

## Files

| File | Purpose |
|---|---|
| [humidifier_driver.py](humidifier_driver.py) | MMIO driver for AXI humidifier registers. |
| [demo_humidifier.py](demo_humidifier.py) | Software humidity demo. |

First integrated path uses PS-side control: read DHT11 humidity in PYNQ, then
write humidifier registers such as `SW_HUM`.

