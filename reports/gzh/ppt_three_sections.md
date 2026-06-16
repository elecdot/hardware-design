# PPT 直接可用讲稿：I2C JY901 / PYNQ 融合 / PC Server 集成

这份材料只包含三段可插入整体汇报的内容，不包含个人工作总览和全局总结。

建议总时长：7 到 8 分钟；如果保留全部 9 页，PC Server 三页每页控制在 40 到 50 秒。  
建议页数：8 到 9 页。  
插入位置：整体 PPT 的硬件 IP 设计部分之后，或系统软件集成部分之前。

| 部分 | 页数 | 时间 | 建议图源 |
|---|---:|---:|---|
| I2C JY901 九轴传感器 | 3 页 | 2.5 到 3 min | `latex/i2c_jy901_arch.mmdc`、`latex/i2c_jy901_burst_read.mmdc` |
| PYNQ 端融合与集成 | 3 页 | 2.5 到 3 min | `latex/pynq_integration_flow.mmdc`、`latex/board_client_sequence.mmdc` |
| PC Server 端集成服务 | 3 页 | 2 到 2.5 min | `latex/four_message_protocol.mmdc`、`latex/pc_server_pipeline.mmdc` |

## 第一部分：I2C JY901 九轴传感器

### 第 1 页：JY901 自定义 IP 的系统角色

PPT 标题：

```text
I2C JY901 九轴传感器：PL 侧自定义采集 IP
```

PPT 页面内容：

- IP 名称：`axi_i2c_jy901_v1_0`
- 系统路径：JY901 -> I2C Master IP -> AXI4-Lite -> PYNQ/PS
- 读取内容：加速度、角速度、磁场、姿态角、温度
- 默认地址：JY901 7-bit I2C 地址 `0x50`
- 默认读取窗口：从 `0x34` 起连续读取 13 个 16-bit word
- 设计目标：PL 负责 I2C 时序，PS 通过寄存器稳定读取

建议配图：

- `reports/gzh/latex/i2c_jy901_arch.mmdc`

直接讲稿：

```text
这一页讲 JY901 在系统里的位置。JY901 负责提供体动和姿态数据，
包括加速度、角速度、磁场、Roll、Pitch、Yaw 和模块温度。

我这里没有把 I2C 读写放在 Python 里做，而是做成了 PL 侧的
AXI-Lite 自定义 IP，名称是 axi_i2c_jy901_v1_0。这样底层 I2C 的
START、RESTART、ACK、NACK 和 timeout 都由硬件状态机完成，
PS 端只需要通过 MMIO 读写寄存器。

JY901 默认的 7 位 I2C 地址是 0x50。正常采样时，IP 从 0x34
这个寄存器开始连续读取 13 个 16 位数据。这样一次 burst read
就能覆盖本系统后续体动判断需要的主要姿态和运动信息。
```

### 第 2 页：I2C burst read 与 AXI-Lite 接口

PPT 标题：

```text
I2C burst read 与 AXI-Lite 软件接口
```

PPT 页面内容：

- I2C 读事务：
  - `START -> 0xA0 -> 0x34 -> RESTART -> 0xA1 -> 26 bytes -> NACK -> STOP`
- RTL 模块：
  - `i2c_master_core`：位级 I2C 状态机
  - `jy901_sampler`：采样调度和数据锁存
  - `axi_lite_regs`：AXI 寄存器和软件可见数据
  - `i2c_open_drain_io`：SCL/SDA 开漏三态
- 软件调用：
  - 写 `CTRL` 触发采样
  - 轮询 `STATUS`
  - 读取 `AX_RAW..TEMP_RAW` 和 `SAMPLE_CNT`

建议配图：

- `reports/gzh/latex/i2c_jy901_burst_read.mmdc`

直接讲稿：

```text
这一页展开底层事务。JY901 的读取不是单字节读，而是一个连续读取流程：
先发 START 和写地址字节 0xA0，再写起始寄存器 0x34，然后 repeated-start
切换到读地址字节 0xA1，连续读回 26 个字节。最后一个字节后主机发 NACK，
再发送 STOP。

RTL 上分成四个主要模块。i2c_master_core 负责位级 I2C 时序；
jy901_sampler 负责单次采样、自动采样和配置写的调度；axi_lite_regs
负责把控制寄存器、状态寄存器和数据寄存器暴露给 PS；i2c_open_drain_io
保证 SCL 和 SDA 只会拉低或释放，不主动输出高电平。

软件调用时逻辑很简单：先配置地址、起始寄存器、读取长度和分频，
然后写 CTRL 启动采样，轮询 STATUS 的 done 和 error 位，最后读数据区。
所以这个 IP 对软件来说是一个稳定的 AXI-Lite 外设。
```

