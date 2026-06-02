# ============================================================
# PYNQ-Z1 + AXI-SPI + ST7789 TFT
# 一键下载 bit、初始化屏幕、显示睡眠监测界面、支持局部更新数字
# ============================================================

from pynq import MMIO
import time
import os

try:
    from pynq import Bitstream
except Exception:
    from pynq.bitstream import Bitstream


# ============================================================
# 0. 用户只需要确认这里
# ============================================================

BIT_PATH = "/home/xilinx/jupyter_notebooks/tft_lcd/tft_lcd.bit"

# 如果你的 Vivado Address Editor 不是 0x43C00000，就只改这里
BASE_ADDR = 0x43C00000
ADDR_RANGE = 0x10000

# SPI 分频。50 更稳，数值越小越快。稳定后可尝试 25。
SPI_CLKDIV = 50


# ============================================================
# 1. 下载 bit，创建 MMIO
# ============================================================

print("bit exists:", os.path.exists(BIT_PATH), BIT_PATH)

bs = Bitstream(BIT_PATH)
bs.download()
print("Bitstream downloaded.")

mmio = MMIO(BASE_ADDR, ADDR_RANGE)
print("MMIO created at", hex(BASE_ADDR))


# ============================================================
# 2. AXI-Lite 寄存器定义
# ============================================================

REG_CTRL   = 0x00
REG_DATA   = 0x04
REG_CLKDIV = 0x08
REG_STATUS = 0x0C

CTRL_START      = 1 << 0
CTRL_DC         = 1 << 1
CTRL_RES        = 1 << 2
CTRL_BLK        = 1 << 3
CTRL_CLEAR_DONE = 1 << 4

STATUS_BUSY         = 1 << 0
STATUS_DONE_LATCHED = 1 << 1
STATUS_DONE_PULSE   = 1 << 2


def status_print():
    status = mmio.read(REG_STATUS)
    print("CTRL   =", hex(mmio.read(REG_CTRL)))
    print("DATA   =", hex(mmio.read(REG_DATA)))
    print("CLKDIV =", hex(mmio.read(REG_CLKDIV)))
    print("STATUS =", hex(status))
    print("busy         =", status & STATUS_BUSY)
    print("done_latched =", (status >> 1) & 1)
    print("done_pulse   =", (status >> 2) & 1)
    print("res_state    =", (status >> 3) & 1)
    print("blk_state    =", (status >> 4) & 1)
    print("dc_state     =", (status >> 5) & 1)


def ctrl_value(start=0, dc=0, res=1, blk=1, clear_done=0):
    v = 0
    if start:
        v |= CTRL_START
    if dc:
        v |= CTRL_DC
    if res:
        v |= CTRL_RES
    if blk:
        v |= CTRL_BLK
    if clear_done:
        v |= CTRL_CLEAR_DONE
    return v


def write_ctrl(start=0, dc=0, res=1, blk=1, clear_done=0):
    mmio.write(REG_CTRL, ctrl_value(start, dc, res, blk, clear_done))


def wait_not_busy(timeout=1.0):
    t0 = time.time()
    while mmio.read(REG_STATUS) & STATUS_BUSY:
        if time.time() - t0 > timeout:
            raise TimeoutError("wait_not_busy timeout, STATUS=" + hex(mmio.read(REG_STATUS)))


def wait_done_clear(timeout=1.0):
    t0 = time.time()
    while mmio.read(REG_STATUS) & STATUS_DONE_LATCHED:
        if time.time() - t0 > timeout:
            raise TimeoutError("done_latched did not clear, STATUS=" + hex(mmio.read(REG_STATUS)))


def wait_done_set(timeout=1.0):
    t0 = time.time()
    while (mmio.read(REG_STATUS) & STATUS_DONE_LATCHED) == 0:
        if time.time() - t0 > timeout:
            raise TimeoutError("done_latched did not set, STATUS=" + hex(mmio.read(REG_STATUS)))


