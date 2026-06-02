# Demo Plan

Final demonstration flow for course defense.

## Priority

1. Integrated overlay and local PYNQ driver demo.
2. PC socket/Excel integration after the board-side demo is stable.
3. Standalone module demos only when needed to isolate or explain an integrated
   bring-up issue.

## Board-Side Demo

The primary live demo should run on one integrated overlay and one PYNQ driver
suite. It should show that the PS can read sensors, update the TFT LCD, and
control the humidifier indicator through AXI registers.

Minimum live sequence:

1. Load the integrated `.bit`/`.hwh`.
2. Bind each IP from `Overlay.ip_dict`.
3. Read or initialize JY901, DHT11, UART SpO2, TFT LCD, and humidifier drivers.
4. Initialize the TFT LCD once.
5. Enter a periodic loop that reads available sensor values, updates local
   turnover/humidifier logic, and refreshes the TFT LCD.

Initial board-side entry point:

```text
pynq/sleep_demo/integrated_demo.py
```

## TFT LCD Screen

Use the handoff's stable ST7789 layout as the first integrated display target:

- title: `SLEEP MONITOR`;
- main cards: heart rate, SpO2, turnover count, and temperature;
- bottom/status area: humidity, JY901/data-valid status, humidifier state, and
  PC sleep state when socket is active.

Stability rules:

- Keep `CLKDIV=50` for the first board test.
- Draw the full dashboard only during initialization or error recovery.
- In the periodic loop, update only changed numeric/status regions.
- Start with a 1 Hz UI refresh target.
- After smoke testing, try up to 2 Hz for faster-changing values if the display
  and sensor reads stay stable.
- Keep DHT11 updates on the sensor's slower valid cadence; show the latest
  cached humidity/temperature between DHT11 samples.

## Humidifier Demo Path

Use PS-side control first. PYNQ reads humidity through the DHT11 driver, then
writes humidifier AXI registers such as `SW_HUM`. The board LEDs show
humidifier state. Direct PL-to-PL DHT11-to-humidifier wiring is later optional
validation, not the first live path.

## PC Socket Extension

The PC socket/Excel path is part of the final system architecture, but it is a
later priority than local overlay/driver stability.

When included:

1. Start `pc_server.py` on the PC.
2. Confirm PC IP address and firewall rules.
3. PYNQ sends newline-delimited `sensor_data` JSON packets.
4. PC writes `sleep_monitor_data.xlsx`.
5. PC returns `sleep_result`.
6. PYNQ prints or displays the returned sleep state.
