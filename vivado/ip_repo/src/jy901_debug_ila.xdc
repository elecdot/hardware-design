


create_debug_core u_ila_0 ila
set_property ALL_PROBE_SAME_MU true [get_debug_cores u_ila_0]
set_property ALL_PROBE_SAME_MU_CNT 1 [get_debug_cores u_ila_0]
set_property C_ADV_TRIGGER false [get_debug_cores u_ila_0]
set_property C_DATA_DEPTH 4096 [get_debug_cores u_ila_0]
set_property C_EN_STRG_QUAL false [get_debug_cores u_ila_0]
set_property C_INPUT_PIPE_STAGES 0 [get_debug_cores u_ila_0]
set_property C_TRIGIN_EN false [get_debug_cores u_ila_0]
set_property C_TRIGOUT_EN false [get_debug_cores u_ila_0]
set_property port_width 1 [get_debug_ports u_ila_0/clk]
connect_debug_port u_ila_0/clk [get_nets [list clk_IBUF_BUFG]]
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe0]
set_property port_width 1 [get_debug_ports u_ila_0/probe0]
connect_debug_port u_ila_0/probe0 [get_nets [list ack_error]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe1]
set_property port_width 16 [get_debug_ports u_ila_0/probe1]
connect_debug_port u_ila_0/probe1 [get_nets [list {data10[0]} {data10[1]} {data10[2]} {data10[3]} {data10[4]} {data10[5]} {data10[6]} {data10[7]} {data10[8]} {data10[9]} {data10[10]} {data10[11]} {data10[12]} {data10[13]} {data10[14]} {data10[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe2]
set_property port_width 16 [get_debug_ports u_ila_0/probe2]
connect_debug_port u_ila_0/probe2 [get_nets [list {data12[0]} {data12[1]} {data12[2]} {data12[3]} {data12[4]} {data12[5]} {data12[6]} {data12[7]} {data12[8]} {data12[9]} {data12[10]} {data12[11]} {data12[12]} {data12[13]} {data12[14]} {data12[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe3]
set_property port_width 16 [get_debug_ports u_ila_0/probe3]
connect_debug_port u_ila_0/probe3 [get_nets [list {data4[0]} {data4[1]} {data4[2]} {data4[3]} {data4[4]} {data4[5]} {data4[6]} {data4[7]} {data4[8]} {data4[9]} {data4[10]} {data4[11]} {data4[12]} {data4[13]} {data4[14]} {data4[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe4]
set_property port_width 16 [get_debug_ports u_ila_0/probe4]
connect_debug_port u_ila_0/probe4 [get_nets [list {data7[0]} {data7[1]} {data7[2]} {data7[3]} {data7[4]} {data7[5]} {data7[6]} {data7[7]} {data7[8]} {data7[9]} {data7[10]} {data7[11]} {data7[12]} {data7[13]} {data7[14]} {data7[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe5]
set_property port_width 16 [get_debug_ports u_ila_0/probe5]
connect_debug_port u_ila_0/probe5 [get_nets [list {data8[0]} {data8[1]} {data8[2]} {data8[3]} {data8[4]} {data8[5]} {data8[6]} {data8[7]} {data8[8]} {data8[9]} {data8[10]} {data8[11]} {data8[12]} {data8[13]} {data8[14]} {data8[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe6]
set_property port_width 16 [get_debug_ports u_ila_0/probe6]
connect_debug_port u_ila_0/probe6 [get_nets [list {data9[0]} {data9[1]} {data9[2]} {data9[3]} {data9[4]} {data9[5]} {data9[6]} {data9[7]} {data9[8]} {data9[9]} {data9[10]} {data9[11]} {data9[12]} {data9[13]} {data9[14]} {data9[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe7]
set_property port_width 16 [get_debug_ports u_ila_0/probe7]
connect_debug_port u_ila_0/probe7 [get_nets [list {data6[0]} {data6[1]} {data6[2]} {data6[3]} {data6[4]} {data6[5]} {data6[6]} {data6[7]} {data6[8]} {data6[9]} {data6[10]} {data6[11]} {data6[12]} {data6[13]} {data6[14]} {data6[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe8]
set_property port_width 16 [get_debug_ports u_ila_0/probe8]
connect_debug_port u_ila_0/probe8 [get_nets [list {data1[0]} {data1[1]} {data1[2]} {data1[3]} {data1[4]} {data1[5]} {data1[6]} {data1[7]} {data1[8]} {data1[9]} {data1[10]} {data1[11]} {data1[12]} {data1[13]} {data1[14]} {data1[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe9]
set_property port_width 8 [get_debug_ports u_ila_0/probe9]
connect_debug_port u_ila_0/probe9 [get_nets [list {error_code_dbg[0]} {error_code_dbg[1]} {error_code_dbg[2]} {error_code_dbg[3]} {error_code_dbg[4]} {error_code_dbg[5]} {error_code_dbg[6]} {error_code_dbg[7]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe10]
set_property port_width 16 [get_debug_ports u_ila_0/probe10]
connect_debug_port u_ila_0/probe10 [get_nets [list {data5[0]} {data5[1]} {data5[2]} {data5[3]} {data5[4]} {data5[5]} {data5[6]} {data5[7]} {data5[8]} {data5[9]} {data5[10]} {data5[11]} {data5[12]} {data5[13]} {data5[14]} {data5[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe11]
set_property port_width 16 [get_debug_ports u_ila_0/probe11]
connect_debug_port u_ila_0/probe11 [get_nets [list {data11[0]} {data11[1]} {data11[2]} {data11[3]} {data11[4]} {data11[5]} {data11[6]} {data11[7]} {data11[8]} {data11[9]} {data11[10]} {data11[11]} {data11[12]} {data11[13]} {data11[14]} {data11[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe12]
set_property port_width 16 [get_debug_ports u_ila_0/probe12]
connect_debug_port u_ila_0/probe12 [get_nets [list {data2[0]} {data2[1]} {data2[2]} {data2[3]} {data2[4]} {data2[5]} {data2[6]} {data2[7]} {data2[8]} {data2[9]} {data2[10]} {data2[11]} {data2[12]} {data2[13]} {data2[14]} {data2[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe13]
set_property port_width 32 [get_debug_ports u_ila_0/probe13]
connect_debug_port u_ila_0/probe13 [get_nets [list {sample_cnt[0]} {sample_cnt[1]} {sample_cnt[2]} {sample_cnt[3]} {sample_cnt[4]} {sample_cnt[5]} {sample_cnt[6]} {sample_cnt[7]} {sample_cnt[8]} {sample_cnt[9]} {sample_cnt[10]} {sample_cnt[11]} {sample_cnt[12]} {sample_cnt[13]} {sample_cnt[14]} {sample_cnt[15]} {sample_cnt[16]} {sample_cnt[17]} {sample_cnt[18]} {sample_cnt[19]} {sample_cnt[20]} {sample_cnt[21]} {sample_cnt[22]} {sample_cnt[23]} {sample_cnt[24]} {sample_cnt[25]} {sample_cnt[26]} {sample_cnt[27]} {sample_cnt[28]} {sample_cnt[29]} {sample_cnt[30]} {sample_cnt[31]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe14]
set_property port_width 16 [get_debug_ports u_ila_0/probe14]
connect_debug_port u_ila_0/probe14 [get_nets [list {data3[0]} {data3[1]} {data3[2]} {data3[3]} {data3[4]} {data3[5]} {data3[6]} {data3[7]} {data3[8]} {data3[9]} {data3[10]} {data3[11]} {data3[12]} {data3[13]} {data3[14]} {data3[15]}]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe15]
set_property port_width 1 [get_debug_ports u_ila_0/probe15]
connect_debug_port u_ila_0/probe15 [get_nets [list ack_error]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe16]
set_property port_width 1 [get_debug_ports u_ila_0/probe16]
connect_debug_port u_ila_0/probe16 [get_nets [list cfg_done_dbg]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe17]
set_property port_width 1 [get_debug_ports u_ila_0/probe17]
connect_debug_port u_ila_0/probe17 [get_nets [list data_valid]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe18]
set_property port_width 1 [get_debug_ports u_ila_0/probe18]
connect_debug_port u_ila_0/probe18 [get_nets [list done]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe19]
set_property port_width 1 [get_debug_ports u_ila_0/probe19]
connect_debug_port u_ila_0/probe19 [get_nets [list i2c_busy]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe20]
set_property port_width 1 [get_debug_ports u_ila_0/probe20]
connect_debug_port u_ila_0/probe20 [get_nets [list scl_drive_low]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe21]
set_property port_width 1 [get_debug_ports u_ila_0/probe21]
connect_debug_port u_ila_0/probe21 [get_nets [list scl_in_dbg]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe22]
set_property port_width 1 [get_debug_ports u_ila_0/probe22]
connect_debug_port u_ila_0/probe22 [get_nets [list sda_drive_low]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe23]
set_property port_width 1 [get_debug_ports u_ila_0/probe23]
connect_debug_port u_ila_0/probe23 [get_nets [list sda_in]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe24]
set_property port_width 1 [get_debug_ports u_ila_0/probe24]
connect_debug_port u_ila_0/probe24 [get_nets [list sda_in_dbg]]
create_debug_port u_ila_0 probe
set_property PROBE_TYPE DATA_AND_TRIGGER [get_debug_ports u_ila_0/probe25]
set_property port_width 1 [get_debug_ports u_ila_0/probe25]
connect_debug_port u_ila_0/probe25 [get_nets [list timeout]]
set_property C_CLK_INPUT_FREQ_HZ 300000000 [get_debug_cores dbg_hub]
set_property C_ENABLE_CLK_DIVIDER false [get_debug_cores dbg_hub]
set_property C_USER_SCAN_CHAIN 1 [get_debug_cores dbg_hub]
connect_debug_port dbg_hub/clk [get_nets clk_IBUF_BUFG]
