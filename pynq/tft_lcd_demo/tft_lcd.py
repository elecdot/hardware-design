"""PYNQ driver for the AXI-Lite TFT LCD SPI IP.

The hardware IP sends one 8-bit SPI byte per CTRL.start pulse.  This driver
keeps a software shadow of CTRL[3:1], so reset/backlight/DC bits are preserved
on every write.
"""

import time
from pathlib import Path
from typing import Optional, Tuple, Union

try:
    from pynq import MMIO, Overlay
except ImportError:  # Allows import on a PC for documentation/linting.
    MMIO = None
    Overlay = None


REG_CTRL = 0x00
REG_DATA = 0x04
REG_CLKDIV = 0x08
REG_STATUS = 0x0C

CTRL_START = 1 << 0
CTRL_DC = 1 << 1
CTRL_RES = 1 << 2
CTRL_BLK = 1 << 3
CTRL_CLEAR_DONE = 1 << 4

STATUS_BUSY = 1 << 0
STATUS_DONE_LATCHED = 1 << 1
STATUS_DONE_PULSE = 1 << 2
STATUS_RES = 1 << 3
STATUS_BLK = 1 << 4
STATUS_DC = 1 << 5

DEFAULT_BASE_ADDR = 0x43C00000
DEFAULT_ADDR_RANGE = 0x10000
DEFAULT_IP_NAME = "tft_lcd_spi_axi_0"
DEFAULT_CLK_DIV = 50


def color565(red: int, green: int, blue: int) -> int:
    """Convert 8-bit RGB values to RGB565."""
    red = max(0, min(255, int(red)))
    green = max(0, min(255, int(green)))
    blue = max(0, min(255, int(blue)))
    return ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)


