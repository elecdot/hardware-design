# rtl

Synthesizable RTL for custom PL-side protocol IP lives here.

## Index

| Path | Purpose |
|---|---|
| `i2c_mpu9250/` | AXI-Lite I2C master IP for JY901/MPU9250 motion data sampling. |

Add one subdirectory per custom IP. Keep protocol cores, AXI wrappers, and shared helper logic separated when practical.
