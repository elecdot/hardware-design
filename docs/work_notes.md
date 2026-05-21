## Safety and Hardware Handling

- Do not hot-plug sensor wires while the board is powered.
- Verify VCC, GND, and signal voltage before connecting modules.
- Treat PYNQ-Z1 Arduino/PMOD I/O as 3.3 V logic.
- Use level shifting or isolation when driving modules that require 5 V signaling.
- Be careful with actuators such as humidifiers, fans, IR LEDs, and speakers; do not drive loads directly from FPGA pins.
- Use current-limiting resistors and proper driver circuits where needed.

## Common Failure Modes

Check these first when debugging:

- Wrong board part: use `xc7z020clg400-1` for PYNQ-Z1.
- Missing or mismatched `.hwh` file for PYNQ overlay.
- AXI IP name changed in Vivado, but Python still uses the old name.
- Register offset mismatch between AXI wrapper and Python driver.
- Start bit expected as rising edge, but software holds it high.
- External input not synchronized before edge detection.
- Wrong clock frequency assumption in counters.
- Hardware debug reset held active; `jy901_hw_debug_top.resetn` is active-high
  release on SW0, so SW0 low keeps the sampler in reset.
- UART baud rate mismatch.
- I2C `ERROR_CODE=0x01` means address-write NACK. Confirm the debug top uses
  PMODA `Y17/Y16`, SCL/SDA idle high at 3.3 V, `core_tx_byte_dbg=0xA0`, and
  the JY901 actually responds to 7-bit address `0x50`.
- In the PYNQ demo, an all-zero JY901 payload immediately before
  `ERROR_CODE=0x01` should be treated as invalid data, not as a real turn or
  posture change. Check sensor power, pullups, jumper contact, and whether the
  module is resetting or losing I2C ACK during repeated oneshot reads.
- I2C SDA/SCL pull-up or tri-state mistake.
- DHT11 bidirectional line not released to high-Z at the correct time.
- SPI mode or display reset sequence mismatch.
- PYNQ-Z1 I/O voltage violation.
- Socket server not started before board-side client connects.
- Vivado DRC `NSTD-1`/`UCIO-1` on `USBIND_0_0_*` in the `axi_i2c_jy901`
  overlay means the PS7 USB0 control interface was accidentally made external.
  Do not assign random PL pins or downgrade DRC severity. This is likely caused
  by using Vivado's "Run Block Automation".

## PYNQ Runtime Constraints

Current board software model for the first JY901 demo:

- Jupyter kernel runs as root with `/opt/python3.6/bin/python3.6`.
- Jupyter kernel package path includes
  `/opt/python3.6/lib/python3.6/site-packages`, where `pynq` is installed.
- SSH CLI default `python3` is `/usr/bin/python3` version 3.4.3+ and does not
  match the Jupyter/PYNQ dependency environment.
- SSH CLI default `python` may report Python 2.7.10, but this is only the old
  Linux default interpreter and should not be used for the PYNQ demo.
- Kernel: `Linux pynq 4.6.0-xilinx ... armv7l`.

Correct SSH CLI invocation for the demo:

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 10
```

Keep PYNQ board-side demo code compatible with Python 3.6. Avoid Python 3.7+
syntax or APIs unless the board image is upgraded.

## Bring-up Notes

### 2026-05-19 JY901 I2C intermittent address NACK

During PL-only ILA bring-up, intermittent `ERROR_CODE=0x01` captures were traced
to a worn Dupont jumper with poor contact. After replacing/reseating the wire,
the same RTL, constraints, and `0x50` JY901 address produced valid ACK waveforms.

During later PS-side testing, the idle state was also observed continuously
capturing `scl` and `sda` as `0`; keep pullups, pin mapping, and IOBUF
tri-state behavior on the debug checklist.
