"""Integrated PYNQ sleep-monitor demo skeleton.

This script expects the final integrated overlay to expose:

- `axi_i2c_jy901_0`
- `dht11_axi_0`
- `axi_uart_spo2_0`
- `tft_lcd_spi_axi_0`
- `axi_humidifier_0`

It keeps PC socket transport out of the first live path; the printed sample
dictionary already matches the fields needed by `docs/protocol.md`.
"""

import argparse
import json
import os
import sys
import time


DEFAULT_BITFILE = "/home/xilinx/jupyter_notebooks/sleep_monitor/sleep_monitor.bit"
DEFAULT_IP_NAMES = {
    "jy901": "axi_i2c_jy901_0",
    "dht11": "dht11_axi_0",
    "spo2": "axi_uart_spo2_0",
    "tft": "tft_lcd_spi_axi_0",
    "humidifier": "axi_humidifier_0",
}


def add_demo_paths():
    here = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(here)
    for rel in ("jy901_demo", "dht11_demo", "spo2_demo", "tft_lcd_demo", "humidifier_demo"):
        path = os.path.join(parent, rel)
        if path not in sys.path:
            sys.path.insert(0, path)


def overlay_ip_addr(overlay, ip_name, allow_missing=False):
    if ip_name in overlay.ip_dict:
        desc = overlay.ip_dict[ip_name]
        return int(desc["phys_addr"]), int(desc.get("addr_range", 0x10000))
    if allow_missing:
        return None, None
    available = ", ".join(sorted(overlay.ip_dict.keys()))
    raise KeyError("Cannot find IP {0}; available IPs: {1}".format(ip_name, available))


class TurnCounter(object):
    def __init__(self, threshold_deg=35.0):
        self.threshold_deg = float(threshold_deg)
        self.last_roll = None
        self.last_pitch = None
        self.count = 0

    def update(self, roll_deg, pitch_deg):
        if roll_deg is None or pitch_deg is None:
            return 0, self.count
        flag = 0
        if self.last_roll is not None and self.last_pitch is not None:
            roll_delta = abs(float(roll_deg) - self.last_roll)
            pitch_delta = abs(float(pitch_deg) - self.last_pitch)
            if max(roll_delta, pitch_delta) >= self.threshold_deg:
                self.count += 1
                flag = 1
        self.last_roll = float(roll_deg)
        self.last_pitch = float(pitch_deg)
        return flag, self.count


def bind_drivers(args):
    add_demo_paths()

    from pynq import Overlay
    from jy901_driver import JY901DemoDriver, scale_raw, status_label
    from dht11_driver import DHT11Driver
    from spo2_mmio import AxiUartSpo2
    from tft_lcd import TftLcd
    from humidifier_driver import AxiHumidifier

    overlay = Overlay(args.bitfile, download=not args.no_download)
    drivers = {
        "overlay": overlay,
        "jy901_scale_raw": scale_raw,
        "jy901_status_label": status_label,
    }

    jy_base, jy_range = overlay_ip_addr(overlay, args.jy901_ip, args.allow_missing)
    if jy_base is not None:
        jy901 = JY901DemoDriver(base_addr=jy_base, addr_range=jy_range)
        jy901.configure(i2c_clkdiv=args.jy901_clkdiv)
        drivers["jy901"] = jy901

    dht_base, dht_range = overlay_ip_addr(overlay, args.dht11_ip, args.allow_missing)
    if dht_base is not None:
        drivers["dht11"] = DHT11Driver(base_addr=dht_base, addr_range=dht_range)

    spo2_base, spo2_range = overlay_ip_addr(overlay, args.spo2_ip, args.allow_missing)
    if spo2_base is not None:
        spo2 = AxiUartSpo2(base_addr=spo2_base, addr_range=spo2_range)
        spo2.set_frame_mode(args.spo2_frame_len)
        drivers["spo2"] = spo2

    if not args.no_humidifier:
        hum_base, hum_range = overlay_ip_addr(overlay, args.humidifier_ip, args.allow_missing)
        if hum_base is not None:
            humidifier = AxiHumidifier.from_base_addr(hum_base, hum_range)
            humidifier.automatic(use_sw_humidity=True)
            humidifier.set_thresholds(
                threshold_low=args.humidity_low,
                hysteresis=args.humidity_hysteresis,
                dry_alert_s=args.dry_alert_s,
            )
            humidifier.set_timing(min_on_s=0, min_off_s=0)
            drivers["humidifier"] = humidifier

    if not args.no_display:
        tft_base, _tft_range = overlay_ip_addr(overlay, args.tft_ip, args.allow_missing)
        if tft_base is not None:
            lcd = TftLcd(
                overlay=overlay,
                ip_name=args.tft_ip,
                clk_div=args.tft_clkdiv,
                auto_init=True,
            )
            drivers["lcd"] = lcd

    return drivers


def empty_sample(sample_id):
    return {
        "type": "sensor_data",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sample_id": sample_id,
        "heart_rate_bpm": None,
        "spo2_percent": None,
        "accel_x": None,
        "accel_y": None,
        "accel_z": None,
        "gyro_x": None,
        "gyro_y": None,
        "gyro_z": None,
        "mag_x": None,
        "mag_y": None,
        "mag_z": None,
        "turnover_flag": 0,
        "turnover_count": 0,
        "temperature_c": None,
        "humidity_percent": None,
        "data_valid": 0,
        "status_code": 0,
        "checksum_ok": 1,
        "remark": "init",
        "jy901_status": "NA",
        "humidifier_on": False,
    }


