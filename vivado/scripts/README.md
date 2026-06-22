# scripts

这里存放 Vivado Tcl 自动化、板卡 preset，以及可复现 project/build 入口。

## 布局

| 路径 | 用途 |
|---|---|
| [presets/](presets/) | Vivado 工程使用的 board 和 processing-system preset。 |

## 已登记脚本

| 路径 | 用途 | 适用范围 |
|---|---|---|
| [presets/pynq_revC.tcl](presets/pynq_revC.tcl) | PYNQ-Z1 Rev C `processing_system7` preset | Zynq PS 配置；目标器件 `xc7z020clg400-1`。 |

## 当前缺口

当前仓库还没有统一的一键重建脚本覆盖所有 [../project/](../project/) 工程。
可追溯的设计入口仍是各 `.xpr`、共享 [../ip_repo/](../ip_repo/) 和本目录下的 preset。
如果后续把手工 Vivado 流程固化为 Tcl，优先新增：

- IP 打包脚本：从 [../../rtl/](../../rtl/) 生成 [../ip_repo/](../ip_repo/)。
- 集成 overlay 重建脚本：创建 Block Design、设置 `ip_repo_paths`、应用集成 XDC、生成 `.bit/.hwh/.tcl`。
- 导出脚本：将匹配的 `.bit`、`.hwh` 和 BD Tcl 复制到 [../gen/](../gen/)。

## 规则

- 跟踪重建设计或配置设计所必需的 Tcl 文件。
- 尽量让脚本路径相对于仓库。
- 如果脚本依赖特定目标板、part 或 Vivado 版本，需要在文档中说明。
- 不要把生成的 journal、log、run 目录、cache 输出或机器相关路径 dump 当作源脚本提交。
