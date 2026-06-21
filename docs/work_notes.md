## 安全和硬件处理

- 板子上电时不要热插拔传感器导线。
- 连接模块前确认 VCC、GND 和信号电压。
- 将 PYNQ-Z1 Arduino/PMOD I/O 视为 3.3 V logic。
- 驱动需要 5 V signaling 的模块时使用 level shifting 或隔离。
- 小心处理加湿器、风扇、IR LED 和扬声器等 actuator；不要从 FPGA 引脚直接驱动负载。
- 需要时使用限流电阻和合适的驱动电路。

## 常见失败模式

调试时先检查这些项：

- 板卡 part 错误：PYNQ-Z1 使用 `xc7z020clg400-1`。
- PYNQ overlay 缺少 `.hwh` 文件，或 `.hwh` 与 `.bit` 不匹配。
- Vivado 中 AXI IP 名称变化，但 Python 仍使用旧名称。
- AXI wrapper 与 Python driver 之间的寄存器 offset 不匹配。
- 软件把 start bit 持续置高，但硬件期望 rising edge。
- 外部输入在边沿检测前没有同步。
- 计数器中的时钟频率假设错误。
- 硬件调试 reset 保持有效；`jy901_hw_debug_top.resetn` 在 SW0 上为 active-high release，因此 SW0 为低会让 sampler 保持 reset。
- UART baud rate 不匹配。
- I2C `ERROR_CODE=0x01` 表示 address-write NACK。确认 debug top 使用 PMODA `Y17/Y16`，
  SCL/SDA idle high 为 3.3 V，`core_tx_byte_dbg=0xA0`，并且 JY901 实际响应 7-bit address `0x50`。
- 在 PYNQ demo 中，如果全零 JY901 payload 紧接在 `ERROR_CODE=0x01` 前出现，应视为无效数据，
  不是一次真实翻身或姿态变化。检查传感器供电、pullup、跳线接触，以及模块是否在重复 oneshot read 中 reset 或丢失 I2C ACK。
- I2C SDA/SCL pull-up 或三态处理错误。
- DHT11 双向线没有在正确时间释放为 high-Z。
- SPI mode 或显示 reset sequence 不匹配。
- PYNQ-Z1 I/O 电压违规。
- 板端 client 连接前 socket server 未启动。
- `axi_i2c_jy901` overlay 中 `USBIND_0_0_*` 上的 Vivado DRC `NSTD-1`/`UCIO-1`
  表示 PS7 USB0 control interface 被误导出为外部接口。不要随意分配 PL 引脚或降低 DRC 严重性。
  这很可能由 Vivado 的 “Run Block Automation” 导致。

## PYNQ Runtime 约束

首个 JY901 demo 的当前板端软件模型：

- Jupyter kernel 以 root 运行，解释器为 `/opt/python3.6/bin/python3.6`。
- Jupyter kernel package path 包含 `/opt/python3.6/lib/python3.6/site-packages`，其中安装了 `pynq`。
- SSH CLI 默认 `python3` 是 `/usr/bin/python3` 版本 3.4.3+，与 Jupyter/PYNQ dependency 环境不一致。
- SSH CLI 默认 `python` 可能显示 Python 2.7.10，但这只是旧 Linux 默认解释器，不应用于 PYNQ demo。
- Kernel：`Linux pynq 4.6.0-xilinx ... armv7l`。

demo 的正确 SSH CLI 调用：

```bash
sudo env -u PYTHONPATH /opt/python3.6/bin/python3.6 demo_cli.py --duration 10
```

保持 PYNQ 板端 demo 代码兼容 Python 3.6。除非升级板端镜像，否则避免使用 Python 3.7+ 语法或 API。

## Bring-up 笔记

### 2026-05-19 JY901 I2C 偶发 address NACK

PL-only ILA bring-up 期间，偶发 `ERROR_CODE=0x01` 捕获最终定位到一根磨损、接触不良的杜邦线。
更换/重新插紧导线后，同一 RTL、约束和 `0x50` JY901 地址产生了有效 ACK 波形。

后续 PS 侧测试期间，也观察到 idle 状态持续捕获 `scl` 和 `sda` 为 `0`；
因此 pullup、pin mapping 和 IOBUF 三态行为应保留在 debug checklist 中。
