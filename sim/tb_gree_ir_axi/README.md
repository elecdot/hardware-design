# tb_gree_ir_axi

TX-only Gree IR AC AXI wrapper 的聚焦模块回归。

## 范围

该仿真在 Vivado IP 打包前验证软件可见契约：

- `PRESET`、`CMD_LOW`、`CMD_HIGH` 和 `STATUS` 的 reset 默认值
- 七个已提交 preset ID 和 command-shadow 寄存器值
- 正常 `CONTROL.start` 到 `STATUS.done` 的行为
- `STATUS.done` 和 `STATUS.error` 的 write-1-to-clear 行为
- busy 期间重复 start 会 latch `STATUS.error`
- `CONTROL.soft_reset` 会清除 active/latch status

testbench 通过层次化的 simulation-only assignment 缩短内部 IR sample ROM entry，
使完整 140-sample 发送 FSM 能快速完成。这不会修改可综合 RTL 或板级时序。

## 运行

从仓库根目录执行：

```powershell
iverilog -g2012 -o E:\tmp\tb_gree_ir_axi.vvp `
  sim\tb_gree_ir_axi\tb_gree_ir_axi.v `
  rtl\gree_ir_axi\gree_ir_core.v `
  rtl\gree_ir_axi\gree_ir_axi_v1_0_S00_AXI.v `
  rtl\gree_ir_axi\gree_ir_axi_v1_0.v
vvp E:\tmp\tb_gree_ir_axi.vvp
```

预期 PASS 标记：

```text
tb_gree_ir_axi PASS
```

这不是 Vivado synthesis、packaged-IP validation、integrated overlay evidence 或 board evidence。
