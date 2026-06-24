# 三、四章正文材料

## 三、详细设计

## 3.1 I2C JY901 模块的设计（撰写人：待填）

JY901 九轴姿态模块用于本系统的体动与翻身检测。模块输出加速度、角速度、磁场、姿态角和温度等数据，其中加速度与 roll/pitch 姿态角主要用于判断睡眠过程中的明显体动和翻身动作。为了避免 PS 侧软件直接处理 I2C 起止位、ACK、重复起始等低层时序，本设计在 PL 侧实现 AXI4-Lite I2C-JY901 自定义 IP，由 PS 侧通过 MMIO 寄存器启动采样、读取状态并取得原始传感器数据。

本模块的实际工作不是简单调用现成 I2C 控制器，而是从 JY901 协议分析开始，独立完成 I2C bit-level master、JY901 burst read 调度、AXI4-Lite 寄存器封装、仿真用从机模型、PL-only ILA debug top、PYNQ MMIO 单模块驱动和翻身检测接口。对应工作量可概括为下表。

| 工作环节 | 具体内容 |
|---|---|
| 协议分析 | 明确 JY901 7-bit 地址、读写地址字节、寄存器 `0x34..0x40`、低字节优先格式、ACK/NACK 和 repeated START 时序 |
| RTL 实现 | 编写 AXI 寄存器层、采样调度器、I2C 位级主机、开漏 IO 适配器和顶层 AXI IP |
| 调试可观测性 | 设计 `STATUS`、`ERROR_CODE`、`SAMPLE_CNT`、SCL/SDA 输入电平、debug probe 和 LED 状态输出 |
| 仿真验证 | 构造 JY901 I2C slave model，覆盖正常 burst read、地址 NACK、扩展 NACK、配置写、自动采样、soft reset 和 timeout |
| 上板 bring-up | 设计 PL-only ILA debug top 先验证真实 I2C，再使用 PYNQ MMIO 驱动完成单模块采样 |
| 应用接口 | 在 PS 侧完成 raw 到物理量换算，并把 roll/pitch 姿态变化暴露给翻身检测逻辑 |

单模块数据链路如下：

