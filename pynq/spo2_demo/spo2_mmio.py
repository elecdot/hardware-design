from time import sleep

from pynq import MMIO, Overlay


BASE_ADDR = 0x43C00000
ADDR_RANGE = 0x10000

REG_CTRL = 0x00
REG_TXDATA = 0x04
REG_STATUS = 0x08
REG_MEASURE = 0x0C
REG_WAVE = 0x10
REG_FLAGS = 0x14
REG_RAW0 = 0x18
REG_RAW1 = 0x1C

CTRL_ENABLE = 1 << 0
CTRL_CLEAR = 1 << 1
CTRL_IRQ_ENABLE = 1 << 2
CTRL_FRAME_7BYTE = 1 << 4


class Spo2Sample:
    __slots__ = (
        "spo2",
        "bpm",
        "pleth",
        "bar",
        "pi",
        "frame_len",
        "raw",
        "sensor_off",
        "sensor_error",
        "searching",
        "search_timeout",
        "crc_ok",
        "frame_count",
    )

    def __init__(
        self,
        spo2,
        bpm,
        pleth,
        bar,
        pi,
        frame_len,
        raw,
        sensor_off,
        sensor_error,
        searching,
        search_timeout,
        crc_ok,
        frame_count,
    ):
        self.spo2 = spo2
        self.bpm = bpm
        self.pleth = pleth
        self.bar = bar
        self.pi = pi
        self.frame_len = frame_len
        self.raw = raw
        self.sensor_off = sensor_off
        self.sensor_error = sensor_error
        self.searching = searching
        self.search_timeout = search_timeout
        self.crc_ok = crc_ok
        self.frame_count = frame_count

    def as_dict(self):
        return {
            "spo2": self.spo2,
            "bpm": self.bpm,
            "pleth": self.pleth,
            "bar": self.bar,
            "pi": self.pi,
            "frame_len": self.frame_len,
            "raw": self.raw,
            "sensor_off": self.sensor_off,
            "sensor_error": self.sensor_error,
            "searching": self.searching,
            "search_timeout": self.search_timeout,
            "crc_ok": self.crc_ok,
            "frame_count": self.frame_count,
        }


class AxiUartSpo2:
    def __init__(self, bitfile=None, base_addr=BASE_ADDR, addr_range=ADDR_RANGE):
        self.overlay = Overlay(bitfile) if bitfile else None
        self.mmio = MMIO(base_addr, addr_range)
        self.ctrl = CTRL_ENABLE
        self.mmio.write(REG_CTRL, self.ctrl)

    def set_frame_mode(self, bytes_per_frame=5):
        if bytes_per_frame not in (5, 7):
            raise ValueError("bytes_per_frame must be 5 or 7")
        if bytes_per_frame == 7:
            self.ctrl |= CTRL_FRAME_7BYTE
        else:
            self.ctrl &= ~CTRL_FRAME_7BYTE
        self.mmio.write(REG_CTRL, self.ctrl | CTRL_CLEAR)
        self.mmio.write(REG_CTRL, self.ctrl)

    def clear(self):
        self.mmio.write(REG_CTRL, self.ctrl | CTRL_CLEAR)
        self.mmio.write(REG_CTRL, self.ctrl)

    def status(self):
        return self.mmio.read(REG_STATUS)

    def has_frame(self):
        return bool(self.status() & 0x1)

    def read_sample(self):
        status = self.mmio.read(REG_STATUS)
        measure = self.mmio.read(REG_MEASURE)
        wave = self.mmio.read(REG_WAVE)
        flags = self.mmio.read(REG_FLAGS)
        raw0 = self.mmio.read(REG_RAW0)
        raw1 = self.mmio.read(REG_RAW1)

        raw = (
            raw0 & 0xFF,
            (raw0 >> 8) & 0xFF,
            (raw0 >> 16) & 0xFF,
            (raw0 >> 24) & 0xFF,
            raw1 & 0xFF,
            (raw1 >> 8) & 0xFF,
            (raw1 >> 16) & 0xFF,
        )

        return Spo2Sample(
            spo2=(measure >> 8) & 0xFF,
            bpm=measure & 0xFF,
            pleth=wave & 0xFF,
            bar=(wave >> 8) & 0xFF,
            pi=(wave >> 16) & 0xFF,
            frame_len=(status >> 7) & 0xF,
            raw=raw,
            sensor_off=bool(status & (1 << 3)),
            sensor_error=bool(status & (1 << 4)),
            searching=bool(status & (1 << 5)),
            search_timeout=bool(status & (1 << 6)),
            crc_ok=bool(status & (1 << 2)),
            frame_count=(flags >> 16) & 0xFFFF,
        )

    def wait_sample(self, timeout_s=2.0, poll_s=0.01):
        loops = max(1, int(timeout_s / poll_s))
        for _ in range(loops):
            if self.has_frame():
                return self.read_sample()
            sleep(poll_s)
        raise TimeoutError("No SpO2 UART frame received")

    def send_byte(self, value):
        self.mmio.write(REG_TXDATA, (1 << 8) | (value & 0xFF))


def demo(bitfile="uart_spo2_pynq.bit", frame_len=5):
    spo2 = AxiUartSpo2(bitfile)
    spo2.set_frame_mode(frame_len)
    while True:
        sample = spo2.wait_sample()
        print(
            f"SpO2={sample.spo2:3d}%  BPM={sample.bpm:3d}  "
            f"pleth={sample.pleth:3d}  raw={[hex(x) for x in sample.raw[:sample.frame_len]]}"
        )
        sleep(0.2)
