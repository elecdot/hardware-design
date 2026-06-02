from pynq import Overlay, MMIO
import time


class DHT11Driver:
    """PYNQ-side reader for dht11_axi AXI-Lite IP.

    Default base address: 0x43C00000.
    Register map:
      0x00 raw data: {humidity_int, humidity_dec, temperature_int, temperature_dec}
      0x04 status/debug
      0x08 count_1us debug
      0x0C reserved
    """

    def __init__(self, bitfile=None, base_addr=0x43C00000, addr_range=0x10000, download_bit=True):
        self.overlay = None
        if bitfile is not None:
            self.overlay = Overlay(bitfile)
            if download_bit:
                self.overlay.download()
        self.mmio = MMIO(base_addr, addr_range)

    def read_raw(self):
        raw = self.mmio.read(0x00)
        status = self.mmio.read(0x04)
        count_1us = self.mmio.read(0x08)
        return raw, status, count_1us

    def read(self):
        raw, status, count_1us = self.read_raw()
        hum_int = (raw >> 24) & 0xff
        hum_dec = (raw >> 16) & 0xff
        temp_int = (raw >> 8) & 0xff
        temp_dec = raw & 0xff
        return {
            "raw": raw,
            "status": status,
            "count_1us": count_1us,
            "humidity_int": hum_int,
            "humidity_dec": hum_dec,
            "temperature_int": temp_int,
            "temperature_dec": temp_dec,
            "humidity": hum_int + hum_dec / 100.0,
            "temperature": temp_int + temp_dec / 100.0,
        }

    def wait_first_valid(self, timeout=10, interval=0.5):
        start = time.time()
        while time.time() - start < timeout:
            data = self.read()
            if data["raw"] != 0:
                return data
            time.sleep(interval)
        return None