### 第 3 页：JY901 IP 验证证据

PPT 标题：

```text
JY901 IP 验证：正常路径、错误路径、板端读取
```

PPT 页面内容：

| 验证层级 | 覆盖内容 | 证据 |
|---|---|---|
| I2C 行为仿真 | burst read、地址 NACK | `tb_jy901_sampler` PASS |
| AXI 顶层仿真 | 寄存器读写、auto、cfg_write、soft_reset、扩展 NACK | `tb_axi_i2c_jy901_top` PASS |
| timeout 仿真 | I2C master 超时退出 | `tb_i2c_master_timeout` PASS |
| 板端路径 | PYNQ MMIO 读取 JY901 数据 | 集成板端烟测通过 |

直接讲稿：

```text
这一页说明验证证据。JY901 这一块没有只验证正常读数，而是按层次验证。

第一层是 I2C 行为仿真，检查完整 burst read 事务，也检查地址 NACK
时能正确报错。第二层是 AXI 顶层仿真，检查 PS 端看到的寄存器路径，
包括 CTRL 触发、STATUS 状态、数据寄存器、auto 模式、配置写、
soft reset 和多种 NACK 错误码。第三层是 timeout 仿真，确认外设异常时
状态机能退出并上报 timeout，而不是卡死。

板端方面，JY901 已经进入集成 demo，PYNQ 端能够读到有效 IMU 数据。
这里需要注意边界：这个 IP 负责提供体动和姿态输入，不直接输出睡眠分期。
睡眠状态判断是在后面的 PC 服务里完成的。
```

## 第二部分：PYNQ 端融合与集成

### 第 4 页：板端软件分层与 IP 绑定

PPT 标题：

```text
PYNQ 端融合：overlay 绑定与驱动层封装
```

PPT 页面内容：

- 当前集成平台：`system_v0_2`
- `integrated_demo.py` 负责硬件绑定：
  - 检查 `.bit/.hwh` 是否匹配
  - 优先从 `Overlay.ip_dict` 获取 AXI 基地址
  - 旧 PYNQ metadata 失败时使用静态地址表
  - 实例化 JY901、DHT11、SpO2、TFT、Humidifier、IR AC 驱动
- 每个驱动只暴露业务接口：
  - `jy901.oneshot()` / `read_raw()`
  - `dht11.read()`
  - `spo2.read_sample()`
  - `lcd` dashboard refresh
  - `humidifier.manual()` / `status()`
  - `ir_ac.send_command()`

建议配图：

- `reports/gzh/latex/pynq_integration_flow.mmdc`

可放 PPT 的模块职责表：

| 文件 | 在板端集成中的作用 |
|---|---|
| `integrated_demo.py` | 负责 overlay 加载、IP 地址发现、驱动实例化和本地硬件烟测 |
| `board_orchestrator.py` | 把多个驱动组织成统一采样、显示刷新和控制执行接口 |
| `board_client.py` | 负责 TCP 连接、四消息协议、响应校验和断线重连 |

直接讲稿：

```text
这一页讲板端软件的第一层，也就是 overlay 绑定和驱动封装。
当前使用的集成硬件平台是 system_v0_2，里面已经把 JY901、DHT11、
UART 血氧、TFT、加湿器和格力空调红外发送 IP 放在同一个 AXI 地址空间里。

PYNQ 端首先由 integrated_demo.py 负责加载 bitstream 和 hwh，
并按照 IP 名称绑定各个 AXI-Lite 外设。正常情况下，地址来自
Overlay.ip_dict，也就是 Vivado 导出的 hwh metadata；如果旧版 PYNQ
解析 metadata 失败，程序会退回到静态地址表，保证课堂演示路径不被
metadata 兼容性卡住。

绑定完成后，上层代码不直接散写 MMIO 地址，而是通过驱动对象访问硬件。
例如 JY901 驱动提供 oneshot 和 read_raw，DHT11 驱动提供 read，
血氧驱动提供 read_sample，TFT 驱动负责显示刷新，执行器驱动负责加湿器
和红外空调命令。这样板端集成的第一步就是把“多个寄存器外设”
变成“多个可调用的 Python 驱动接口”。
```

