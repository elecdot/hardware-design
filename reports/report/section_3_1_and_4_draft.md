# 三、四章正文材料

## 三、详细设计

## 3.1 I2C JY901 模块的设计（撰写人：待填）

JY901 九轴姿态模块用于本系统的体动与翻身检测。模块输出加速度、角速度、磁场、姿态角和温度等数据，其中加速度与 roll/pitch 姿态角主要用于判断睡眠过程中的明显体动和翻身动作。为了避免 PS 侧软件直接处理 I2C 起止位、ACK、重复起始等低层时序，本设计在 PL 侧实现 AXI4-Lite I2C-JY901 自定义 IP，由 PS 侧通过 MMIO 寄存器启动采样、读取状态并取得原始传感器数据。

整体数据通路如下：

```text
JY901 九轴模块
    -> I2C 开漏总线
    -> PL 侧 axi_i2c_jy901_v1_0 自定义 IP
    -> AXI4-Lite 寄存器
    -> PYNQ Python MMIO 驱动
    -> 翻身检测、TFT 显示、PC socket 上传
```

![图3-1 I2C JY901 单模块完整链路图：JY901、I2C 自定义 IP、AXI4-Lite、PYNQ MMIO 驱动、单模块测试和翻身检测接口](assert/fig3-1-jy901-single-module-path.svg)

### 3.1.1 IP 设计

#### （1）IP 实现的功能

本 IP 的封装名称为 `axi_i2c_jy901_v1_0`，对外提供一个 AXI4-Lite 从接口和两个 I2C 总线端口 `i2c_scl`、`i2c_sda`。IP 的主要功能包括：

1. 作为 I2C Master 访问 JY901 模块，默认 7-bit 从机地址为 `0x50`。
2. 支持从 JY901 寄存器 `0x34` 开始连续读取 13 个 16-bit 数据字，共 26 字节。
3. 将读取到的 `AX`、`AY`、`AZ`、`GX`、`GY`、`GZ`、`HX`、`HY`、`HZ`、`Roll`、`Pitch`、`Yaw`、`TEMP` 缓存在 AXI 可读寄存器中。
4. 支持单次采样 `oneshot_start` 和周期自动采样 `auto_mode`。
5. 通过寄存器暴露 `busy`、`done`、`data_valid`、`ack_error`、`timeout`、`cfg_done` 等状态位，便于驱动和测试定位问题。
6. 支持一个通用的 16-bit 配置写事务，用于后续扩展 JY901 配置寄存器写入。
7. 通过 `I2C_CLKDIV` 寄存器配置 I2C 时钟分频，避免把 100 MHz 系统时钟和 100 kHz/50 kHz I2C 速率写死在 RTL 中。

JY901 数据寄存器为 16-bit 有符号数，I2C 读取时低字节在前、高字节在后。IP 在 PL 侧只负责读取和拼接原始整数，不在硬件里做浮点换算；物理量换算由 PYNQ Python 驱动完成。这样做可以减少 PL 资源消耗，并让后续算法调整更灵活。

#### （2）工作原理

JY901 的 I2C 读取格式为：

```text
START
(IICAddr << 1) | 0
RegAddr
RESTART
(IICAddr << 1) | 1
Data1L
Data1H
...
STOP
```

本设计中默认 7-bit 地址为 `0x50`，因此写地址字节为 `0xA0`，读地址字节为 `0xA1`。报告中需要特别说明，`0xA1` 是读地址字节，不是应写入 `DEV_ADDR` 寄存器的 7-bit 地址。驱动和 RTL 均使用 `DEV_ADDR=0x50`。

一次完整的默认 burst read 事务为：

```text
START, 0xA0, ACK, 0x34, ACK,
RESTART, 0xA1, ACK,
26 个数据字节,
最后一个字节后主机 NACK,
STOP
```

I2C 总线为开漏结构，SCL/SDA 不能由 FPGA 主动输出高电平。RTL 中使用 `drive_low` 信号控制是否拉低总线，当不拉低时释放为高阻态，由外部 3.3 V 上拉电阻把信号拉高。该设计避免了 FPGA 管脚和传感器总线同时驱动高低电平的风险。

```verilog
assign i2c_scl = scl_drive_low ? 1'b0 : 1'bz;
assign i2c_sda = sda_drive_low ? 1'b0 : 1'bz;
```

默认寄存器参数中 `I2C_CLKDIV=250`。在 100 MHz AXI 时钟下，一个 I2C bit 周期分为低电平准备、低电平保持、高电平采样、高电平保持四个 phase，因此：

```text
100 MHz / 100 kHz / 4 = 250
```

在部分上板演示中，为提高长杜邦线和外接上拉情况下的稳定性，软件可将 `I2C_CLKDIV` 配置为 `500`，使 SCL 降至约 50 kHz。由于分频值是寄存器可配置项，调试时可以在不重新综合 bitstream 的情况下调整总线速率。

JY901 原始数据的换算关系如下表。

| 数据 | JY901 寄存器 | 原始格式 | Python 换算公式 |
|---|---:|---|---|
| X/Y/Z 轴加速度 | `0x34` 到 `0x36` | signed int16 | `raw / 32768 * 16`，单位 g |
| X/Y/Z 轴角速度 | `0x37` 到 `0x39` | signed int16 | `raw / 32768 * 2000`，单位 deg/s |
| X/Y/Z 轴磁场 | `0x3A` 到 `0x3C` | signed int16 | 第一版保留 raw count |
| Roll/Pitch/Yaw | `0x3D` 到 `0x3F` | signed int16 | `raw / 32768 * 180`，单位 deg |
| 模块温度 | `0x40` | signed int16 | `raw / 100`，单位摄氏度 |

#### （3）电路设计

IP 内部按“AXI 寄存器层、采样调度层、I2C 协议核心、开漏 IO 适配层”划分。顶层 `axi_i2c_jy901_v1_0.v` 实例化三个主要模块：

1. `axi_lite_regs.v`：实现 AXI4-Lite 寄存器读写、控制位脉冲生成、状态读回和数据寄存器映射。
2. `jy901_sampler.v`：根据 `oneshot_start`、`auto_mode` 和 `cfg_write_start` 调度一次 I2C 事务，并在事务完成后锁存数据。
3. `i2c_open_drain_io.v` 与 `i2c_master_core.v`：前者负责开漏三态适配，后者负责 I2C 位级时序、ACK 检测、读字节、主机 ACK/NACK 和 STOP。

![图3-2 JY901 IP 内部架构图：axi_lite_regs、jy901_sampler、i2c_master_core 和 i2c_open_drain_io](assert/fig3-2-jy901-ip-architecture.png)

`i2c_master_core` 是位级状态机。状态机在收到 `start` 后，先产生 START 条件，然后依次发送地址写字节、寄存器地址、重复起始、地址读字节，再接收指定长度的数据。每发送一个字节后都会释放 SDA 并在 SCL 高电平采样 ACK；如果 SDA 为高，则认为从机未应答，并根据当前步骤写入错误码。读最后一个字节后主机释放 SDA 发送 NACK，然后产生 STOP。

简化后的状态流如下：