def spi_write_byte(value, dc):
    """
    稳定发送 1 个 SPI 字节。
    dc=0：命令
    dc=1：数据
    """
    value &= 0xFF
    dc = 1 if dc else 0

    wait_not_busy()

    # 清除上一次 done
    write_ctrl(start=0, dc=dc, res=1, blk=1, clear_done=1)
    wait_done_clear()

    # 写待发送字节
    mmio.write(REG_DATA, value)

    # start 拉高一次
    write_ctrl(start=1, dc=dc, res=1, blk=1, clear_done=0)

    # 等待本字节真正发送完成
    wait_done_set()
    wait_not_busy()


mmio.write(REG_CLKDIV, SPI_CLKDIV)
write_ctrl(start=0, dc=0, res=1, blk=1, clear_done=1)

print("AXI-SPI ready.")
status_print()


# ============================================================
# 3. 颜色定义
# ============================================================

def rgb565(r, g, b):
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


BLACK   = 0x0000
WHITE   = 0xFFFF
RED     = 0xF800
GREEN   = 0x07E0
BLUE    = 0x001F
YELLOW  = 0xFFE0
CYAN    = 0x07FF
MAGENTA = 0xF81F
GRAY    = 0x8410

BG_DARK      = rgb565(5, 8, 15)
CARD_BG      = rgb565(18, 22, 30)
TITLE_BG     = rgb565(12, 18, 35)
BORDER       = rgb565(70, 80, 100)
TEXT_MAIN    = rgb565(245, 248, 255)
TEXT_SUB     = rgb565(160, 170, 180)
ACCENT_BLUE  = rgb565(80, 180, 255)
ACCENT_RED   = rgb565(255, 80, 80)
ACCENT_GOLD  = rgb565(255, 190, 70)
ACCENT_GREEN = rgb565(80, 255, 160)


# ============================================================
# 4. ST7789 TFT 驱动
# ============================================================

class ST7789_Robust:
    def __init__(self, width=240, height=240, x_offset=0, y_offset=0, clkdiv=50):
        self.width = width
        self.height = height
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.clkdiv = clkdiv

        mmio.write(REG_CLKDIV, int(clkdiv) & 0xFFFF)
        write_ctrl(start=0, dc=0, res=1, blk=1, clear_done=1)

    def cmd(self, value):
        spi_write_byte(value, dc=0)

    def data(self, value):
        spi_write_byte(value, dc=1)

    def data16(self, value):
        value &= 0xFFFF
        self.data((value >> 8) & 0xFF)
        self.data(value & 0xFF)

    def reset(self):
        write_ctrl(start=0, dc=0, res=1, blk=0, clear_done=1)
        time.sleep(0.05)

        write_ctrl(start=0, dc=0, res=0, blk=0, clear_done=1)
        time.sleep(0.10)

        write_ctrl(start=0, dc=0, res=1, blk=1, clear_done=1)
        time.sleep(0.15)

    def init(self, madctl=0x00, inversion=True):
        self.reset()

        self.cmd(0x11)
        time.sleep(0.12)

        self.cmd(0x36)
        self.data(madctl)

        self.cmd(0x3A)
        self.data(0x05)

        self.cmd(0xB2)
        self.data(0x1F)
        self.data(0x1F)
        self.data(0x00)
        self.data(0x33)
        self.data(0x33)

        self.cmd(0xB7)
        self.data(0x35)

        self.cmd(0xBB)
        self.data(0x2B)

        self.cmd(0xC0)
        self.data(0x2C)

        self.cmd(0xC2)
        self.data(0x01)

        self.cmd(0xC3)
        self.data(0x0F)

        self.cmd(0xC4)
        self.data(0x20)

        self.cmd(0xC6)
        self.data(0x13)

        self.cmd(0xD0)
        self.data(0xA4)
        self.data(0xA1)

        self.cmd(0xE0)
        for v in [0xF0, 0x04, 0x07, 0x04, 0x04, 0x04, 0x25, 0x33,
                  0x3C, 0x36, 0x14, 0x12, 0x29, 0x30]:
            self.data(v)

        self.cmd(0xE1)
        for v in [0xF0, 0x02, 0x04, 0x05, 0x05, 0x05, 0x21, 0x25,
                  0x32, 0x3B, 0x38, 0x12, 0x14, 0x27, 0x31]:
            self.data(v)

        self.cmd(0xE4)
        self.data(0x1D)
        self.data(0x00)
        self.data(0x00)

        if inversion:
            self.cmd(0x21)
        else:
            self.cmd(0x20)

        self.cmd(0x29)
        time.sleep(0.12)

    def set_window(self, x0, y0, x1, y1):
        x0 = int(x0)
        y0 = int(y0)
        x1 = int(x1)
        y1 = int(y1)

        if x0 < 0:
            x0 = 0
        if y0 < 0:
            y0 = 0
        if x1 > self.width - 1:
            x1 = self.width - 1
        if y1 > self.height - 1:
            y1 = self.height - 1

        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0

        x0_real = x0 + self.x_offset
        x1_real = x1 + self.x_offset
        y0_real = y0 + self.y_offset
        y1_real = y1 + self.y_offset

        self.cmd(0x2A)
        self.data((x0_real >> 8) & 0xFF)
        self.data(x0_real & 0xFF)
        self.data((x1_real >> 8) & 0xFF)
        self.data(x1_real & 0xFF)

        self.cmd(0x2B)
        self.data((y0_real >> 8) & 0xFF)
        self.data(y0_real & 0xFF)
        self.data((y1_real >> 8) & 0xFF)
        self.data(y1_real & 0xFF)

        self.cmd(0x2C)

    def push_color(self, color, count):
        color &= 0xFFFF
        hi = (color >> 8) & 0xFF
        lo = color & 0xFF

        for _ in range(int(count)):
            self.data(hi)
            self.data(lo)

    def fill_rect(self, x, y, w, h, color):
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)
        color = int(color) & 0xFFFF

        if w <= 0 or h <= 0:
            return

        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width - 1, x + w - 1)
        y1 = min(self.height - 1, y + h - 1)

        if x1 < x0 or y1 < y0:
            return

        self.set_window(x0, y0, x1, y1)
        self.push_color(color, (x1 - x0 + 1) * (y1 - y0 + 1))

    def fill_screen(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)


