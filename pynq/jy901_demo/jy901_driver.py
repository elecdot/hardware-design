from __future__ import division

import time


DEFAULT_BITFILE = "/home/xilinx/jupyter_notebooks/jy901_test/jy901_axi_package.bit"
DEFAULT_BASE_ADDR = 0x43C00000
DEFAULT_ADDR_RANGE = 0x10000
DEFAULT_I2C_CLKDIV = 500
DEFAULT_SAMPLE_PERIOD = 10000000

EXPECTED_VERSION = 0x4A593101

CTRL = 0x00
STATUS = 0x04
DEV_ADDR = 0x08
START_REG = 0x0C
WORD_COUNT = 0x10
SAMPLE_PERIOD = 0x14
I2C_CLKDIV = 0x18
ERROR_CODE = 0x1C
VERSION = 0x28

AX_RAW = 0x40
AY_RAW = 0x44
AZ_RAW = 0x48
GX_RAW = 0x4C
GY_RAW = 0x50
GZ_RAW = 0x54
HX_RAW = 0x58
HY_RAW = 0x5C
HZ_RAW = 0x60
ROLL_RAW = 0x64
PITCH_RAW = 0x68
YAW_RAW = 0x6C
TEMP_RAW = 0x70
SAMPLE_CNT = 0x74

CTRL_ENABLE = 1 << 0
CTRL_ONESHOT = 1 << 1
CTRL_AUTO = 1 << 2
CTRL_CLEAR_DONE = 1 << 3
CTRL_CLEAR_ERROR = 1 << 4
CTRL_SOFT_RESET = 1 << 5

STATUS_BUSY = 1 << 0
STATUS_DONE = 1 << 1
STATUS_DATA_VALID = 1 << 2
STATUS_ACK_ERROR = 1 << 3
STATUS_TIMEOUT = 1 << 4
STATUS_CFG_DONE = 1 << 5
STATUS_SCL_IN = 1 << 6
STATUS_SDA_IN = 1 << 7

RAW_FIELDS = (
    ("ax", AX_RAW),
    ("ay", AY_RAW),
    ("az", AZ_RAW),
    ("gx", GX_RAW),
    ("gy", GY_RAW),
    ("gz", GZ_RAW),
    ("hx", HX_RAW),
    ("hy", HY_RAW),
    ("hz", HZ_RAW),
    ("roll", ROLL_RAW),
    ("pitch", PITCH_RAW),
    ("yaw", YAW_RAW),
    ("temp", TEMP_RAW),
)

RAW_FIELD_NAMES = tuple(name for name, _offset in RAW_FIELDS)

ERROR_CODE_LABELS = {
    0x00: "none",
    0x01: "address-write NACK",
    0x02: "register-address NACK",
    0x03: "address-read NACK",
    0x04: "config-low-byte NACK",
    0x05: "config-high-byte NACK",
    0x10: "timeout",
}