```text
IDLE
 -> START
 -> WRITE 地址写字节
 -> ACK
 -> WRITE 起始寄存器
 -> ACK
 -> RESTART
 -> WRITE 地址读字节
 -> ACK
 -> READ 数据字节
 -> MASTER_ACK 或 MASTER_NACK
 -> STOP
 -> DONE
```

错误路径包括地址写 NACK、寄存器地址 NACK、地址读 NACK、配置写低/高字节 NACK 和超时。错误码通过 `ERROR_CODE` 寄存器读回，驱动可据此区分地址、接线、上拉和总线卡死等问题。

`jy901_sampler` 负责把 I2C 核输出的字节流整理为 16-bit 数据寄存器。由于 JY901 低字节在前，采样器在事务结束后按如下方式拼接：

```verilog
data0 <= {byte_buf[1], byte_buf[0]};
data1 <= {byte_buf[3], byte_buf[2]};
data2 <= {byte_buf[5], byte_buf[4]};
```

实际代码中使用 `latch_word` 任务按 word 索引写入 13 个数据槽。`WORD_COUNT` 允许软件配置，但硬件会把 `0` 处理为 1 word，并把超过 13 的值钳位到 13，防止 PS 侧错误配置导致越界读取。

`axi_lite_regs` 把软件写入的 `CTRL` 位转换为单周期脉冲。例如 `oneshot_start`、`clear_done`、`clear_error`、`soft_reset` 和 `cfg_write_start` 都是写 1 触发型脉冲。这样 PS 侧只需写寄存器启动动作，PL 侧不会因为控制位保持为 1 而重复启动同一事务。

![图3-3 I2C JY901 burst read 时序图：START、0xA0、0x34、RESTART、0xA1、连续数据和 STOP](assert/fig3-3-jy901-i2c-burst-read.svg)

#### （4）IP 封装

Vivado 中封装后的 IP 为 `xilinx.com:user:axi_i2c_jy901_v1_0:1.0`。主要参数和端口如下。

| 项目 | 内容 |
|---|---|
| AXI 数据宽度 | `C_S00_AXI_DATA_WIDTH = 32` |
| AXI 地址宽度 | `C_S00_AXI_ADDR_WIDTH = 7` |
| 时钟 | `s00_axi_aclk`，最终集成中使用 Zynq PS FCLK，按 100 MHz 设计 |
| 复位 | `s00_axi_aresetn`，低有效 |
| AXI 接口 | 标准 AXI4-Lite slave `S_AXI` |
| 外部端口 | `i2c_scl`、`i2c_sda`，均为 inout 开漏风格信号 |
| 默认 I2C 地址 | `0x50` |
| 默认起始寄存器 | `0x34` |
| 默认读取长度 | 13 个 16-bit word |
| 默认采样周期 | `10_000_000` 个 AXI clock，100 MHz 下为 100 ms |
| 版本寄存器 | `VERSION = 0x4A593101` |

核心寄存器表如下。完整寄存器表在设计归档中统一维护，报告正文列出与 JY901 采样和调试直接相关的寄存器。

| 偏移 | 名称 | 访问 | 说明 |
|---:|---|---|---|
| `0x00` | `CTRL` | RW | `enable`、`oneshot_start`、`auto_mode`、清标志、软复位、配置写触发 |
| `0x04` | `STATUS` | R | `busy`、`done`、`data_valid`、`ack_error`、`timeout`、`cfg_done`、SCL/SDA 输入电平 |
| `0x08` | `DEV_ADDR` | RW | JY901 7-bit I2C 地址，默认 `0x50` |
| `0x0C` | `START_REG` | RW | burst read 起始寄存器，默认 `0x34` |
| `0x10` | `WORD_COUNT` | RW | 读取的 16-bit word 数，硬件最多 13 |
| `0x14` | `SAMPLE_PERIOD` | RW | 自动采样周期 |
| `0x18` | `I2C_CLKDIV` | RW | I2C quarter-period 分频值 |
| `0x1C` | `ERROR_CODE` | R | NACK 或 timeout 错误码 |
| `0x28` | `VERSION` | R | IP 版本标识 |
| `0x40` 到 `0x70` | 数据寄存器 | R | `AX_RAW` 到 `TEMP_RAW` |
| `0x74` | `SAMPLE_CNT` | R | 成功采样计数 |

在最终集成硬件平台中，JY901 IP 的 AXI 基地址为 `0x4000_0000`，地址范围为 4 KB。独立 JY901 调试平台曾使用 `0x43C0_0000` 和 64 KB 范围，该地址只用于单模块 bring-up，不作为最终系统集成地址。

最终集成系统的板级约束中，JY901 使用 Arduino SCL/SDA：

| 信号 | PYNQ-Z1 引脚 | 说明 |
|---|---|---|
| `i2c_scl` | Arduino SCL `P16` | 3.3 V I2C，上拉到 3.3 V |
| `i2c_sda` | Arduino SDA `P15` | 开漏数据线，上拉到 3.3 V |

早期 JY901 独立 overlay 和 PL-only debug top 可使用 PMODA `Y17/Y16`。最终系统中 PMODA 已分配给 TFT LCD，因此报告第四章应以 Arduino `P16/P15` 作为最终集成接线。

![图3-4 Vivado 封装后的 axi_i2c_jy901_v1_0 IP 符号截图：S_AXI、时钟复位和 i2c_scl/i2c_sda 外部端口](assert/fig3-4-vivado-jy901-ip-symbol.png)

### 3.1.2 软件设计

PYNQ 侧软件的目标是把 AXI 寄存器访问封装成稳定的传感器读数接口，并把 JY901 数据接入系统采样字典。软件分为两个层次：

1. 单模块 MMIO 驱动，用于 JY901 独立硬件平台的课堂演示和调试。
2. 集成系统采样与编排逻辑，用于最终多 IP 硬件平台。

单模块驱动 `JY901DemoDriver` 使用 PYNQ `MMIO` 读写寄存器。主要 API 包括：

| API | 功能 |
|---|---|
| `configure()` | 写入 `DEV_ADDR`、`START_REG`、`WORD_COUNT`、`SAMPLE_PERIOD`、`I2C_CLKDIV` |
| `oneshot()` | 清除标志、启动一次采样、轮询 `STATUS`，检测 ACK/timeout 错误 |
| `read_raw()` | 从 `AX_RAW` 到 `TEMP_RAW` 读取 13 个原始寄存器 |
| `read_scaled()` | 将 signed int16 raw 值换算为 g、deg/s、deg、摄氏度等物理量 |
| `status_label()` | 把状态寄存器转换为 `OK`、`ACK_ERR`、`TIMEOUT`、`NO_DATA` 等可读标签 |

软件读取流程如下：

```text
下载 bitstream 或加载 Overlay
 -> 创建 MMIO 对象
 -> 检查 VERSION 是否为 0x4A593101
 -> 配置 I2C 地址、起始寄存器、读取长度和分频
 -> 写 CTRL 触发 oneshot 或 auto_mode
 -> 轮询 STATUS
 -> 若 ack_error/timeout 置位则读取 ERROR_CODE 并报错
 -> 若 done 和 data_valid 置位则读取 raw 数据
 -> signed int16 转换和物理量换算
 -> 填入 sensor_data，用于显示、翻身检测和上传
```

