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
- UART baud rate mismatch.
- I2C SDA/SCL pull-up or tri-state mistake.
- DHT11 bidirectional line not released to high-Z at the correct time.
- SPI mode or display reset sequence mismatch.
- PYNQ-Z1 I/O voltage violation.
- Socket server not started before board-side client connects.
