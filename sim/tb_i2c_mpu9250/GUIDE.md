# I2C-JY901 仿真波形观察指南

本文不是软件操作手册，而是波形分析指南。重点回答三个问题：

1. 波形里应该添加哪些信号。
2. 每个 testbench 的仿真逻辑是什么。
3. 观察这些信号如何判断 RTL 设计正确。

本指南只对应行为仿真。仿真通过不能替代 JY901 实物、PYNQ 上板、ILA 或逻辑分析仪证据。

## 1. 设计和仿真总体逻辑

`i2c_mpu9250` 当前实现的主路径是：

```text
AXI-Lite CTRL / config registers
        -> jy901_sampler
        -> i2c_master_core
        -> open-drain SCL/SDA
        -> jy901_i2c_slave_model
        -> rx byte stream
        -> 13 个 16-bit 数据寄存器
        -> AXI-Lite readable data registers
```

正常读取 JY901 数据时，I2C 总线上应出现：

```text
START
0xA0                 // 7-bit dev_addr=0x50, write bit=0
ACK
0x34                 // start_reg
ACK
RESTART
0xA1                 // 7-bit dev_addr=0x50, read bit=1
ACK
26 data bytes
ACK after byte0..byte24
NACK after byte25
STOP
```

从机模型 `jy901_i2c_slave_model.v` 固定输出 26 个字节：

```text
34 12 78 56 BC 9A 02 01 04 03 06 05 08 07
0A 09 0C 0B 0E 0D 10 0F 12 11 0C 0D
```

JY901 数据是低字节先传，因此 sampler 锁存后应得到：

| word | 字节流 | 锁存结果 |
|---:|---|---:|
| `data0` / `AX_RAW` | `34 12` | `0x1234` |
| `data1` / `AY_RAW` | `78 56` | `0x5678` |
| `data2` / `AZ_RAW` | `BC 9A` | `0x9ABC` |
| `data12` / `TEMP_RAW` | `0C 0D` | `0x0D0C` |

仿真中有三类 VCD：

| VCD | 核心用途 |
|---|---|
| `tb_jy901_sampler.vcd` | 观察 sampler + I2C core + slave model 的正常 burst read 和地址 NACK。 |
| `tb_axi_i2c_jy901_top.vcd` | 观察 AXI-Lite 寄存器如何触发采样、读回状态和数据，并覆盖扩展错误路径。 |
| `tb_i2c_master_timeout.vcd` | 观察 `i2c_master_core` 的 timeout 路径。 |

## 2. `tb_jy901_sampler` 的仿真逻辑

`tb_jy901_sampler.v` 直接实例化 `jy901_sampler` 和 `jy901_i2c_slave_model`，不经过 AXI 层。它验证的是采样调度器和 I2C 位级控制是否能完成一次 JY901 burst read。

### 2.1 正常读流程

testbench 初始配置：

```text
dev_addr      = 0x50
start_reg     = 0x34
word_count    = 13
i2c_clkdiv    = 4        // 为了仿真加速
enable        = 1
oneshot_start = 1 pulse
```

预期逻辑：

1. `oneshot_start` 进入 `jy901_sampler`。
2. sampler 产生单周期 `core_start`。
3. `i2c_master_core` 置 `busy=1`，锁存配置。
4. core 产生 `START -> 0xA0 -> 0x34 -> RESTART -> 0xA1`。
5. slave model 对正确地址和寄存器 ACK。
6. core 读取 26 个数据字节。
7. core 对前 25 个字节 ACK，对最后一个字节 NACK。
8. core 产生 STOP 和 `core_done`。
9. sampler 将 byte buffer 拼成 13 个 16-bit word。
10. sampler 置 `done=1`、`data_valid=1`、`sample_cnt=1`。

### 2.2 地址 NACK 流程

正常读通过后，testbench 清状态并修改：

```text
dev_addr = 0x51
oneshot_start = 1 pulse
```

预期逻辑：

1. core 发送写地址字节 `{0x51, 1'b0}`，即 `0xA2`。
2. slave model 只响应 `0x50`，所以不会 ACK。
3. ACK 位期间 `sda_in=1`。
4. core 在 `STEP_ADDR_W` 阶段检测到 NACK。
5. core 设置 `ack_error=1`、`error_code=0x01`。
6. sampler 对外保持 `done=1`，但 `sample_cnt` 不增加。

