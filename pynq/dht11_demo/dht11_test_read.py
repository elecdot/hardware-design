import time
from dht11_driver import DHT11Driver

# Keep dht11_axi.bit and dht11_axi.hwh in the same directory as this script,
# or pass the correct relative/absolute bitfile path.
sensor = DHT11Driver(bitfile="dht11_axi.bit", base_addr=0x43C00000)

first = sensor.wait_first_valid(timeout=10)
print("first_valid =", first)

for i in range(20):
    data = sensor.read()
    print(
        i,
        "raw=", hex(data["raw"]),
        "humidity=", data["humidity"],
        "temperature=", data["temperature"],
        "status=", hex(data["status"]),
        "count_1us=", data["count_1us"],
    )
    time.sleep(2)
