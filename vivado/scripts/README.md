# scripts

这里存放 Vivado Tcl 自动化、板卡 preset，以及可复现 project/build 入口。

## 布局

| 路径 | 用途 |
|---|---|
| [presets/](presets/) | Vivado 工程使用的 board 和 processing-system preset。 |

## 已登记脚本

| 路径 | 用途 |
|---|---|
| [presets/pynq_revC.tcl](presets/pynq_revC.tcl) | PYNQ-Z1 Rev C `processing_system7` preset。 |

## 规则

- 跟踪重建设计或配置设计所必需的 Tcl 文件。
- 尽量让脚本路径相对于仓库。
- 如果脚本依赖特定目标板、part 或 Vivado 版本，需要在文档中说明。
- 不要把生成的 journal、log、run 目录、cache 输出或机器相关路径 dump 当作源脚本提交。