错误事务也会 `done=1`，这是有意设计：软件轮询 `done` 不会永久卡死，但必须同时检查 `ack_error/timeout/error_code`。

## 3. `tb_axi_i2c_jy901_top` 的仿真逻辑

`tb_axi_i2c_jy901_top.v` 实例化完整顶层 `axi_i2c_jy901_v1_0`，验证 AXI-Lite 寄存器和底层 I2C 路径是否贯通。

它覆盖这些行为：

| 行为 | 仿真意图 |
|---|---|
| 读 `VERSION` | 验证 AXI 读通道和固定版本寄存器。 |
| 读 reset `DEV_ADDR` | 验证寄存器复位值是 `0x50`。 |
| 写 `I2C_CLKDIV/START_REG/WORD_COUNT/DEV_ADDR` | 验证 AXI 写通道能配置采样参数。 |
| 写 `CTRL=enable|oneshot_start` | 验证 AXI 控制位能产生采样启动脉冲。 |
| 轮询 `STATUS.done` | 验证完成状态对软件可见。 |
| 读 `AX_RAW/AY_RAW/TEMP_RAW/SAMPLE_CNT` | 验证采样结果能通过 AXI 读回。 |
| `clear_done/clear_error` | 验证 sticky 状态可被软件清除。 |
| `WORD_COUNT=1/0/20` | 验证读长度边界处理。 |
| `auto_mode` | 验证周期采样能重复启动 core。 |
| `cfg_write_start` | 验证配置写事务和低字节优先发送。 |
| 多种 NACK | 验证错误码区分地址、寄存器、读地址、配置数据阶段。 |
| `soft_reset` | 验证采样状态和数据寄存器清零。 |

## 4. `tb_i2c_master_timeout` 的仿真逻辑

`tb_i2c_master_timeout.v` 直接实例化 `i2c_master_core`，并人为设置：

```text
TIMEOUT_CYCLES = 20
clkdiv         = 1000
```

这会让 timeout 计数先到达阈值，而 I2C 子相位还没完成。预期：

```text
timeout    = 1
ack_error  = 0
error_code = 0x10
done       = 1
```

这条路径证明 timeout 和 ACK/NACK 错误是两个不同的错误类别。timeout 不是从机不应答，而是事务超过允许周期仍未完成。

## 5. 必加信号分组

下面的信号分组是波形观察的核心。建议按模块层级分组添加，不要只看顶层 `i2c_scl/i2c_sda`，否则无法解释状态机为什么进入某个路径。

### 5.1 全局和 testbench 控制信号

适用于 `tb_jy901_sampler.vcd`：

| 信号 | 为什么要看 |
|---|---|
| `clk` | 判断同步逻辑、单周期 pulse、寄存器更新时间。 |
| `resetn` | 确认事务发生在复位释放之后。 |
| `enable` | sampler 只有 enable 后才响应启动。 |
| `oneshot_start` | 正常读和 NACK 测试都是由它触发。 |
| `clear_done` | 地址 NACK 前清除上一笔 done。 |
| `clear_error` | 地址 NACK 前清除上一笔错误状态。 |
| `dev_addr` | 区分正常读 `0x50` 和错误地址 `0x51`。 |
| `start_reg` | 确认读取起始寄存器是 `0x34`。 |
| `word_count` | 确认读取 13 个 16-bit word。 |
| `i2c_clkdiv` | 解释仿真中 SCL 周期为什么很短。 |

这些信号回答的问题是：测试到底给 DUT 输入了什么条件。

### 5.2 I2C 物理总线和开漏信号

适用于所有含 I2C 总线的 VCD：

| 信号 | 正确设计应表现为 |
|---|---|
| `i2c_scl` | 空闲为 1；事务中周期性高低变化。 |
| `i2c_sda` | 空闲为 1；START/STOP/数据/ACK 都体现在此线上。 |
| `scl_drive_low` | 为 1 时主机拉低 SCL；为 0 时释放 SCL。 |
| `sda_drive_low` | 为 1 时主机拉低 SDA；为 0 时释放 SDA。 |
| `scl_in` | core 实际采样到的 SCL 线电平。 |
| `sda_in` | core 实际采样到的 SDA 线电平。 |
| `slave.sda_drive_low` | slave ACK 或发送 0 bit 时拉低 SDA。 |

