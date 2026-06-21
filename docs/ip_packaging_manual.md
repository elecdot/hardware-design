# IP Packaging Manual

本文档是迁移 RTL 模块的 Vivado IP 打包执行手册。目标是把可复用 AXI-Lite IP 放入
`vivado/ip_repo/`，并让后续 Block Design 能稳定重新发现、连接和验证这些 IP。

## 入口条件

1. 从干净或已明确审查的工作区开始。
2. 确认 [test_plan.md](test_plan.md) 中已有 Phase 2 smoke 证据。
3. 确认目标 part 为 PYNQ-Z1 / `xc7z020clg400-1`。
4. 除非 IP 参数另有说明，AXI/system clock 使用 100 MHz。
5. 不要把板级 pin 约束放入可复用 IP package。
6. 不要把 Vivado 生成的 HDL 副本当作源码编辑；如需修 RTL，回到 `rtl/<ip>/` 修改。

优先打包顺序：

1. `axi_humidifier_v1_0`
2. `tft_lcd_spi_axi_v1_0`
3. `dht11_axi_v1_0`
4. `axi_uart_spo2_v1_0`

## 仓库约定

| Purpose | Path |
|---|---|
| 权威 RTL | `rtl/<ip>/` |
| 临时打包工程 | `vivado/project/<ip>_package/` |
| 共享已打包 IP 输出 | `vivado/ip_repo/<ip>/` |
| 最终集成约束 | `vivado/constraints/integrated/` |
| 临时 build/export 输出 | `vivado/gen/` |

通常需要跟踪：

- `vivado/ip_repo/<ip>/component.xml`
- `vivado/ip_repo/<ip>/xgui/*.tcl`
- packager 复制或引用的必要 RTL/source 文件

通常不要跟踪：

- Vivado cache、run directory、journal、log
- `ip_user_files/`
- 仿真产物和机器相关路径 dump
- 板级 XDC，除非它属于消费该 IP 的顶层工程

## IP 清单

| IP | Top Module | 需要添加的 RTL 文件 | 外部端口 | 参数 | Phase 2 证据 |
|---|---|---|---|---|---|
| Humidifier | `axi_humidifier_v1_0` | `axi_humidifier_v1_0.v`, `axi_humidifier_v1_0_S00_AXI.v`, `humidifier_core.v` | `humidity_hw_valid`, `humidity_hw[7:0]`, `humidifier_led`, `humidifier_leds[3:0]` | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5`, `CLK_FREQ_HZ=100000000` | `tb_humidifier_core PASS`, `tb_axi_humidifier PASS` |
| TFT LCD SPI | `tft_lcd_spi_axi_v1_0` | `tft_lcd_spi_axi_v1_0.v`, `tft_lcd_spi_axi_v1_0_S00_AXI.v`, `spi_lcd_master.v` | `lcd_scl`, `lcd_sda`, `lcd_res`, `lcd_dc`, `lcd_blk` | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5` | `tb_spi_lcd_master PASS`, `tb_tft_lcd_spi_axi PASS` |
| DHT11 | `dht11_axi_v1_0` | `dht11_axi_v1_0.v`, `dht11_axi_v1_0_S00_AXI.v`, `dht11_onewire.v` | RTL 中为 `dht11`；当前 XDC 期望集成 BD 外部端口名为 `dht11_0` 或显式映射到该名 | `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=4` | `tb_dht11_onewire_smoke PASS`；AXI top 可 elaboration |
| UART SpO2 | `axi_uart_spo2_v1_0` | `axi_uart_spo2_v1_0.v`, `axi_uart_spo2_v1_0_S00_AXI.v`, `uart_rx.v`, `uart_tx.v`, `spo2_frame_parser.v` | `uart_rxd`, `uart_txd`, `irq` | `C_BPS=9600`, `C_SYS_CLK_FRE=100000000`, `C_S00_AXI_DATA_WIDTH=32`, `C_S00_AXI_ADDR_WIDTH=5` | `tb_spo2_frame_parser PASS`；AXI top 可 elaboration |

## GUI 打包流程

### 1. 创建临时 RTL 工程

1. `File -> Project -> New`
2. Project name：`<ip>_package`
3. Project location：`vivado/project/`
4. Project type：`RTL Project`
5. 从对应 `rtl/<ip>/` 目录添加源码。
6. 不添加 constraints。
7. 选择 part `xc7z020clg400-1`。
8. 完成工程创建。
9. 在 `Sources` 中右键顶层模块，选择 `Set as Top`，确认顶层与上表一致。

### 2. 打包前先 elaboration