关键配置逻辑可概括如下：

```python
def configure(self, dev_addr=0x50, start_reg=0x34,
              word_count=13, sample_period=10000000,
              i2c_clkdiv=500):
    self.write_reg(DEV_ADDR, dev_addr & 0x7F)
    self.write_reg(START_REG, start_reg & 0xFF)
    self.write_reg(WORD_COUNT, word_count & 0xFF)
    self.write_reg(SAMPLE_PERIOD, sample_period & 0xFFFFFFFF)
    self.write_reg(I2C_CLKDIV, i2c_clkdiv & 0xFFFFFFFF)
```

原始数据先按 signed int16 解释，再进行物理量换算：

```python
def to_int16(value):
    value &= 0xFFFF
    if value & 0x8000:
        return value - 0x10000
    return value

ax_g = ax_raw / 32768.0 * 16.0
roll_deg = roll_raw / 32768.0 * 180.0
```

在最终集成软件中，板端程序会加载最终集成硬件平台，并通过硬件描述或静态地址表绑定所有 IP。JY901 读取流程支持短暂重试和 stale cache：如果单次 JY901 读取失败，但上一次有效数据仍在允许时间内，系统可标记 `imu_stale=1` 并继续让 HR/SpO2 分类链路工作，避免一次 IMU 瞬态失败重置整个 PC 分类 warm-up。

翻身检测放在 PS 侧 `TurnCounter` 中，而不是放进 PL IP。当前第一版逻辑使用 roll/pitch 变化阈值，默认阈值为 `35.0` 度。这样做的原因是翻身动作判断和防抖策略更接近应用层，后续可以调整阈值、加入冷却时间或融合加速度变化，而不需要重新生成 bitstream。

![图3-5 JY901 PYNQ 软件读取流程图：配置寄存器、启动采样、轮询状态、读取 raw、换算和更新 sensor_data](assert/fig3-5-jy901-pynq-driver-flow.svg)

### 3.1.3 模块测试

JY901 模块按仿真、单模块上板和集成上板三个层次验证。

#### （1）行为仿真

行为仿真使用 Icarus Verilog 和 JY901 I2C slave model，可以验证 I2C 正常 burst read、地址 NACK、AXI 顶层寄存器路径和 timeout 路径。

| 测试项 | 预期结果 |
|---|---|
| sampler 正常读取 | 出现 `START, 0xA0, 0x34, RESTART, 0xA1`，读出 26 字节，`data_valid=1`，`sample_cnt=1` |
| 地址错误 | `DEV_ADDR=0x51` 时 `ack_error=1`，`ERROR_CODE=0x01` |
| AXI 顶层路径 | `VERSION=0x4A593101`，可写配置寄存器，可轮询 `STATUS.done`，可读 `AX_RAW`、`AY_RAW`、`TEMP_RAW` |
| `WORD_COUNT` 边界 | `1`、`0`、`20` 均能完成，硬件把 `0` 当作 1，把大于 13 的值钳位 |
| 自动采样 | `auto_mode` 下 `SAMPLE_CNT` 随周期事务递增 |
| 配置写 | `cfg_write_start` 触发 16-bit 配置写并置位 `cfg_done` |
| timeout | 缩短 `TIMEOUT_CYCLES` 后能置位 `timeout=1`，`ERROR_CODE=0x10` |

仿真期望 PASS 输出包括：

```text
PASS: JY901 burst read simulation completed
PASS: JY901 address NACK simulation completed
PASS: AXI top burst read register path completed
PASS: AXI top clear_done/clear_error path completed
PASS: AXI top WORD_COUNT boundary paths completed
PASS: AXI top auto_mode path completed
PASS: AXI top cfg_write path completed
PASS: AXI top address NACK register path completed
PASS: AXI top extended NACK paths completed
PASS: AXI top soft_reset path completed
PASS: I2C master timeout path completed
```

![图3-6 JY901 仿真 PASS 终端截图：sampler、AXI top、NACK 和 timeout 测试通过](assert/fig3-6-jy901-simulation-pass.png)

![图3-7 JY901 I2C 仿真波形截图：START、RESTART、ACK、NACK 和 STOP](assert/fig3-7-jy901-i2c-waveform.png)

#### （2）单模块 PYNQ 上板测试

单模块测试使用 PYNQ 命令行测试程序完成。测试流程为：下载独立 JY901 bitstream，创建 direct MMIO，检查 `VERSION`，启动一次 oneshot，随后周期性读取并打印 scaled 数据。该流程不依赖硬件描述自动解析，适合快速排查 I2C 地址、上拉、线序和 AXI 寄存器问题。

通过标准为：

1. `VERSION` 读回 `0x4A593101`。
2. 初始 oneshot 后 `SAMPLE_CNT` 增加。
3. `STATUS.ack_error=0`，`STATUS.timeout=0`。
4. 连续输出数据表格时 `SAMPLE_CNT` 持续增加。
5. 手动移动或旋转 JY901 模块时，加速度和 roll/pitch/yaw 数值有相应变化。

![图3-8 JY901 单模块 PYNQ CLI 输出截图：VERSION PASS、SAMPLE_CNT、STATUS OK 和姿态数据变化](assert/fig3-8-jy901-single-module-cli-pass.png)

#### （3）集成系统测试

在集成硬件平台测试中，JY901 IP 挂接在 AXI 地址 `0x4000_0000`。PYNQ 板端软件通过统一驱动套件读取 JY901，并把结果写入 `sensor_data` 字段：

| 字段 | 来源 |
|---|---|
| `accel_x/y/z` | JY901 加速度换算值 |
| `gyro_x/y/z` | JY901 角速度换算值 |
| `mag_x/y/z` | JY901 磁场 raw count |
| `turnover_flag` | PS 侧阈值判断结果 |
| `turnover_count` | 累计翻身次数 |
| `imu_valid`、`imu_stale` | 当前 IMU 数据质量 |
| `jy901_status` | `OK`、`ERR` 或 `STALE` |

早期集成板级 smoke 测试证明 JY901 在集成硬件平台中能返回有效样本，`jy901_status="OK"` 且 `data_valid=1`。该阶段没有进行翻身计数专项动作测试，因此当时的共享输出中 `turnover_count` 保持为 0。最终演示中已通过手动改变 JY901 姿态验证翻身检测效果，roll/pitch 明显变化时 `turnover_flag` 置位，`turnover_count` 累计增加，说明 JY901 单模块采集数据已能支撑系统体动/翻身检测功能。

![图3-9 集成系统中 JY901 字段的 JSON 输出截图：jy901_status、imu_valid、accel、gyro 和 turnover 字段](assert/fig3-9-integrated-jy901-json-fields.png)

![图3-10 最终演示翻身计数验证截图：旋转 JY901 前后 turnover_flag 置位且 turnover_count 增加](assert/fig3-10-final-demo-turnover-pass.png)

## 3.2 PYNQ 板端软件集成设计（撰写人：待填）

