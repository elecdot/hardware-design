# tft_lcd_demo

PYNQ-side TFT LCD demo files migrated from the teammate handoff package.

## Files

| File | Purpose |
|---|---|
| [tft_lcd.py](tft_lcd.py) | Reusable ST7789 AXI SPI display driver. |
| [demo_color_bars.py](demo_color_bars.py) | Simple color-bar demo. |
| [jupyter_tft_display_working.py](jupyter_tft_display_working.py) | Handoff's board-tested display UI/reference script. |

First integrated display target:

- keep `CLKDIV=50`;
- draw the full `SLEEP MONITOR` dashboard once;
- update only numeric/status regions in the loop;
- start at 1 Hz and try up to 2 Hz after board smoke testing.