# ============================================================
# 5. ASCII 字模
# ============================================================

FONT5X7 = {
    " ": [0x00,0x00,0x00,0x00,0x00],
    "!": [0x00,0x00,0x5F,0x00,0x00],
    "%": [0x63,0x13,0x08,0x64,0x63],
    ".": [0x00,0x60,0x60,0x00,0x00],
    ":": [0x00,0x36,0x36,0x00,0x00],
    "-": [0x08,0x08,0x08,0x08,0x08],
    "/": [0x20,0x10,0x08,0x04,0x02],

    "0": [0x3E,0x51,0x49,0x45,0x3E],
    "1": [0x00,0x42,0x7F,0x40,0x00],
    "2": [0x42,0x61,0x51,0x49,0x46],
    "3": [0x21,0x41,0x45,0x4B,0x31],
    "4": [0x18,0x14,0x12,0x7F,0x10],
    "5": [0x27,0x45,0x45,0x45,0x39],
    "6": [0x3C,0x4A,0x49,0x49,0x30],
    "7": [0x01,0x71,0x09,0x05,0x03],
    "8": [0x36,0x49,0x49,0x49,0x36],
    "9": [0x06,0x49,0x49,0x29,0x1E],

    "A": [0x7E,0x11,0x11,0x11,0x7E],
    "B": [0x7F,0x49,0x49,0x49,0x36],
    "C": [0x3E,0x41,0x41,0x41,0x22],
    "D": [0x7F,0x41,0x41,0x22,0x1C],
    "E": [0x7F,0x49,0x49,0x49,0x41],
    "F": [0x7F,0x09,0x09,0x09,0x01],
    "G": [0x3E,0x41,0x49,0x49,0x7A],
    "H": [0x7F,0x08,0x08,0x08,0x7F],
    "I": [0x00,0x41,0x7F,0x41,0x00],
    "J": [0x20,0x40,0x41,0x3F,0x01],
    "K": [0x7F,0x08,0x14,0x22,0x41],
    "L": [0x7F,0x40,0x40,0x40,0x40],
    "M": [0x7F,0x02,0x0C,0x02,0x7F],
    "N": [0x7F,0x04,0x08,0x10,0x7F],
    "O": [0x3E,0x41,0x41,0x41,0x3E],
    "P": [0x7F,0x09,0x09,0x09,0x06],
    "Q": [0x3E,0x41,0x51,0x21,0x5E],
    "R": [0x7F,0x09,0x19,0x29,0x46],
    "S": [0x46,0x49,0x49,0x49,0x31],
    "T": [0x01,0x01,0x7F,0x01,0x01],
    "U": [0x3F,0x40,0x40,0x40,0x3F],
    "V": [0x1F,0x20,0x40,0x20,0x1F],
    "W": [0x7F,0x20,0x18,0x20,0x7F],
    "X": [0x63,0x14,0x08,0x14,0x63],
    "Y": [0x07,0x08,0x70,0x08,0x07],
    "Z": [0x61,0x51,0x49,0x45,0x43],
}