PYNQ 板端软件是 PL 自定义 IP 和 PC 端服务之间的中间层。它不负责复杂模型推理，而是负责加载硬件平台、绑定各个 AXI4-Lite IP、周期性读取传感器、刷新本地 TFT 显示、执行经过校验的控制命令，并把每一轮采样结果组织为规范的 `sensor_data` 消息。这样划分后，PL 侧保持时序接口稳定，PC 侧集中处理分类、策略和可视化，板端软件则承担实时采样与设备执行的职责。

![图3-11 PYNQ 板端软件集成结构图：Overlay 加载、驱动绑定、采样、TFT 更新、socket 通信和命令执行](assert/fig3-11-pynq-software-integration.svg)

### 3.2.1 Overlay 加载与驱动绑定

板端程序启动后首先加载最终集成 overlay，并读取与 bitstream 匹配的硬件描述，用于定位各个 IP 的 AXI 基地址和地址范围。考虑到部分旧版 PYNQ 运行环境可能无法自动解析硬件描述，软件保留静态地址表作为兼容方案。静态地址表只用于运行时绑定，不改变硬件地址规划；最终报告和系统集成仍以 Vivado 导出的地址映射为准。

驱动绑定时，每个 IP 被包装为职责单一的软件对象或函数接口。PYNQ 主循环只调用这些接口，不直接在业务逻辑中散落寄存器偏移量，便于调试和后续替换模块。

| 驱动对象 | 绑定内容 | 板端职责 |
|---|---|---|
| JY901 驱动 | I2C-JY901 AXI IP | 触发 oneshot，读取姿态原始值，换算加速度、角速度、磁场和 roll/pitch/yaw |
| DHT11 驱动 | DHT11 AXI IP | 读取温度、湿度和数据有效状态 |
| SpO2 驱动 | UART SpO2 AXI IP | 解析心率、血氧、帧状态和校验标志 |
| TFT 驱动 | TFT LCD SPI AXI IP | 初始化屏幕，按固定区域刷新数值 |
| 加湿器驱动 | Humidifier AXI IP | 写入目标状态，读取当前控制结果 |
| IR 空调驱动 | Gree IR AC AXI IP | 写入 preset，触发红外波形发送，读取 done/error 状态 |

板端驱动绑定完成后，软件会检查关键 IP 是否存在。最终演示要求 JY901、DHT11、SpO2、TFT、加湿器和 IR 空调 IP 均完成绑定；仅在 bring-up 或隔离调试时允许跳过个别模块。

### 3.2.2 采样流程与数据质量标志

板端软件以约 1 s 为默认周期执行采样。每一轮采样生成一个递增的 `sample_id`，并读取 JY901、DHT11、SpO2 等传感器。采样结果统一写入 `sensor_data` 字典，随后用于 TFT 显示、PC 上传和本地控制状态关联。

采样流程如下：

```text
生成 sample_id 和 timestamp
 -> 读取 JY901，更新姿态和翻身计数
 -> 读取 DHT11，更新温湿度
 -> 读取 UART SpO2，更新心率和血氧
 -> 合并质量标志和状态文本
 -> 刷新 TFT 显示
 -> 输出 sensor_data
```

JY901 读取采用“短暂重试 + 最近有效值缓存”的策略。若某一轮 I2C 读取瞬时失败，板端会进行有限次数重试；若仍失败但最近有效 IMU 数据未超时，则复用最近值并标记 `imu_stale=1`。这样做可以避免一次 IMU 瞬态故障导致整个 PC 分类 warm-up 被重置。心率和血氧链路仍由 `spo2_valid`、`data_valid` 等标志独立表达。

`sensor_data` 的主要字段分组如下。

| 字段组 | 代表字段 | 设计说明 |
|---|---|---|
| 采样标识 | `type`、`sample_id`、`timestamp` | 保证 PC 端能把四类消息按同一采样周期对齐 |
| 生理数据 | `heart_rate_bpm`、`spo2_percent`、`spo2_valid` | 来源于 UART SpO2 模块，是睡眠分类的主要输入 |
| 姿态数据 | `accel_x/y/z`、`gyro_x/y/z`、`mag_x/y/z` | 来源于 JY901，用于体动分析和状态展示 |
| 翻身数据 | `turnover_flag`、`turnover_count` | 由板端基于 roll/pitch 变化阈值计算 |
| 环境数据 | `temperature_c`、`humidity_percent`、`env_valid` | 来源于 DHT11，也用于 PC 舒适度策略 |
| 质量标志 | `data_valid`、`imu_valid`、`imu_stale`、`checksum_ok`、`status_code` | 区分“可分类样本”和“局部传感器异常” |
| 调试状态 | `jy901_status`、`jy901_attempts`、`remark` | 便于端到端测试时定位单个模块问题 |

### 3.2.3 本地显示与执行器控制

板端 TFT 显示用于课堂演示和脱离 PC 时的基本观察。软件采用固定区域局部刷新方式，避免每秒全屏重绘造成明显闪烁。显示内容包括心率、血氧、翻身次数、温湿度、当前睡眠状态摘要和最近一次控制状态。PC 端仍是完整 dashboard，本地 TFT 只保留关键运行值。

执行器控制由 PC 端下发 `control_command` 后在 PYNQ 侧执行。板端只接受经过协议校验的目标，且不会把 `sleep_result` 直接解释成硬件动作。当前支持两类执行器：

1. 加湿器目标状态：`humidifier.enabled=true/false`，板端写入加湿器 IP 并读取执行后的状态。
2. IR 空调一次性命令：`ir_ac.command`，板端把命令映射为已验证的 preset，并触发红外发送。

IR 空调控制额外加入两类保护。第一类是最小发送间隔，避免连续红外波形过密；第二类是重复命令冷却，避免 dashboard 或自动策略在短时间内重复发送同一空调命令。由于红外链路没有真实状态反馈，`sent=true` 只表示 PYNQ 已完成红外波形发送，不代表空调一定接收成功。最终实物验证仍需要观察空调响应。

板端执行结果统一组织为 `control_status`。

| `status_code` | 含义 | 典型原因 |
|---:|---|---|
| `0` | 正常处理 | 命令被接受并执行，或合法 no-action |
| `1` | 拒绝 | 命令 schema 无效、target 非法或 sample 不匹配 |
| `2` | 跳过 | no-action、IR cooldown、缺少硬件或当前不适合执行 |
| `3` | 硬件错误 | IP 返回 error、发送超时或执行器驱动异常 |

### 3.2.4 Socket 客户端通信设计

板端 socket 客户端连接 PC 的真实 IPv4 地址和固定端口，传输格式为换行分隔 JSON。每个采样周期中，板端先发送一条 `sensor_data`，然后等待 PC 端按顺序返回 `sleep_result` 和 `control_command`。只有两条消息的 `sample_id` 与当前采样匹配时，板端才执行控制命令；如果超时、消息格式错误或 sample 不匹配，则本轮跳过控制，并继续下一轮采样。

通信状态机可概括为：

```text
CONNECT
 -> SEND sensor_data
 -> WAIT sleep_result
 -> WAIT control_command
 -> APPLY 或 SKIP command
 -> SEND control_status
 -> NEXT SAMPLE
```