### 第 5 页：board_orchestrator.py：统一采样与本地状态

PPT 标题：

```text
board_orchestrator.py：把硬件读数组织成 sensor_data
```

PPT 页面内容：

- 核心类：`SleepMonitorBoard`
- `read_sample()`：
  - 递增 `sample_id`
  - 创建统一 `sensor_data`
  - 读取 JY901、DHT11、SpO2
  - 更新 humidifier 当前状态
  - 生成 `data_valid`、`imu_valid`、`spo2_valid`、`env_valid`
- 板端容错：
  - JY901 支持 retry
  - 短时间失败时可复用 stale IMU 数据
  - DHT11 低频读取并缓存
  - SpO2 依据 CRC / sensor flag 判断有效性
- 本地轻量逻辑：
  - `TurnCounter` 根据 Roll/Pitch 变化统计翻身
  - `update_display()` 把采样和控制状态同步到 TFT

建议配图：

- `reports/gzh/latex/pynq_integration_flow.mmdc`

可放 PPT 的数据生成流程：

```text
drivers -> SleepMonitorBoard.read_sample()
        -> read_jy901 / read_dht11 / read_spo2
        -> update_humidifier
        -> finalize_sample_validity
        -> sensor_data
```

直接讲稿：

```text
这一页讲 board_orchestrator.py。它是板端软件的系统编排层，
核心类叫 SleepMonitorBoard。这个类不关心 AXI 寄存器细节，
它只拿 integrated_demo.py 绑定好的驱动，然后在每个采样周期调用
read_sample。

read_sample 会先递增 sample_id，然后创建统一的 sensor_data 模板。
接着依次读取 JY901、DHT11 和血氧模块，更新加湿器当前状态，
最后调用 finalize_sample_validity 生成数据质量标志。
这里的质量标志包括 data_valid、imu_valid、imu_stale、spo2_valid
和 env_valid。这样 PC 端不仅知道数值是多少，也知道这一帧数据是否可靠。

这层还做了几个板端容错处理。JY901 读取失败时会 retry；
如果短时间内失败，可以复用最近一次 IMU 数据并标记 imu_stale；
DHT11 不是每秒强制读，而是按周期读取并缓存；血氧数据会结合 CRC
和 sensor flag 判断有效性。翻身统计也在板端完成，TurnCounter 根据
Roll 和 Pitch 的变化累积 turnover_count。

所以 board_orchestrator.py 的作用可以概括为一句话：
它把多个硬件驱动的原始读数，整理成 PC 端可以直接消费的 sensor_data。
```

### 第 6 页：board_client.py：四消息会话与执行保护

PPT 标题：

```text
board_client.py：socket 会话和板端执行边界
```

PPT 页面内容：

- `board_client.py` 负责通信闭环：
  1. `read_sample()` 生成 `sensor_data`
  2. 发送 newline-delimited JSON
  3. 接收 `sleep_result`
  4. 接收 `control_command`
  5. 校验顺序和 `sample_id`
  6. 调用 `apply_control_command()`
  7. 回传 `control_status`
- `apply_control_command()` 的保护：
  - command schema 校验
  - `mode`、`policy_id`、`reason` 校验
  - 只接受 `ir_ac` 和 `humidifier`
  - IR 命令限定在白名单
  - 湿化器必须给出 `enabled`
- 执行语义：
  - Humidifier：目标状态控制
  - IR AC：一次性红外脉冲
  - no-action：合法 skipped 状态
  - 执行 / 跳过 / 拒绝 / 硬件错误都回传

建议配图：

- `reports/gzh/latex/board_client_sequence.mmdc`

可放 PPT 的状态码表：

| `status_code` | 板端含义 | 典型场景 |
|---:|---|---|
| `0` | OK | 命令执行成功 |
| `1` | rejected | 命令格式或目标非法 |
| `2` | skipped | no-action、设备缺失、IR cooldown |
| `3` | hardware error | 驱动调用或硬件执行失败 |

直接讲稿：