观察这些信号可以确认开漏设计是否正确：

| 观察 | 能证明什么 |
|---|---|
| `*_drive_low=0` 时总线回到 1 | testbench 上拉模型有效，RTL 没有主动驱高。 |
| ACK 位主机 `sda_drive_low=0`，slave `sda_drive_low=1` | 主机释放 SDA，从机能够应答。 |
| 读数据阶段主机 `sda_drive_low=0` | 主机没有和从机争用 SDA。 |
| 最后一个字节后主机释放 SDA | 主机用 NACK 结束 burst read。 |

如果只看 `i2c_sda`，无法判断低电平是谁拉出来的；必须同时看主机和从机的 `sda_drive_low`。

### 5.3 `jy901_sampler` 调度信号

添加 `tb_jy901_sampler.dut` 或 `tb_axi_i2c_jy901_top.dut.u_jy901_sampler` 下的：

| 信号 | 正常读预期 | 能证明什么 |
|---|---|---|
| `state` | `IDLE -> START -> WAIT_CORE -> IDLE` | sampler 调度流程正确。 |
| `core_start` | 每笔事务开始时 1 个 `clk` 周期 | 不会重复启动 core。 |
| `core_cfg_write` | 正常读为 0，配置写为 1 | read/write 事务类型选择正确。 |
| `pending_cfg` | 正常读为 0，配置写为 1 | sampler 正确锁存配置写请求。 |
| `core_done` | core 完成时出现 | sampler 能接收底层完成。 |
| `done` | 事务完成后置 1 | 软件或上层可观察完成。 |
| `data_valid` | 正常读成功后置 1 | 数据寄存器已有有效采样。 |
| `ack_error` | 正常读为 0，NACK 时为 1 | ACK 错误被传播到 sampler。 |
| `timeout` | 正常读为 0 | timeout 错误被传播到 sampler。 |
| `cfg_done` | 配置写成功后置 1 | 配置写完成可见。 |
| `error_code` | 正常读 `0x00`，错误路径为对应错误码 | 错误原因没有丢失。 |
| `sample_cnt` | 成功读后加 1，错误和配置写不加 | 成功采样计数语义正确。 |
| `byte_buf[0..25]` | 依次存放收到的 26 字节 | 数据拼接来源正确。 |
| `data0..data12` | 完成后锁存 13 个 word | JY901 低字节优先拼接正确。 |

sampler 层重点不是看 I2C 每个 bit，而是看“启动 core、等待完成、锁存数据、更新状态”这条控制链是否成立。

### 5.4 `i2c_master_core` 位级状态信号

添加 `u_i2c_master_core` 下的：

| 信号 | 用途 |
|---|---|
| `state` | 判断当前处于 START、写字节、ACK、读字节、主机 ACK/NACK、STOP、ERROR。 |
| `step` | 判断当前事务阶段：写地址、写寄存器、读地址、配置低/高字节、读数据。 |
| `tick` | I2C 子相位推进点。 |
| `div_cnt` | 验证 `clkdiv` 分频是否在工作。 |
| `tx_byte` | 当前发送字节，应看到 `0xA0`、`0x34`、`0xA1`。 |
| `bit_cnt` | 字节发送/接收从 bit7 到 bit0。 |
| `byte_cnt` | 读数据字节计数，应从 0 到 25。 |
| `latched_read_len` | 正常 13 word 时应为 26。 |
| `last_read_byte` | 最后一个字节时为 1，用于决定 NACK。 |
| `shifter` | 接收过程中的字节暂存。 |
| `rx_valid` | 每收到一个完整字节脉冲一次。 |
| `rx_index` | `rx_data` 对应的字节序号。 |
| `rx_data` | 收到的字节值。 |
| `busy` | 事务进行中为 1。 |
| `done` | core 完成时脉冲。 |
| `ack_error` | ACK 位采样为 1 时置位。 |
| `timeout` | timeout 路径置位。 |
| `error_code` | 错误码。 |

状态编号：

