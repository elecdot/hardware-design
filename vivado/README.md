# vivado

这里存放 Vivado 项目材料、约束、Block Design 导出、已打包 IP 输出和自动化脚本。
权威 RTL 源码仍在 [../rtl/](../rtl/)；这里的工程目录用于打包、集成、调试或保留历史状态。

## 当前状态

- 目标板卡/器件：PYNQ-Z1 / `xc7z020clg400-1`。
- 已知 Vivado 版本：当前导出的 Block Design Tcl 和工程状态来自 Vivado `2023.2`。
- 当前课堂集成 overlay 的本地导出文件是 [gen/system_v0_2.bit](gen/system_v0_2.bit)、[gen/system_v0_2.hwh](gen/system_v0_2.hwh) 和 [gen/system_v0_2.tcl](gen/system_v0_2.tcl)。
- 集成工程目录仍名为 [project/system_v0_1/](project/system_v0_1/)，其 Block Design 名也是 `system_v0_1`；`system_v0_2` 是加入 TX-only Gree IR AC 后导出的 artifact 命名。
- 队友交接的原始压缩包保存在 [project/](project/) 根目录，用作追溯和课程提交材料；已迁移后的 RTL、IP repo、PYNQ driver 和文档以仓库内对应目录为准。

## 索引

| 路径 | 用途 |
|---|---|
| [constraints/](constraints/) | 外部 PL 端口的板级 XDC 约束；集成 overlay 使用 [constraints/integrated/sleep_monitor_pynq_z1.xdc](constraints/integrated/sleep_monitor_pynq_z1.xdc)。 |
| [gen/](gen/) | 本地临时 `.bit`/`.hwh`/`.tcl` 导出位置；用于 PYNQ overlay smoke 和课堂 demo artifact。 |
| [ip_repo/](ip_repo/) | 已打包、可复用自定义 AXI IP 的共享仓库。 |
| [project/](project/) | 用于 IP 打包、PYNQ overlay 构建、PL-only 调试、legacy 参考和队友 zip 交接包的 Vivado 工程目录。 |
| [scripts/](scripts/) | Tcl 自动化、板卡 preset，以及可复现 project/build 入口。 |

## IP 仓库约定

已打包自定义 IP 统一放在共享仓库 [ip_repo/](ip_repo/) 中。位于
[project/](project/) 下的各个 Vivado 工程应通过 IP repository path 引用这个目录，
不要在各工程内保留私有的已打包 IP 副本作为权威来源。

源 RTL 仍以 [../rtl/](../rtl/) 为准。Vivado 重新发现 IP 所需的已打包 IP 元数据和文件可以纳入 Git，
但 Vivado 生成的 cache、run、hardware、IP user files 和仿真输出不应成为设计源文件，
除非有意作为构建证据保留。

## Project 和 Zip 约定

- `project/*_package/` 通常是从仓库 RTL 打包自定义 IP 的 Vivado 工程入口。
- `project/system_v0_1/` 是当前集成 overlay 的 Vivado 工程入口，使用集成 XDC 并导出 `system_v0_2` artifact。
- `project/i2c_ip_test/` 是 legacy 参考工程，不作为新构建入口。
- `project/*.zip` 是队友原始交接包或外部完整 Vivado 项目包。不要直接从 zip 内生成的新副本改设计；需要修改时先把源码迁移到仓库规范位置，再同步文档。

## Tcl 脚本约定

影响工程可复现性的手工维护或导出 Tcl 应放在 [scripts/](scripts/) 下。
这包括 PYNQ-Z1 board 或 PS preset、工程创建脚本、IP 打包脚本、Block Design 再生成脚本和 overlay 导出 helper。

提交到这里的 Tcl 脚本应避免机器相关的绝对路径。除非有意作为构建证据保留，
否则不要把 Vivado 生成的 journal、log、run script 和工程 cache 输出纳入 Git。

## 导出约定

[gen/](gen/) 用于存放从 Vivado 复制出的本地 overlay artifact，例如 `.bit`、`.hwh` 和 `.tcl` 文件。
PYNQ overlay 需要来自同一次构建的匹配 `.bit` 和 `.hwh` 文件；只有 bitstream 不足以可靠地绑定 MMIO driver。
