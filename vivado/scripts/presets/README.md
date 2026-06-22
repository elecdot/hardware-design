# presets

这里存放可复用的 Vivado board 和 processing-system preset。

## 已登记 preset

| 路径 | 用途 | 说明 |
|---|---|---|
| [pynq_revC.tcl](pynq_revC.tcl) | 用于 Zynq PS 配置的 PYNQ-Z1 Rev C `processing_system7` preset | 面向 `xc7z020clg400-1`；当前 Vivado 工程/BD Tcl 已知来自 Vivado `2023.2`。 |

## 使用规则

- 当 preset Tcl 文件影响工程可复现性时，应将其提交。
- 提交前移除本地绝对路径，或将其参数化。
- preset 只配置 PS/board 相关属性，不应包含工程本地 run、cache 或导出路径。