| 编号 | 状态 | 观察意义 |
|---:|---|---|
| 0 | `ST_IDLE` | 空闲，释放总线。 |
| 1,2,3 | `ST_START_A/B/C` | 产生 START。 |
| 4,5 | `ST_WRITE_LOW/HIGH` | 低电平准备 SDA，高电平保持数据。 |
| 6,7 | `ST_ACK_LOW/HIGH` | 释放 SDA 并采样从机 ACK。 |
| 8,9 | `ST_READ_LOW/HIGH` | 释放 SDA 并采样从机数据。 |
| 10,11 | `ST_MACK_LOW/HIGH` | 主机向从机发送 ACK 或 NACK。 |
| 12,13,14 | `ST_STOP_A/B/C` | 产生 STOP。 |
| 15 | `ST_DONE` | 完成脉冲。 |
| 16 | `ST_ERROR` | 错误完成。 |
| 17,18,19 | `ST_RESTART_A/B/C` | repeated START。 |

`step` 编号：

| 编号 | 阶段 | 正常读含义 |
|---:|---|---|
| 0 | `STEP_ADDR_W` | 发送 `0xA0`。 |
| 1 | `STEP_REG` | 发送 `0x34`。 |
| 2 | `STEP_ADDR_R` | 发送 `0xA1`。 |
| 3 | `STEP_CFG_L` | 配置写低字节。 |
| 4 | `STEP_CFG_H` | 配置写高字节。 |
| 5 | `STEP_READ` | 连续读数据。 |

### 5.5 JY901 slave model 信号

添加 `slave` 下的：

| 信号 | 用途 |
|---|---|
| `sda_drive_low` | 判断 slave 是否 ACK 或发送 0 bit。 |
| `byte_value` | slave 收到的主机字节，例如 `0xA0/0x34/0xA1`。 |
| `reg_addr` | slave 收到的寄存器地址。 |
| `master_ack` | slave 发送数据后看到主机是否 ACK。 |
| `nack_reg` | AXI 顶层扩展错误测试中注入寄存器 NACK。 |
| `nack_addr_read` | 注入读地址 NACK。 |
| `nack_cfg_low` | 注入配置低字节 NACK。 |
| `nack_cfg_high` | 注入配置高字节 NACK。 |
| `expect_cfg_write` | 标记当前 slave 期望配置写事务。 |
| `cfg_write_seen` | 配置写是否成功被 slave 捕获。 |
| `cfg_reg_addr` | 配置写寄存器地址。 |
| `cfg_word` | 配置写 16-bit 数据。 |

slave 信号的作用是区分“主机没有发送正确内容”和“从机模型按预期拒绝应答”。例如地址 NACK 时，`tx_byte=0xA2` 且 `slave.sda_drive_low=0`，说明 NACK 是由地址不匹配造成的。

### 5.6 AXI-Lite 信号

只在 `tb_axi_i2c_jy901_top.vcd` 中需要。

写通道：

| 信号 | 用途 |
|---|---|
| `s_axi_awaddr` | 写寄存器地址。 |
| `s_axi_awvalid` | 写地址有效。 |
| `s_axi_awready` | IP 接收写地址。 |
| `s_axi_wdata` | 写寄存器数据。 |
| `s_axi_wstrb` | 字节写使能。 |
| `s_axi_wvalid` | 写数据有效。 |
| `s_axi_wready` | IP 接收写数据。 |
| `s_axi_bvalid` | 写响应有效。 |
| `s_axi_bresp` | 应为 `0`，表示 OKAY。 |

读通道：

| 信号 | 用途 |
|---|---|
| `s_axi_araddr` | 读寄存器地址。 |
| `s_axi_arvalid` | 读地址有效。 |
| `s_axi_arready` | IP 接收读地址。 |
| `s_axi_rdata` | 读回数据。 |
| `s_axi_rvalid` | 读数据有效。 |
| `s_axi_rresp` | 应为 `0`，表示 OKAY。 |

寄存器层内部信号：

| 信号 | 用途 |
|---|---|
| `enable` | `CTRL[0]` 保持位。 |
| `auto_mode` | `CTRL[2]` 保持位。 |
| `oneshot_start_pulse` | `CTRL[1]` 写 1 生成的单周期启动脉冲。 |
| `clear_done_pulse` | `CTRL[3]` 写 1 生成的清 done 脉冲。 |
| `clear_error_pulse` | `CTRL[4]` 写 1 生成的清错误脉冲。 |
| `soft_reset_pulse` | `CTRL[5]` 写 1 生成的软件复位脉冲。 |
| `cfg_write_start_pulse` | `CTRL[8]` 写 1 生成的配置写启动脉冲。 |
| `dev_addr` | AXI 可写 7-bit I2C 地址。 |
| `start_reg` | AXI 可写起始寄存器。 |
| `word_count` | AXI 可写读取 word 数。 |
| `sample_period` | 自动采样周期。 |
| `i2c_clkdiv` | I2C 分频。 |
| `cfg_reg_addr` | 配置写寄存器地址。 |
| `cfg_data` | 配置写数据。 |

