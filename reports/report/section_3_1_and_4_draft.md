# 报告正文草稿：3.1 I2C JY901 模块设计与第四章系统集成及测试

> 使用说明：本文件是为了复制到 `report-template-with-cover.docx` 的正文材料，不尝试复刻 Word 样式。复制到 Word 后，请按模板统一字体、字号、分页、图题和表题。
>
> 正文中的图片统一按 `![材料描述及图名](assert/xxx)` 形式插入。当前 `assert/` 为报告素材目录名；已有可复用图像已从 `reports/gzh/diagrams/` 复制到 `reports/report/assert/`。现有 Mermaid 渲染图保留为 SVG，真实照片、终端截图和 dashboard 截图仍以 PNG 文件名占位。

## 已确认写作口径

1. 3.1 尊重完整的 I2C JY901 单模块路径。

   本节按“协议分析、RTL/IP 设计、AXI 寄存器、Vivado IP 封装、单模块仿真、单模块 PYNQ overlay/CLI、JY901 上板读取、翻身检测接口”展开。最终 `system_v0_2` 只作为第四章系统集成口径，不压缩 3.1 的单模块工作量。

2. 翻身检测可以宣称最终演示验证通过。

   上轮提到的“集成日志”指 `docs/test_plan.md` 中 2026-06-09 的 Phase5 Integrated Board Runtime Smoke。该日志验证了 JY901、DHT11、SpO2、TFT 和加湿器的集成读取/显示路径，但当时未做翻身计数专项动作，所以日志中的 `turnover_count` 为 0。现在报告按最终演示效果口径写：翻身计数已通过验证，图片材料以最终演示截图/视频帧补入。

3. 第四章可以宣称完整端到端系统已经最终验收。

   第四章按最终演示路径 `system_v0_2 overlay -> PYNQ board_client.py -> PC dashboard_server.py` 描述，写明 PYNQ 采集、TFT 显示、PC dashboard、JSONL 记录、睡眠分类、控制命令和执行状态闭环已验收通过。

4. 缺失图像按 Markdown 图片占位写入。

   正文中不使用“占位要求”方括号，统一插入 `![对应的材料描述及名称](assert/xxx)`。已有 Mermaid/PPT 展示图优先复用 `reports/gzh/diagrams/` 下的素材，例如 `i2c_jy901_arch.png`、`pynq_integration_flow.mmd.svg`、`pc_server_pipeline.mmd.svg`、`four_message_protocol.mmd.svg` 和 `board_client_sequence.mmd.svg`。

---

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

![图3-1 I2C JY901 单模块完整路径图：JY901、I2C 自定义 IP、AXI4-Lite、PYNQ MMIO 驱动、单模块测试和翻身检测接口](assert/fig3-1-jy901-single-module-path.svg)

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

核心寄存器表如下，完整寄存器定义见工程文档 `docs/register_map.md`。

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

在最终 `system_v0_2` 集成 overlay 中，JY901 IP 的 AXI 基地址为 `0x4000_0000`，地址范围为 4 KB。独立 JY901 调试 overlay 曾使用 `0x43C0_0000` 和 64 KB 范围，该地址只用于单模块 bring-up，不作为最终系统集成地址。

最终集成系统的板级约束中，JY901 使用 Arduino SCL/SDA：

| 信号 | PYNQ-Z1 引脚 | 说明 |
|---|---|---|
| `i2c_scl` | Arduino SCL `P16` | 3.3 V I2C，上拉到 3.3 V |
| `i2c_sda` | Arduino SDA `P15` | 开漏数据线，上拉到 3.3 V |

早期 JY901 独立 overlay 和 PL-only debug top 可使用 PMODA `Y17/Y16`。最终系统中 PMODA 已分配给 TFT LCD，因此报告第四章应以 Arduino `P16/P15` 作为最终集成接线。