READABLE_FIELDS = (
    {
        "source_reg": 0x34,
        "name": "AX",
        "raw_key": "ax",
        "value_key": "ax_g",
        "scale": 16.0 / 32768.0,
        "unit": "g",
    },
    {
        "source_reg": 0x35,
        "name": "AY",
        "raw_key": "ay",
        "value_key": "ay_g",
        "scale": 16.0 / 32768.0,
        "unit": "g",
    },
    {
        "source_reg": 0x36,
        "name": "AZ",
        "raw_key": "az",
        "value_key": "az_g",
        "scale": 16.0 / 32768.0,
        "unit": "g",
    },
    {
        "source_reg": 0x37,
        "name": "GX",
        "raw_key": "gx",
        "value_key": "gx_dps",
        "scale": 2000.0 / 32768.0,
        "unit": "dps",
    },
    {
        "source_reg": 0x38,
        "name": "GY",
        "raw_key": "gy",
        "value_key": "gy_dps",
        "scale": 2000.0 / 32768.0,
        "unit": "dps",
    },
    {
        "source_reg": 0x39,
        "name": "GZ",
        "raw_key": "gz",
        "value_key": "gz_dps",
        "scale": 2000.0 / 32768.0,
        "unit": "dps",
    },
    {
        "source_reg": 0x3A,
        "name": "HX",
        "raw_key": "hx",
        "value_key": "hx_counts",
        "scale": 1.0,
        "unit": "raw_count",
    },
    {
        "source_reg": 0x3B,
        "name": "HY",
        "raw_key": "hy",
        "value_key": "hy_counts",
        "scale": 1.0,
        "unit": "raw_count",
    },
    {
        "source_reg": 0x3C,
        "name": "HZ",
        "raw_key": "hz",
        "value_key": "hz_counts",
        "scale": 1.0,
        "unit": "raw_count",
    },
    {
        "source_reg": 0x3D,
        "name": "Roll",
        "raw_key": "roll",
        "value_key": "roll_deg",
        "scale": 180.0 / 32768.0,
        "unit": "deg",
    },
    {
        "source_reg": 0x3E,
        "name": "Pitch",
        "raw_key": "pitch",
        "value_key": "pitch_deg",
        "scale": 180.0 / 32768.0,
        "unit": "deg",
    },
    {
        "source_reg": 0x3F,
        "name": "Yaw",
        "raw_key": "yaw",
        "value_key": "yaw_deg",
        "scale": 180.0 / 32768.0,
        "unit": "deg",
    },
    {
        "source_reg": 0x40,
        "name": "TEMP",
        "raw_key": "temp",
        "value_key": "temp_c",
        "scale": 1.0 / 100.0,
        "unit": "C",
    },
)


class JY901DemoError(Exception):
    pass


class JY901TimeoutError(JY901DemoError):
    pass


class JY901HardwareError(JY901DemoError):
    pass


def error_code_label(value):
    return ERROR_CODE_LABELS.get(value, "unknown")


def download_bitstream(bitfile):
    from pynq import Bitstream

    bs = Bitstream(bitfile)
    bs.download()
    return bs


def to_int16(value):
    value &= 0xFFFF
    if value & 0x8000:
        return value - 0x10000
    return value


def parse_status(value):
    return {
        "raw": value & 0xFFFFFFFF,
        "busy": 1 if value & STATUS_BUSY else 0,
        "done": 1 if value & STATUS_DONE else 0,
        "data_valid": 1 if value & STATUS_DATA_VALID else 0,
        "ack_error": 1 if value & STATUS_ACK_ERROR else 0,
        "timeout": 1 if value & STATUS_TIMEOUT else 0,
        "cfg_done": 1 if value & STATUS_CFG_DONE else 0,
        "scl_in": 1 if value & STATUS_SCL_IN else 0,
        "sda_in": 1 if value & STATUS_SDA_IN else 0,
    }


def status_label(status):
    if status.get("ack_error"):
        return "ACK_ERR"
    if status.get("timeout"):
        return "TIMEOUT"
    if not status.get("data_valid"):
        return "NO_DATA"
    return "OK"


def is_all_zero_sample(raw):
    for name in RAW_FIELD_NAMES:
        if raw.get(name, 0) != 0:
            return False
    return True


def validate_sample_payload(raw):
    if is_all_zero_sample(raw):
        raise JY901HardwareError(
            "all-zero sensor payload at SAMPLE_CNT=%d; treating this as invalid data"
            % raw.get("sample_cnt", -1)
        )
    return raw


def scale_raw(raw):
    scaled = {}
    for field in READABLE_FIELDS:
        scaled[field["value_key"]] = raw[field["raw_key"]] * field["scale"]
    scaled["sample_cnt"] = raw["sample_cnt"]
    return scaled


def readable_measurements(raw, scaled=None):
    if scaled is None:
        scaled = scale_raw(raw)

    rows = []
    for field in READABLE_FIELDS:
        rows.append(
            {
                "source_reg": field["source_reg"],
                "name": field["name"],
                "raw_key": field["raw_key"],
                "value_key": field["value_key"],
                "raw": raw[field["raw_key"]],
                "value": scaled[field["value_key"]],
                "unit": field["unit"],
            }
        )
    return rows