当 PC 服务不可达或连接断开时，板端客户端按固定间隔重试连接，而不是退出整个采样程序。这样在课堂演示中可以先启动 PYNQ 或先启动 PC，系统最终都能进入稳定闭环。程序停止时会关闭 socket，并保留最后的终端输出作为演示证据。

### 3.2.5 板端软件测试设计

PYNQ 板端软件测试分为可在 PC 环境运行的逻辑自测和真实 PYNQ 板级测试两类。逻辑自测使用 fake driver 或 localhost socket，验证采样字典形状、JY901 重试策略、no-action 命令、加湿器 target、IR cooldown、命令拒绝路径和 socket loopback，不作为真实硬件证据。真实板级测试则需要加载最终 overlay，读取实际传感器，刷新 TFT，并与 PC 服务完成四消息闭环。

该划分的好处是：协议和控制逻辑可以在没有板卡时快速回归；真实硬件测试则集中验证驱动绑定、外设接线、传感器读数和执行器响应。第四章系统测试部分给出最终板级和端到端验收结果。

## 3.3 PC 端服务与可视化设计（撰写人：待填）

PC 端服务负责接收 PYNQ 上传的结构化采样数据，执行睡眠状态分类，依据舒适度策略生成设备控制命令，保存四类运行记录，并向 dashboard 提供实时可视化。PC 端不直接访问硬件寄存器，也不绕过主 socket loop 直接控制设备；所有自动或手动控制都必须通过 `control_command` 下发，再由 PYNQ 返回 `control_status`。

![图3-12 PC 端服务模块设计图：协议校验、服务编排、分类器适配、舒适度策略、状态管理、JSONL 存储和 dashboard](assert/fig3-12-pc-service-module-design.svg)

### 3.3.1 模块划分

PC 端服务采用分层组合方式，各模块职责如下。

| 模块 | 输入 | 输出 | 设计职责 |
|---|---|---|---|
| 协议模块 | socket 字节流或消息字典 | 校验后的四类消息 | 处理 newline JSON 编解码、字段检查、消息类型检查和错误报告 |
| 分类器适配模块 | `sensor_data` | `sleep_result` | 包装睡眠分类模型，保证输出 schema 稳定，异常时返回 invalid result |
| 睡眠分类模型 | 心率、血氧、体动、历史窗口 | 睡眠状态编号 | 基于轻量 DREAMT GRU 推理，输出清醒、浅睡或深睡状态 |
| 舒适度策略模块 | `sensor_data`、`sleep_result`、运行状态 | `control_command` | 根据温湿度、睡眠状态、手动命令和 cooldown 生成执行器目标 |
| 状态管理模块 | 四类消息和 UI 操作 | 最新状态快照 | 维护 active client、latest records、pending manual command、控制历史和显示用目标状态 |
| 持久化存储模块 | 四类规范消息 | JSONL 记录流 | 分别保存原始采样、分类结果、控制命令和执行状态 |
| Socket 服务模块 | PYNQ TCP 连接 | 双向四消息闭环 | 对每条 `sensor_data` 返回 `sleep_result` 和 `control_command`，并接收 `control_status` |
| Dashboard 模块 | 状态快照和用户操作 | Web 页面与手动命令 | 展示实时数据、分类、控制状态和手动控制入口 |

这种划分避免把协议、模型、策略、存储和 UI 混在一个大循环中。即使分类模型失败或策略生成 no-action，socket 服务仍能按协议返回合法消息，保证 PYNQ 客户端不会因为 PC 内部异常而卡死。

### 3.3.2 协议层与服务主循环

PC 服务监听固定 TCP 端口，第一版只支持一个 active PYNQ client。传输层使用 UTF-8 newline JSON，每条消息以 `\n` 结束，解决 TCP 字节流没有天然消息边界的问题。协议层会校验四种消息：

1. `sensor_data`：PYNQ 上传的原始采样。
2. `sleep_result`：PC 输出的睡眠分类结果。
3. `control_command`：PC 输出的设备控制目标。
4. `control_status`：PYNQ 回传的执行结果。

每一轮服务主循环严格遵守以下顺序：

```text
接收 sensor_data
 -> 协议校验并记录原始采样
 -> 调用分类器适配模块生成 sleep_result
 -> 调用舒适度策略模块生成 control_command
 -> 依次发送 sleep_result 和 control_command
 -> 接收 PYNQ 回传的 control_status
 -> 更新状态并写入存储
```

即使自动策略决定不动作，PC 端也发送合法的 no-action `control_command`，其中 `targets` 为空并给出 `reason`。这样 PYNQ 端无需依赖“没有收到命令”这种隐式状态判断，协议时序更稳定。

### 3.3.3 睡眠分类适配设计

睡眠分类模块的输入来自 `sensor_data`，主要包括心率、血氧、体动强度、时间序列历史和数据有效标志。分类器适配层负责把板端数据转换为模型需要的稳定输入，并把模型输出转换为统一的 `sleep_result` 消息。

`sleep_result` 的核心字段包括：

| 字段 | 含义 |
|---|---|
| `type` | 固定为 `sleep_result` |
| `sample_id` | 回显对应输入采样 |
| `sleep_state_code` | `0` 表示清醒或未入睡，`1` 表示浅睡，`2` 表示深睡 |
| `state_valid` | 分类结果是否有效 |
| `remark` | 模型置信度、warm-up 或异常说明 |

适配层的关键设计是“模型异常不破坏协议”。当输入字段不足、模型尚未 warm-up 或分类函数异常时，PC 端返回 `state_valid=0` 的 `sleep_result`，并在后续策略中生成 no-action `control_command`。此外，JY901 单独瞬态失败不应强制心率/血氧主链路失效，避免体动模块偶发错误导致分类历史被不必要清空。

### 3.3.4 舒适度策略设计

舒适度策略模块根据 `sensor_data`、`sleep_result` 和当前运行状态生成 `control_command`。策略输出只表达期望执行器目标，不直接控制硬件。第一版策略包含自动模式和手动模式。

自动模式规则如下：

1. 如果 `state_valid != 1` 或关键传感器数据缺失，则输出 no-action。
2. 湿度低于约 40% RH 时，生成 `humidifier.enabled=true`。
3. 湿度高于约 60% RH 时，生成 `humidifier.enabled=false`。
4. 温度高于当前睡眠状态对应舒适区时，生成 `temp_26`、`temp_25` 或 `temp_24` 等空调命令。
5. 温度低于舒适区时，生成 `temp_27` 或 `temp_28` 等空调命令。
6. 处于舒适区或受 cooldown 限制时，输出 no-action 并说明原因。

不同睡眠状态使用不同策略强度。清醒或未入睡时可以更主动调整；浅睡时适中；深睡时舒适区更宽，以减少红外空调和加湿器动作对睡眠的干扰。

手动模式由 dashboard 设置 pending command，但不会从 HTTP 请求处理流程直接写 socket。下一条 `sensor_data` 到达时，PC 服务把 pending command 转换成合法的 `control_command(mode="manual")` 下发。空调命令是 one-shot 红外动作，发送后清除；加湿器命令是目标状态，可持续显示在 dashboard 上。