```text
JY901 九轴模块
    -> I2C 开漏总线
    -> PL 侧 axi_i2c_jy901_v1_0 自定义 IP
    -> AXI4-Lite 寄存器
    -> PYNQ Python MMIO 驱动
    -> 姿态数据换算与翻身检测接口
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

第一版设计有意控制范围，优先保证“可读、可调、可定位问题”。未实现的内容包括多主机仲裁、clock stretching、10-bit 地址、中断、DMA、FIFO 大缓存和硬件内姿态算法。原因是本系统只有一个 FPGA I2C master 访问单个 JY901，数据量也只有每次 26 字节；使用 AXI4-Lite 寄存器轮询已经能满足课程演示和翻身检测需求。把复杂功能留在后续版本，可以降低首版 RTL 状态机的风险。

为便于调试，IP 没有只暴露“数据寄存器”这一条成功路径，而是把关键中间状态也暴露给软件：`STATUS[6]` 和 `STATUS[7]` 直接反映 SCL/SDA 实际输入电平；`ERROR_CODE` 区分地址写 NACK、寄存器 NACK、读地址 NACK、配置低/高字节 NACK 和 timeout；`SAMPLE_CNT` 只在成功数据采样后增加，因此可以判断是否真的读到新样本，而不是只看到事务结束。

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

默认寄存器参数中 `I2C_CLKDIV=250`。该寄存器控制 I2C 状态机每个低/高电平子状态保持的时钟周期数，调试时可按实际 AXI 时钟、目标 SCL 速率、线长和上拉电阻重新配置。上板初期优先使用较低速率，确认 ACK、数据读取和 STOP 均稳定后再提高速率。在部分上板演示中，为提高长杜邦线和外接上拉情况下的稳定性，软件可将 `I2C_CLKDIV` 配置为 `500` 或更大，使总线进一步降速。由于分频值是寄存器可配置项，调试时可以在不重新综合 bitstream 的情况下调整总线速率。

JY901 原始数据的换算关系如下表。

| 数据 | JY901 寄存器 | 原始格式 | Python 换算公式 |
|---|---:|---|---|
| X/Y/Z 轴加速度 | `0x34` 到 `0x36` | signed int16 | `raw / 32768 * 16`，单位 g |
| X/Y/Z 轴角速度 | `0x37` 到 `0x39` | signed int16 | `raw / 32768 * 2000`，单位 deg/s |
| X/Y/Z 轴磁场 | `0x3A` 到 `0x3C` | signed int16 | 第一版保留 raw count |
| Roll/Pitch/Yaw | `0x3D` 到 `0x3F` | signed int16 | `raw / 32768 * 180`，单位 deg |
| 模块温度 | `0x40` | signed int16 | `raw / 100`，单位摄氏度 |

#### （3）电路设计

IP 内部按“AXI 寄存器层、采样调度层、I2C 协议核心、开漏 IO 适配层”划分。顶层 `axi_i2c_jy901_v1_0` 实例化三个主要模块：

1. `axi_lite_regs`：实现 AXI4-Lite 寄存器读写、控制位脉冲生成、状态读回和数据寄存器映射。
2. `jy901_sampler`：根据 `oneshot_start`、`auto_mode` 和 `cfg_write_start` 调度一次 I2C 事务，并在事务完成后锁存数据。
3. `i2c_open_drain_io` 与 `i2c_master_core`：前者负责开漏三态适配，后者负责 I2C 位级时序、ACK 检测、读字节、主机 ACK/NACK 和 STOP。

各子模块职责进一步细化如下。

| 子模块 | 主要输入 | 主要输出 | 设计重点 |
|---|---|---|---|
| AXI 寄存器层 | AXI4-Lite AW/W/B/AR/R 通道、采样器状态、数据寄存器 | `enable`、`oneshot_start_pulse`、`auto_mode`、配置寄存器、AXI 读回数据 | 地址译码、字节写使能、写 1 触发脉冲、状态/数据对 PS 可见 |
| 采样调度器 | 控制脉冲、I2C 地址、起始寄存器、word 数、采样周期、配置写参数 | `core_start`、`core_cfg_write`、13 个 raw word、`done`、`data_valid`、`sample_cnt` | 把软件请求转换为一次 I2C 事务，处理自动周期采样、清标志、软复位和数据锁存 |
| I2C 位级核心 | `start`、`cfg_write`、`dev_addr`、`start_reg`、`read_len`、`clkdiv`、SCL/SDA 输入 | `scl_drive_low`、`sda_drive_low`、`rx_valid`、`rx_index`、`rx_data`、错误状态 | 生成 START/RESTART/STOP，按 MSB first 发送字节，采样 ACK，接收数据字节并产生主机 ACK/NACK |
| 开漏 IO 适配 | `scl_drive_low`、`sda_drive_low` | `i2c_scl`、`i2c_sda`、`scl_in`、`sda_in` | 只拉低或释放总线，不主动输出高电平，保证 I2C 开漏电气行为 |
| PL-only debug top | 板载时钟、SW0 reset、PMODA I2C、sampler/debug probe | LED、mark_debug 信号、SCL/SDA | 不经过 AXI，直接验证真实 JY901 总线事务和 ILA 可观测性 |

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

位级核心内部把“总线电平动作”和“事务阶段”分开处理。`state` 表示当前处于 START、写 bit、ACK、读 bit、主机 ACK/NACK、STOP 或错误完成；`step` 表示当前字节属于地址写、寄存器地址、地址读、配置低字节、配置高字节或读数据阶段。这样做的好处是：ACK 位采样失败时，核心可以根据 `step` 生成明确错误码，而不是只有一个笼统的 I2C 错误。

| `state` 类别 | 作用 | 关键波形判据 |
|---|---|---|
| `ST_START_A/B/C` | 在 SCL 高电平期间拉低 SDA，产生 START | 空闲高电平后，SDA 先下降，随后 SCL 被拉低 |
| `ST_RESTART_A/B/C` | 不先 STOP，直接再次产生 START | 写寄存器地址后出现 repeated START |
| `ST_WRITE_LOW/HIGH` | 发送一个字节的 8 个 bit | `tx_byte` 按 bit7 到 bit0 发送，SCL 高电平期间数据保持 |
| `ST_ACK_LOW/HIGH` | 释放 SDA 并采样从机 ACK | 主机不驱动 SDA，从机 ACK 时 SDA 为低 |
| `ST_READ_LOW/HIGH` | 释放 SDA 并接收从机数据 bit | 主机保持释放，`rx_data` 在 8 bit 后有效 |
| `ST_MACK_LOW/HIGH` | 主机对收到的数据字节 ACK 或 NACK | 非最后字节拉低 SDA，最后字节释放 SDA 表示 NACK |
| `ST_STOP_A/B/C` | 在 SCL 高电平期间释放 SDA，产生 STOP | SCL 高时 SDA 上升回高电平 |
| `ST_DONE/ST_ERROR` | 输出完成脉冲或错误完成 | `done=1`，上层轮询不会永久卡死 |

| `step` | 事务阶段 | 正常读事务中的含义 | NACK 错误码 |
|---:|---|---|---:|
| `0` | `STEP_ADDR_W` | 发送 `0xA0` | `0x01` |
| `1` | `STEP_REG` | 发送起始寄存器 `0x34` | `0x02` |
| `2` | `STEP_ADDR_R` | repeated START 后发送 `0xA1` | `0x03` |
| `3` | `STEP_CFG_L` | 配置写低字节 | `0x04` |
| `4` | `STEP_CFG_H` | 配置写高字节 | `0x05` |
| `5` | `STEP_READ` | 连续读取数据字节 | 不在该阶段采样从机 ACK |

错误路径包括地址写 NACK、寄存器地址 NACK、地址读 NACK、配置写低/高字节 NACK 和超时。错误码通过 `ERROR_CODE` 寄存器读回，驱动可据此区分地址、接线、上拉和总线卡死等问题。

`jy901_sampler` 负责把 I2C 核输出的字节流整理为 16-bit 数据寄存器。由于 JY901 低字节在前，采样器在事务结束后按如下方式拼接：

```verilog
data0 <= {byte_buf[1], byte_buf[0]};
data1 <= {byte_buf[3], byte_buf[2]};
data2 <= {byte_buf[5], byte_buf[4]};
```

实际代码中使用 `latch_word` 任务按 word 索引写入 13 个数据槽。`WORD_COUNT` 允许软件配置，但硬件会把 `0` 处理为 1 word，并把超过 13 的值钳位到 13，防止 PS 侧错误配置导致越界读取。

`axi_lite_regs` 把软件写入的 `CTRL` 位转换为单周期脉冲。例如 `oneshot_start`、`clear_done`、`clear_error`、`soft_reset` 和 `cfg_write_start` 都是写 1 触发型脉冲。这样 PS 侧只需写寄存器启动动作，PL 侧不会因为控制位保持为 1 而重复启动同一事务。

采样调度器内部只有 `IDLE`、`START`、`WAIT_CORE` 三类顶层状态，但它承担了连接软件寄存器和 I2C core 的关键工作：

1. `oneshot_start` 到来时，调度器把 `pending_cfg` 置 0，产生一个周期的 `core_start`。
2. `cfg_write_start` 到来时，调度器把 `pending_cfg` 置 1，I2C core 进入配置写事务。
3. `auto_mode=1` 时，调度器使用 `SAMPLE_PERIOD` 计数，到达周期后自动产生下一次 `core_start`。
4. I2C core 每收到一个字节会给出 `rx_valid`、`rx_index`、`rx_data`，调度器先缓存到 26 字节缓冲区。
5. core 完成且无错误时，调度器才把字节缓冲区拼接到 `data0..data12`，置位 `data_valid`，并让 `sample_cnt` 加 1。
6. core 完成但有 NACK 或 timeout 时，调度器仍置位 `done`，但不增加 `sample_cnt`，也不把错误事务伪装成有效采样。

这里特别区分 `done` 和 `data_valid`：`done=1` 只表示最近一次事务已经结束；`data_valid=1` 才表示数据寄存器中存在有效样本。软件轮询时必须同时检查 `ack_error`、`timeout` 和 `data_valid`，不能只看 `done`。

AXI 控制寄存器采用“保持位 + 写 1 脉冲位”的混合设计。

| 控制位 | 类型 | 设计原因 |
|---|---|---|
| `enable` | 保持位 | 用于统一打开或关闭 IP 响应 |
| `auto_mode` | 保持位 | 软件可长期保持自动采样状态 |
| `oneshot_start` | 写 1 脉冲 | 避免软件写 1 后重复触发同一次采样 |
| `clear_done` | 写 1 脉冲 | 清除 sticky 完成标志，便于下一次轮询 |
| `clear_error` | 写 1 脉冲 | 清除 ACK/timeout/error_code，便于重新测试 |
| `soft_reset` | 写 1 脉冲 | 清空采样状态、数据寄存器和计数器 |
| `cfg_write_start` | 写 1 脉冲 | 触发一次配置写事务，不影响正常读取配置 |

`WORD_COUNT` 允许软件配置读取 word 数，但硬件做了边界保护：写入 `0` 时按 1 个 word 处理，写入大于 13 时钳位到 13 个 word。这样可以防止软件误配置造成读长度为 0 或越过 13 个数据槽。

![图3-3 I2C JY901 burst read 时序图：START、0xA0、0x34、RESTART、0xA1、连续数据和 STOP](assert/fig3-3-jy901-i2c-burst-read.svg)

#### （4）IP 封装

Vivado 中封装后的 IP 为 `xilinx.com:user:axi_i2c_jy901_v1_0:1.0`。主要参数和端口如下。

| 项目 | 内容 |
|---|---|
| AXI 数据宽度 | `C_S00_AXI_DATA_WIDTH = 32` |
| AXI 地址宽度 | `C_S00_AXI_ADDR_WIDTH = 7` |
| 时钟 | `s00_axi_aclk`，AXI/PYNQ 单模块平台按 100 MHz 设计 |
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
| `0x18` | `I2C_CLKDIV` | RW | I2C 低/高电平子状态分频值 |
| `0x1C` | `ERROR_CODE` | R | NACK 或 timeout 错误码 |
| `0x28` | `VERSION` | R | IP 版本标识 |
| `0x40` 到 `0x70` | 数据寄存器 | R | `AX_RAW` 到 `TEMP_RAW` |
| `0x74` | `SAMPLE_CNT` | R | 成功采样计数 |

单模块 AXI/PYNQ 调试平台中，JY901 IP 通过独立 overlay 暴露给 PYNQ MMIO，调试地址曾使用 `0x43C0_0000` 和 64 KB 范围。该地址只用于单模块 bring-up；系统集成后的统一地址映射放在第四章说明。

单模块 AXI/PYNQ overlay 和 PL-only ILA debug top 主要使用 PMODA 接线，便于在不占用系统集成中其他外设引脚的情况下单独调通 JY901：

| 信号 | PYNQ-Z1 引脚 | 说明 |
|---|---|---|
| `i2c_scl` | PMODA `Y17` | 3.3 V I2C，上拉到 3.3 V |
| `i2c_sda` | PMODA `Y16` | 开漏数据线，上拉到 3.3 V |

另有 Arduino SCL/SDA `P16/P15` 的备用约束，用于后续构建目标明确切换到 Arduino 排针时使用。单个 Vivado 构建中不能同时应用 PMODA 和 Arduino 两套 JY901 pin mapping，否则会产生同名端口的引脚冲突。无论使用哪套约束，SCL/SDA 都必须按 3.3 V open-drain I2C 处理，外部上拉不应接到 5 V。

![图3-4 Vivado 封装后的 axi_i2c_jy901_v1_0 IP 符号截图：S_AXI、时钟复位和 i2c_scl/i2c_sda 外部端口](assert/fig3-4-vivado-jy901-ip-symbol.png)

### 3.1.2 软件设计

PYNQ 侧单模块软件的目标是把 AXI 寄存器访问封装成稳定的传感器读数接口，使调试人员不需要手工计算寄存器偏移、状态位和原始数据换算。该软件只面向 JY901 单模块 bring-up：先验证 MMIO 能访问 IP，再验证 I2C 能读到真实传感器，最后把 raw 数据换算为物理量并提供翻身检测接口。

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
 -> 输出单模块读数表格，并把 roll/pitch 提供给翻身检测接口
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

翻身检测放在 PS 侧 `TurnCounter` 中，而不是放进 PL IP。当前第一版逻辑使用 roll/pitch 变化阈值，默认阈值为 `35.0` 度。这样做的原因是翻身动作判断和防抖策略更接近应用层，后续可以调整阈值、加入冷却时间或融合加速度变化，而不需要重新生成 bitstream。

![图3-5 JY901 PYNQ 软件读取流程图：配置寄存器、启动采样、轮询状态、读取 raw、换算和输出单模块读数](assert/fig3-5-jy901-pynq-driver-flow.svg)

### 3.1.3 模块测试

JY901 单模块测试按“行为仿真、ILA debug top 上板、单模块 PYNQ 上板”三个层次组织。行为仿真用于证明 RTL 协议和寄存器路径正确；ILA debug top 用于在不依赖 AXI/PYNQ 软件的情况下确认真实硬件 I2C 总线能工作；单模块 PYNQ 上板测试用于证明 PS 侧可以通过 MMIO 读取真实 JY901 数据并完成物理量换算。集成系统测试不放在本节，统一放在第四章说明。

#### （1）行为仿真：Icarus Verilog + GTKWave/Vivado 波形观察

行为仿真使用 Icarus Verilog 编译 RTL 和 testbench，并使用 JY901 I2C slave model 作为传感器替身。该从机模型固定响应 7-bit 地址 `0x50`，在收到起始寄存器 `0x34` 后输出 26 个预设字节，用于验证 JY901 低字节优先的数据拼接。仿真同时生成 VCD 波形，可通过 GTKWave 观察；同一组 RTL 和 testbench 也可加入 Vivado behavioral simulation，用 xsim 波形窗口观察。

仿真分为三组。

| 仿真组 | 验证对象 | 主要覆盖内容 |
|---|---|---|
| sampler 仿真 | `jy901_sampler` + `i2c_master_core` + JY901 slave model | 正常 burst read、地址写 NACK、26 字节接收、13 个 word 锁存、`sample_cnt` 增加 |
| AXI 顶层仿真 | 完整 AXI IP 顶层 | AXI 写配置、`CTRL` 脉冲、`STATUS` 轮询、数据寄存器读回、`WORD_COUNT` 边界、auto mode、配置写、soft reset |
| timeout 仿真 | `i2c_master_core` timeout 路径 | 人为缩短 `TIMEOUT_CYCLES`，使事务在 I2C 子状态完成前超时，验证 `timeout=1` 和 `ERROR_CODE=0x10` |

正常 burst read 仿真的预设字节流和锁存结果如下。

| 字节序号 | 从机输出 | 锁存目标 | 期望 word |
|---:|---:|---|---:|
| 0, 1 | `0x34, 0x12` | `AX_RAW` | `0x1234` |
| 2, 3 | `0x78, 0x56` | `AY_RAW` | `0x5678` |
| 4, 5 | `0xBC, 0x9A` | `AZ_RAW` | `0x9ABC` |
| 24, 25 | `0x0C, 0x0D` | `TEMP_RAW` | `0x0D0C` |

行为仿真检查点如下。

| 检查项 | 预期结果 | 证明内容 |
|---|---|---|
| START/RESTART/STOP | SCL 高电平期间 SDA 出现规定下降/上升沿 | I2C 事务边界正确 |
| 地址写 | `tx_byte=0xA0` 后从机 ACK | `DEV_ADDR=0x50` 与写方向位组合正确 |
| 起始寄存器 | `tx_byte=0x34` 后从机 ACK | 读取从 JY901 `AX` 寄存器开始 |
| 地址读 | repeated START 后 `tx_byte=0xA1` | 随机读方向切换正确 |
| 数据读取 | `rx_valid` 出现 26 次，`rx_index=0..25` | 连续读取 13 个 16-bit word |
| 主机 ACK/NACK | byte0..byte24 后 ACK，byte25 后 NACK | burst read 结束条件正确 |
| 数据拼接 | `AX_RAW=0x1234`、`AY_RAW=0x5678`、`TEMP_RAW=0x0D0C` | JY901 低字节优先格式处理正确 |
| 地址 NACK | `DEV_ADDR=0x51` 时发送 `0xA2`，`ERROR_CODE=0x01` | 地址错误能被定位 |
| 扩展 NACK | 起始寄存器、读地址、配置低/高字节 NACK 分别生成不同错误码 | 错误阶段可区分 |
| `WORD_COUNT` 边界 | 写 `0` 按 1 word，写大于 13 钳位到 13 word | 软件误配置不会越界 |
| auto mode | `SAMPLE_CNT` 随周期事务递增 | 自动采样不依赖软件重复写启动位 |
| soft reset | 数据、状态和 `SAMPLE_CNT` 清零 | 软件可恢复到已知状态 |
| timeout | `timeout=1`、`ack_error=0`、`ERROR_CODE=0x10` | 超时和 NACK 是不同错误类别 |

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

波形观察不是只看 PASS 文本，而是按信号组逐层确认设计正确。GTKWave 或 Vivado behavioral simulation 中建议至少加入以下信号。

| 信号组 | 代表信号 | 观察目的 |
|---|---|---|
| I2C 总线 | `i2c_scl`、`i2c_sda`、`scl_drive_low`、`sda_drive_low`、`sda_in` | 判断开漏释放、ACK 方向、START/STOP 是否正确 |
| sampler | `state`、`core_start`、`core_done`、`done`、`data_valid`、`sample_cnt` | 判断调度器是否正确启动 core 并锁存数据 |
| I2C core | `state`、`step`、`tx_byte`、`bit_cnt`、`byte_cnt`、`rx_valid`、`rx_data` | 判断协议阶段、字节顺序和读数据过程 |
| AXI | `AW/W/B/AR/R` 通道、`oneshot_start_pulse`、`clear_error_pulse`、`s_axi_rdata` | 判断 PS 可见寄存器路径是否打通 |
| 错误路径 | `ack_error`、`timeout`、`error_code`、`sample_cnt` | 判断错误事务不会被误判为成功采样 |

![图3-6 JY901 仿真 PASS 终端截图：sampler、AXI top、NACK 和 timeout 测试通过](assert/fig3-6-jy901-simulation-pass.png)

![图3-7 JY901 I2C 仿真波形截图：START、RESTART、ACK、NACK、STOP、rx_data 和 AXI 读回](assert/fig3-7-jy901-i2c-waveform.png)

#### （2）ILA debug top 上板测试

在 AXI/PYNQ 单模块测试之前，先设计 PL-only ILA debug top。该顶层不经过 AXI，也不依赖 PYNQ Python 驱动，而是直接例化 `jy901_sampler`，使用固定配置访问真实 JY901：

| 配置项 | 数值或说明 |
|---|---|
| 顶层时钟 | PYNQ-Z1 125 MHz PL clock |
| 复位 | SW0 输入，低有效复位 |
| JY901 地址 | `0x50` |
| 起始寄存器 | `0x34` |
| 读取长度 | 13 个 16-bit word |
| I2C 引脚 | PMODA `Y17/Y16`，SCL/SDA 均为 3.3 V open-drain |
| 采样方式 | reset 释放后可先触发一次调试读取，随后按 `SAMPLE_PERIOD_CYCLES` 自动采样 |

![图3-8 JY901 PL-only ILA debug top 结构图：125 MHz 时钟、SW0 reset、PMODA I2C、sampler、core debug probes 和 LED 状态](assert/fig3-8-jy901-ila-debug-top.svg)

LED 用于快速判断当前硬件状态：

| LED | 显示内容 | 用途 |
|---|---|---|
| `led[0]` | `i2c_busy` | 事务是否正在进行 |
| `led[1]` | `done` | 最近一次事务是否完成 |
| `led[2]` | `data_valid` | 是否已有有效采样 |
| `led[3]` | `ack_error \| timeout` | 是否出现 NACK 或 timeout |

debug top 中对关键内部信号添加 `mark_debug`，便于 Vivado ILA 捕获。核心 probe 包括：

| probe 类别 | 代表信号 | 观察目标 |
|---|---|---|
| 物理总线 | `scl_in_dbg`、`sda_in_dbg`、`core_scl_in_dbg`、`core_sda_in_dbg` | 判断 SCL/SDA 是否能回到高电平，ACK 位是否被拉低 |
| sampler 状态 | `sampler_state_dbg`、`period_cnt_dbg`、`core_start_dbg`、`core_done_dbg` | 判断自动采样周期和 core 启动是否正确 |
| core 阶段 | `core_state_dbg`、`core_step_dbg`、`core_tx_byte_dbg` | 判断是否发送 `0xA0`、`0x34`、`0xA1` |
| 读数据 | `core_bit_cnt_dbg`、`core_byte_cnt_dbg`、`core_latched_read_len_dbg`、`core_last_read_byte_dbg` | 判断是否读满 26 字节、最后字节是否 NACK |
| 错误定位 | `error_code_dbg`、`ack_error`、`timeout` | 判断是地址、寄存器、读地址、配置字节还是 timeout 问题 |
| 数据结果 | `data0..data12`、`sample_cnt` | 判断真实模块数据是否被锁存，姿态变化时 raw word 是否变化 |

ILA 上板测试流程如下：

1. 板卡断电后连接 JY901，VCC 接 3.3 V，GND 共地，SCL/SDA 接 PMODA 对应引脚，并确认上拉到 3.3 V。
2. 使用 debug top 生成 bitstream，并在 Vivado Hardware Manager 中打开 ILA。
3. 释放 SW0 reset，观察 LED：正常情况下 `done` 和 `data_valid` 会在事务完成后置位，错误 LED 不应常亮。
4. 在 ILA 中触发 `core_start_dbg` 或 `done`，观察一次完整事务。
5. 检查 `core_tx_byte_dbg` 是否依次出现 `0xA0`、`0x34`、`0xA1`。
6. 检查 `core_latched_read_len_dbg=26`，`core_byte_cnt_dbg` 能推进到最后字节，最后字节后 `core_last_read_byte_dbg` 触发 NACK。
7. 手动改变 JY901 姿态，观察 `data0..data12` 或至少一个 raw data word 发生变化。

若 ILA 中在 ACK 状态附近看到 `core_sda_in_dbg=1`，说明从机没有应答，应优先检查模块供电、SCL/SDA 是否接反、上拉电阻、PMODA 引脚约束、JY901 默认地址是否被改写。若 SCL/SDA 一直为低，则优先检查短路、无上拉、模块接线和开漏释放逻辑。若 `timeout=1` 但 `ack_error=0`，说明事务未在限定周期内完成，应检查时钟、分频、reset 和状态机是否卡住。

![图3-9 JY901 ILA 上板捕获截图：core_tx_byte、core_step、SCL/SDA、data_valid、sample_cnt 和 data word 变化](assert/fig3-9-jy901-ila-debug-capture.png)

#### （3）单模块 PYNQ 上板测试

ILA debug top 证明真实 I2C 总线可用后，再进行单模块 PYNQ 上板测试。该测试使用独立 JY901 overlay 和 PYNQ MMIO 驱动，目标是证明 PS 侧能够通过 AXI4-Lite 配置 IP、启动采样、读回状态和数据，并完成物理量换算。

单模块 PYNQ 测试流程如下：

1. 下载独立 JY901 bitstream，创建 direct MMIO 或根据 overlay 元数据绑定 IP。
2. 读取 `VERSION`，确认值为 `0x4A593101`，证明 AXI 读通道和 IP 版本寄存器正确。
3. 写入 `DEV_ADDR=0x50`、`START_REG=0x34`、`WORD_COUNT=13`、`I2C_CLKDIV` 和采样周期。
4. 写 `CTRL.clear_done` 和 `CTRL.clear_error` 清除旧状态。
5. 写 `CTRL.enable | CTRL.oneshot_start` 触发一次采样。
6. 轮询 `STATUS.done`，同时检查 `ack_error` 和 `timeout`。
7. 若 `data_valid=1`，读取 `AX_RAW` 到 `TEMP_RAW` 和 `SAMPLE_CNT`。
8. 将 16-bit raw 转换为 signed int16，再换算为 g、deg/s、deg 和摄氏度。
9. 周期性打印读数，并手动旋转 JY901，观察加速度和 roll/pitch/yaw 的变化。

单模块 PYNQ 测试通过标准如下。

| 检查项 | 通过标准 | 说明 |
|---|---|---|
| AXI 访问 | `VERSION=0x4A593101` | 证明 AXI-Lite 寄存器读通 |
| 参数写入 | 读回或行为符合 `DEV_ADDR=0x50`、`START_REG=0x34`、`WORD_COUNT=13` | 证明配置寄存器生效 |
| 单次采样 | `done=1`、`data_valid=1`、`ack_error=0`、`timeout=0` | 证明一次 JY901 read 成功 |
| 采样计数 | `SAMPLE_CNT` 在成功采样后增加 | 证明不是旧状态误判 |
| 原始数据 | `AX_RAW..TEMP_RAW` 有非固定值 | 证明数据寄存器被真实采样更新 |
| 换算数据 | 加速度、角速度、姿态角、温度显示在合理范围内 | 证明 signed int16 和量程换算正确 |
| 姿态响应 | 手动移动或旋转模块时 roll/pitch/yaw 有相应变化 | 证明模块可用于体动/翻身检测 |

PYNQ 上板测试也用于定位剩余问题。若 `VERSION` 读不对，优先检查 bitstream、overlay 元数据、基地址和 AXI 地址范围；若 `VERSION` 正确但 `ack_error=1`，优先检查 JY901 供电、地址、SCL/SDA 线序和上拉；若 `timeout=1`，优先检查 reset、I2C 分频、SCL/SDA 是否卡死；若状态正常但数据不随姿态变化，优先检查高低字节拼接、signed int16 解释和模块安装方向。

![图3-10 JY901 单模块 PYNQ CLI 输出截图：VERSION PASS、SAMPLE_CNT、STATUS OK 和姿态数据变化](assert/fig3-10-jy901-single-module-cli-pass.png)

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

---

## 五、总结

本课程设计围绕基于 PYNQ-Z1 / Zynq-7000 平台的智能睡眠监测辅助系统展开，完成了从 PL 侧自定义外设 IP、PS 侧 PYNQ 驱动与任务编排、PC 侧数据接收与分类策略，到本地显示和辅助控制执行的完整设计。系统最终能够采集姿态/体动、心率血氧、温湿度等睡眠相关数据，在板端 TFT 上实时显示关键状态，通过网络向 PC 侧发送结构化数据，由 PC 侧完成记录、睡眠状态估计和舒适度控制策略生成，再由 PYNQ 侧执行加湿器状态控制和红外空调控制，形成“采集—显示—上传—分析—控制—反馈”的端到端闭环。

从功能完成度看，本设计已经实现课程要求中的主要硬件综合内容。PL 侧完成了多个面向真实外设的 AXI-Lite 自定义 IP，包括 I2C JY901 姿态传感器接口、DHT11 温湿度接口、UART 心率血氧接口、TFT LCD SPI 显示接口、加湿器/指示器控制接口和 Gree 空调红外发送接口。PYNQ 侧完成 overlay 加载、MMIO 寄存器访问、传感器轮询、翻身检测、本地显示刷新、控制命令执行和状态回传。PC 侧完成 socket 服务、四消息协议、原始数据记录、睡眠分类适配、环境舒适度策略和 dashboard 可视化。最终演示中，系统完成了真实板端采集、TFT 显示、PC dashboard 展示、JSONL 数据记录、睡眠状态输出和控制闭环，关键链路已经通过端到端验收。需要说明的是，本系统输出用于课程设计中的睡眠辅助估计和环境辅助控制，不作为医学诊断结论。

### 5.1 主要工作归纳

本次课程设计的工作可以归纳为以下几个方面。

| 工作方向 | 完成内容 | 形成的能力 |
|---|---|---|
| 硬件接口设计 | 针对 JY901、DHT11、心率血氧模块、TFT LCD、红外空调和加湿器/指示器设计自定义 IP 或完成模块集成 | 将真实外设时序封装为可由 PS 访问的硬件模块 |
| AXI-Lite 寄存器抽象 | 为各模块设计控制、状态和数据寄存器，区分 start、busy、done、valid、error 等状态 | 形成软硬件边界清晰的寄存器接口 |
| Vivado 系统集成 | 将多路自定义 IP 接入 Zynq PS，经 AXI Interconnect 统一映射到 PS 地址空间，并完成外部端口约束和 bitstream 生成 | 掌握从单模块 IP 到完整 Block Design 的集成流程 |
| PYNQ 板端软件 | 完成 overlay 加载、MMIO 驱动、传感器轮询、翻身计数、本地 TFT 显示和控制命令执行 | 将硬件寄存器接口组织为可复用的软件驱动与板端任务 |
| PC 侧服务 | 完成 socket 通信、数据校验、分类适配、舒适度策略、记录存储和 dashboard 显示 | 将板端数据转化为可观察、可记录、可交互的系统服务 |
| 分层测试 | 采用行为仿真、单模块上板、PYNQ 驱动测试、集成上板测试和端到端演示逐层验证 | 建立由局部到整体的硬件系统验证方法 |

其中，I2C JY901 模块是本人投入较多、设计过程也最完整的部分。该模块不仅包括 I2C 开漏总线时序、寄存器地址写入、连续字节读取、超时保护和错误码上报，还包括 AXI-Lite 控制/状态接口、仿真测试平台、ILA 调试顶层、单模块 PYNQ 驱动和最终系统集成。通过这一模块，完成了从传感器协议理解、RTL 状态机设计、波形观察、板级调试到软件调用的完整闭环，也为后续其他外设 IP 的集成提供了接口设计和测试组织上的参考。

### 5.2 收获与体会

本次设计最大的收获是把课堂中的数字系统、接口协议和嵌入式软硬件协同知识落实到一个可运行系统中。单个 IP 模块在仿真中通过并不代表系统可以稳定工作；只有当寄存器语义、外部接线、电平安全、PYNQ 驱动、PC 协议和演示流程全部闭合后，系统才能真正被展示和验收。

在硬件设计方面，对 AXI-Lite 外设 IP 的理解更加具体。以前容易把 AXI 接口看作“能读写寄存器即可”，本次设计中需要进一步考虑寄存器语义是否稳定、状态位是否会被误读、一次采样是否有明确完成标志、错误是否可定位、软件轮询是否会卡死等问题。例如 JY901 模块中增加 `data_valid`、`busy`、`done`、`timeout`、`error_code`、`sample_cnt` 等状态信息后，PYNQ 软件才能判断当前数据是否可靠，测试人员也能根据状态码快速判断问题发生在总线应答、寄存器地址、读取阶段还是超时阶段。

在软件集成方面，PYNQ 的作用不仅是简单读写 MMIO，还要承担板端任务编排。系统需要把多个传感器的读取频率、异常处理、本地显示、网络发送和控制执行组织在同一循环中。PC 侧服务也不能只接收一串数据，而要定义清晰的数据协议，将 `sensor_data`、`sleep_result`、`control_command` 和 `control_status` 分离记录，使每一次采样、分类和控制都有可追踪依据。通过这一过程，我对软硬件协同系统中的“可观察性”和“可复现性”有了更深体会。

在测试方法方面，本次设计建立了逐层验证意识。行为仿真用于验证时序和状态机；ILA 和单模块 PYNQ 测试用于确认真实板级信号与寄存器读写；集成上板测试用于确认多个 IP 能在同一 overlay 中共同运行；端到端演示用于确认数据链路、显示链路和控制链路同时成立。相比只在最终演示时一次性排查问题，分层测试能显著缩小定位范围，也能为报告提供更可信的证据链。

### 5.3 遇到的问题及解决思考

设计和调试过程中遇到的问题主要集中在真实外设接口、软硬件边界和系统集成三个层面。

| 问题 | 现象 | 分析与解决 |
|---|---|---|
| JY901 I2C 地址理解容易混淆 | 资料中可能出现 `0x50`、`0xA0`、`0xA1` 等不同写法，仿真或上板时容易 NACK | 将 `0x50` 明确为 7-bit 从机地址，读写方向位由 I2C 控制器在地址字节最低位生成；设计说明中统一这一口径 |
| I2C 总线开漏行为与 FPGA 普通输出不同 | 若直接推高 SDA/SCL，可能导致总线行为异常或与外部上拉冲突 | RTL 中采用输出低电平和释放高阻两种状态表达开漏语义，板级连接使用 3.3 V 上拉，并通过 ILA 观察 start、ack、read bit 等关键阶段 |
| 单次采样状态不易判定 | 软件可能读到旧数据，或无法区分“未开始”“正在采样”“完成但错误” | 设计中增加 start/busy/done/data_valid/timeout/error_code/sample_cnt 等状态，软件读取前后比较计数并检查错误位 |
| 行为仿真和真实外设响应存在差异 | 仿真测试平台能通过，但上板后可能受接线、上拉、频率、模块状态影响 | 将测试拆分为仿真、ILA 调试顶层、单模块 PYNQ 测试和集成测试，逐层确认问题位置 |
| 多 IP 集成后地址和元数据需要一致 | 软件若解析到错误地址，会造成读写寄存器无效 | 集成时统一地址映射，并在板端软件中对 overlay 信息和静态地址表进行一致性处理，确保课堂演示环境可稳定运行 |
| 早期分阶段调试记录覆盖面不完整 | 某些早期记录只验证传感器读取或控制发送，未同时覆盖翻身计数、dashboard 和控制闭环 | 报告中区分“单模块证据”“集成上板证据”和“最终演示证据”，最终功能结论以正式端到端演示为准 |
| 红外空调控制缺少反向反馈 | IP 可确认红外波形发送完成，但无法从空调获得电子回执 | 报告中将 `done` 解释为“发送完成”，将空调实际响应作为人工观察证据，避免把发送状态等同于接收成功 |
| PC/PYNQ 协议耦合度较高 | 若消息字段混乱，dashboard、记录和控制策略难以同步 | 采用四消息结构，将传感器数据、分类结果、控制命令和执行状态分开传输和记录，并用 sample_id 关联一次闭环 |

这些问题说明，硬件课程设计不只是把若干模块连接起来，还需要在接口定义、错误暴露、测试证据和报告表述之间保持一致。特别是最终报告中，必须清楚说明哪些结论来自仿真，哪些来自单模块上板，哪些来自完整系统演示。这样既能真实反映工作过程，也能避免把局部测试结果扩大成没有证据支撑的系统结论。

### 5.4 不足与改进方向

由于课程时间和实验条件限制，本系统仍有一些不足。

1. 睡眠状态估计仍以规则和适配器为主，能够满足课程演示和工程要求，但距离真实睡眠质量评估还有差距。后续可采集更长时间数据，引入更严格的特征工程、模型训练和交叉验证。
2. 系统以辅助估计为目标，没有医学级传感器标定和临床验证。后续若用于更严肃场景，需要增加传感器校准、数据质量评估和异常数据剔除机制。
3. 红外空调控制是 TX-only 方案，无法直接读取空调实际状态。后续可考虑增加红外接收、温湿度闭环反馈或带回读能力的控制设备，使控制状态更加可靠。
4. 外部低速异步接口的工程约束仍可进一步规范。虽然当前板级演示已经通过，但后续工程化交付时应补充更完整的外部时序说明和约束策略。
5. dashboard 和数据分析功能仍偏向课堂演示。后续可增加更完整的历史曲线、睡眠阶段统计、异常事件标注和报告导出功能。
6. 板端运行环境对时间同步、网络状态和 overlay 元数据一致性有一定依赖。后续可增加启动自检、时间校准提示、自动重连和更清晰的故障提示。

### 5.5 对课程的建议

本课程设计综合性强，能够把数字逻辑、接口协议、SoC 架构、嵌入式软件和系统测试结合起来，对理解“硬件模块如何变成可用系统”很有帮助。通过本次项目，我更加明确了硬件设计不是孤立完成 RTL，而是要同时考虑软件如何控制、测试如何观察、错误如何定位、最终演示如何证明。

对课程后续安排有以下建议。

1. 建议鼓励同学在报告中明确证据来源，将仿真截图、ILA 波形、板端输出、实物照片和端到端记录分层呈现，这样更能体现硬件综合课程的工程过程。

总体而言，本次课程设计完成了一个具有真实外设、板端显示、PC 侧分析和控制执行能力的智能睡眠监测辅助系统。项目过程中既完成了功能实现，也经历了从协议理解、RTL 设计、仿真验证、板级调试、系统集成到最终演示的完整工程流程。通过这个过程，我对 PYNQ-Z1 平台、AXI-Lite 自定义 IP、软硬件协同设计和分层测试方法都有了更系统的认识，也认识到硬件系统开发中清晰接口、可靠证据和严格表述的重要性。