# ============================================================
# 6. 图形和文字显示
# ============================================================

def lcd_write_pixels(lcd, colors):
    for c in colors:
        c &= 0xFFFF
        lcd.data((c >> 8) & 0xFF)
        lcd.data(c & 0xFF)


def lcd_draw_char_fast(lcd, x, y, ch, color=WHITE, bg=BLACK, scale=1):
    ch = str(ch).upper()
    bitmap = FONT5X7.get(ch, FONT5X7[" "])
    scale = max(1, int(scale))

    w = 6 * scale
    h = 8 * scale
    pixels = []

    for yy in range(h):
        src_row = yy // scale
        for xx in range(w):
            src_col = xx // scale
            if src_col >= 5 or src_row >= 7:
                pixels.append(bg)
            else:
                pixels.append(color if ((bitmap[src_col] >> src_row) & 0x01) else bg)

    lcd.set_window(x, y, x + w - 1, y + h - 1)
    lcd_write_pixels(lcd, pixels)

    return w


def lcd_draw_text_fast(lcd, x, y, text, color=WHITE, bg=BLACK, scale=1):
    x_cur = int(x)
    y_cur = int(y)
    x_start = x_cur

    for ch in str(text):
        if ch == "\n":
            y_cur += 9 * scale
            x_cur = x_start
        else:
            x_cur += lcd_draw_char_fast(
                lcd,
                x_cur,
                y_cur,
                ch,
                color=color,
                bg=bg,
                scale=scale
            )

    return x_cur