class TftLcd:
    WIDTH = 240
    HEIGHT = 240

    RED = 0xF800
    GREEN = 0x07E0
    BLUE = 0x001F
    WHITE = 0xFFFF
    BLACK = 0x0000

    def __init__(
        self,
        overlay=None,
        ip_name: str = DEFAULT_IP_NAME,
        base_addr: Optional[int] = None,
        addr_range: int = DEFAULT_ADDR_RANGE,
        clk_div: int = DEFAULT_CLK_DIV,
        x_offset: int = 0,
        y_offset: int = 0,
        auto_init: bool = False,
    ) -> None:
        if MMIO is None:
            raise RuntimeError("This driver must run on PYNQ with pynq.MMIO available.")

        if overlay is not None:
            base_addr, addr_range = self._find_ip(overlay, ip_name)
        elif base_addr is None:
            base_addr = DEFAULT_BASE_ADDR

        self.mmio = MMIO(base_addr, addr_range)
        self.base_addr = base_addr
        self.addr_range = addr_range
        self.x_offset = x_offset
        self.y_offset = y_offset
        self._ctrl_shadow = CTRL_RES | CTRL_BLK

        self.set_clk_div(clk_div)
        self._write_ctrl()

        if auto_init:
            self.init_panel()

    @staticmethod
    def _find_ip(overlay, ip_name: str) -> Tuple[int, int]:
        if ip_name in overlay.ip_dict:
            desc = overlay.ip_dict[ip_name]
            return int(desc["phys_addr"]), int(desc.get("addr_range", DEFAULT_ADDR_RANGE))

        for name, desc in overlay.ip_dict.items():
            if desc.get("type") == "xilinx.com:user:tft_lcd_spi_axi:1.0":
                return int(desc["phys_addr"]), int(desc.get("addr_range", DEFAULT_ADDR_RANGE))

        available = ", ".join(sorted(overlay.ip_dict.keys()))
        raise KeyError(f"Cannot find {ip_name!r}; available IPs: {available}")

    @classmethod
    def from_bitfile(cls, bitfile: Union[str, Path], download: bool = True, **kwargs) -> "TftLcd":
        if Overlay is None:
            raise RuntimeError("This helper must run on PYNQ with pynq.Overlay available.")
        overlay = Overlay(str(bitfile), download=download)
        return cls(overlay=overlay, **kwargs)

    def read_status(self) -> int:
        return int(self.mmio.read(REG_STATUS))

    def set_clk_div(self, clk_div: int) -> None:
        """Set SPI divider. SCL = AXI_clock / (2 * clk_div)."""
        if not 0 <= int(clk_div) <= 0xFFFF:
            raise ValueError("clk_div must fit in 16 bits; 0 selects RTL default.")
        self.mmio.write(REG_CLKDIV, int(clk_div))

    def _write_ctrl(
        self,
        *,
        dc: Optional[Union[int, bool]] = None,
        reset: Optional[Union[int, bool]] = None,
        backlight: Optional[Union[int, bool]] = None,
        start: bool = False,
        clear_done: bool = False,
    ) -> None:
        if dc is not None:
            self._set_shadow_bit(CTRL_DC, dc)
        if reset is not None:
            self._set_shadow_bit(CTRL_RES, reset)
        if backlight is not None:
            self._set_shadow_bit(CTRL_BLK, backlight)

        value = self._ctrl_shadow
        if start:
            value |= CTRL_START
        if clear_done:
            value |= CTRL_CLEAR_DONE
        self.mmio.write(REG_CTRL, value)

    def _set_shadow_bit(self, mask: int, enabled: Union[int, bool]) -> None:
        if enabled:
            self._ctrl_shadow |= mask
        else:
            self._ctrl_shadow &= ~mask

    def wait_idle(self, timeout_s: float = 1.0) -> None:
        deadline = time.monotonic() + timeout_s
        while self.read_status() & STATUS_BUSY:
            if time.monotonic() > deadline:
                raise TimeoutError("TFT SPI IP stayed busy too long.")

    def wait_done(self, timeout_s: float = 1.0) -> None:
        deadline = time.monotonic() + timeout_s
        while not (self.read_status() & STATUS_DONE_LATCHED):
            if time.monotonic() > deadline:
                raise TimeoutError("TFT SPI byte did not finish before timeout.")

    def clear_done(self) -> None:
        self._write_ctrl(clear_done=True)

    def set_backlight(self, enabled: bool) -> None:
        self._write_ctrl(backlight=enabled)

    def hardware_reset(self, low_s: float = 0.10, high_s: float = 0.12) -> None:
        self._write_ctrl(reset=False, backlight=False, dc=True)
        time.sleep(low_s)
        self._write_ctrl(reset=True, backlight=True, dc=True)
        time.sleep(high_s)

    def send_byte(self, value: int, dc: Union[int, bool], timeout_s: float = 1.0) -> None:
        self.wait_idle(timeout_s)
        self.mmio.write(REG_DATA, int(value) & 0xFF)
        self._write_ctrl(dc=dc, start=True)
        self.wait_done(timeout_s)

    def send_bytes(self, values, dc: Union[int, bool], timeout_s: float = 1.0) -> None:
        for value in values:
            self.send_byte(value, dc=dc, timeout_s=timeout_s)

    def command(self, cmd: int, data=(), delay_s: float = 0.0) -> None:
        self.send_byte(cmd, dc=False)
        if data:
            self.send_bytes(data, dc=True)
        if delay_s:
            time.sleep(delay_s)

    def init_panel(self, rotation: int = 0) -> None:
        """Initialize a 240x240 ST7789 panel using the tested Jupyter sequence."""
        madctl_by_rotation = {
            0: 0x00,
            1: 0xC0,
            2: 0x70,
            3: 0xA0,
        }
        madctl = madctl_by_rotation[int(rotation) & 0x3]

        self.hardware_reset()
        self.command(0x11, delay_s=0.120)  # Sleep out
        self.command(0x36, [madctl])
        self.command(0x3A, [0x05])  # RGB565
        self.command(0xB2, [0x1F, 0x1F, 0x00, 0x33, 0x33])
        self.command(0xB7, [0x35])
        self.command(0xBB, [0x2B])
        self.command(0xC0, [0x2C])
        self.command(0xC2, [0x01])
        self.command(0xC3, [0x0F])
        self.command(0xC4, [0x20])
        self.command(0xC6, [0x13])
        self.command(0xD0, [0xA4, 0xA1])
        self.command(0xE0, [0xF0, 0x04, 0x07, 0x04, 0x04, 0x04, 0x25,
                            0x33, 0x3C, 0x36, 0x14, 0x12, 0x29, 0x30])
        self.command(0xE1, [0xF0, 0x02, 0x04, 0x05, 0x05, 0x05, 0x21, 0x25,
                            0x32, 0x3B, 0x38, 0x12, 0x14, 0x27, 0x31])
        self.command(0xE4, [0x1D, 0x00, 0x00])
        self.command(0x21)  # Display inversion on
        self.command(0x29, delay_s=0.120)  # Display on

    def set_window(self, x0: int, y0: int, x1: int, y1: int) -> None:
        if not (0 <= x0 <= x1 < self.WIDTH and 0 <= y0 <= y1 < self.HEIGHT):
            raise ValueError("Window must be inside 240x240 bounds and use inclusive x1/y1.")

        x0 += self.x_offset
        x1 += self.x_offset
        y0 += self.y_offset
        y1 += self.y_offset

        self.command(0x2A, [(x0 >> 8) & 0xFF, x0 & 0xFF, (x1 >> 8) & 0xFF, x1 & 0xFF])
        self.command(0x2B, [(y0 >> 8) & 0xFF, y0 & 0xFF, (y1 >> 8) & 0xFF, y1 & 0xFF])
        self.command(0x2C)

    def write_pixels_rgb565(self, data) -> None:
        if len(data) % 2:
            raise ValueError("RGB565 pixel stream must contain an even number of bytes.")
        self.send_bytes(data, dc=True)

    def fill(self, color: int, chunk_pixels: int = 256) -> None:
        self.fill_rect(0, 0, self.WIDTH, self.HEIGHT, color, chunk_pixels=chunk_pixels)

    def fill_rect(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        color: int,
        chunk_pixels: int = 256,
    ) -> None:
        if width <= 0 or height <= 0:
            return
        self.set_window(x, y, x + width - 1, y + height - 1)

        color &= 0xFFFF
        pair = bytes(((color >> 8) & 0xFF, color & 0xFF))
        pixels_left = width * height
        while pixels_left:
            n = min(pixels_left, chunk_pixels)
            self.write_pixels_rgb565(pair * n)
            pixels_left -= n

    def draw_pixel(self, x: int, y: int, color: int) -> None:
        self.set_window(x, y, x, y)
        self.write_pixels_rgb565(bytes(((color >> 8) & 0xFF, color & 0xFF)))


def default_bitfile() -> Path:
    return Path(__file__).resolve().parents[1] / "vivado_export" / "tft_lcd.bit"
