# PPT 直接可用讲稿：I2C JY901 / PYNQ 融合 / PC Server 集成

这份材料只包含三段可插入整体汇报的内容，不包含个人工作总览和全局总结。

建议总时长：7 到 8 分钟。  
建议页数：6 到 7 页。  
插入位置：整体 PPT 的硬件 IP 设计部分之后，或系统软件集成部分之前。

| 部分 | 页数 | 时间 | 建议图源 |
|---|---:|---:|---|
| I2C JY901 九轴传感器 | 3 页 | 2.5 到 3 min | `latex/i2c_jy901_arch.tex`、`latex/i2c_jy901_burst_read.tex` |
| PYNQ 端融合与集成 | 2 页 | 2 到 2.5 min | `latex/pynq_integration_flow.tex`、`latex/board_client_sequence.tex` |
| PC Server 端集成服务 | 2 页 | 2 到 2.5 min | `latex/four_message_protocol.tex`、`latex/pc_server_pipeline.tex` |

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

- `reports/gzh/latex/i2c_jy901_arch.tex`

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

- `reports/gzh/latex/i2c_jy901_burst_read.tex`

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

### 第 4 页：多 IP 融合成统一板端采样

PPT 标题：

```text
PYNQ 端融合：从多个 AXI IP 到统一 sensor_data
```

PPT 页面内容：

- 当前集成平台：`system_v0_2`
- 板端绑定 IP：
  - JY901 I2C、DHT11、UART SpO2
  - TFT LCD、Humidifier、Gree IR AC
- `integrated_demo.py`：本地硬件烟测入口
- `board_orchestrator.py`：统一采样、显示刷新、执行器控制、状态生成
- 输出统一 `sensor_data`：
  - 心率、血氧、IMU、温湿度、翻身字段、质量标志

建议配图：

- `reports/gzh/latex/pynq_integration_flow.tex`

直接讲稿：

```text
这一页讲 PYNQ 端如何把单个 IP 组织成系统。当前集成硬件平台是
system_v0_2，里面包含 JY901、DHT11、UART 血氧、TFT、加湿器和
格力空调红外发送 IP。

在 PYNQ 端，integrated_demo.py 主要作为本地硬件烟测入口，用来确认
overlay 能加载、各个 IP 能绑定、传感器能读到数据、TFT 能刷新。
真正面向系统复用的逻辑放在 board_orchestrator.py。它负责每个采样周期
读取多个传感器，维护 IMU 有效性、血氧有效性、环境数据有效性和翻身相关字段，
然后组装成统一的 sensor_data。

这样后面 PC 端不需要分别理解每个硬件 IP 的寄存器细节，只需要处理统一的数据包。
```

### 第 5 页：板端控制执行与 socket client

PPT 标题：

```text
PYNQ 端执行边界：接收命令、校验命令、返回状态
```

PPT 页面内容：

- `board_client.py` 负责通信：
  - 发送 `sensor_data`
  - 接收 `sleep_result`
  - 接收 `control_command`
  - 回传 `control_status`
- PYNQ 执行保护：
  - 检查消息顺序和 `sample_id`
  - 校验控制命令和目标设备
  - 湿化器按目标状态执行
  - IR 空调按一次性命令执行
  - 执行 IR 最小间隔和重复命令 cooldown
- accepted / skipped / rejected 都回传状态

建议配图：

- `reports/gzh/latex/board_client_sequence.tex`

直接讲稿：

```text
这一页讲板端控制边界。PC 发来的不是直接硬件写寄存器，而是控制意图。
PYNQ 端收到 control_command 后，还要检查消息类型、sample_id、
目标设备和命令是否合法。

湿化器是目标状态语义，也就是打开或关闭；红外空调是一次性脉冲命令，
例如 power_on、power_off 或 temp_26。红外命令还需要做保护：
距离上一次发送太近时要跳过，同一命令重复发送也要进入 cooldown。

无论命令被执行、跳过还是拒绝，PYNQ 都会返回 control_status。
这点很重要，因为 PC 端最终记录的是实际处理结果，而不只是策略想做什么。
```

