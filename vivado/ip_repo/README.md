# ip_repo

可复用自定义 AXI IP 的共享 Vivado IP 仓库。工程入口在 [../project/](../project/)；
权威 RTL 源码在 [../../rtl/](../../rtl/)。

## 约定

- 权威 RTL 源码保存在 [../../rtl/](../../rtl/) 下。
- 将可复用自定义 IP 打包到这里，JY901 的历史包在根级 `component.xml/src/xgui`，队友迁移 IP 使用独立子目录。
- [../project/](../project/) 下的 Vivado 工程应通过 `ip_repo_paths` 和 `update_ip_catalog` 引用这个共享目录。
- 除非是有文档说明的临时实验，否则不要为每个 Vivado 工程维护一份已打包 IP 副本。

## Git 跟踪

跟踪重新发现和复用 IP 所需的已打包 IP 文件，例如 `component.xml`、`xgui/`，
以及 packager 生成的必需 HDL 或数据文件。不要把 Vivado 生成的 cache、run directory、hardware export、
`ip_user_files`、仿真输出、journal 或 log 当作设计源文件。

板级 XDC 文件不得包含在可复用 IP 的 synthesis file set 中。引脚约束属于消费该 IP 的 Vivado 工程，
不应放在已打包 IP 内部。

## 已打包 IP

| 路径 | VLNV / IP | 外部端口 | 权威 RTL | 打包工程 |
|---|---|---|---|---|
| [./component.xml](component.xml), [src/](src/), [xgui/](xgui/) | `xilinx.com:user:axi_i2c_jy901_v1_0:1.0` | `i2c_scl`, `i2c_sda` | [../../rtl/i2c_mpu9250/](../../rtl/i2c_mpu9250/) | [../project/axi_i2c_jy901_package/](../project/axi_i2c_jy901_package/) |
| [axi_humidifier/](axi_humidifier/) | `xilinx.com:user:axi_humidifier_v1_0:1.0` | `humidifier_led`, `humidifier_leds[3:0]`, `humidity_hw`, `humidity_hw_valid` | [../../rtl/axi_humidifier/](../../rtl/axi_humidifier/) | [../project/axi_humidifier_package/](../project/axi_humidifier_package/) |
| [axi_uart_spo2/](axi_uart_spo2/) | `xilinx.com:user:axi_uart_spo2_v1_0:1.0` | `uart_rxd`, `uart_txd`, `irq` | [../../rtl/axi_uart_spo2/](../../rtl/axi_uart_spo2/) | [../project/axi_uart_spo2/](../project/axi_uart_spo2/) |
| [dht11_axi/](dht11_axi/) | `xilinx.com:user:dht11_axi_v1_0:1.0` | `dht11` | [../../rtl/dht11_axi/](../../rtl/dht11_axi/) | [../project/dht11_axi/](../project/dht11_axi/) |
| [ir_ac_axi/](ir_ac_axi/) | `xilinx.com:user:gree_ir_axi_v1_0:1.0` | `ir_pwm` | [../../rtl/gree_ir_axi/](../../rtl/gree_ir_axi/) | [../project/ir_axi_package/](../project/ir_axi_package/) |
| [tft_lcd_spi_axi/](tft_lcd_spi_axi/) | `xilinx.com:user:tft_lcd_spi_axi_v1_0:1.0` | `lcd_scl`, `lcd_sda`, `lcd_res`, `lcd_dc`, `lcd_blk` | [../../rtl/tft_lcd_spi_axi/](../../rtl/tft_lcd_spi_axi/) | [../project/tft_lcd_spi_axi_package/](../project/tft_lcd_spi_axi_package/) |

## 集成提示

- 集成 overlay 当前使用 [../constraints/integrated/sleep_monitor_pynq_z1.xdc](../constraints/integrated/sleep_monitor_pynq_z1.xdc) 约束外部端口。
- 单模块 overlay 或队友原始 zip 中的 XDC 可能使用不同 pinout；不要与集成 XDC 同时启用。
- 修改寄存器、端口或参数后，需要同步 [../../docs/register_map.md](../../docs/register_map.md)、[../../docs/wiring.md](../../docs/wiring.md) 和相关 README。
