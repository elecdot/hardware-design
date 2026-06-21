# vivado/gen

这里存放供本地 PYNQ overlay 使用的临时 Vivado 导出 artifact。

预期 overlay artifact：

- overlay implementation run 生成的 `.bit` bitstream。
- 同一 Block Design 构建导出的匹配 `.hwh` hardware handoff。

本目录中的构建 artifact 被 Git 忽略。把 `.bit` 复制到这里便于本地测试，
但除非同时导出了匹配的 `.hwh`，否则不要声称 overlay 已可用于 PYNQ。
