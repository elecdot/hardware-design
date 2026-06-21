# vivado

这里存放 Vivado 项目材料、约束、Block Design 导出、已打包 IP 输出和自动化脚本。

## 索引

| 路径 | 用途 |
|---|---|
| [constraints/](constraints/) | 外部 IP 端口的板级 XDC 约束。 |
| [gen/](gen/) | 本地临时 `.bit`/`.hwh` 导出位置；被 Git 忽略。 |
| [ip_repo/](ip_repo/) | 已打包、可复用自定义 AXI IP 的共享仓库。 |
| [project/](project/) | 用于 IP 打包、PYNQ overlay 构建、PL-only 调试和 legacy 参考的 Vivado 工程目录。 |
| [scripts/](scripts/) | Tcl 自动化、板卡 preset，以及可复现 project/build 入口。 |

## IP 仓库约定

已打包自定义 IP 统一放在共享仓库 [ip_repo/](ip_repo/) 中。位于
[project/](project/) 下的各个 Vivado 工程应通过 IP repository path 引用这个目录，
不要在各工程内保留私有的已打包 IP 副本。

源 RTL 仍以 [../rtl/](../rtl/) 为准。Vivado 重新发现 IP 所需的已打包 IP 元数据和文件可以纳入 Git，
但 Vivado 生成的 cache、run、hardware、IP user files 和仿真输出不应成为设计源文件，
除非有意作为构建证据保留。

## Tcl 脚本约定

影响工程可复现性的手工维护或导出 Tcl 应放在 [scripts/](scripts/) 下。
这包括 PYNQ-Z1 board 或 PS preset、工程创建脚本、IP 打包脚本、Block Design 再生成脚本和 overlay 导出 helper。

提交到这里的 Tcl 脚本应避免机器相关的绝对路径。除非有意作为构建证据保留，
否则不要把 Vivado 生成的 journal、log、run script 和工程 cache 输出纳入 Git。

## 导出约定

[gen/](gen/) 用于存放从 Vivado 复制出的本地 overlay artifact，例如 `.bit` 和 `.hwh` 文件。
PYNQ overlay 需要来自同一次构建的匹配 `.bit` 和 `.hwh` 文件；只有 bitstream 不足以可靠地绑定 MMIO driver。