class JY901DemoDriver(object):
    def __init__(self, base_addr=DEFAULT_BASE_ADDR, addr_range=DEFAULT_ADDR_RANGE, mmio=None):
        if mmio is None:
            from pynq import MMIO

            mmio = MMIO(base_addr, addr_range)
        self.mmio = mmio
        self.base_addr = base_addr
        self.addr_range = addr_range

    def read_reg(self, offset):
        return self.mmio.read(offset)

    def write_reg(self, offset, value):
        self.mmio.write(offset, value)

    def version(self):
        return self.read_reg(VERSION)

    def check_version(self):
        value = self.version()
        if value != EXPECTED_VERSION:
            raise JY901DemoError(
                "unexpected VERSION 0x%08X, expected 0x%08X" % (value, EXPECTED_VERSION)
            )
        return value

    def read_status(self):
        return parse_status(self.read_reg(STATUS))

    def error_code(self):
        return self.read_reg(ERROR_CODE)

    def sample_count(self):
        return self.read_reg(SAMPLE_CNT)

    def clear_flags(self, keep_enable=False):
        value = CTRL_CLEAR_DONE | CTRL_CLEAR_ERROR
        if keep_enable:
            value |= CTRL_ENABLE
        self.write_reg(CTRL, value)
        time.sleep(0.001)
        self.write_reg(CTRL, CTRL_ENABLE if keep_enable else 0)

    def soft_reset(self):
        self.write_reg(CTRL, CTRL_SOFT_RESET)
        time.sleep(0.001)
        self.write_reg(CTRL, 0)

    def configure(
        self,
        dev_addr=0x50,
        start_reg=0x34,
        word_count=13,
        sample_period=DEFAULT_SAMPLE_PERIOD,
        i2c_clkdiv=DEFAULT_I2C_CLKDIV,
    ):
        self.write_reg(DEV_ADDR, dev_addr & 0x7F)
        self.write_reg(START_REG, start_reg & 0xFF)
        self.write_reg(WORD_COUNT, word_count & 0xFF)
        self.write_reg(SAMPLE_PERIOD, sample_period & 0xFFFFFFFF)
        self.write_reg(I2C_CLKDIV, i2c_clkdiv & 0xFFFFFFFF)

    def oneshot(self, timeout=1.0):
        self.clear_flags(keep_enable=False)
        before = self.sample_count()

        self.write_reg(CTRL, CTRL_ENABLE)
        time.sleep(0.001)
        self.write_reg(CTRL, CTRL_ENABLE | CTRL_ONESHOT)

        start_time = time.time()
        last_status = self.read_status()
        while time.time() - start_time < timeout:
            last_status = self.read_status()
            if last_status["ack_error"] or last_status["timeout"]:
                error_code = self.error_code()
                self.write_reg(CTRL, CTRL_ENABLE)
                raise JY901HardwareError(
                    "I2C error status=0x%08X error_code=0x%02X (%s)"
                    % (last_status["raw"], error_code, error_code_label(error_code))
                )
            if last_status["done"]:
                self.write_reg(CTRL, CTRL_ENABLE)
                if not last_status["data_valid"]:
                    raise JY901HardwareError(
                        "oneshot completed without data_valid status=0x%08X"
                        % last_status["raw"]
                    )
                return {
                    "before_count": before,
                    "after_count": self.sample_count(),
                    "status": last_status,
                    "error_code": self.error_code(),
                }
            time.sleep(0.001)

        self.write_reg(CTRL, CTRL_ENABLE)
        raise JY901TimeoutError(
            "oneshot timeout status=0x%08X error_code=0x%02X"
            % (last_status["raw"], self.error_code())
        )

    def start_auto(self):
        self.clear_flags(keep_enable=False)
        self.write_reg(CTRL, CTRL_ENABLE | CTRL_AUTO)

    def stop(self):
        self.write_reg(CTRL, 0)

    def read_raw(self):
        values = {}
        for name, offset in RAW_FIELDS:
            values[name] = to_int16(self.read_reg(offset))
        values["sample_cnt"] = self.sample_count()
        return values

    def read_valid_raw(self):
        return validate_sample_payload(self.read_raw())

    def read_scaled(self):
        return scale_raw(self.read_raw())

    def read_readable(self):
        raw = self.read_raw()
        return readable_measurements(raw)
