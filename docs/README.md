# docs

Project design notes, hardware references, register maps, wiring notes, and test plans live here.

## Index

| Path | Purpose |
|---|---|
| `i2c_axi_mpu9250.md` | Detailed design note for the JY901/MPU9250 I2C AXI IP. |
| `register_map.md` | Canonical AXI-Lite register map for implemented custom IP. |
| `wiring.md` | Physical wiring and voltage notes for external modules. |
| `test_plan.md` | Simulation and board-level test checklist. |
| `protocol.md` | PYNQ-to-PC payload protocol placeholder. |
| `demo_plan.md` | Course demo or presentation flow notes. |
| `work_notes.md` | Human-oriented work notes, safety reminders, and common failure modes. |
| `JY901/` | Vendor documentation, tools, and example code for the JY901 module. |

Keep implementation details in module-specific docs when they grow large, and update `register_map.md` whenever RTL-visible registers change.