![图3-4 Vivado 封装后的 axi_i2c_jy901_v1_0 IP 符号截图：S_AXI、时钟复位和 i2c_scl/i2c_sda 外部端口](assert/fig3-4-vivado-jy901-ip-symbol.png)

### 3.1.2 软件设计

PYNQ 侧软件的目标是把 AXI 寄存器访问封装成稳定的传感器读数接口，并把 JY901 数据接入系统采样字典。软件分为两个层次：

1. 单模块驱动 `pynq/jy901_demo/jy901_driver.py`，用于 JY901 独立 overlay 的课堂演示和调试。
2. 集成系统驱动绑定与采样逻辑 `pynq/sleep_demo/integrated_demo.py`、`board_orchestrator.py`，用于最终 `system_v0_2` 多 IP overlay。

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

在最终集成软件中，`integrated_demo.py` 会加载 `system_v0_2.bit`，通过 `.hwh` metadata 或旧 PYNQ 镜像上的静态地址表绑定所有 IP。JY901 读数由 `read_jy901()` 完成。该函数支持短暂重试和 stale cache：如果单次 JY901 读取失败，但上一次有效数据仍在允许时间内，系统可标记 `imu_stale=1` 并继续让 HR/SpO2 分类链路工作，避免一次 IMU 瞬态失败重置整个 PC 分类 warm-up。

翻身检测放在 PS 侧 `TurnCounter` 中，而不是放进 PL IP。当前第一版逻辑使用 roll/pitch 变化阈值，默认阈值为 `35.0` 度。这样做的原因是翻身动作判断和防抖策略更接近应用层，后续可以调整阈值、加入冷却时间或融合加速度变化，而不需要重新生成 bitstream。

![图3-5 JY901 PYNQ 软件读取流程图：配置寄存器、启动采样、轮询状态、读取 raw、换算和更新 sensor_data](assert/fig3-5-jy901-pynq-driver-flow.svg)

### 3.1.3 模块测试

JY901 模块按仿真、单模块上板和集成上板三个层次验证。

#### （1）行为仿真

仿真位于 `sim/tb_i2c_mpu9250/`，使用 Icarus Verilog。仿真包含 JY901 I2C slave model，可以验证 I2C 正常 burst read、地址 NACK、AXI 顶层寄存器路径和 timeout 路径。

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

单模块测试使用 `pynq/jy901_demo/` 下的 `demo_cli.py`。测试路径为：下载独立 JY901 bitstream，创建 direct MMIO，检查 `VERSION`，启动一次 oneshot，随后周期性读取并打印 scaled 数据。该路径不依赖 `.hwh` metadata，适合快速排查 I2C 地址、上拉、线序和 AXI 寄存器问题。

通过标准为：

1. `VERSION` 读回 `0x4A593101`。
2. 初始 oneshot 后 `SAMPLE_CNT` 增加。
3. `STATUS.ack_error=0`，`STATUS.timeout=0`。
4. 连续输出数据表格时 `SAMPLE_CNT` 持续增加。
5. 手动移动或旋转 JY901 模块时，加速度和 roll/pitch/yaw 数值有相应变化。

![图3-8 JY901 单模块 PYNQ CLI 输出截图：VERSION PASS、SAMPLE_CNT、STATUS OK 和姿态数据变化](assert/fig3-8-jy901-single-module-cli-pass.png)

#### （3）集成系统测试

在集成 overlay 测试中，JY901 IP 作为 `system_v0_2` 的一部分挂接在 AXI 地址 `0x4000_0000`。PYNQ `integrated_demo.py` 和 `board_client.py` 通过统一驱动套件读取 JY901，并把结果写入 `sensor_data` 字段：