def read_jy901(drivers, sample, turn_counter, timeout_s):
    jy901 = drivers.get("jy901")
    if jy901 is None:
        sample["remark"] = "jy901_missing"
        return

    try:
        jy901.oneshot(timeout=timeout_s)
        raw = jy901.read_raw()
        scaled = drivers["jy901_scale_raw"](raw)
        status = jy901.read_status()
        sample.update(
            {
                "accel_x": scaled.get("ax_g"),
                "accel_y": scaled.get("ay_g"),
                "accel_z": scaled.get("az_g"),
                "gyro_x": scaled.get("gx_dps"),
                "gyro_y": scaled.get("gy_dps"),
                "gyro_z": scaled.get("gz_dps"),
                "mag_x": scaled.get("hx_counts"),
                "mag_y": scaled.get("hy_counts"),
                "mag_z": scaled.get("hz_counts"),
                "jy901_status": drivers["jy901_status_label"](status),
            }
        )
        flag, count = turn_counter.update(scaled.get("roll_deg"), scaled.get("pitch_deg"))
        sample["turnover_flag"] = flag
        sample["turnover_count"] = count
        sample["data_valid"] = 1
        sample["remark"] = "normal"
    except Exception as exc:
        sample["status_code"] |= 0x01
        sample["jy901_status"] = "ERR"
        sample["remark"] = "jy901:{0}".format(exc)


def read_dht11(drivers, sample, cache, now, period_s):
    dht11 = drivers.get("dht11")
    if dht11 is None:
        return

    if cache.get("last_read") is not None and now - cache["last_read"] < period_s:
        if cache.get("data") is not None:
            sample["temperature_c"] = cache["data"].get("temperature")
            sample["humidity_percent"] = int(cache["data"].get("humidity"))
        return

    cache["last_read"] = now
    try:
        data = dht11.read()
        if data["raw"] != 0:
            cache["data"] = data
            sample["temperature_c"] = data["temperature"]
            sample["humidity_percent"] = int(data["humidity"])
    except Exception as exc:
        sample["status_code"] |= 0x02
        sample["remark"] = "dht11:{0}".format(exc)


def read_spo2(drivers, sample):
    spo2 = drivers.get("spo2")
    if spo2 is None:
        return
    try:
        if spo2.has_frame():
            data = spo2.read_sample()
            sample["heart_rate_bpm"] = int(data.bpm)
            sample["spo2_percent"] = int(data.spo2)
            sample["checksum_ok"] = 1 if data.crc_ok else 0
            if data.sensor_off or data.sensor_error:
                sample["status_code"] |= 0x04
    except Exception as exc:
        sample["status_code"] |= 0x04
        sample["remark"] = "spo2:{0}".format(exc)


def update_humidifier(drivers, sample):
    humidifier = drivers.get("humidifier")
    humidity = sample.get("humidity_percent")
    if humidifier is None:
        return
    try:
        if humidity is not None:
            humidifier.set_software_humidity(humidity)
        status = humidifier.status()
        sample["humidifier_on"] = bool(status["humidifier_on"])
    except Exception as exc:
        sample["status_code"] |= 0x08
        sample["remark"] = "humidifier:{0}".format(exc)


def run_demo(args):
    drivers = bind_drivers(args)
    turn_counter = TurnCounter(threshold_deg=args.turn_threshold_deg)
    dht_cache = {}
    display_values = None

    if "lcd" in drivers:
        from display_ui import draw_dashboard

        display_values = draw_dashboard(drivers["lcd"], empty_sample(0))

    sample_id = 0
    try:
        while args.samples == 0 or sample_id < args.samples:
            sample_id += 1
            now = time.time()
            sample = empty_sample(sample_id)
            read_jy901(drivers, sample, turn_counter, args.sensor_timeout)
            read_dht11(drivers, sample, dht_cache, now, args.dht11_period)
            read_spo2(drivers, sample)
            update_humidifier(drivers, sample)

            if "lcd" in drivers:
                from display_ui import update_dashboard

                display_values = update_dashboard(drivers["lcd"], sample, display_values)

            print(json.dumps(sample, sort_keys=True))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Interrupted; stopping integrated demo.")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run the integrated sleep monitor demo.")
    parser.add_argument("--bitfile", default=DEFAULT_BITFILE)
    parser.add_argument("--samples", type=int, default=0, help="0 means run until Ctrl-C.")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--sensor-timeout", type=float, default=0.5)
    parser.add_argument("--dht11-period", type=float, default=2.0)
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--no-download", action="store_true")
    parser.add_argument("--no-display", action="store_true")
    parser.add_argument("--no-humidifier", action="store_true")
    parser.add_argument("--jy901-ip", default=DEFAULT_IP_NAMES["jy901"])
    parser.add_argument("--dht11-ip", default=DEFAULT_IP_NAMES["dht11"])
    parser.add_argument("--spo2-ip", default=DEFAULT_IP_NAMES["spo2"])
    parser.add_argument("--tft-ip", default=DEFAULT_IP_NAMES["tft"])
    parser.add_argument("--humidifier-ip", default=DEFAULT_IP_NAMES["humidifier"])
    parser.add_argument("--jy901-clkdiv", type=int, default=500)
    parser.add_argument("--tft-clkdiv", type=int, default=50)
    parser.add_argument("--spo2-frame-len", type=int, choices=(5, 7), default=5)
    parser.add_argument("--humidity-low", type=int, default=45)
    parser.add_argument("--humidity-hysteresis", type=int, default=5)
    parser.add_argument("--dry-alert-s", type=int, default=10)
    parser.add_argument("--turn-threshold-deg", type=float, default=35.0)
    return parser.parse_args(argv)


def main(argv=None):
    run_demo(parse_args(argv))


if __name__ == "__main__":
    main()
