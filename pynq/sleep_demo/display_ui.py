"""Small ST7789 dashboard helpers for the integrated sleep demo.

The functions operate on `tft_lcd_demo.tft_lcd.TftLcd` and update only fixed
numeric/status regions after the first full draw.
"""


def color565(red, green, blue):
    red = max(0, min(255, int(red)))
    green = max(0, min(255, int(green)))
    blue = max(0, min(255, int(blue)))
    return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)


BLACK = 0x0000
WHITE = 0xFFFF
BG_DARK = color565(5, 8, 15)
CARD_BG = color565(18, 22, 30)
TITLE_BG = color565(12, 18, 35)
BORDER = color565(70, 80, 100)
TEXT_MAIN = color565(245, 248, 255)
TEXT_SUB = color565(160, 170, 180)
ACCENT_BLUE = color565(80, 180, 255)
ACCENT_RED = color565(255, 80, 80)
ACCENT_GOLD = color565(255, 190, 70)
ACCENT_GREEN = color565(80, 255, 160)
CYAN = color565(80, 220, 235)


FONT5X7 = {
    " ": [0x00, 0x00, 0x00, 0x00, 0x00],
    "!": [0x00, 0x00, 0x5F, 0x00, 0x00],
    "%": [0x63, 0x13, 0x08, 0x64, 0x63],
    ".": [0x00, 0x60, 0x60, 0x00, 0x00],
    ":": [0x00, 0x36, 0x36, 0x00, 0x00],
    "-": [0x08, 0x08, 0x08, 0x08, 0x08],
    "/": [0x20, 0x10, 0x08, 0x04, 0x02],
    "0": [0x3E, 0x51, 0x49, 0x45, 0x3E],
    "1": [0x00, 0x42, 0x7F, 0x40, 0x00],
    "2": [0x42, 0x61, 0x51, 0x49, 0x46],
    "3": [0x21, 0x41, 0x45, 0x4B, 0x31],
    "4": [0x18, 0x14, 0x12, 0x7F, 0x10],
    "5": [0x27, 0x45, 0x45, 0x45, 0x39],
    "6": [0x3C, 0x4A, 0x49, 0x49, 0x30],
    "7": [0x01, 0x71, 0x09, 0x05, 0x03],
    "8": [0x36, 0x49, 0x49, 0x49, 0x36],
    "9": [0x06, 0x49, 0x49, 0x29, 0x1E],
    "A": [0x7E, 0x11, 0x11, 0x11, 0x7E],
    "B": [0x7F, 0x49, 0x49, 0x49, 0x36],
    "C": [0x3E, 0x41, 0x41, 0x41, 0x22],
    "D": [0x7F, 0x41, 0x41, 0x22, 0x1C],
    "E": [0x7F, 0x49, 0x49, 0x49, 0x41],
    "F": [0x7F, 0x09, 0x09, 0x09, 0x01],
    "G": [0x3E, 0x41, 0x49, 0x49, 0x7A],
    "H": [0x7F, 0x08, 0x08, 0x08, 0x7F],
    "I": [0x00, 0x41, 0x7F, 0x41, 0x00],
    "J": [0x20, 0x40, 0x41, 0x3F, 0x01],
    "K": [0x7F, 0x08, 0x14, 0x22, 0x41],
    "L": [0x7F, 0x40, 0x40, 0x40, 0x40],
    "M": [0x7F, 0x02, 0x0C, 0x02, 0x7F],
    "N": [0x7F, 0x04, 0x08, 0x10, 0x7F],
    "O": [0x3E, 0x41, 0x41, 0x41, 0x3E],
    "P": [0x7F, 0x09, 0x09, 0x09, 0x06],
    "Q": [0x3E, 0x41, 0x51, 0x21, 0x5E],
    "R": [0x7F, 0x09, 0x19, 0x29, 0x46],
    "S": [0x46, 0x49, 0x49, 0x49, 0x31],
    "T": [0x01, 0x01, 0x7F, 0x01, 0x01],
    "U": [0x3F, 0x40, 0x40, 0x40, 0x3F],
    "V": [0x1F, 0x20, 0x40, 0x20, 0x1F],
    "W": [0x7F, 0x20, 0x18, 0x20, 0x7F],
    "X": [0x63, 0x14, 0x08, 0x14, 0x63],
    "Y": [0x07, 0x08, 0x70, 0x08, 0x07],
    "Z": [0x61, 0x51, 0x49, 0x45, 0x43],
}


VALUE_AREAS = {
    "heart_rate_bpm": (17, 95, 72, 24, 3),
    "spo2_percent": (132, 95, 72, 24, 3),
    "turnover_count": (17, 175, 72, 24, 3),
    "temperature_c": (132, 175, 88, 24, 3),
    "humidity_percent": (18, 223, 90, 8, 1),
    "status_line": (112, 223, 110, 8, 1),
}


def _text_or_na(value, fmt=None):
    if value is None:
        return "NA"
    if fmt is not None:
        return fmt.format(value)
    return str(value)


def _pixel_bytes(colors):
    data = bytearray()
    for color in colors:
        color &= 0xFFFF
        data.append((color >> 8) & 0xFF)
        data.append(color & 0xFF)
    return bytes(data)