```text
这一页讲 board_client.py。它是板端和 PC Server 的通信入口，
负责把 SleepMonitorBoard 接到 TCP socket 上。每个采样周期的顺序是固定的：
先调用 read_sample 生成 sensor_data，然后发送给 PC；PC 返回 sleep_result
和 control_command；板端检查这两个响应的类型和 sample_id 是否匹配；
确认无误后才执行 control_command，并把结果作为 control_status 回传。

这里有一个关键边界：PC 发来的不是直接寄存器写操作，而是控制意图。
真正能不能执行，要由 PYNQ 端再次校验。apply_control_command 会检查
消息类型、mode、policy_id、reason、targets 和每个 target 的合法性。
当前只接受 humidifier 和 ir_ac 两类目标。humidifier 是目标状态语义，
也就是打开或关闭；ir_ac 是一次性红外命令，例如 power_on、power_off
或 temp_26。

红外命令还加了本地保护：距离上一次发送太近会跳过；
同一个红外命令在 cooldown 时间内重复出现也会跳过。这样可以避免 PC 策略
或网络重试导致红外命令被密集发送。

最后，无论命令是执行成功、被跳过、被拒绝，还是硬件执行失败，
PYNQ 都会回传 control_status。这样 PC 端记录的是“实际执行结果”，
而不只是“策略想执行什么”。如果讲到红外空调，要明确 sent=true
只代表红外 IP 完成发送，不代表空调真实状态有反馈。
```

## 第三部分：PC Server 端集成服务

### 第 7 页：PC Server 处理链：接收、分类、决策、回写

PPT 标题：

```text
PC Server：从 sensor_data 到 sleep_result 和 control_command
```

PPT 页面内容：

- 传输方式：TCP + newline-delimited JSON
- 每个采样周期的四消息闭环：
  1. PYNQ -> PC：`sensor_data`
  2. PC -> PYNQ：`sleep_result`
  3. PC -> PYNQ：`control_command`
  4. PYNQ -> PC：`control_status`
- `SleepMonitorPcService.process_sensor_data()`：
  - 校验 `sensor_data`
  - 保存原始传感器记录
  - 调用 `classifier_adapter` 得到 `sleep_result`
  - 调用 `comfort_policy` 得到 `control_command`
  - 更新 dashboard 状态
- `process_control_status()`：
  - 记录 PYNQ 实际执行结果
  - 把确认后的执行结果反馈给策略状态
- 协议边界：
  - `sleep_result` 只表示睡眠分类结果
  - `control_command` 表示控制意图
  - `control_status` 表示 PYNQ 实际处理结果
  - no-action 也作为合法命令返回

建议配图：

- `reports/gzh/latex/four_message_protocol.mmdc`

直接讲稿：

```text
这一页讲 PC Server 端的处理链路。PC Server 不是只负责收数据，
它是整个闭环里“分类和决策”的一层。

每个采样周期固定走四类消息。第一步，PYNQ 上传 sensor_data，
里面包含心率、血氧、IMU、温湿度和质量标志。第二步，PC 返回
sleep_result，这只表示睡眠分类结果。第三步，PC 返回 control_command，
表示策略生成的控制意图。第四步，PYNQ 执行、跳过或拒绝后，
回传 control_status。

代码上，核心入口是 SleepMonitorPcService.process_sensor_data。
它先校验 sensor_data 并保存原始记录，然后调用 classifier_adapter
得到 sleep_result，再调用 comfort_policy 得到 control_command，
最后把三类消息写入 AppState，供 dashboard 和存储模块使用。

收到 PYNQ 回传的 control_status 后，PC 端还会调用 process_control_status。
这个步骤不仅保存执行结果，还会把“红外是否真的 sent=true”这样的执行状态
反馈给策略运行状态。这样下一轮自动控制不会只根据“PC 想发送过命令”
来判断，而是根据“板端确认执行过什么”来判断。
```

### 第 8 页：自动控制逻辑：comfort_v1

PPT 标题：

```text
自动控制逻辑：由睡眠状态和环境数据生成控制意图
```

PPT 页面内容：

- 输入：
  - `sensor_data`：温度、湿度、数据有效性、心率血氧可用性
  - `sleep_result`：`sleep_state_code`、`state_valid`
  - `policy_state`：上次红外命令、上次加湿器状态、冷却时间