## 6. 正常读波形如何证明设计正确

### 6.1 证明开漏总线设计正确

观察信号：

```text
i2c_scl
i2c_sda
scl_drive_low
sda_drive_low
slave.sda_drive_low
scl_in
sda_in
```

正确现象：

| 现象 | 设计结论 |
|---|---|
| 空闲时 `scl_drive_low=0`、`sda_drive_low=0`，总线为 1 | 主机释放总线，`tri1` 上拉有效。 |
| 主机发送 0 时 `sda_drive_low=1` | RTL 用拉低表达 0。 |
| 主机发送 1 时 `sda_drive_low=0` | RTL 用释放表达 1，没有主动驱高。 |
| 从机 ACK 时主机释放 SDA，slave 拉低 SDA | ACK 方向正确，没有总线争用。 |
| 读数据阶段主机始终释放 SDA | 从机能独占 SDA 输出数据。 |

如果这些成立，能证明 `i2c_open_drain_io` 和 core 的开漏控制符合 I2C 基本要求。

### 6.2 证明 START / RESTART / STOP 正确

观察信号：

```text
i2c_scl
i2c_sda
state
tick
```

正确现象：

| 协议动作 | 波形判据 | 设计结论 |
|---|---|---|
| START | SCL 为 1 时，SDA 从 1 下降到 0 | 从机能识别事务开始。 |
| RESTART | 写寄存器后，未先 STOP，而是在 SCL 高时再次让 SDA 下降 | 符合 I2C 随机读流程。 |
| STOP | SCL 为 1 时，SDA 从 0 上升到 1 | 从机能识别事务结束。 |

JY901 burst read 必须用 repeated START：先写寄存器地址，再切换读方向。若没有 RESTART，很多 I2C 从机会认为事务已经结束或寄存器地址未保持。

### 6.3 证明发送字节顺序正确

观察信号：

```text
tx_byte
step
bit_cnt
i2c_scl
i2c_sda
sda_in
```

正常读必须看到：

| 阶段 | `step` | `tx_byte` | 设计结论 |
|---|---:|---:|---|
| 写地址 | 0 | `0xA0` | `dev_addr=0x50` 和写方向位组合正确。 |
| 起始寄存器 | 1 | `0x34` | 从 JY901 AX 寄存器开始读。 |
| 读地址 | 2 | `0xA1` | repeated START 后切换到读方向。 |

同时 `bit_cnt` 应从 7 递减到 0，说明字节按 MSB first 发送。I2C 字节传输规定最高位先传，因此这是位序正确性的证据。

### 6.4 证明 ACK 检查正确

观察信号：

```text
state
step
sda_drive_low
slave.sda_drive_low
sda_in
ack_error
error_code
```

正常读：

| ACK 位置 | 应看到 |
|---|---|
| `0xA0` 后 | 主机释放 SDA，从机拉低，`sda_in=0`。 |
| `0x34` 后 | 主机释放 SDA，从机拉低，`sda_in=0`。 |
| `0xA1` 后 | 主机释放 SDA，从机拉低，`sda_in=0`。 |

如果 `sda_in=0`，core 不进入 `ST_ERROR`，`ack_error=0`、`error_code=0x00`。这证明 ACK 采样点和错误判断正确。

地址 NACK：

| 条件 | 应看到 |
|---|---|
| `dev_addr=0x51` | `tx_byte=0xA2`。 |
| ACK 位 | 从机不拉低，`sda_in=1`。 |
| 错误输出 | `ack_error=1`、`error_code=0x01`。 |

这证明写地址阶段 NACK 能被正确识别并编码。

### 6.5 证明读数据和字节计数正确

观察信号：

```text
step
byte_cnt
latched_read_len
rx_valid
rx_index
rx_data
shifter
last_read_byte
```

正确现象：