def lcd_draw_center_text_fast(lcd, y, text, color=WHITE, bg=BLACK, scale=1):
    text = str(text)
    text_w = len(text) * 6 * scale
    x = max(0, (lcd.width - text_w) // 2)
    return lcd_draw_text_fast(lcd, x, y, text, color=color, bg=bg, scale=scale)


def lcd_draw_hline(lcd, x, y, w, color):
    lcd.fill_rect(x, y, w, 1, color)


def lcd_draw_vline(lcd, x, y, h, color):
    lcd.fill_rect(x, y, 1, h, color)


def lcd_draw_rect(lcd, x, y, w, h, color):
    lcd_draw_hline(lcd, x, y, w, color)
    lcd_draw_hline(lcd, x, y + h - 1, w, color)
    lcd_draw_vline(lcd, x, y, h, color)
    lcd_draw_vline(lcd, x + w - 1, y, h, color)


# ============================================================
# 7. UI 区域坐标统一管理
# ============================================================

HR_VALUE_AREA    = (17,  95, 72, 24)
SPO2_VALUE_AREA  = (132, 95, 72, 24)
TURN_VALUE_AREA  = (17,  175, 72, 24)
TEMP_VALUE_AREA  = (132, 175, 88, 24)
HUM_VALUE_AREA   = (18,  223, 90, 8)


def draw_card(lcd, x, y, w, h, title, value, unit, accent):
    lcd.fill_rect(x, y, w, h, CARD_BG)
    lcd_draw_rect(lcd, x, y, w, h, BORDER)

    lcd.fill_rect(x, y, w, 4, accent)

    lcd_draw_text_fast(lcd, x + 7, y + 11, title, color=TEXT_SUB, bg=CARD_BG, scale=2)
    lcd_draw_text_fast(lcd, x + 7, y + 35, str(value), color=TEXT_MAIN, bg=CARD_BG, scale=3)
    lcd_draw_text_fast(lcd, x + 73, y + 43, unit, color=accent, bg=CARD_BG, scale=1)


def draw_sleep_ui(lcd, hr=76, spo2=97, turn=5, temp=26.8, hum=48):
    """
    首次绘制完整界面。
    """
    lcd.fill_screen(BG_DARK)

    lcd.fill_rect(0, 0, 240, 34, TITLE_BG)
    lcd_draw_center_text_fast(lcd, 9, "SLEEP MONITOR", color=ACCENT_BLUE, bg=TITLE_BG, scale=2)

    lcd_draw_text_fast(lcd, 12, 42, "PYNQ-Z1  ST7789  SPI", color=TEXT_SUB, bg=BG_DARK, scale=1)

    draw_card(lcd, 10, 60, 105, 70, "HR",   int(hr),        "BPM", ACCENT_RED)
    draw_card(lcd, 125, 60, 105, 70, "SPO2", int(spo2),      "%",   ACCENT_BLUE)
    draw_card(lcd, 10, 140, 105, 70, "TURN", int(turn),      "TIM", ACCENT_GOLD)
    draw_card(lcd, 125, 140, 105, 70, "TEMP", f"{temp:.1f}", "C",   ACCENT_GREEN)

    lcd.fill_rect(10, 218, 220, 18, CARD_BG)
    lcd_draw_rect(lcd, 10, 218, 220, 18, BORDER)
    lcd_draw_text_fast(lcd, 18, 223, f"HUM {int(hum)}%", color=CYAN, bg=CARD_BG, scale=1)


def clear_and_write(lcd, area, text, scale=3, color=TEXT_MAIN, bg=CARD_BG):
    """
    只清除一个数字区域并写入新数字。
    """
    x, y, w, h = area
    lcd.fill_rect(x, y, w, h, bg)
    lcd_draw_text_fast(lcd, x, y, str(text), color=color, bg=bg, scale=scale)


def update_sleep_data(hr=None, spo2=None, turn=None, temp=None, hum=None):
    """
    后续更新数据时只调用这个函数。
    不传的参数不会更新。
    
    示例：
    update_sleep_data(hr=88, spo2=96, turn=9, temp=27.6, hum=55)
    update_sleep_data(hr=80)
    update_sleep_data(temp=28.1, hum=60)
    """
    if hr is not None:
        clear_and_write(lcd, HR_VALUE_AREA, int(hr), scale=3)

    if spo2 is not None:
        clear_and_write(lcd, SPO2_VALUE_AREA, int(spo2), scale=3)

    if turn is not None:
        clear_and_write(lcd, TURN_VALUE_AREA, int(turn), scale=3)

    if temp is not None:
        clear_and_write(lcd, TEMP_VALUE_AREA, f"{float(temp):.1f}", scale=3)

    if hum is not None:
        lcd.fill_rect(*HUM_VALUE_AREA, CARD_BG)
        lcd_draw_text_fast(lcd, HUM_VALUE_AREA[0], HUM_VALUE_AREA[1],
                           f"HUM {int(hum)}%", color=CYAN, bg=CARD_BG, scale=1)

    print("Updated:", "hr=", hr, "spo2=", spo2, "turn=", turn, "temp=", temp, "hum=", hum)


def redraw_sleep_ui(hr=76, spo2=97, turn=5, temp=26.8, hum=48):
    """
    需要完整重画界面时调用这个。
    一般不用频繁调用。
    """
    draw_sleep_ui(lcd, hr=hr, spo2=spo2, turn=turn, temp=temp, hum=hum)


# ============================================================
# 8. 一键执行：初始化 LCD 并显示默认界面
# ============================================================

print("Initializing LCD...")

lcd = ST7789_Robust(
    width=240,
    height=240,
    x_offset=0,
    y_offset=0,
    clkdiv=SPI_CLKDIV
)

lcd.init(madctl=0x00, inversion=True)

print("LCD initialized.")
status_print()

print("Drawing sleep monitor UI...")
draw_sleep_ui(lcd, hr=0, spo2=0, turn=0, temp=0.0, hum=0)

print("Done.")
print("后续改数字请调用：update_sleep_data(hr=88, spo2=96, turn=9, temp=27.6, hum=55)")