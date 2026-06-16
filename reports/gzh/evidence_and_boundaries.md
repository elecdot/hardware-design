# 证据、边界与追问准备

本文件用于配合 `ppt_three_sections.md`，避免答辩时把“已验证内容”和“演示路径”混在一起。

## 证据表

| 主题 | 可讲证据 | 建议措辞 | 不建议措辞 |
|---|---|---|---|
| I2C JY901 RTL | `tb_jy901_sampler` 覆盖 burst read 和地址 NACK | “JY901 I2C 正常事务和地址 NACK 已有仿真 PASS” | “所有 I2C 场景都完全覆盖” |
| I2C JY901 AXI | `tb_axi_i2c_jy901_top` 覆盖寄存器路径、auto、cfg_write、soft_reset、NACK | “AXI 寄存器可控制采样并读取状态/数据” | “软件永远不会读到异常数据” |
| I2C timeout | `tb_i2c_master_timeout` PASS | “外设异常时能 timeout 退出并上报错误码” | “断线后自动恢复一定成功” |
| JY901 板端 | 集成 demo 中 `jy901_status=OK`、`imu_valid=1` | “集成板端路径能读到有效 IMU 数据” | “JY901 已直接判断睡眠状态” |
| PYNQ 集成 | `system_v0_2` 集成 JY901、DHT11、SpO2、TFT、humidifier、IR AC | “PYNQ 端已形成多 IP 统一采样和控制执行框架” | “所有模块在任何环境下都稳定长时间运行” |
| IR AC | PYNQ MMIO 发送 `power_on`、`power_off`、`temp_26`，实验室空调有人工响应 | “IR IP 发送完成，实验室条件下观察到空调响应” | “系统能读取空调真实状态” |
| PC 协议 | `sensor_data -> sleep_result -> control_command -> control_status` 四消息协议 | “分类结果和控制命令分离，执行状态回传闭环” | “一个 sleep_result 就能代表控制动作” |
| PC 记录 | `pynq_integration_smoke` 四类 JSONL 各 90 条 | “四类记录可以按 sample_id 关联复盘” | “时间戳完全可信” |

## 当前 `pynq_integration_smoke` 可引用事实

| 记录流 | 文件 | 行数 | 讲述用途 |
|---|---|---:|---|
| 传感器输入 | `pc_server/records/pynq_integration_smoke/sensor_data.jsonl` | 90 | 证明板端上传结构化传感器记录 |
| 分类输出 | `pc_server/records/pynq_integration_smoke/sleep_result.jsonl` | 90 | 证明 PC 端返回 `sleep_result` |
| 控制命令 | `pc_server/records/pynq_integration_smoke/control_command.jsonl` | 90 | 证明 PC 端策略输出 `control_command` |
| 执行状态 | `pc_server/records/pynq_integration_smoke/control_status.jsonl` | 90 | 证明 PYNQ 回传 `control_status` |

可选展示 sample：

| sample | 可讲点 |
|---:|---|
| `sample_id=1..30` | 模型 warmup，`state_valid=0`，策略 no-action |
| `sample_id=86..90` | 已出现 `state_valid=1` 和模型置信度，后续策略根据 cooldown / comfort 判断 no-action |
| `sample_id=90` | `sensor_data` 中有 JY901、SpO2、温湿度、翻身累计等字段；`control_status` 返回 skipped reason |

## 老师可能追问

### 1. 为什么 JY901 放在 PL 侧，不直接在 PYNQ Python 中读？

推荐回答：

```text
JY901 的 I2C 时序、ACK/NACK 检测和 timeout 更适合放到 PL 状态机里。
这样 PS 端只需要通过 AXI-Lite 读写寄存器，采样路径更稳定，也符合课程
“自定义 IP + AXI + 软件驱动”的考核重点。
```

### 2. `0x50`、`0xA0`、`0xA1` 三个值怎么区分？

推荐回答：

```text
`0x50` 是 JY901 的 7-bit I2C 从机地址。真正上总线发送时，写地址字节是
`0x50 << 1 | 0 = 0xA0`，读地址字节是 `0x50 << 1 | 1 = 0xA1`。寄存器里配置
的是 7-bit 地址，所以不能把 `0xA1` 写进 `DEV_ADDR`。
```

### 3. 你们如何判断一条 sensor_data 可用？

推荐回答：

```text
协议里把整体 `data_valid` 和各子模块质量标志分开。比如 JY901 有
`imu_valid`、`imu_stale`、`jy901_status`，SpO2 有 `spo2_valid` 和
`checksum_ok`，环境数据有 `env_valid`。这样某个模块短暂异常时，PC 端可以
知道是哪一类数据有问题，而不是只看到一个模糊失败。
```

### 4. 为什么要把 `sleep_result` 和 `control_command` 分开？

推荐回答：

```text
`sleep_result` 是模型输出，只表示睡眠状态和有效性；`control_command`
是策略输出，表示对空调或加湿器的控制意图。两者分开后，模型、策略和硬件
执行可以独立验证。即使模型 warmup 或策略 no-action，也会有明确的命令
和 reason，便于日志复盘。
```

### 5. `control_status` 的意义是什么？

推荐回答：

```text
它表示 PYNQ 端真实处理结果。PC 端发出的只是控制意图，PYNQ 还需要检查
命令是否合法、是否触发 IR cooldown、硬件是否存在、执行是否成功。
所以 accepted、applied、skipped、error 都要回传给 PC。
```

### 6. 红外空调发送成功是否等于空调真的执行？

推荐回答：

```text
不等于。`sent=true` 只说明 PYNQ 端 IR IP 完成了红外波形发送，真实空调
是否收到还取决于发射头方向、距离和接收窗口。我们实验室里在约 20 cm
对准时观察到 `power_on`、`power_off`、`temp_26` 有响应，但没有 IR RX
或空调反馈时不能声称系统能读取真实空调状态。
```

### 7. 当前 PC/PYNQ 闭环有没有真实板端证据？

推荐回答：

```text
`pynq_integration_smoke` 中四类 JSONL 各 90 条，包含板端上传的 JY901、
SpO2、温湿度和控制状态字段，可以说明记录链路和四消息协议跑通。需要同时
说明板端系统时间仍是旧时间，所以这里证明的是协议和记录链路，不证明系统
时间同步。
```

