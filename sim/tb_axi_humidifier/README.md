# tb_axi_humidifier

AXI 加湿器控制器的行为仿真材料。

## 文件

| 文件 | 用途 |
|---|---|
| [tb_humidifier_core.v](tb_humidifier_core.v) | 核心行为 testbench。 |
| [tb_axi_humidifier.v](tb_axi_humidifier.v) | AXI 寄存器路径 testbench。 |

交接包预期 PASS 标记：

```text
tb_humidifier_core PASS
tb_axi_humidifier PASS
```

## 运行

在本目录下执行：

```powershell
iverilog -g2012 -o build/tb_humidifier_core.vvp tb_humidifier_core.v ../../rtl/axi_humidifier/humidifier_core.v
vvp build/tb_humidifier_core.vvp
iverilog -g2012 -o build/tb_axi_humidifier.vvp tb_axi_humidifier.v ../../rtl/axi_humidifier/axi_humidifier_v1_0.v ../../rtl/axi_humidifier/axi_humidifier_v1_0_S00_AXI.v ../../rtl/axi_humidifier/humidifier_core.v
vvp build/tb_axi_humidifier.vvp
```