| 字段 | 来源 |
|---|---|
| `accel_x/y/z` | JY901 加速度换算值 |
| `gyro_x/y/z` | JY901 角速度换算值 |
| `mag_x/y/z` | JY901 磁场 raw count |
| `turnover_flag` | PS 侧阈值判断结果 |
| `turnover_count` | 累计翻身次数 |
| `imu_valid`、`imu_stale` | 当前 IMU 数据质量 |
| `jy901_status` | `OK`、`ERR` 或 `STALE` |

早期集成板级 smoke 记录见 `docs/test_plan.md` 的 2026-06-09 Phase5 Integrated Board Runtime Smoke。该记录证明 JY901 在集成 overlay 中能返回有效样本，`jy901_status="OK"` 且 `data_valid=1`，但当时没有进行翻身计数专项动作，所以共享日志中的 `turnover_count` 为 0。最终演示中已通过手动改变 JY901 姿态验证翻身检测效果，roll/pitch 明显变化时 `turnover_flag` 置位，`turnover_count` 累计增加，说明 JY901 单模块采集数据已能支撑系统体动/翻身检测功能。

![图3-9 集成系统中 JY901 字段的 JSON 输出截图：jy901_status、imu_valid、accel、gyro 和 turnover 字段](assert/fig3-9-integrated-jy901-json-fields.png)

![图3-10 最终演示翻身计数验证截图：旋转 JY901 前后 turnover_flag 置位且 turnover_count 增加](assert/fig3-10-final-demo-turnover-pass.png)

---

## 四、系统集成及测试

本章说明各自定义 IP 如何集成为完整的睡眠监测辅助系统，并给出硬件、软件和系统功能测试证据。系统采用 PYNQ-Z1/Zynq-7000 平台，PL 侧负责传感器和执行器的时序接口，PS 侧负责数据读取、显示刷新、PC 通信和控制命令执行，PC 侧负责睡眠状态分类、舒适度策略、数据存储和 dashboard 显示。

![图4-1 最终系统实物场景照片：PYNQ-Z1、JY901、DHT11、SpO2、TFT、加湿器 LED、IR 发射器和 PC dashboard](assert/fig4-1-final-system-photo.png)

### 4.1 系统集成总体架构

系统分为三层：

1. PL 自定义 IP 层：包括 JY901 I2C、DHT11 单总线、UART SpO2、TFT SPI、加湿器/LED 控制和 Gree IR 空调发射 IP。每个 IP 均通过 AXI4-Lite 暴露寄存器接口。
2. PYNQ 板端软件层：加载 `system_v0_2.bit/.hwh`，绑定各 IP 驱动，周期读取传感器，更新 TFT，并通过 socket 与 PC 服务交换 JSON 消息。
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

最终硬件平台为 Vivado 集成 overlay `system_v0_2`。Block Design 中 Zynq Processing System 通过 `M_AXI_GP0` 连接 AXI Interconnect，再挂接所有自定义 AXI4-Lite IP。各 IP 共享 PS 输出的 FCLK 和复位网络，外部传感器/执行器端口通过 XDC 约束连接到 PYNQ-Z1 板卡引脚。

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

Vivado 构建验证记录显示，`system_v0_2.bit/.hwh/.tcl` 已导出到 `vivado/gen/`。静态验证中，IR AC IP 已加入 `.hwh` 和 BD Tcl，`ir_pwm` 端口已导出并约束到 `T14`。路由后 DRC 报告为 0 violation，route status 无 routing error，时序摘要显示没有 setup、hold 和 pulse-width 失败端点，`impl_1/runme.log` 记录 bitstream 生成成功。方法学报告仍存在低速外设端口缺少 input/output delay 的 `TIMING-18` 警告，这些警告对首次板级 smoke 不构成阻塞，但说明外部低速接口尚未建立完整时序模型。

### 4.3 软件集成

PYNQ 端软件以 `pynq/sleep_demo/` 为最终集成入口。`integrated_demo.py` 负责加载 overlay 和绑定驱动；`board_orchestrator.py` 提供 `SleepMonitorBoard` 类，统一完成采样、显示更新、加湿器目标执行、IR 空调命令执行和 `control_status` 生成；`board_client.py` 负责 socket 通信。

