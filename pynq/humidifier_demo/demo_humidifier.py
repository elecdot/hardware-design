"""Simple PYNQ demo for the AXI humidifier LED controller.

Usage on PYNQ:
    python3 pynq/demo_humidifier.py your_overlay.bit axi_humidifier_0
"""

import sys
import time

from humidifier_driver import AxiHumidifier


def main():
    bitfile = sys.argv[1] if len(sys.argv) > 1 else "your_overlay.bit"
    ip_name = sys.argv[2] if len(sys.argv) > 2 else "axi_humidifier_0"

    humidifier = AxiHumidifier.from_bitfile(bitfile, ip_name=ip_name)
    humidifier.automatic(use_sw_humidity=True)
    humidifier.set_thresholds(threshold_low=45, hysteresis=5, dry_alert_s=10)
    humidifier.set_timing(min_on_s=0, min_off_s=0)
    humidifier.clear_counter()

    for humidity in [60, 50, 44, 35, 42, 55]:
        humidifier.set_software_humidity(humidity)
        time.sleep(0.2)
        status = humidifier.status()
        print(
            "humidity={humidity:3d}%  on={on}  leds=0b{leds:04b}  dry_level={level}".format(
                humidity=status["humidity"],
                on=int(status["humidifier_on"]),
                leds=status["leds"],
                level=status["dry_level"],
            )
        )


if __name__ == "__main__":
    main()