- 自动模式保护：
  - `state_valid != 1` 时不自动控制
  - 模型 warmup 时返回 no-action
  - 缺少温度或湿度时返回 no-action
  - 策略异常时 fallback 为 no-action
- 湿度规则：
  - `< 40%`：请求打开加湿器
  - `> 60%`：请求关闭加湿器
  - `40%..60%`：舒适区，不动作
- 温度规则：

| `sleep_state_code` | 状态 | 舒适温区 |
|---:|---|---|
| `0` | 未入睡 | `24.5..27.0 C` |
| `1` | 浅睡眠 | `24.0..27.5 C` |
| `2` | 深度睡眠 | `23.5..28.0 C` |

- `AGGRESSIVENESS` 控制强度：

| `sleep_state_code` | 状态 | `AGGRESSIVENESS` | 控制含义 |
|---:|---|---:|---|
| `0` | 未入睡 | `1.0` | 响应最快，偏离温区后可以直接调节 |
| `1` | 浅睡眠 | `0.6` | 中等响应，避免轻微波动频繁打扰 |
| `2` | 深度睡眠 | `0.3` | 最保守，只在明显偏离时控制 |

- 空调命令：
  - 先算越界偏差：`delta = abs(temperature - nearest_band_edge)`
  - 再算加权偏差：`weighted_delta = delta * AGGRESSIVENESS[state]`
  - 温度过高：按 `weighted_delta` 输出 `temp_26` / `temp_25` / `temp_24`
  - 温度过低：按 `weighted_delta` 输出 `temp_27` / `temp_28`
  - `weighted_delta < 0.5 C` 时不动作，避免临界抖动
  - IR 最小间隔 `5s`，同一命令重复 cooldown `60s`
  - cooldown 只在 PYNQ 回传 `sent=true` 后生效
- `AGGRESSIVENESS` 与 cooldown 的关系：
  - `AGGRESSIVENESS` 决定“要不要动、动多大”
  - cooldown 决定“已经决定要动时，现在能不能发”
  - 二者不是同一个策略，但可联动：睡得越深，控制越保守，cooldown 也可适当拉长

建议配图：

- `reports/gzh/latex/pc_server_pipeline.mmdc`

可放 PPT 的自动控制流程：

```text
sensor_data + sleep_result
        -> validity guard
        -> humidity decision
        -> temperature band decision
        -> AGGRESSIVENESS weighted delta
        -> cooldown / duplicate guard
        -> control_command
```

可放 PPT 的 AGGRESSIVENESS 伪代码：

```text
a = AGGRESSIVENESS[sleep_state_code]
delta = temperature outside comfort band
weighted_delta = delta * a

if weighted_delta < 0.5:
    no_action
elif temperature > high:
    temp_26 / temp_25 / temp_24 by weighted_delta
elif temperature < low:
    temp_27 / temp_28 by weighted_delta

then apply cooldown guard before sending IR command
```

直接讲稿：

```text
这一页重点讲自动控制逻辑。PC 端的策略模块是 comfort_policy.py，
策略 ID 是 comfort_v1。它的输入不是单独一个温度或睡眠状态，
而是 sensor_data、sleep_result 和上一轮策略状态。

自动控制首先有保护条件。只要分类结果 state_valid 不是 1，
比如模型还在 warmup 阶段，就不会改变空调或加湿器状态，而是返回一个
targets 为空的 no-action control_command。如果缺少温度或湿度，
也不会盲目控制。策略内部异常时，service.py 也会兜底生成 no-action，
避免 PC Server 因策略错误中断通信。

湿度控制比较直接：湿度低于 40% 时请求打开加湿器，高于 60% 时请求关闭，
40% 到 60% 之间认为是舒适区，不动作。如果上一次已经是同样的加湿器状态，
策略也不会重复发送没有意义的状态切换。

空调控制会结合睡眠状态。未入睡、浅睡眠、深度睡眠分别有不同的舒适温区。
在这个基础上，可以进一步引入 AGGRESSIVENESS 控制强度。未入睡时系数是 1.0，
说明系统可以比较积极地调节环境；浅睡眠时系数是 0.6；深度睡眠时系数是 0.3，
说明系统更保守，避免轻微温度波动打扰用户。

具体做法是先计算温度越过舒适温区边界的偏差 delta，再乘以当前睡眠状态的
AGGRESSIVENESS，得到 weighted_delta。后续空调命令不直接按原始温差决定，
而是按 weighted_delta 决定。weighted_delta 很小的时候不动作；温度偏高时，
按加权偏差输出 temp_26、temp_25 或 temp_24；温度偏低时，输出 temp_27
或 temp_28。这样同样是 1 度偏差，未入睡状态可能触发控制，深睡状态则可能
因为加权后偏差不足而保持不动作。

红外空调还有冷却保护：两次红外发送至少间隔 5 秒，同一个命令 60 秒内
不重复发送。这里要区分 AGGRESSIVENESS 和 cooldown。AGGRESSIVENESS 决定
控制强度，也就是要不要动、动多大；cooldown 是频率保护，也就是已经决定要动时，
现在能不能发送。二者不是同一个策略，但可以联动，比如深睡状态下可以同时让
weighted_delta 变小，并把重复命令 cooldown 拉长。

当前 cooldown 不是 PC 发出 control_command 就开始算，
而是 PYNQ 回传 control_status 里 ir_ac.sent=true 后才开始算。
这样如果板端缺少红外硬件或执行失败，PC 后续仍然可以重试，而不会误以为
命令已经真正发送过。
```

