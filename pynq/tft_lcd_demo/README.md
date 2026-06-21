# tft_lcd_demo

从队友交接包迁移的 PYNQ 侧 TFT LCD demo 文件。

## 文件

| 文件 | 用途 |
|---|---|
| [tft_lcd.py](tft_lcd.py) | 可复用的 ST7789 AXI SPI 显示驱动。 |
| [demo_color_bars.py](demo_color_bars.py) | 简单色条 demo。 |
| [jupyter_tft_display_working.py](jupyter_tft_display_working.py) | 交接包中已板测的显示 UI/参考脚本。 |

首个集成显示目标：

- 保持 `CLKDIV=50`；
- 先绘制完整 `SLEEP MONITOR` dashboard；
- 循环中只更新数值/状态区域；
- 从 1 Hz 开始，板级 smoke test 后再尝试提升到 2 Hz。
