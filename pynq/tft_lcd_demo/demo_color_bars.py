"""Simple PYNQ board demo for the TFT LCD handoff package."""

import time

from tft_lcd import TftLcd, color565, default_bitfile


def main() -> None:
    lcd = TftLcd.from_bitfile(default_bitfile(), clk_div=50)
    lcd.init_panel(rotation=0)

    colors = [
        TftLcd.RED,
        TftLcd.GREEN,
        TftLcd.BLUE,
        TftLcd.WHITE,
        TftLcd.BLACK,
        color565(255, 128, 0),
    ]

    while True:
        for value in colors:
            lcd.fill(value)
            time.sleep(0.5)


if __name__ == "__main__":
    main()