### 第 9 页：PC Server 服务拆分与记录证据

PPT 标题：

```text
PC Server 服务拆分：协议、模型、策略、状态、存储
```

PPT 页面内容：

- `protocol.py`：四消息 JSON 编解码和校验
- `classifier_adapter.py`：统一分类器输出为 `sleep_result`
- `comfort_policy.py`：生成 `control_command`
- `service.py`：组合分类、策略、状态和存储
- `state_store.py`：维护最新状态、历史记录、pending manual command
- `dashboard_server.py`：Web dashboard、socket loop、手动命令排队
- `storage.py`：四类 JSONL 记录独立保存
- 当前记录证据：四类 JSONL 各 90 条

建议配图：

- `reports/gzh/latex/pc_server_pipeline.mmdc`

可放 PPT 的证据表：

| 记录流 | 样本数 | 说明 |
|---|---:|---|
| `sensor_data.jsonl` | 90 | 板端上传传感器数据 |
| `sleep_result.jsonl` | 90 | PC 端分类输出 |
| `control_command.jsonl` | 90 | PC 策略输出 |
| `control_status.jsonl` | 90 | PYNQ 执行状态回传 |

直接讲稿：

```text
最后这一页讲 PC Server 的内部结构和证据。PC 端没有把所有逻辑写在一个
socket 回调里，而是拆成几个边界清楚的模块。

protocol.py 负责四类 JSON 消息的编解码和校验；classifier_adapter.py
把底层 sleep_classifier 的输出统一成 sleep_result；comfort_policy.py
根据睡眠状态、温湿度和策略状态生成 control_command；service.py
把协议校验、分类、策略、状态和存储组合成一个采样周期的处理链。
state_store.py 保存最新状态和历史记录，同时支持 dashboard 的 pending
manual command；dashboard_server.py 则把 Web 页面、socket 循环和手动控制入口
接到同一个 service 上。

当前 pynq_integration_smoke 目录中，sensor_data、sleep_result、
control_command 和 control_status 四类 JSONL 各有 90 条记录。
这说明板端上传、PC 分类、策略输出和 PYNQ 状态回传可以按同一个 sample_id
串起来复盘。需要说明的是，板端系统时间仍可能是旧时间，所以这里证明的是
协议和记录链路有效，不用它证明时间同步。
```

## 可删减版本

如果整体 PPT 时间被压缩到 5 分钟以内，建议删减为 4 页：

1. JY901 IP 系统角色 + burst read 合并。
2. JY901 验证证据。
3. PYNQ 端三层软件：`integrated_demo.py`、`board_orchestrator.py`、`board_client.py` 合并。
4. PC Server 四消息协议 + 自动控制逻辑 + 模块拆分合并。

删减时保留这三句话：

```text
JY901 的 I2C 时序放在 PL 侧，PS 通过 AXI-Lite 寄存器读取。
PYNQ 端把多个 IP 融合成统一 sensor_data，并对 PC 命令做本地执行保护。
PC Server 用四消息协议把原始数据、分类结果、自动控制命令和执行状态分开记录。
```
