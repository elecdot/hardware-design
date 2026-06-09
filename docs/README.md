# docs

Project design notes, hardware references, register maps, wiring notes, and test plans live here.

## Index

| Path | Purpose |
|---|---|
| [i2c_axi_mpu9250.md](i2c_axi_mpu9250.md) | Detailed design note for the JY901/MPU9250 I2C AXI IP. |
| [register_map.md](register_map.md) | Canonical AXI-Lite register map for implemented custom IP. |
| [wiring.md](wiring.md) | Physical wiring and voltage notes for external modules. |
| [test_plan.md](test_plan.md) | Simulation and board-level test checklist. |
| [handoff_and_integration.md](handoff_and_integration.md) | Handoff migration and Vivado/PYNQ integration plan for teammate modules. |
| [ir_ac_integration_plan.md](ir_ac_integration_plan.md) | TX-only Gree IR AC integration plan, protocol decisions, and execution phases. |
| [software_integration_plan.md](software_integration_plan.md) | Deferred PC/PYNQ software integration plan after IR hardware demo validation. |
| [ip_packaging_manual.md](ip_packaging_manual.md) | Phase 3 executable Vivado IP packaging checklist for migrated RTL modules. |
| [protocol.md](protocol.md) | PYNQ-to-PC newline-delimited JSON protocol. |
| [demo_plan.md](demo_plan.md) | Course demo or presentation flow notes. |
| [work_notes.md](work_notes.md) | Human-oriented work notes, safety reminders, and common failure modes. |
| [JY901/](JY901/) | Vendor documentation, tools, and example code for the JY901 module. |

Keep implementation details in module-specific docs when they grow large, and update [register_map.md](register_map.md) whenever RTL-visible registers change.