def draw_char(lcd, x, y, ch, color=WHITE, bg=BLACK, scale=1):
    ch = str(ch).upper()
    bitmap = FONT5X7.get(ch, FONT5X7[" "])
    scale = max(1, int(scale))
    width = 6 * scale
    height = 8 * scale
    pixels = []

    for yy in range(height):
        src_row = yy // scale
        for xx in range(width):
            src_col = xx // scale
            if src_col >= 5 or src_row >= 7:
                pixels.append(bg)
            elif (bitmap[src_col] >> src_row) & 0x01:
                pixels.append(color)
            else:
                pixels.append(bg)

    lcd.set_window(x, y, x + width - 1, y + height - 1)
    lcd.write_pixels_rgb565(_pixel_bytes(pixels))
    return width


def draw_text(lcd, x, y, text, color=WHITE, bg=BLACK, scale=1):
    x_cur = int(x)
    y_cur = int(y)
    x_start = x_cur
    for ch in str(text):
        if ch == "\n":
            y_cur += 9 * scale
            x_cur = x_start
        else:
            x_cur += draw_char(lcd, x_cur, y_cur, ch, color=color, bg=bg, scale=scale)
    return x_cur


def draw_center_text(lcd, y, text, color=WHITE, bg=BLACK, scale=1):
    text = str(text)
    text_w = len(text) * 6 * scale
    x = max(0, (lcd.WIDTH - text_w) // 2)
    return draw_text(lcd, x, y, text, color=color, bg=bg, scale=scale)


def draw_hline(lcd, x, y, width, color):
    lcd.fill_rect(x, y, width, 1, color)


def draw_vline(lcd, x, y, height, color):
    lcd.fill_rect(x, y, 1, height, color)


def draw_rect(lcd, x, y, width, height, color):
    draw_hline(lcd, x, y, width, color)
    draw_hline(lcd, x, y + height - 1, width, color)
    draw_vline(lcd, x, y, height, color)
    draw_vline(lcd, x + width - 1, y, height, color)


def draw_card(lcd, x, y, width, height, title, value, unit, accent):
    lcd.fill_rect(x, y, width, height, CARD_BG)
    draw_rect(lcd, x, y, width, height, BORDER)
    lcd.fill_rect(x, y, width, 4, accent)
    draw_text(lcd, x + 7, y + 11, title, color=TEXT_SUB, bg=CARD_BG, scale=2)
    draw_text(lcd, x + 7, y + 35, value, color=TEXT_MAIN, bg=CARD_BG, scale=3)
    draw_text(lcd, x + 73, y + 43, unit, color=accent, bg=CARD_BG, scale=1)


def format_dashboard_values(sample):
    return {
        "heart_rate_bpm": _text_or_na(sample.get("heart_rate_bpm")),
        "spo2_percent": _text_or_na(sample.get("spo2_percent")),
        "turnover_count": str(int(sample.get("turnover_count") or 0)),
        "temperature_c": _text_or_na(sample.get("temperature_c"), "{:.1f}"),
        "humidity_percent": "HUM {0}%".format(
            _text_or_na(sample.get("humidity_percent"))
        ),
        "status_line": "JY {0} H {1}".format(
            sample.get("jy901_status") or "NA",
            "ON" if sample.get("humidifier_on") else "OFF",
        ),
    }


def draw_dashboard(lcd, sample):
    values = format_dashboard_values(sample)

    lcd.fill(BG_DARK)
    lcd.fill_rect(0, 0, 240, 34, TITLE_BG)
    draw_center_text(lcd, 9, "SLEEP MONITOR", color=ACCENT_BLUE, bg=TITLE_BG, scale=2)
    draw_text(lcd, 12, 42, "PYNQ-Z1  ST7789  SPI", color=TEXT_SUB, bg=BG_DARK, scale=1)

    draw_card(lcd, 10, 60, 105, 70, "HR", values["heart_rate_bpm"], "BPM", ACCENT_RED)
    draw_card(lcd, 125, 60, 105, 70, "SPO2", values["spo2_percent"], "%", ACCENT_BLUE)
    draw_card(lcd, 10, 140, 105, 70, "TURN", values["turnover_count"], "TIM", ACCENT_GOLD)
    draw_card(lcd, 125, 140, 105, 70, "TEMP", values["temperature_c"], "C", ACCENT_GREEN)

    lcd.fill_rect(10, 218, 220, 18, CARD_BG)
    draw_rect(lcd, 10, 218, 220, 18, BORDER)
    draw_text(lcd, 18, 223, values["humidity_percent"], color=CYAN, bg=CARD_BG, scale=1)
    draw_text(lcd, 112, 223, values["status_line"], color=TEXT_SUB, bg=CARD_BG, scale=1)
    return values


def update_dashboard(lcd, sample, previous_values):
    values = format_dashboard_values(sample)
    if previous_values is None:
        return draw_dashboard(lcd, sample)

    for key, value in values.items():
        if value == previous_values.get(key):
            continue
        x, y, width, height, scale = VALUE_AREAS[key]
        lcd.fill_rect(x, y, width, height, CARD_BG)
        color = CYAN if key == "humidity_percent" else TEXT_MAIN
        if key == "status_line":
            color = TEXT_SUB
        draw_text(lcd, x, y, value, color=color, bg=CARD_BG, scale=scale)

    return values