| 观察 | 设计结论 |
|---|---|
| `latched_read_len=26` | `word_count=13` 被正确转换成 26 字节。 |
| `step=STEP_READ` | 已进入连续读数据阶段。 |
| `rx_valid` 脉冲 26 次 | 收到 26 个完整字节。 |
| `rx_index` 从 0 到 25 | 字节序号没有丢失或越界。 |
| `rx_data=34,12,78,56,...,0C,0D` | 从机模型数据被正确采样。 |
| `last_read_byte` 只在最后字节为 1 | 主机 ACK/NACK 决策点正确。 |

这些信号能证明 I2C core 的接收状态机、字节计数和最大读长度逻辑正确。

### 6.6 证明主机 ACK/NACK 结束条件正确

观察信号：

```text
byte_cnt
last_read_byte
sda_drive_low
i2c_scl
i2c_sda
slave.master_ack
```

正确现象：

| 数据字节 | `last_read_byte` | 主机响应 | 设计结论 |
|---|---:|---|---|
| byte0..byte24 | 0 | 主机拉低 SDA，ACK | 告诉从机继续发。 |
| byte25 | 1 | 主机释放 SDA，NACK | 告诉从机 burst read 结束。 |

如果最后一个字节后仍 ACK，从机可能继续发送；如果中间字节 NACK，读数据会提前结束。该观察点证明 burst read 结束条件正确。

### 6.7 证明低字节优先拼接正确

观察信号：

```text
rx_valid
rx_index
rx_data
byte_buf
data0
data1
data12
data_valid
sample_cnt
```

正确现象：

| 字节序号 | `rx_data` | 最终 word |
|---:|---:|---:|
| 0 | `0x34` | `data0[7:0]` |
| 1 | `0x12` | `data0[15:8]` |
| 2 | `0x78` | `data1[7:0]` |
| 3 | `0x56` | `data1[15:8]` |
| 24 | `0x0C` | `data12[7:0]` |
| 25 | `0x0D` | `data12[15:8]` |

最终：

```text
data0  = 0x1234
data1  = 0x5678
data12 = 0x0D0C
```

这证明 sampler 按 JY901 的 little-endian 寄存器格式拼接数据，而不是把高低字节反接。

### 6.8 证明完成状态和采样计数正确

观察信号：

```text
core_done
done
data_valid
ack_error
timeout
error_code
sample_cnt
```

正常读完成后：

```text
done       = 1
data_valid = 1
ack_error  = 0
timeout    = 0
error_code = 0x00
sample_cnt = 1
```

这证明“事务完成”和“数据有效”两个语义都成立。`done=1` 只表示事务结束；只有 `data_valid=1` 且无错误，才表示本次采样成功。

## 7. 错误路径如何证明设计正确

### 7.1 地址写 NACK

关键观察：

```text
dev_addr = 0x51
tx_byte  = 0xA2
step     = STEP_ADDR_W
sda_in   = 1 at ACK bit
ack_error = 1
error_code = 0x01
sample_cnt does not increment
```

证明点：

- 地址字节由 7-bit 地址和 R/W 位正确组合。
- 从机不响应错误地址。
- core 在地址写阶段检测 NACK。
- 错误码能区分为地址写 NACK。
- 错误事务不会伪装成成功采样。

### 7.2 起始寄存器 NACK

在 AXI 顶层仿真中，`slave.nack_reg=1` 注入错误。

关键观察：

```text
tx_byte = 0x34
step = STEP_REG
ACK bit sda_in = 1
error_code = 0x02
```

证明点：寄存器地址阶段 NACK 不会被误报为地址 NACK。

### 7.3 读地址 NACK

关键观察：

```text
tx_byte = 0xA1
step = STEP_ADDR_R
ACK bit sda_in = 1
error_code = 0x03
```

证明点：写地址和寄存器地址都已成功，错误发生在 repeated START 后的读地址阶段。

### 7.4 配置低/高字节 NACK

配置写正常字节顺序：

```text
0xA0
cfg_reg_addr
cfg_data[7:0]
cfg_data[15:8]
STOP
```

对于 testbench 中：

```text
CFG_REG_ADDR = 0x1A
CFG_DATA     = 0x55AA
```

波形应看到：

```text
tx_byte = 0xA0, 0x1A, 0xAA, 0x55
```

错误码：

