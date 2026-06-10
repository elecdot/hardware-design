"""TX-only PYNQ MMIO driver for the Gree IR AC transmitter IP.

The first integrated scope supports the seven verified Gree YB0F2 preset
commands from the handoff package. It does not expose the handoff RX capture
logic and does not implement arbitrary raw Gree command encoding.
"""

import json
import os
import time


DEFAULT_STANDALONE_BASE_ADDR = 0x43C00000
DEFAULT_INTEGRATED_BASE_ADDR = 0x40005000
DEFAULT_ADDR_RANGE = 0x10000
DEFAULT_IP_NAME = "gree_ir_axi_v1_0_0"

REG_CONTROL = 0x00
REG_STATUS = 0x04
REG_CMD_LOW = 0x08
REG_CMD_HIGH = 0x0C
REG_PRESET = 0x10
REG_DEBUG = 0x14

CONTROL_START = 1 << 0
CONTROL_SOFT_RESET = 1 << 1

STATUS_BUSY = 1 << 0
STATUS_DONE = 1 << 1
STATUS_ERROR = 1 << 2

GREE_YB0F2_COMMANDS = {
    "power_on": {
        "preset": 1,
        "hex67": "0x1090040A400080016",
        "low64": 0x090040A400080016,
        "description": "power on",
    },
    "power_off": {
        "preset": 2,
        "hex67": "0x8050040A40008001C",
        "low64": 0x050040A40008001C,
        "description": "power off",
    },
    "temp_24": {
        "preset": 3,
        "hex67": "0x9010040A400080016",
        "low64": 0x010040A400080016,
        "description": "set temperature to 24 C",
    },
    "temp_25": {
        "preset": 4,
        "hex67": "0x9090040A40008000E",
        "low64": 0x090040A40008000E,
        "description": "set temperature to 25 C",
    },
    "temp_26": {
        "preset": 5,
        "hex67": "0x9050040A40008001E",
        "low64": 0x050040A40008001E,
        "description": "set temperature to 26 C",
    },
    "temp_27": {
        "preset": 6,
        "hex67": "0x90D0040A400080000",
        "low64": 0x0D0040A400080000,
        "description": "set temperature to 27 C",
    },
    "temp_28": {
        "preset": 7,
        "hex67": "0x9030040A400080010",
        "low64": 0x030040A400080010,
        "description": "set temperature to 28 C",
    },
}

GREE_YB0F2_PRESETS = dict(
    (cfg["preset"], name) for name, cfg in GREE_YB0F2_COMMANDS.items()
)


def parse_int(value):
    return int(str(value), 0)


def load_command_library(path=None):
    if path is None:
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "gree_yb0f2_command_library_7.json",
        )
    with open(path, "r") as handle:
        rows = json.load(handle)
    return dict((row["name"], row) for row in rows)


def download_bitstream_compat(bitfile):
    """Download a bitstream while avoiding old PYNQ Tcl metadata issues."""
    try:
        from pynq import Bitstream
    except ImportError:
        from pynq.pl import Bitstream

    tcl_name = os.path.splitext(bitfile)[0] + ".tcl"
    disabled_tcl_name = tcl_name + ".disabled"
    moved_tcl = False
    if os.path.exists(tcl_name):
        if os.path.exists(disabled_tcl_name):
            os.remove(disabled_tcl_name)
        os.rename(tcl_name, disabled_tcl_name)
        moved_tcl = True
    try:
        Bitstream(bitfile).download()
    finally:
        if moved_tcl and os.path.exists(disabled_tcl_name):
            os.rename(disabled_tcl_name, tcl_name)