PYNQ 端每次采样生成一个 `sensor_data` 字典，主要字段包括：

| 字段组 | 内容 |
|---|---|
| 生理数据 | `heart_rate_bpm`、`spo2_percent`、`spo2_valid` |
| 体动数据 | `accel_x/y/z`、`gyro_x/y/z`、`mag_x/y/z`、`turnover_flag`、`turnover_count` |
| 环境数据 | `temperature_c`、`humidity_percent`、`env_valid` |
| 质量标志 | `data_valid`、`imu_valid`、`imu_stale`、`checksum_ok`、`status_code` |
| 调试信息 | `jy901_status`、`jy901_attempts`、`remark` |

PC 端软件位于 `pc_server/`，以 `dashboard_server.py` 为课堂演示入口。内部按协议、分类器适配、舒适度策略、状态存储、持久化存储和 dashboard 静态资源拆分。PC 收到 `sensor_data` 后，先生成 `sleep_result`，再生成 `control_command`。PYNQ 执行或跳过控制后返回 `control_status`。四类记录分别存储，避免把原始传感器数据、模型输出和控制执行结果混在同一张表中。

系统 socket 协议采用换行分隔 JSON。每个采样周期严格遵守以下顺序：

```text
PYNQ -> PC: sensor_data
PC -> PYNQ: sleep_result
PC -> PYNQ: control_command
PYNQ -> PC: control_status
```

其中 `sleep_result` 只表示睡眠状态分类结果，不承载控制动作；设备控制统一通过 `control_command` 表达。`control_command` 可以包含 `ir_ac.command` 和 `humidifier.enabled` 两类目标。PYNQ 端会进行命令合法性检查、IR 最小间隔保护和重复命令冷却保护，并在 `control_status` 中报告 accepted、skipped、sent、error 等结果。

![图4-5 PC/PYNQ 软件流程图：sensor_data、sleep_result、control_command、control_status 四消息闭环](assert/fig4-5-pc-pynq-four-message-flow.svg)

PC 端服务内部进一步分为协议解析、分类器适配、舒适度策略、状态存储、持久化存储和 dashboard 展示几个部分。PYNQ 端 `board_client.py` 则把硬件采样、消息收发、命令执行和执行状态回传串成一个顺序流程，保证每个 `sample_id` 都能对应到同一轮 `sensor_data`、`sleep_result`、`control_command` 和 `control_status`。

![图4-6 PC server 内部处理流水线：protocol、classifier adapter、comfort policy、storage 和 dashboard](assert/fig4-6-pc-server-pipeline.svg)

![图4-7 PYNQ board_client 顺序流程图：采样、发送、接收、执行和回传 control_status](assert/fig4-7-board-client-sequence.svg)

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

Vivado 集成测试检查 Block Design 内容、地址映射、外部端口、XDC 引脚、DRC、route status、timing summary 和 bitstream 导出。`system_v0_1` 阶段验证了 JY901、DHT11、SpO2、TFT 和加湿器的集成；`system_v0_2` 阶段在此基础上加入 TX-only Gree IR AC IP，并导出匹配的 `.bit`、`.hwh` 和 `.tcl`。

集成构建通过标准包括：

1. BD validate 通过，所有目标 IP 均在设计中。
2. 地址映射与软件静态 fallback 表一致。
3. 外部端口与 XDC 引脚对应。
4. routed DRC 无 violation。
5. route status 无 routing error。
6. timing summary 无 setup/hold/pulse-width 失败端点。
7. bitstream 写出成功，并导出与之匹配的 `.hwh` metadata。

![图4-10 Vivado Address Editor 或 HWH 地址映射截图：0x40000000 到 0x40005000 的集成 IP 地址](assert/fig4-10-vivado-address-map.png)

#### （3）PYNQ 本地集成板级测试

