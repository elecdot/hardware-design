# i2c_ip_test Legacy Status

该 Vivado 工程仅作为历史参考保留。

不要把该工程作为新 IP 打包、Block Design 集成或 PYNQ overlay bitstream 构建的干净入口。
它把多个不同 Vivado 工作流混在一个 `.xpr` 中：

- 自定义 AXI IP 打包文件；
- 完整 `system_experimental` Block Design 集成；
- 可选 PL-only `jy901_hw_debug_top` bring-up 逻辑；
- debug ILA XDC 文件和板级 pin XDC 文件；
- 多次实验生成的 IP/output 产物。

这种混合状态很容易破坏 Vivado 工程。一个常见失败模式是把 `axi_i2c_jy901_v1_0`
设为顶层模块后运行 implementation；所有 AXI-Lite 端口都会变成顶层 FPGA IO，
导致 `[Place 30-58] Number of unplaced IO Ports is greater than number of available pins`
这类 IO placement 错误。

## 推荐拆分

后续工作使用独立 Vivado 入口：

1. **IP 打包工程**
   - 使用 [../axi_i2c_jy901_package/](../axi_i2c_jy901_package/)。
   - 将 `axi_i2c_jy901_v1_0` 打包到 [../../ip_repo/](../../ip_repo/)。
   - 不运行整板 implementation 或 bitstream 生成。
   - 不把板级 pin 约束或 debug ILA XDC 文件包含在已打包 IP 内部。

2. **AXI/PYNQ overlay 工程**
   - 使用 [../axi_i2c_jy901/](../axi_i2c_jy901/)。
   - 在 Zynq Block Design 中例化已打包 IP。
   - 使用 BD wrapper `jy901_axi_system_wrapper` 作为顶层。
   - 只导出真实外部 PL 端口，目前为 `i2c_scl` 和 `i2c_sda`。
   - 对 PMODA `Y17/Y16` 使用 [../../constraints/axi_i2c_jy901_package.xdc](../../constraints/axi_i2c_jy901_package.xdc)。
   - 同时生成 PYNQ 需要的 `.bit` 和 `.hwh` 文件。

3. **PL-only 硬件调试工程**
   - 使用 [../jy901_hw_debug/](../jy901_hw_debug/)。
   - 使用 `jy901_hw_debug_top.v` 和 debug 专用约束。
   - bring-up 期间可以包含 ILA probe。
   - 与已打包 AXI IP 和 PYNQ overlay 构建保持分离。

4. **集成 overlay 工程**
   - 使用 [../system_v0_1/](../system_v0_1/)。
   - 应用 [../../constraints/integrated/sleep_monitor_pynq_z1.xdc](../../constraints/integrated/sleep_monitor_pynq_z1.xdc)。
   - 当前本地导出 artifact 为 [../../gen/system_v0_2.bit](../../gen/system_v0_2.bit) 和匹配 `.hwh/.tcl`。

本目录下当前文件仍可用于参考，但新的可复现构建流程应记录为 Tcl 脚本，或放在 [../](../) 下的独立 Vivado 工程中。