### 3.3.5 状态管理、存储与 Dashboard

状态管理模块维护服务运行时的最新状态，包括 active client、最近一轮 `sensor_data`、`sleep_result`、`control_command`、`control_status`、pending manual command、控制历史和 display-only desired-state。该状态用于 dashboard 刷新，也用于舒适度策略判断 IR cooldown 和手动命令是否已经消费。

持久化存储采用四类 JSONL 记录流：

| 记录流 | 内容 | 作用 |
|---|---|---|
| `sensor_data` | 原始板端采样 | 保留未处理输入，便于复现实验 |
| `sleep_result` | 分类输出 | 记录模型对每个 sample 的判断 |
| `control_command` | PC 下发的控制目标 | 记录自动策略或手动控制的决策 |
| `control_status` | PYNQ 回传执行结果 | 记录命令是否 accepted、skipped、sent 或 error |

四类记录分开保存，可以避免把原始传感器数据、模型输出、控制决策和执行结果混在同一结构中。后续做图表、问题定位或报告截图时，可以按同一 `sample_id` 关联四类消息。

Dashboard 展示内容包括连接状态、实时心率/血氧/体动/温湿度、睡眠状态、最新控制命令、PYNQ 执行状态、控制历史、pending manual command 和显示用目标状态。Dashboard 的手动按钮只创建下一轮待发送命令，不直接绕过 socket 主循环，因此最终演示中的控制路径和日志记录路径保持一致。

### 3.3.6 PC 端软件测试设计

PC 端软件测试采用自底向上的方式覆盖主要模块：

1. 协议测试：校验四种消息的编码、解码、字段缺失、非法 target、no-action 和 rejected-status。
2. 分类器适配测试：校验有效分类、模型异常降级、输入无效和 JY901-only 失败不破坏 HR/SpO2 主链路。
3. 舒适度策略测试：覆盖分类无效、湿度低/高、温度高/低、手动 pending、IR cooldown 和 no-action。
4. 状态与存储测试：验证 latest records、pending manual command、控制历史和四类 JSONL 写入。
5. 服务组合测试：对一条 `sensor_data` 生成 `sleep_result` 和 `control_command`，并记录 `control_status`。
6. Socket 与 dashboard 测试：使用模拟板端客户端完成四消息 loopback，验证 dashboard 页面和静态资源可加载。

这些 PC-only 测试证明协议、分类、策略、状态、存储和 dashboard 逻辑可以独立运行；真实板端 socket 测试和端到端验收结果在第四章说明。

---

## 四、系统集成及测试

本章说明各自定义 IP 如何集成为完整的睡眠监测辅助系统，并给出硬件、软件和系统功能测试证据。系统采用 PYNQ-Z1/Zynq-7000 平台，PL 侧负责传感器和执行器的时序接口，PS 侧负责数据读取、显示刷新、PC 通信和控制命令执行，PC 侧负责睡眠状态分类、舒适度策略、数据存储和 dashboard 显示。

![图4-1 最终系统实物场景照片：PYNQ-Z1、JY901、DHT11、SpO2、TFT、加湿器 LED、IR 发射器和 PC dashboard](assert/fig4-1-final-system-photo.png)

### 4.1 系统集成总体架构

系统分为三层：

1. PL 自定义 IP 层：包括 JY901 I2C、DHT11 单总线、UART SpO2、TFT SPI、加湿器/LED 控制和 Gree IR 空调发射 IP。每个 IP 均通过 AXI4-Lite 暴露寄存器接口。
2. PYNQ 板端软件层：加载最终集成硬件平台及匹配硬件描述，绑定各 IP 驱动，周期读取传感器，更新 TFT，并通过 socket 与 PC 服务交换 JSON 消息。
3. PC 服务层：接收 PYNQ 上传的 `sensor_data`，调用睡眠分类适配器，生成 `sleep_result`，根据舒适度策略或 dashboard 手动控制生成 `control_command`，记录 PYNQ 返回的 `control_status`。

系统运行时的核心闭环为：

```text
PYNQ 读取传感器
 -> 生成 sensor_data
 -> PC 分类得到 sleep_result
 -> PC 策略生成 control_command
 -> PYNQ 执行或跳过控制命令
 -> PYNQ 返回 control_status
 -> PC 存储和 dashboard 显示
```

![图4-2 系统软硬件总体框图：PL 自定义 IP、PYNQ Python 和 PC service/dashboard 三层结构](assert/fig4-2-system-architecture.svg)

### 4.2 硬件集成

最终硬件平台为 Vivado 集成 overlay。Block Design 中 Zynq Processing System 通过 `M_AXI_GP0` 连接 AXI Interconnect，再挂接所有自定义 AXI4-Lite IP。各 IP 共享 PS 输出的 FCLK 和复位网络，外部传感器/执行器端口通过 XDC 约束连接到 PYNQ-Z1 板卡引脚。

集成后的 AXI 地址分配如下。

| IP 实例 | 基地址 | 范围 | 功能 |
|---|---:|---:|---|
| `axi_i2c_jy901_v1_0_0` | `0x4000_0000` | 4 KB | JY901 I2C 运动数据采集 |
| `axi_humidifier_v1_0_0` | `0x4000_1000` | 4 KB | 加湿器/LED 控制 |
| `tft_lcd_spi_axi_v1_0_0` | `0x4000_2000` | 4 KB | TFT LCD SPI 显示 |
| `dht11_axi_v1_0_0` | `0x4000_3000` | 4 KB | DHT11 温湿度采集 |
| `axi_uart_spo2_v1_0_0` | `0x4000_4000` | 4 KB | UART 心率/血氧数据接收 |
| `gree_ir_axi_v1_0_0` | `0x4000_5000` | 4 KB | Gree 空调红外命令发射 |

最终系统外设引脚分配如下。

| 模块 | 信号 | PYNQ-Z1 引脚 | 说明 |
|---|---|---|---|
| TFT LCD | `lcd_scl` | PMODA `Y18` | SPI 时钟 |
| TFT LCD | `lcd_sda` | PMODA `Y19` | SPI MOSI |
| TFT LCD | `lcd_res` | PMODA `Y16` | LCD 复位 |
| TFT LCD | `lcd_dc` | PMODA `Y17` | 命令/数据选择 |
| TFT LCD | `lcd_blk` | PMODA `U18` | 背光 |
| JY901 | `i2c_scl` | Arduino SCL `P16` | 3.3 V I2C，上拉 |
| JY901 | `i2c_sda` | Arduino SDA `P15` | 3.3 V I2C，上拉 |
| SpO2 | `uart_txd` | PMODB `W14` | 与外部模块 RX/TX 交叉连接 |
| SpO2 | `uart_rxd` | PMODB `Y14` | 与外部模块 RX/TX 交叉连接 |
| DHT11 | `dht11_0` | Arduino IO11 `R17` | 单总线，上拉 |
| 加湿器/指示 | `humidifier_leds[3:0]` | 板载 LED `R14/P14/N16/M14` | 课程演示中用 LED 表示执行状态 |
| IR 空调 | `ir_pwm` | Arduino `ck_io[0]`，`T14` | 红外发射模块输入 |