PYNQ 本地集成测试使用 `integrated_demo.py`，直接加载 `system_v0_1` 或 `system_v0_2` overlay，读取各传感器并更新 TFT，不依赖 PC socket。已有板级 smoke 记录显示：

1. TFT 初始化并能更新显示内容。
2. JY901 返回有效样本，`jy901_status="OK"`，IMU 字段可读。
3. DHT11 返回温度和湿度，例如约 `26.0 C`、`22..24% RH`。
4. UART SpO2 在修正 RX/TX 物理接线方向后返回有效 5 字节/polling 样本，例如心率约 `86..87`、血氧 `99`。
5. 加湿器/LED 控制参与循环，在低湿度条件下报告 `humidifier_on=true`。
6. 集成循环输出 JSON-compatible `sensor_data`，没有模块异常导致主循环退出。

该测试证明多 IP 能在同一 overlay 中被 PYNQ 驱动读取和更新。早期 smoke 记录中的板上系统时间曾不正确，正式最终演示已按实际演示流程保留 dashboard、PYNQ 终端和记录文件材料。翻身计数不以早期 smoke 日志为准，而以最终演示中 `turnover_flag` 和 `turnover_count` 的变化作为验收依据。

![图4-11 PYNQ integrated_demo.py 输出截图：JY901、DHT11、SpO2 和 humidifier 字段](assert/fig4-11-pynq-integrated-demo-output.png)

![图4-12 TFT 实时显示照片：心率、血氧、翻身次数、温湿度和控制状态更新](assert/fig4-12-tft-live-dashboard-photo.png)

#### （4）IR 空调控制测试

TX-only Gree IR AC IP 在 `system_v0_2` 中集成，基地址为 `0x4000_5000`。PYNQ 通过 `demo_ir_ac.py` 写入 preset 并触发发送。已有板级 smoke 记录显示，发送 `temp_26` 后寄存器状态为 `busy=false`、`done=true`、`error=false`、`preset=5`、`raw_status=2`。用户确认真实实验室 Gree 空调对 `power_on`、`power_off` 和 `temp_26` 有响应。

需要在报告中说明：IP 的 `done=true` 只能证明红外波形发送完成，不能证明空调真实接收；真实接收依赖发射器角度、距离和空调接收窗位置。本次实验中红外发射器需要放在距离接收窗约 20 cm 内才能可靠响应。

![图4-13 IR AC PYNQ 输出截图：done true、error false 和 command temp_26](assert/fig4-13-ir-ac-pynq-output.png)

![图4-14 IR 发射器对准空调接收窗照片：约 20 cm 距离下验证 power_on、power_off 或 temp_26 响应](assert/fig4-14-ir-transmitter-ac-response-photo.png)

#### （5）PC/PYNQ 软件闭环测试

PC/PYNQ 软件闭环按以下层次测试：

1. PC 本地自测：`protocol_selftest.py`、`sleep_classifier_selftest.py`、`classifier_adapter_selftest.py`、`comfort_policy_selftest.py`、`state_storage_selftest.py`、`service_selftest.py`、`socket_service_selftest.py`、`fake_pynq_client_selftest.py`、`dashboard_server_selftest.py` 等。
2. PYNQ 端 PC-runnable 自测：`integrated_demo_selftest.py`、`board_orchestrator_selftest.py`、`board_client_selftest.py`，使用 fake driver 或 localhost socket 验证协议形状，不作为真实板级证据。
3. PC-only socket smoke：fake PYNQ client 发送 `sensor_data`，PC 返回 `sleep_result` 和 `control_command`，fake client 返回 `control_status`。
4. 真实 PYNQ socket 运行：PYNQ 发送板端 `sensor_data`，PC 保存四类 JSONL 记录，dashboard 显示最新传感器、分类、控制命令和执行状态。