| 注入 | 阶段 | 错误码 |
|---|---|---:|
| `nack_cfg_low=1` | 配置低字节 `0xAA` 后 | `0x04` |
| `nack_cfg_high=1` | 配置高字节 `0x55` 后 | `0x05` |

证明点：配置写也遵守低字节优先，并且错误定位到具体数据字节。

### 7.5 timeout

关键观察：

```text
start = 1 pulse
busy = 1
timeout_cnt increases
timeout = 1
ack_error = 0
error_code = 0x10
done = 1
```

证明点：

- timeout 是独立于 ACK/NACK 的错误类别。
- timeout 后也会完成事务，避免上层永久等待。
- `error_code=0x10` 能让软件区分“总线/状态机超时”和“从机 NACK”。

## 8. AXI 路径如何证明软件可见性正确

### 8.1 AXI 写配置寄存器

观察：

```text
s_axi_awaddr
s_axi_awvalid
s_axi_awready
s_axi_wdata
s_axi_wstrb
s_axi_wvalid
s_axi_wready
s_axi_bvalid
s_axi_bresp
```

正确现象：

| AXI 写 | 预期内部结果 |
|---|---|
| `0x18 <- 4` | `i2c_clkdiv=4`。 |
| `0x0C <- 0x34` | `start_reg=0x34`。 |
| `0x10 <- 13` | `word_count=13`。 |
| `0x08 <- 0x50` | `dev_addr=0x50`。 |
| `0x00 <- 0x00000003` | `enable=1`，`oneshot_start_pulse=1`。 |

证明点：

- AXI 写握手有效。
- 写入地址解码正确。
- `CTRL` 中 pulse 位不是保持位，而是写 1 产生单周期控制脉冲。

### 8.2 AXI 读状态寄存器

观察：

```text
s_axi_araddr = 0x04
s_axi_rdata
s_axi_rvalid
s_axi_rresp
```

完成后 `STATUS` 位应满足：

| bit | 期望 | 含义 |
|---:|---:|---|
| 0 `busy` | 0 | 事务结束。 |
| 1 `done` | 1 | 最近一次事务完成。 |
| 2 `data_valid` | 1 | 数据寄存器有效。 |
| 3 `ack_error` | 0 | 无 ACK 错误。 |
| 4 `timeout` | 0 | 无超时。 |
| 5 `cfg_done` | 0 | 不是配置写。 |

证明点：底层 sampler 状态已通过 AXI 寄存器暴露给 PS。

### 8.3 AXI 读数据寄存器

观察：

| AXI 地址 | 寄存器 | 期望读回 |
|---:|---|---:|
| `0x40` | `AX_RAW` | `0x00001234` |
| `0x44` | `AY_RAW` | `0x00005678` |
| `0x70` | `TEMP_RAW` | `0x00000D0C` |
| `0x74` | `SAMPLE_CNT` | `0x00000001` |

证明点：I2C 读到的数据不只停留在 core 或 sampler 内部，而是能通过 AXI-Lite 被软件读取。

### 8.4 clear_done / clear_error

观察：

```text
CTRL write includes bit3 clear_done
CTRL write includes bit4 clear_error
clear_done_pulse = 1
clear_error_pulse = 1
subsequent STATUS done/ack_error/timeout cleared
```

证明点：sticky 状态可以被软件显式清除，方便下一次事务重新判断。

### 8.5 WORD_COUNT 边界

观察：

| AXI 写入 `WORD_COUNT` | 期望硬件行为 |
|---:|---|
| 1 | `latched_read_len=2`。 |
| 0 | 当作 1 word，`latched_read_len=2`。 |
| 20 | clamp 到 13 word，`latched_read_len=26`。 |

证明点：读取长度不会为 0，也不会超过 13 个数据槽位。

### 8.6 auto_mode

观察：

```text
auto_mode = 1
sample_period = 4 in testbench
period_cnt repeatedly counts
core_start appears periodically
sample_cnt increases multiple times
```

证明点：自动采样不依赖软件反复写 `oneshot_start`，sampler 能按周期重复发起 I2C 事务。

### 8.7 soft_reset

观察：

```text
soft_reset_pulse = 1
sample_cnt = 0
data0..data12 = 0
done = 0
data_valid = 0
ack_error = 0
timeout = 0
```