硬件安全方面，所有接入 PL 的信号均按 3.3 V 逻辑处理。I2C 和 DHT11 信号需要上拉到 3.3 V，不能上拉到 5 V。红外发射器和加湿器类负载不能由 FPGA 管脚直接驱动，应使用模块输入或驱动电路。本系统演示中加湿器路径以板载 LED 表示状态，避免直接驱动外部负载。

![图4-3 Vivado Block Design 截图：Zynq PS、AXI Interconnect 和六个自定义 AXI-Lite IP](assert/fig4-3-vivado-block-design.png)

![图4-4 最终接线照片：JY901、DHT11、SpO2、TFT、IR 发射器和板载 LED 连接位置](assert/fig4-4-final-wiring-photo.png)

Vivado 构建验证结果显示，最终集成硬件平台已导出匹配的 bitstream、硬件描述和设计重建脚本。静态验证中，IR AC IP 已加入硬件描述和 Block Design Tcl，`ir_pwm` 端口已导出并约束到 `T14`。路由后 DRC 报告为 0 violation，route status 无 routing error，时序摘要显示没有 setup、hold 和 pulse-width 失败端点，bitstream 生成成功。方法学报告仍存在低速外设端口缺少 input/output delay 的 `TIMING-18` 警告，这些警告对首次板级 smoke 不构成阻塞，但说明外部低速接口尚未建立完整时序模型。

### 4.3 软件集成

PYNQ 端软件作为最终集成入口，负责加载 overlay 和绑定驱动。板端编排模块统一完成采样、显示更新、加湿器目标执行、IR 空调命令执行和 `control_status` 生成；板端 socket 客户端负责与 PC 服务通信。

PYNQ 端每次采样生成一个 `sensor_data` 字典，主要字段包括：

| 字段组 | 内容 |
|---|---|
| 生理数据 | `heart_rate_bpm`、`spo2_percent`、`spo2_valid` |
| 体动数据 | `accel_x/y/z`、`gyro_x/y/z`、`mag_x/y/z`、`turnover_flag`、`turnover_count` |
| 环境数据 | `temperature_c`、`humidity_percent`、`env_valid` |
| 质量标志 | `data_valid`、`imu_valid`、`imu_stale`、`checksum_ok`、`status_code` |
| 调试信息 | `jy901_status`、`jy901_attempts`、`remark` |

PC 端软件以 dashboard 服务为课堂演示入口，内部按协议、分类器适配、舒适度策略、状态存储、持久化存储和 dashboard 静态资源拆分。PC 收到 `sensor_data` 后，先生成 `sleep_result`，再生成 `control_command`。PYNQ 执行或跳过控制后返回 `control_status`。四类记录分别存储，避免把原始传感器数据、模型输出和控制执行结果混在同一张表中。

系统 socket 协议采用换行分隔 JSON。每个采样周期严格遵守以下顺序：

```text
PYNQ -> PC: sensor_data
PC -> PYNQ: sleep_result
PC -> PYNQ: control_command
PYNQ -> PC: control_status
```

其中 `sleep_result` 只表示睡眠状态分类结果，不承载控制动作；设备控制统一通过 `control_command` 表达。`control_command` 可以包含 `ir_ac.command` 和 `humidifier.enabled` 两类目标。PYNQ 端会进行命令合法性检查、IR 最小间隔保护和重复命令冷却保护，并在 `control_status` 中报告 accepted、skipped、sent、error 等结果。

![图4-5 PC/PYNQ 软件流程图：sensor_data、sleep_result、control_command、control_status 四消息闭环](assert/fig4-5-pc-pynq-four-message-flow.svg)

PC 端服务内部进一步分为协议解析、分类器适配、舒适度策略、状态存储、持久化存储和 dashboard 展示几个部分。PYNQ 端板端客户端则把硬件采样、消息收发、命令执行和执行状态回传串成一个顺序流程，保证每个 `sample_id` 都能对应到同一轮 `sensor_data`、`sleep_result`、`control_command` 和 `control_status`。

![图4-6 PC 端服务内部处理流水线：协议解析、分类器适配、舒适度策略、存储和 dashboard](assert/fig4-6-pc-server-pipeline.svg)

![图4-7 PYNQ 板端客户端顺序流程图：采样、发送、接收、执行和回传 control_status](assert/fig4-7-board-client-sequence.svg)

### 4.4 系统功能测试

系统测试按“模块仿真、IP 封装、Vivado 集成、PYNQ 本地板级 smoke、PC/PYNQ 软件闭环”逐层进行。这样可以在最终演示失败时快速定位是单个 IP、外设接线、overlay metadata、socket 网络还是 PC 策略问题。

![图4-8 系统测试分层流程图：模块仿真、IP 封装、Vivado 集成、PYNQ 板级 smoke 和端到端验收](assert/fig4-8-system-test-layered-flow.svg)

#### （1）模块级测试

已记录的模块级测试包括：

| 模块 | 测试方式 | 结果/范围 |
|---|---|---|
| JY901 I2C | Icarus 行为仿真 | burst read、address NACK、AXI 顶层路径、timeout 路径均有 PASS 期望 |
| DHT11 | Icarus 行为仿真 | 有效帧解码，例如 55% RH、25 C |
| TFT LCD SPI | Icarus 行为仿真 | SPI byte transmitter 和 AXI wrapper byte-send 路径 PASS |
| UART SpO2 | 帧解析仿真 | 5 字节和 7 字节已知帧解析 PASS |
| 加湿器 | 核心和 AXI 仿真 | 阈值、手动模式和 AXI 寄存器路径 PASS |
| Gree IR AC | Icarus 行为仿真 | 七个 preset、start/done/error、W1C 清状态、busy 时重复 start 错误路径 PASS |

![图4-9 各模块仿真 PASS 截图：JY901、DHT11、TFT、SpO2、加湿器和 IR AC 模块级测试](assert/fig4-9-module-simulation-pass-summary.png)

#### （2）Vivado 集成构建测试

Vivado 集成测试检查 Block Design 内容、地址映射、外部端口、XDC 引脚、DRC、route status、timing summary 和 bitstream 导出。第一阶段验证了 JY901、DHT11、SpO2、TFT 和加湿器的集成；第二阶段在此基础上加入 TX-only Gree IR AC IP，并导出匹配的 bitstream、硬件描述和设计重建脚本。

集成构建通过标准包括：

1. BD validate 通过，所有目标 IP 均在设计中。
2. 地址映射与软件静态 fallback 表一致。
3. 外部端口与 XDC 引脚对应。
4. routed DRC 无 violation。
5. route status 无 routing error。
6. timing summary 无 setup/hold/pulse-width 失败端点。
7. bitstream 写出成功，并导出与之匹配的硬件描述。

![图4-10 Vivado Address Editor 或 HWH 地址映射截图：0x40000000 到 0x40005000 的集成 IP 地址](assert/fig4-10-vivado-address-map.png)

#### （3）PYNQ 本地集成板级测试

PYNQ 本地集成测试直接加载集成 overlay，读取各传感器并更新 TFT，不依赖 PC socket。已有板级 smoke 结果显示：

