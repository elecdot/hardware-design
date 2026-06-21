# tb_dht11_axi

DHT11 AXI IP 的行为仿真材料。

## 文件

| 文件 | 用途 |
|---|---|
| [tb_dht11.v](tb_dht11.v) | 交接包中的 DHT11 testbench。 |
| [tb_dht11_onewire_smoke.v](tb_dht11_onewire_smoke.v) | Icarus 兼容的 smoke test，包含 `IOBUF` stub 和显式 PASS/ERROR 输出。 |

## 下一步

Vivado 打包前先运行 smoke test。在本目录下执行：

```powershell
iverilog -g2012 -o build/tb_dht11_onewire_smoke.vvp tb_dht11_onewire_smoke.v ../../rtl/dht11_axi/dht11_onewire.v
vvp build/tb_dht11_onewire_smoke.vvp
```

预期 PASS 标记：

```text
tb_dht11_onewire_smoke PASS
```
