# dht11_demo

PYNQ-side DHT11 demo files migrated from the teammate handoff package.

## Files

| File | Purpose |
|---|---|
| [dht11_driver.py](dht11_driver.py) | Direct MMIO DHT11 driver. |
| [dht11_test_read.py](dht11_test_read.py) | Simple read test script. |

The current driver defaults to the single-module handoff address
`0x43C00000`. Integrated overlay code should bind the IP through `.hwh` /
`Overlay.ip_dict` or pass the Vivado-assigned base address explicitly.