1. TFT 初始化并能更新显示内容。
2. JY901 返回有效样本，`jy901_status="OK"`，IMU 字段可读。
3. DHT11 返回温度和湿度，例如约 `26.0 C`、`22..24% RH`。
4. UART SpO2 在修正 RX/TX 物理接线方向后返回有效 5 字节/polling 样本，例如心率约 `86..87`、血氧 `99`。
5. 加湿器/LED 控制参与循环，在低湿度条件下报告 `humidifier_on=true`。
6. 集成循环输出 JSON-compatible `sensor_data`，没有模块异常导致主循环退出。

该测试证明多 IP 能在同一 overlay 中被 PYNQ 驱动读取和更新。早期 smoke 阶段中的板上系统时间曾不正确，正式最终演示已按实际演示流程保留 dashboard、PYNQ 终端和记录文件材料。翻身计数不以早期 smoke 输出为准，而以最终演示中 `turnover_flag` 和 `turnover_count` 的变化作为验收依据。

![图4-11 PYNQ 本地集成输出截图：JY901、DHT11、SpO2 和 humidifier 字段](assert/fig4-11-pynq-integrated-demo-output.png)

![图4-12 TFT 实时显示照片：心率、血氧、翻身次数、温湿度和控制状态更新](assert/fig4-12-tft-live-dashboard-photo.png)

#### （4）IR 空调控制测试

TX-only Gree IR AC IP 在最终集成硬件平台中集成，基地址为 `0x4000_5000`。PYNQ 通过板端红外控制驱动写入 preset 并触发发送。已有板级 smoke 结果显示，发送 `temp_26` 后寄存器状态为 `busy=false`、`done=true`、`error=false`、`preset=5`、`raw_status=2`。最终实物验证中，真实实验室 Gree 空调对 `power_on`、`power_off` 和 `temp_26` 有响应。

需要在报告中说明：IP 的 `done=true` 只能证明红外波形发送完成，不能证明空调真实接收；真实接收依赖发射器角度、距离和空调接收窗位置。本次实验中红外发射器需要放在距离接收窗约 20 cm 内才能可靠响应。

![图4-13 IR AC PYNQ 输出截图：done true、error false 和 command temp_26](assert/fig4-13-ir-ac-pynq-output.png)

![图4-14 IR 发射器对准空调接收窗照片：约 20 cm 距离下验证 power_on、power_off 或 temp_26 响应](assert/fig4-14-ir-transmitter-ac-response-photo.png)

#### （5）PC/PYNQ 软件闭环测试

PC/PYNQ 软件闭环按以下层次测试：

1. PC 本地自测：覆盖协议编解码、睡眠分类适配、舒适度策略、状态存储、服务组合、socket 服务、模拟板端客户端和 dashboard 页面加载等内容。
2. PYNQ 端可在 PC 环境运行的自测：使用 fake driver 或 localhost socket 验证板端采样字典、编排逻辑和通信协议形状，不作为真实板级证据。
3. PC-only socket smoke：fake PYNQ client 发送 `sensor_data`，PC 返回 `sleep_result` 和 `control_command`，fake client 返回 `control_status`。
4. 真实 PYNQ socket 运行：PYNQ 发送板端 `sensor_data`，PC 保存四类 JSONL 记录，dashboard 显示最新传感器、分类、控制命令和执行状态。

软件集成测试包括一次 90-sample 真实 PYNQ socket 运行，生成了匹配的 `sensor_data`、`sleep_result`、`control_command`、`control_status` 流；另有 dashboard 加模拟板端客户端的 smoke 测试完成 10 个四消息周期，并验证页面和静态资源可正常加载。最终演示采用 PC 端 dashboard 服务和真实 PYNQ 板端客户端的完整闭环，已经完成端到端验收；对应证据材料包括 PC dashboard、PYNQ stdout 和 JSONL 记录文件截图。

![图4-15 PC dashboard 页面截图：实时传感器数据、睡眠状态、控制命令、执行状态和 desired-state 区域](assert/fig4-15-pc-dashboard-final-demo.png)

![图4-16 四类 JSONL 记录文件截图：sensor_data、sleep_result、control_command 和 control_status 同一 sample_id 记录](assert/fig4-16-jsonl-four-record-streams.png)

### 4.5 功能演示结果汇总

系统功能与测试结果可汇总如下。

| 功能 | 实现方式 | 测试结果 | 证据材料 |
|---|---|---|---|
| 体动/姿态采集 | JY901 I2C IP + PYNQ MMIO | 已有仿真和板级采样证据，姿态数据可读 | JY901 单模块输出或集成输出截图 |
| 温湿度采集 | DHT11 AXI IP | 集成 smoke 中可读温湿度 | PYNQ 输出截图 |
| 心率/血氧采集 | UART SpO2 AXI IP | 修正 RX/TX 接线后可读 BPM/SpO2 | PYNQ 输出截图和接线说明 |
| 本地显示 | TFT LCD SPI AXI IP | TFT 初始化并更新数值 | TFT 照片 |
| 加湿器状态/控制 | AXI humidifier IP | 低湿度时 LED/状态参与循环 | LED 照片或 JSON 输出 |
| 空调红外控制 | Gree IR AC TX IP | `power_on`、`power_off`、`temp_26` 实验室空调响应已确认 | IR 输出截图和实物照片 |
| PC 分类与策略 | PC 分类适配器 + 舒适度策略 | PC 自测和 socket smoke 通过 | 自测 PASS、dashboard 截图 |
| 数据记录 | JSONL 四消息记录 | 已有真实 PYNQ socket 运行和模拟客户端 dashboard 运行 | JSONL 文件截图 |
| 端到端闭环 | PYNQ 板端客户端 + PC dashboard 服务 | 最终演示已验收通过 | dashboard + PYNQ stdout + JSONL 同步截图 |

### 4.6 已知问题与改进方向

1. PYNQ 板上系统时间曾出现错误时间戳。正式采集 PC 日志和 dashboard 截图前，应先在板端校准系统时间，否则记录文件中的时间不适合直接作为报告证据。
2. 早期集成 smoke 阶段未做翻身计数专项测试，因此该阶段输出中的 `turnover_count` 为 0；最终演示已验证翻身计数通过，报告证据以最终演示截图为准。
3. 部分旧版 PYNQ 运行环境可能无法正确解析硬件描述，当前软件提供静态地址表 fallback。报告中可写这是兼容旧板卡镜像的工程处理，但最终验收仍应尽量保留同名匹配的 bitstream、硬件描述和设计导出文件。
4. IR 空调控制没有真实状态反馈。`control_status.ir_ac.sent=true` 只能说明 PYNQ 发送波形且 IP 完成，不代表空调一定接收。报告中应把“发送成功”和“人工观察到空调响应”分开表述。
5. 外部低速端口尚未建立完整 input/output delay 约束。Vivado 构建已满足内部时序并能上板 smoke，但若后续追求更规范的工程交付，应补充外设时序约束或说明低速异步外设的约束策略。

![图4-17 最终演示证据拼图：PC dashboard、PYNQ 终端、TFT 显示和实物系统照片](assert/fig4-17-final-demo-evidence-collage.png)