1. `Flow Navigator -> RTL Analysis -> Open Elaborated Design`
2. 继续前修复所有缺失 module、parameter 或 primitive error。
3. 检查顶层端口是否正好是该 IP 预期端口。
4. 确认没有把 testbench 或 standalone demo top 误设为顶层。

### 3. 启动 IP Packager

1. `Tools -> Create and Package New IP`
2. 选择 `Package your current project`
3. IP location：`vivado/ip_repo/<ip>/`
4. 进入 IP Packager view。

建议 metadata：

| Field | Value |
|---|---|
| Vendor | `xilinx.com` |
| Library | `user` |
| Name | 顶层模块名，例如 `axi_humidifier_v1_0` |
| Version | `1.0` |
| Display name | 人可读模块名 |
| Description | 一句话说明角色和接口 |

保持 Name 稳定；它会影响 VLNV、`Overlay.ip_dict` key 和打包 diff。

### 4. 检查 File Groups

1. 确认清单中所有必需 RTL 文件都已包含。
2. 确认 testbench 不在 synthesis file group 中。
3. 确认 standalone demo top 不在 synthesis file group 中。
4. 如果 packager 复制源码到 package，检查复制文件与 `rtl/<ip>/` 中权威源码一致。

### 5. 检查 Ports And Interfaces

1. 确认 Vivado 从 `s00_axi_*` 推断出一个 AXI4-Lite slave interface。
2. Interface mode 应为 slave。
3. Interface type 应为 AXI4-Lite，不是带 burst transaction 的 full AXI memory-mapped。
4. 将 AXI interface 关联到 `s00_axi_aclk`。
5. 将 reset 关联到 `s00_axi_aresetn`，active low。
6. 物理外设端口保持为普通 external port。

如果 AXI interface 未自动推断：

1. 检查顶层是否存在全部 AXI signal。
2. 检查 `C_S00_AXI_DATA_WIDTH` 和 `C_S00_AXI_ADDR_WIDTH` 是否作为参数可见。
3. 手动使用 `Infer Bus Interface` 并选择 AXI memory mapped slave。
4. 重新运行 `Package IP -> Review and Package -> Check Integrity`。

### 6. 检查 Addressing And Memory

1. 确认 AXI-Lite slave 有一个 memory map。
2. 使用保守 aperture，例如 `4K` 或 `64K`。
3. 不要在这里分配最终集成 base address；base address 由消费该 IP 的 BD 工程分配。

已用寄存器范围：

| IP | Address Width | Used Register Range |
|---|---:|---|
| DHT11 | 4 | `0x00` to `0x0C` |
| Humidifier | 5 | `0x00` to `0x18` |
| TFT LCD SPI | 5 | `0x00` to `0x0C` |
| UART SpO2 | 5 | `0x00` to `0x1C` |

### 7. 检查 Parameters

- 确认 AXI data/address width 参数存在且默认值正确。
- 确认时钟相关参数与 100 MHz 假设一致。
- 对 UART SpO2 保持 `C_BPS=9600` 和 `C_SYS_CLK_FRE=100000000`，除非 BD 时钟和文档同步更新。
- 不要把仿真专用参数暴露成最终硬件依赖。

### 8. Review And Re-Package

1. 点击 `Run IP Checks` 或 `Check Integrity`。
2. 审查所有 warning。
3. 修复阻塞性的 interface、file group 或 memory map 问题。
4. 点击 `Re-Package IP`。
5. 关闭临时打包工程前，确认 `component.xml` 和 `xgui/` 已写入 `vivado/ip_repo/<ip>/`。

## 可选 Tcl 骨架

GUI 流程是当前推荐路径。需要脚本化时，使用类似骨架，但先在 GUI 中确认推断出的 bus interface 名称。

```tcl
create_project <ip>_package vivado/project/<ip>_package -part xc7z020clg400-1
add_files [glob rtl/<ip>/*.v]
set_property top <top_module> [current_fileset]
update_compile_order -fileset sources_1
ipx::package_project -root_dir vivado/ip_repo/<ip> -vendor xilinx.com -library user -taxonomy /UserIP -import_files
ipx::associate_bus_interfaces -busif s00_axi -clock s00_axi_aclk [ipx::current_core]
ipx::associate_bus_interfaces -busif s00_axi -reset s00_axi_aresetn [ipx::current_core]
ipx::save_core [ipx::current_core]
```

在消费工程中刷新 IP catalog：

```tcl
set_property ip_repo_paths [file normalize vivado/ip_repo] [current_project]
update_ip_catalog
```

## Per-IP 打包说明

### Humidifier

