# 课设中期个人 IP 检查说明书：I2C JY901 模块

| 字段 | 内容 |
|---|---|
| IP名称 | `axi_i2c_jy901_v1_0`，即 I2C-JY901/MPU9250 数据采集 AXI4-Lite 自定义 IP。该 IP 位于 PL 侧，通过 I2C 总线连接 JY901 九轴姿态模块，并通过 AXI4-Lite 寄存器向 PS/PYNQ 软件提供采样数据。 |
| 预期功能 | 作为 JY901 模块的 I2C Master，访问模块默认 7-bit 地址 `0x50`；从 `0x34` 起始寄存器连续读取 13 个 16-bit 数据 word，覆盖加速度、角速度、磁场、姿态角和温度原始值；通过 AXI4-Lite 寄存器配置设备地址、起始寄存器、读取长度、自动采样周期和 I2C 分频；提供 `busy`、`done`、`data_valid`、`ack_error`、`timeout`、`error_code`、`sample_cnt` 等状态，支持单次采样和自动周期采样，供 PS 侧 Python 驱动进行数据换算、体动/翻身检测和系统集成。 |
| 已实现的功能 | ARM/PS 端软件可通过 AXI4-Lite 寄存器控制 I2C IP 启动单次采样或自动周期采样，并读取 JY901 返回的原始传感器数据。I2C IP 定制为：<br>--仅主模式；<br>--面向 JY901 单从机采集，不支持多主仲裁；<br>--使用 7-bit I2C 地址，默认地址为 `0x50`；<br>--支持标准 I2C START、RESTART、STOP、ACK/NACK 检测和 timeout 错误上报；<br>--主要支持从 `0x34` 起始寄存器进行 burst read，一次最多读取 13 个 16-bit word；<br>--按 JY901 低字节在前格式拼接加速度、角速度、磁场、姿态角和温度 raw 数据；<br>--通过 AXI 状态寄存器提供 `busy`、`done`、`data_valid`、`ack_error`、`timeout`、`sample_cnt` 等状态；<br>--已保留 16-bit 配置写入通道，用于后续扩展模块配置；<br>--暂不支持 clock stretching、10-bit 地址、DMA、FIFO 和中断。 |
| 功能测试方法 | 1. 行为仿真：在 `sim/tb_i2c_mpu9250/` 执行 `just sim`，确认 testbench 输出 `PASS`；重点检查 I2C burst read 时序是否为 `START -> 0xA0 -> 0x34 -> RESTART -> 0xA1 -> 26 字节读取 -> NACK -> STOP`，并检查 `data_valid=1`、`ack_error=0`、`timeout=0`、`sample_cnt` 增加以及 AXI 数据寄存器读回值正确。2. ILA 测试：在 Vivado 上板工程中抓取 `scl_in`、`sda_in`、`scl_drive_low`、`sda_drive_low`、状态机状态、`tx_byte`、`rx_data`、`ack_error`、`timeout`、`data_valid`、`sample_cnt` 等信号；通过 ILA 确认 SCL/SDA 具备开漏释放/拉低行为，能看到 `0xA0 0x34 0xA1` 的 JY901 读事务，且采样完成后 `data_valid` 置位、`sample_cnt` 增加、无 ACK 或 timeout 错误。3. 上板 PS 端 demo 测试：JY901 使用 3.3 V 供电，SCL/SDA 接 PMODA `Y17/Y16` 并上拉到 3.3 V；在 PYNQ 端运行 `pynq/jy901_demo/demo_cli.py --duration 10`，检查 `VERSION=0x4A593101`、`SAMPLE_CNT` 持续增加、无 `ACK_ERR/TIMEOUT`，并观察移动或旋转 JY901 时加速度和姿态角 raw/scaled 数据随之变化。 |

## 当前中期结论

I2C JY901 个人 IP 已完成 RTL、AXI 寄存器接口、仿真用从机模型、错误路径仿真、Vivado 集成材料和 PYNQ 侧最小 demo 代码。2026-05-21 本地执行 `just sim` 时，`tb_jy901_sampler`、`tb_axi_i2c_jy901_top` 和 `tb_i2c_master_timeout` 均输出 `PASS`。后续应补充 ILA 截图和 PS 端 demo 运行记录，作为最终验收中的板级测试证据。
