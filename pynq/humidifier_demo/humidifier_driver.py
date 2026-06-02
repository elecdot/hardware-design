"""PYNQ MMIO driver for the AXI humidifier LED controller."""


class AxiHumidifier:
    RANGE = 0x1000

    REG_CTRL = 0x00
    REG_SW_HUM = 0x04
    REG_THRESH = 0x08
    REG_TIMING = 0x0C
    REG_STATUS = 0x10
    REG_DRY_SEC = 0x14
    REG_VERSION = 0x18

    CTRL_ENABLE = 1 << 0
    CTRL_MANUAL_MODE = 1 << 1
    CTRL_MANUAL_ON = 1 << 2
    CTRL_USE_SW_HUMIDITY = 1 << 3
    CTRL_CLEAR_COUNTER = 1 << 4

    def __init__(self, mmio):
        self.mmio = mmio

    @classmethod
    def from_base_addr(cls, base_addr, length=RANGE):
        from pynq import MMIO

        return cls(MMIO(base_addr, length))

    @classmethod
    def from_overlay(cls, overlay, ip_name="axi_humidifier_0"):
        base_addr = overlay.ip_dict[ip_name]["phys_addr"]
        return cls.from_base_addr(base_addr)

    @classmethod
    def from_bitfile(cls, bitfile, ip_name="axi_humidifier_0"):
        from pynq import Overlay

        overlay = Overlay(bitfile)
        return cls.from_overlay(overlay, ip_name=ip_name)

    def read(self, offset):
        return self.mmio.read(offset)

    def write(self, offset, value):
        self.mmio.write(offset, value & 0xFFFFFFFF)

    @property
    def ctrl(self):
        return self.read(self.REG_CTRL)

    def set_ctrl(self, enable=True, manual_mode=False, manual_on=False, use_sw_humidity=True):
        value = 0
        if enable:
            value |= self.CTRL_ENABLE
        if manual_mode:
            value |= self.CTRL_MANUAL_MODE
        if manual_on:
            value |= self.CTRL_MANUAL_ON
        if use_sw_humidity:
            value |= self.CTRL_USE_SW_HUMIDITY
        self.write(self.REG_CTRL, value)

    def use_software_humidity(self, enabled=True):
        value = self.ctrl
        if enabled:
            value |= self.CTRL_USE_SW_HUMIDITY
        else:
            value &= ~self.CTRL_USE_SW_HUMIDITY
        value &= ~self.CTRL_CLEAR_COUNTER
        self.write(self.REG_CTRL, value)

    def set_software_humidity(self, humidity):
        humidity = max(0, min(100, int(humidity)))
        self.write(self.REG_SW_HUM, humidity)

    def set_thresholds(self, threshold_low=45, hysteresis=5, dry_alert_s=10):
        threshold_low = max(0, min(100, int(threshold_low)))
        hysteresis = max(0, min(100, int(hysteresis)))
        dry_alert_s = max(0, min(0xFFFF, int(dry_alert_s)))
        value = threshold_low | (hysteresis << 8) | (dry_alert_s << 16)
        self.write(self.REG_THRESH, value)

    def set_timing(self, min_on_s=0, min_off_s=0):
        min_on_s = max(0, min(0xFFFF, int(min_on_s)))
        min_off_s = max(0, min(0xFFFF, int(min_off_s)))
        self.write(self.REG_TIMING, min_on_s | (min_off_s << 16))

    def manual(self, on):
        self.set_ctrl(enable=True, manual_mode=True, manual_on=bool(on), use_sw_humidity=True)

    def automatic(self, use_sw_humidity=True):
        self.set_ctrl(enable=True, manual_mode=False, manual_on=False, use_sw_humidity=use_sw_humidity)

    def clear_counter(self):
        value = (self.ctrl & ~self.CTRL_CLEAR_COUNTER) | self.CTRL_CLEAR_COUNTER
        self.write(self.REG_CTRL, value)

    def status(self):
        raw = self.read(self.REG_STATUS)
        return {
            "raw": raw,
            "humidity": raw & 0xFF,
            "humidifier_on": bool((raw >> 8) & 0x1),
            "dry_level": (raw >> 9) & 0x3,
            "leds": (raw >> 12) & 0xF,
            "dry_seconds": self.read(self.REG_DRY_SEC),
            "version": self.read(self.REG_VERSION),
        }


__all__ = ["AxiHumidifier"]
