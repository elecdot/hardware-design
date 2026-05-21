# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.3
#   kernelspec:
#     display_name: Python 3 (PYNQ)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # JY901 AXI I2C Smoke Demo
#
# Minimal notebook-facing demo for PYNQ-Z1. This follows the verified flow:
# download the bitstream with `Bitstream.download()`, bind direct `MMIO`, then
# run one JY901 oneshot transaction.

# %%
from __future__ import division
from __future__ import print_function

from jy901_driver import (
    DEFAULT_ADDR_RANGE,
    DEFAULT_BASE_ADDR,
    DEFAULT_BITFILE,
    DEFAULT_I2C_CLKDIV,
    EXPECTED_VERSION,
    JY901DemoDriver,
    download_bitstream,
    readable_measurements,
    scale_raw,
    status_label,
    validate_sample_payload,
)

print("target runtime: /opt/python3.6/bin/python3.6 on Linux 4.6.0-xilinx")
print("bitfile:", DEFAULT_BITFILE)
print("base address: 0x%08X" % DEFAULT_BASE_ADDR)

# %% [markdown]
# ## Download Bitstream And Bind MMIO
#
# Keep this first version independent from `.hwh` auto discovery.

# %%
download_bitstream(DEFAULT_BITFILE)
imu = JY901DemoDriver(DEFAULT_BASE_ADDR, DEFAULT_ADDR_RANGE)
print("bitstream downloaded and MMIO created")

# %% [markdown]
# ## Version And Status Check
#
# `VERSION` should be `0x4A593101`. `scl_in` and `sda_in` should normally idle
# high when wiring and pullups are correct.

# %%
version = imu.check_version()
status = imu.read_status()

print("VERSION: 0x%08X expected 0x%08X" % (version, EXPECTED_VERSION))
print("STATUS : 0x%08X %s" % (status["raw"], status_label(status)))
print("SCL/SDA: scl=%d sda=%d" % (status["scl_in"], status["sda_in"]))

# %% [markdown]
# ## Configure And Run One Oneshot

# %%
imu.configure(i2c_clkdiv=DEFAULT_I2C_CLKDIV)
result = imu.oneshot(timeout=1.0)

print("oneshot sample_cnt: %d -> %d" % (result["before_count"], result["after_count"]))
print("status: 0x%08X error_code: 0x%02X" % (result["status"]["raw"], result["error_code"]))

# %% [markdown]
# ## Read Raw And Scaled Values

# %%
raw = imu.read_raw()
validate_sample_payload(raw)
scaled = scale_raw(raw)
measurements = readable_measurements(raw, scaled)

print("raw:", raw)
print(
    "scaled: ax={0:.3f}g ay={1:.3f}g az={2:.3f}g roll={3:.2f} pitch={4:.2f} yaw={5:.2f} temp={6:.2f}C".format(
        scaled["ax_g"],
        scaled["ay_g"],
        scaled["az_g"],
        scaled["roll_deg"],
        scaled["pitch_deg"],
        scaled["yaw_deg"],
        scaled["temp_c"],
    )
)
print("")
print("%-6s %-8s %-12s %-10s" % ("field", "raw", "value", "unit"))
for item in measurements:
    print(
        "%-6s %-8d %-12.3f %-10s"
        % (item["name"], item["raw"], item["value"], item["unit"])
    )

# %% [markdown]
# ## Stop

# %%
imu.stop()
print("demo stopped")