class GreeIrTransmitter(object):
    def __init__(self, mmio):
        self.mmio = mmio

    @classmethod
    def from_base_addr(cls, base_addr=DEFAULT_STANDALONE_BASE_ADDR, addr_range=DEFAULT_ADDR_RANGE):
        from pynq import MMIO

        return cls(MMIO(int(base_addr), int(addr_range)))

    @classmethod
    def from_overlay(cls, overlay, ip_name=DEFAULT_IP_NAME):
        base_addr, addr_range = cls.find_ip(overlay, ip_name)
        return cls.from_base_addr(base_addr, addr_range)

    @classmethod
    def from_bitfile(
        cls,
        bitfile,
        base_addr=DEFAULT_STANDALONE_BASE_ADDR,
        addr_range=DEFAULT_ADDR_RANGE,
        download=True,
    ):
        if download:
            download_bitstream_compat(bitfile)
        return cls.from_base_addr(base_addr, addr_range)

    @staticmethod
    def find_ip(overlay, ip_name=DEFAULT_IP_NAME):
        if ip_name in overlay.ip_dict:
            desc = overlay.ip_dict[ip_name]
            return int(desc["phys_addr"]), int(desc.get("addr_range", DEFAULT_ADDR_RANGE))

        for name, desc in overlay.ip_dict.items():
            ip_type = str(desc.get("type", "")).lower()
            if "gree_ir_axi" in name.lower() or "gree_ir_axi" in ip_type:
                return int(desc["phys_addr"]), int(desc.get("addr_range", DEFAULT_ADDR_RANGE))

        available = ", ".join(sorted(overlay.ip_dict.keys()))
        raise KeyError("Cannot find {0}; available IPs: {1}".format(ip_name, available))

    def read(self, offset):
        return int(self.mmio.read(offset))

    def write(self, offset, value):
        self.mmio.write(offset, int(value) & 0xFFFFFFFF)

    def clear_status(self):
        self.write(REG_STATUS, STATUS_DONE | STATUS_ERROR)

    def soft_reset(self):
        self.write(REG_CONTROL, CONTROL_SOFT_RESET)
        self.clear_status()

    def set_preset(self, preset_id):
        preset_id = int(preset_id)
        if preset_id not in GREE_YB0F2_PRESETS:
            raise ValueError("preset_id must be 1..7")
        self.write(REG_PRESET, preset_id)

    def set_command(self, command):
        if isinstance(command, str):
            key = command.lower()
            if key not in GREE_YB0F2_COMMANDS:
                raise ValueError("unknown IR AC command: {0}".format(command))
            preset_id = GREE_YB0F2_COMMANDS[key]["preset"]
        else:
            preset_id = int(command)
        self.set_preset(preset_id)

    def command_library(self):
        return dict(GREE_YB0F2_COMMANDS)

    def preset_name(self, preset_id=None):
        if preset_id is None:
            preset_id = self.read(REG_PRESET)
        return GREE_YB0F2_PRESETS.get(int(preset_id), "unknown")

    def status(self):
        st = self.read(REG_STATUS)
        dbg = self.read(REG_DEBUG)
        low = self.read(REG_CMD_LOW)
        high = self.read(REG_CMD_HIGH)
        preset = self.read(REG_PRESET)
        return {
            "busy": bool(st & STATUS_BUSY),
            "done": bool(st & STATUS_DONE),
            "error": bool(st & STATUS_ERROR),
            "debug_state": dbg & 0xF,
            "debug_sample_index": (dbg >> 8) & 0x3FF,
            "cmd64": ((high << 32) | low) & 0xFFFFFFFFFFFFFFFF,
            "preset": preset,
            "command": self.preset_name(preset),
            "raw_status": st,
        }

    def wait_done(self, timeout=15.0):
        deadline = time.time() + float(timeout)
        while time.time() < deadline:
            st = self.read(REG_STATUS)
            if st & STATUS_ERROR:
                raise RuntimeError("IR TX error status 0x%08X" % st)
            if st & STATUS_DONE:
                return
            time.sleep(0.001)
        raise RuntimeError("Timed out waiting for IR TX")

    def send(self, timeout=15.0):
        self.clear_status()
        self.write(REG_CONTROL, CONTROL_START)
        self.wait_done(timeout=timeout)

    def send_preset(self, preset_id, timeout=15.0):
        self.set_preset(preset_id)
        self.send(timeout=timeout)

    def send_command(self, command, timeout=15.0):
        self.set_command(command)
        self.send(timeout=timeout)

    def send_power_on(self, timeout=15.0):
        self.send_command("power_on", timeout=timeout)

    def send_power_off(self, timeout=15.0):
        self.send_command("power_off", timeout=timeout)

    def set_temperature(self, temperature_c, timeout=15.0):
        temperature_c = int(temperature_c)
        if temperature_c < 24 or temperature_c > 28:
            raise ValueError("temperature_c must be 24..28")
        self.send_command("temp_%d" % temperature_c, timeout=timeout)