补充说明：

```text
如果讲到红外空调，要明确 sent=true 只代表红外 IP 完成发送，
不代表空调真实状态有反馈。真实空调响应仍然需要现场观察。
```

## 第三部分：PC Server 端集成服务

### 第 6 页：四消息协议

PPT 标题：

```text
PC Server：四消息协议串起分类和控制
```

PPT 页面内容：

- 传输方式：TCP + newline-delimited JSON
- 每个采样周期：
  1. PYNQ -> PC：`sensor_data`
  2. PC -> PYNQ：`sleep_result`
  3. PC -> PYNQ：`control_command`
  4. PYNQ -> PC：`control_status`
- 协议边界：
  - `sleep_result` 只表示睡眠分类结果
  - `control_command` 表示控制意图
  - no-action 也作为合法命令返回
  - `control_status` 表示 PYNQ 实际处理结果

建议配图：

- `reports/gzh/latex/four_message_protocol.tex`

直接讲稿：

```text
这一页讲 PC Server 的通信协议。整个 PC/PYNQ 链路固定为四类消息。
第一步，PYNQ 上传 sensor_data，里面包含心率、血氧、IMU、温湿度和质量标志。
第二步，PC 返回 sleep_result，只表示睡眠分类输出。第三步，PC 返回
control_command，表示策略决定的控制意图。第四步，PYNQ 执行或跳过后，
回传 control_status。

这里最关键的设计点是：分类结果和控制命令分开。sleep_result 不编码设备动作，
control_command 才描述要不要控制空调或加湿器。即使策略判断不动作，
也会返回一个 targets 为空、reason 清楚的合法 control_command。
这样日志里每个采样周期都能完整复盘。
```

### 第 7 页：PC Server 服务拆分与记录证据

PPT 标题：

```text
PC Server 服务拆分：协议、策略、状态、存储
```

PPT 页面内容：

- `protocol.py`：四消息 JSON 编解码和校验
- `classifier_adapter.py`：统一分类器输出为 `sleep_result`
- `comfort_policy.py`：生成 `control_command`
- `state_store.py`：维护最新状态、历史记录、pending manual command
- `storage.py`：四类 JSONL 记录独立保存
- `service.py`：组合分类、策略、状态和存储
- 当前记录证据：四类 JSONL 各 90 条

建议配图：

- `reports/gzh/latex/pc_server_pipeline.tex`

可放 PPT 的证据表：

| 记录流 | 样本数 | 说明 |
|---|---:|---|
| `sensor_data.jsonl` | 90 | 板端上传传感器数据 |
| `sleep_result.jsonl` | 90 | PC 端分类输出 |
| `control_command.jsonl` | 90 | PC 策略输出 |
| `control_status.jsonl` | 90 | PYNQ 执行状态回传 |

直接讲稿：

```text
最后这一页讲 PC Server 的内部结构。PC 端没有把所有逻辑写在一个 socket
回调里，而是拆成几个边界清楚的模块。

protocol.py 负责四类 JSON 消息的编解码和校验；classifier_adapter.py
把底层 sleep_classifier 的输出统一成 sleep_result；comfort_policy.py
根据睡眠状态、温湿度和执行器状态生成 control_command；state_store.py
保存当前状态和历史记录；storage.py 把四类记录分别保存成 JSONL；
service.py 则把这些模块组合起来。

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
3. PYNQ 端融合与控制执行合并。
4. PC Server 四消息协议 + 模块拆分合并。

删减时保留这三句话：

```text
JY901 的 I2C 时序放在 PL 侧，PS 通过 AXI-Lite 寄存器读取。
PYNQ 端把多个 IP 融合成统一 sensor_data，并对 PC 命令做本地执行保护。
PC Server 用四消息协议把原始数据、分类结果、控制命令和执行状态分开记录。
```
