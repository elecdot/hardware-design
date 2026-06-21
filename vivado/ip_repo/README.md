# ip_repo

可复用自定义 AXI IP 的共享 Vivado IP 仓库。

## 约定

- 权威 RTL 源码保存在 [../../rtl/](../../rtl/) 下。
- 将可复用自定义 IP 打包到这里的子目录中，例如 `vivado/ip_repo/axi_i2c_jy901/`。
- [../project/](../project/) 下的 Vivado 工程应通过 `ip_repo_paths` 和 `update_ip_catalog` 引用这个共享目录。
- 除非是有文档说明的临时实验，否则不要为每个 Vivado 工程维护一份已打包 IP 副本。

## Git 跟踪

跟踪重新发现和复用 IP 所需的已打包 IP 文件，例如 `component.xml`、`xgui/`，
以及 packager 生成的必需 HDL 或数据文件。不要把 Vivado 生成的 cache、run directory、hardware export、
`ip_user_files`、仿真输出、journal 或 log 当作设计源文件。

板级 XDC 文件不得包含在可复用 IP 的 synthesis file set 中。根级 JY901 package 同时被旧 PMODA overlay
和集成 overlay 复用；引脚约束属于消费该 IP 的 Vivado 工程，不应放在已打包 IP 内部。

## 已打包 IP

| 路径 | IP |
|---|---|
| [ir_ac_axi/](ir_ac_axi/) | `xilinx.com:user:gree_ir_axi_v1_0:1.0`，TX-only Gree IR AC AXI IP。 |
