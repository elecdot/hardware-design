"""PC-runnable checks for integrated demo driver binding.

This self-test uses fake driver modules so it can run without PYNQ hardware.
"""

import sys
import types

import integrated_demo


class _FakeJY901(object):
    def __init__(self, base_addr, addr_range):
        self.base_addr = base_addr
        self.addr_range = addr_range
        self.configured = False

    def configure(self, i2c_clkdiv):
        self.configured = True


class _FakeDht11(object):
    def __init__(self, base_addr, addr_range):
        self.base_addr = base_addr
        self.addr_range = addr_range


class _FakeSpo2(object):
    def __init__(self, base_addr, addr_range):
        self.base_addr = base_addr
        self.addr_range = addr_range
        self.frame_len = None

    def set_frame_mode(self, frame_len):
        self.frame_len = int(frame_len)


class _FakeTft(object):
    def __init__(self, overlay, ip_name, clk_div, auto_init):
        self.overlay = overlay
        self.ip_name = ip_name
        self.clk_div = clk_div
        self.auto_init = auto_init


class _FakeHumidifier(object):
    @classmethod
    def from_base_addr(cls, base_addr, addr_range):
        obj = cls()
        obj.base_addr = base_addr
        obj.addr_range = addr_range
        return obj

    def automatic(self, use_sw_humidity=True):
        self.use_sw_humidity = use_sw_humidity

    def set_thresholds(self, threshold_low, hysteresis, dry_alert_s):
        self.threshold_low = threshold_low

    def set_timing(self, min_on_s, min_off_s):
        self.min_on_s = min_on_s


class _FakeIrAc(object):
    @classmethod
    def from_base_addr(cls, base_addr, addr_range):
        obj = cls()
        obj.base_addr = base_addr
        obj.addr_range = addr_range
        return obj


def _module(**attrs):
    mod = types.ModuleType("_fake")
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def install_fake_modules():
    originals = {}
    fake_modules = {
        "jy901_driver": _module(
            JY901DemoDriver=_FakeJY901,
            scale_raw=lambda raw: raw,
            status_label=lambda status: "OK",
        ),
        "dht11_driver": _module(DHT11Driver=_FakeDht11),
        "spo2_mmio": _module(AxiUartSpo2=_FakeSpo2),
        "tft_lcd": _module(TftLcd=_FakeTft),
        "humidifier_driver": _module(AxiHumidifier=_FakeHumidifier),
        "ir_ac": _module(GreeIrTransmitter=_FakeIrAc),
    }
    for name, mod in fake_modules.items():
        originals[name] = sys.modules.get(name)
        sys.modules[name] = mod
    return originals


def restore_modules(originals):
    for name, original in originals.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


def test_static_bind_includes_ir_ac():
    originals = install_fake_modules()
    try:
        args = integrated_demo.parse_args(
            [
                "--bitfile",
                "system_v0_2.bit",
                "--skip-artifact-check",
                "--metadata-source",
                "static",
                "--no-download",
            ]
        )
        drivers = integrated_demo.bind_drivers(args)

        expected = {
            "overlay",
            "jy901",
            "dht11",
            "spo2",
            "lcd",
            "humidifier",
            "ir_ac",
            "jy901_scale_raw",
            "jy901_status_label",
        }
        missing = expected - set(drivers)
        assert not missing, "missing bound drivers: {0}".format(sorted(missing))
        assert drivers["ir_ac"].base_addr == integrated_demo.STATIC_IP_LAYOUT["ir_ac"]["phys_addr"]
    finally:
        restore_modules(originals)


def main():
    test_static_bind_includes_ir_ac()
    print("integrated_demo_selftest PASS")


if __name__ == "__main__":
    main()