已有软件集成记录包括一次 90-sample 真实 PYNQ socket 运行，生成了匹配的 `sensor_data`、`sleep_result`、`control_command`、`control_status` 流；另有 dashboard 加 fake-client smoke 完成 10 个四消息周期，并能加载 `/`、`dashboard.css` 和 `dashboard.js`。最终演示采用 PC 运行 `dashboard_server.py`、PYNQ 运行真实 `board_client.py` 的完整路径，已经完成端到端验收；报告材料中应放入 PC dashboard、PYNQ stdout 和 JSONL 记录文件截图。

![图4-15 PC dashboard 页面截图：实时传感器数据、睡眠状态、控制命令、执行状态和 desired-state 区域](assert/fig4-15-pc-dashboard-final-demo.png)

![图4-16 四类 JSONL 记录文件截图：sensor_data、sleep_result、control_command 和 control_status 同一 sample_id 记录](assert/fig4-16-jsonl-four-record-streams.png)

### 4.5 功能演示结果汇总

系统功能与测试结果可汇总如下。

| 功能 | 实现路径 | 测试结果 | 证据建议 |
|---|---|---|---|
| 体动/姿态采集 | JY901 I2C IP + PYNQ MMIO | 已有仿真和板级采样证据，姿态数据可读 | JY901 CLI 或 integrated_demo 截图 |
| 温湿度采集 | DHT11 AXI IP | 集成 smoke 中可读温湿度 | PYNQ 输出截图 |
| 心率/血氧采集 | UART SpO2 AXI IP | 修正 RX/TX 接线后可读 BPM/SpO2 | PYNQ 输出截图和接线说明 |
| 本地显示 | TFT LCD SPI AXI IP | TFT 初始化并更新数值 | TFT 照片 |
| 加湿器状态/控制 | AXI humidifier IP | 低湿度时 LED/状态参与循环 | LED 照片或 JSON 输出 |
| 空调红外控制 | Gree IR AC TX IP | `power_on`、`power_off`、`temp_26` 实验室空调响应已确认 | IR 输出截图和实物照片 |
| PC 分类与策略 | PC classifier adapter + comfort policy | PC 自测和 socket smoke 通过 | selftest PASS、dashboard 截图 |
| 数据记录 | JSONL 四消息记录 | 已有真实 PYNQ socket run 和 fake-client dashboard run | JSONL 文件截图 |
| 端到端闭环 | PYNQ board_client + PC dashboard_server | 最终演示已验收通过 | dashboard + PYNQ stdout + JSONL 同步截图 |

### 4.6 已知问题与改进方向

1. PYNQ 板上系统时间曾出现错误时间戳。正式采集 PC 日志和 dashboard 截图前，应先在板端校准系统时间，否则记录文件中的时间不适合直接作为报告证据。
2. 早期集成 smoke 日志未做翻身计数专项测试，因此该日志中的 `turnover_count` 为 0；最终演示已验证翻身计数通过，报告证据以最终演示截图为准。
3. 旧 PYNQ 镜像可能无法正确解析 `.hwh` 或 `.tcl` metadata，当前软件提供静态地址表 fallback。报告中可写这是兼容旧板卡镜像的工程处理，但最终验收仍应尽量保留 `.bit/.hwh/.tcl` 同名匹配文件。
4. IR 空调控制没有真实状态反馈。`control_status.ir_ac.sent=true` 只能说明 PYNQ 发送波形且 IP 完成，不代表空调一定接收。报告中应把“发送成功”和“人工观察到空调响应”分开表述。
5. 外部低速端口尚未建立完整 input/output delay 约束。Vivado 构建已满足内部时序并能上板 smoke，但若后续追求更规范的工程交付，应补充外设时序约束或说明低速异步外设的约束策略。

![图4-17 最终演示证据拼图：PC dashboard、PYNQ 终端、TFT 显示和实物系统照片](assert/fig4-17-final-demo-evidence-collage.png)