- `humidity_hw_valid` 和 `humidity_hw[7:0]` 是可选硬件湿度输入；首个 PS-controlled build 可在 BD 中绑常量。
- `humidifier_leds[3:0]` 是外部 LED 输出。
- 不要把 DHT11 直接连入该 IP 作为第一版验收路径；当前路径是 PYNQ 读取 DHT11 后写 `SW_HUM`。

### TFT LCD SPI

- 顶层必须是 `tft_lcd_spi_axi_v1_0`。
- 不要把 `top_spi_lcd_test.v` 打包为 synthesis top。
- 外部端口为 `lcd_scl/lcd_sda/lcd_res/lcd_dc/lcd_blk`。
- 当前 RTL 没有 `CS` 或 `MISO`，带 `CS` 的显示屏需要硬件保持有效或后续扩展。

### DHT11

- RTL 顶层端口为 `dht11` inout。
- 当前集成 XDC 约束的 BD external port 名称为 `dht11_0`；打包后在 BD 中保持该外部名或同步更新 XDC。
- `dht11_onewire.v` 使用 Vivado `IOBUF` primitive；Icarus smoke test 中用 stub。

### UART SpO2

- 保持默认 9600 baud 和 100 MHz clock 参数。
- `irq` 可保留但第一版软件走 polling-first。
- 默认 frame mode 为 5-byte；7-byte mode 需要先确认物理模块格式。

## 打包后检查

PowerShell 静态检查：

```powershell
Test-Path vivado\ip_repo\<ip>\component.xml
Get-ChildItem vivado\ip_repo\<ip>\xgui
rg -n "<ip>|busInterface|memoryMap|addressBlock" vivado\ip_repo\<ip>
```

Vivado 检查：

```tcl
set_property ip_repo_paths [file normalize vivado/ip_repo] [current_project]
update_ip_catalog
```

验收点：

1. IP 出现在 Vivado IP Catalog 的 User Repository 下。
2. IP 能加入空白 Block Design。
3. AXI interface 能连接 AXI Interconnect 或 SmartConnect。
4. 连接 clock/reset 和 address 后，`Validate Design` 不报告缺失 interface 连接。
5. 外部端口与 [wiring.md](wiring.md) 和集成 XDC 命名一致。

## Phase 3 退出条件

1. `component.xml` 和 `xgui/` 存在于 `vivado/ip_repo/<ip>/`。
2. Vivado IP integrity check 没有阻塞错误。
3. 共享 `vivado/ip_repo/` 路径能在独立工程中重新发现该 IP。
4. BD 中可见 AXI4-Lite slave interface、clock、reset 和 memory map。
5. 非 AXI 物理端口与计划集成接线一致。
6. 进入 BD integration 前，已记录所有 IP-specific warning。

## 常见失败

| Symptom | Likely Cause | Fix |
|---|---|---|
| AXI interface not inferred | 端口命名或参数 metadata 未被识别 | 手动推断 AXI4-Lite slave interface，并关联 `s00_axi_aclk` / `s00_axi_aresetn` |
| IP appears but cannot connect to AXI interconnect | interface 被推断为错误协议或缺少 address map | 重新检查 `Ports and Interfaces` 与 `Addressing and Memory` |
| DHT11 port constraint fails | BD external port 名称与 XDC 不匹配 | 将 BD external port 重命名为 `dht11_0`，或在同一范围更新集成 XDC |
| TFT package includes unexpected top | `top_spi_lcd_test.v` 被作为 source top 包含 | 从 packaging file group 移除它，并把 `tft_lcd_spi_axi_v1_0` 设为 top |
| Humidifier input ports block validation | 可选 PL humidity input 悬空 | 首个 PS-controlled build 中将它们绑到常量 |
| SpO2 timing wrong after integration | clock 参数与 AXI clock 不匹配 | 计划 100 MHz clock 下保持 `C_SYS_CLK_FRE=100000000`，否则同步更新 BD 和文档 |
| Pin conflicts after BD export | 旧单模块 XDC 与集成 XDC 混用 | 最终 overlay 只使用集成 XDC |
| PYNQ driver cannot find IP by name | IP 或 BD cell name 改变 | 保持 package name 稳定，并在 driver binding 前记录最终 BD instance name |

## 移交 Phase 4

Phase 4 需要的产物：

- `vivado/ip_repo/` 下的可复用 IP package。
- 每个 package 的静态检查记录。
- 需要绑常量、导出外部端口或命名匹配的 Per-IP 说明。
- 更新后的 [register_map.md](register_map.md)、[wiring.md](wiring.md) 和 [test_plan.md](test_plan.md)。