证明点：软件复位能清空采样状态和旧数据，但不等同于重新配置 AXI 寄存器。

## 9. 最小信号集合

如果只想添加最少信号，按下面三组即可完成主要分析。

### 9.1 `tb_jy901_sampler.vcd` 最小集合

```text
clk
resetn
enable
oneshot_start
dev_addr
i2c_scl
i2c_sda
scl_drive_low
sda_drive_low
slave.sda_drive_low
dut.state
dut.core_start
dut.core_done
dut.done
dut.data_valid
dut.ack_error
dut.timeout
dut.error_code
dut.sample_cnt
dut.data0
dut.data1
dut.data12
dut.u_i2c_master_core.state
dut.u_i2c_master_core.step
dut.u_i2c_master_core.tx_byte
dut.u_i2c_master_core.bit_cnt
dut.u_i2c_master_core.byte_cnt
dut.u_i2c_master_core.latched_read_len
dut.u_i2c_master_core.last_read_byte
dut.u_i2c_master_core.rx_valid
dut.u_i2c_master_core.rx_index
dut.u_i2c_master_core.rx_data
dut.u_i2c_master_core.sda_in
dut.u_i2c_master_core.error_code
```

### 9.2 `tb_axi_i2c_jy901_top.vcd` 最小集合

```text
clk
resetn
s_axi_awaddr
s_axi_awvalid
s_axi_awready
s_axi_wdata
s_axi_wvalid
s_axi_wready
s_axi_bvalid
s_axi_bresp
s_axi_araddr
s_axi_arvalid
s_axi_arready
s_axi_rdata
s_axi_rvalid
s_axi_rresp
dut.u_axi_lite_regs.enable
dut.u_axi_lite_regs.oneshot_start_pulse
dut.u_axi_lite_regs.auto_mode
dut.u_axi_lite_regs.clear_done_pulse
dut.u_axi_lite_regs.clear_error_pulse
dut.u_axi_lite_regs.soft_reset_pulse
dut.u_axi_lite_regs.cfg_write_start_pulse
dut.u_jy901_sampler.core_start
dut.u_jy901_sampler.done
dut.u_jy901_sampler.data_valid
dut.u_jy901_sampler.ack_error
dut.u_jy901_sampler.timeout
dut.u_jy901_sampler.cfg_done
dut.u_jy901_sampler.error_code
dut.u_jy901_sampler.sample_cnt
dut.u_jy901_sampler.data0
dut.u_jy901_sampler.data1
dut.u_jy901_sampler.data12
dut.u_jy901_sampler.u_i2c_master_core.tx_byte
dut.u_jy901_sampler.u_i2c_master_core.step
dut.u_jy901_sampler.u_i2c_master_core.rx_valid
dut.u_jy901_sampler.u_i2c_master_core.rx_index
dut.u_jy901_sampler.u_i2c_master_core.rx_data
```

### 9.3 `tb_i2c_master_timeout.vcd` 最小集合

```text
clk
resetn
start
done
timeout
ack_error
error_code
dut.state
dut.busy
dut.timeout_cnt
dut.timeout
dut.ack_error
dut.error_code
dut.done
dut.scl_drive_low
dut.sda_drive_low
```

## 10. 最小结论模板

完成波形观察后，可以用下面模板写结论：

```text
1. 正常 burst read 中，I2C 总线出现 START、0xA0、ACK、0x34、ACK、RESTART、0xA1、ACK、26 个数据字节、最后 NACK、STOP，说明 I2C 随机读协议顺序正确。
2. rx_data 依次出现 0x34、0x12、0x78、0x56，最终 data0=0x1234、data1=0x5678，说明 JY901 低字节优先的数据拼接正确。
3. 正常事务完成后 done=1、data_valid=1、ack_error=0、timeout=0、sample_cnt 增加，说明成功采样状态正确。
4. dev_addr=0x51 时 tx_byte=0xA2，ACK 位 sda_in=1，error_code=0x01，sample_cnt 不增加，说明地址 NACK 错误路径正确。
5. AXI 顶层仿真中，写 CTRL 能产生 oneshot_start_pulse，STATUS 和数据寄存器能读回结果，说明采样结果对 PS 侧软件可见。
6. timeout 仿真中 timeout=1、ack_error=0、error_code=0x10，说明 timeout 与 NACK 错误被区分。
```
