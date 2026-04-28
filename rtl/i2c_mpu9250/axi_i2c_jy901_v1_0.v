`timescale 1ns / 1ps

module axi_i2c_jy901_v1_0 #(
    parameter C_S00_AXI_DATA_WIDTH = 32,
    parameter C_S00_AXI_ADDR_WIDTH = 7
) (
    input  wire                                      s00_axi_aclk,
    input  wire                                      s00_axi_aresetn,
    input  wire [C_S00_AXI_ADDR_WIDTH-1:0]           s00_axi_awaddr,
    input  wire [2:0]                                s00_axi_awprot,
    input  wire                                      s00_axi_awvalid,
    output wire                                      s00_axi_awready,
    input  wire [C_S00_AXI_DATA_WIDTH-1:0]           s00_axi_wdata,
    input  wire [(C_S00_AXI_DATA_WIDTH/8)-1:0]       s00_axi_wstrb,
    input  wire                                      s00_axi_wvalid,
    output wire                                      s00_axi_wready,
    output wire [1:0]                                s00_axi_bresp,
    output wire                                      s00_axi_bvalid,
    input  wire                                      s00_axi_bready,
    input  wire [C_S00_AXI_ADDR_WIDTH-1:0]           s00_axi_araddr,
    input  wire [2:0]                                s00_axi_arprot,
    input  wire                                      s00_axi_arvalid,
    output wire                                      s00_axi_arready,
    output wire [C_S00_AXI_DATA_WIDTH-1:0]           s00_axi_rdata,
    output wire [1:0]                                s00_axi_rresp,
    output wire                                      s00_axi_rvalid,
    input  wire                                      s00_axi_rready,

    inout  wire                                      i2c_scl,
    inout  wire                                      i2c_sda
);
    wire scl_drive_low;
    wire sda_drive_low;
    wire scl_in;
    wire sda_in;

    wire enable;
    wire auto_mode;
    wire oneshot_start_pulse;
    wire clear_done_pulse;
    wire clear_error_pulse;
    wire soft_reset_pulse;
    wire cfg_write_start_pulse;
    wire [6:0] dev_addr;
    wire [7:0] start_reg;
    wire [7:0] word_count;
    wire [31:0] sample_period;
    wire [15:0] i2c_clkdiv;
    wire [7:0] cfg_reg_addr;
    wire [15:0] cfg_data;

    wire busy;
    wire done;
    wire data_valid;
    wire ack_error;
    wire timeout;
    wire cfg_done;
    wire [7:0] error_code;
    wire [15:0] data0;
    wire [15:0] data1;
    wire [15:0] data2;
    wire [15:0] data3;
    wire [15:0] data4;
    wire [15:0] data5;
    wire [15:0] data6;
    wire [15:0] data7;
    wire [15:0] data8;
    wire [15:0] data9;
    wire [15:0] data10;
    wire [15:0] data11;
    wire [15:0] data12;
    wire [31:0] sample_cnt;

    i2c_open_drain_io u_i2c_open_drain_io (
        .scl_drive_low(scl_drive_low),
        .sda_drive_low(sda_drive_low),
        .i2c_scl(i2c_scl),
        .i2c_sda(i2c_sda),
        .scl_in(scl_in),
        .sda_in(sda_in)
    );

    jy901_sampler u_jy901_sampler (
        .clk(s00_axi_aclk),
        .resetn(s00_axi_aresetn),
        .enable(enable),
        .soft_reset(soft_reset_pulse),
        .oneshot_start(oneshot_start_pulse),
        .auto_mode(auto_mode),
        .cfg_write_start(cfg_write_start_pulse),
        .clear_done(clear_done_pulse),
        .clear_error(clear_error_pulse),
        .dev_addr(dev_addr),
        .start_reg(start_reg),
        .word_count(word_count),
        .sample_period(sample_period),
        .i2c_clkdiv(i2c_clkdiv),
        .cfg_reg_addr(cfg_reg_addr),
        .cfg_data(cfg_data),
        .scl_in(scl_in),
        .sda_in(sda_in),
        .scl_drive_low(scl_drive_low),
        .sda_drive_low(sda_drive_low),
        .i2c_busy(busy),
        .done(done),
        .data_valid(data_valid),
        .ack_error(ack_error),
        .timeout(timeout),
        .cfg_done(cfg_done),
        .error_code(error_code),
        .data0(data0),
        .data1(data1),
        .data2(data2),
        .data3(data3),
        .data4(data4),
        .data5(data5),
        .data6(data6),
        .data7(data7),
        .data8(data8),
        .data9(data9),
        .data10(data10),
        .data11(data11),
        .data12(data12),
        .sample_cnt(sample_cnt)
    );

    axi_lite_regs #(
        .C_S_AXI_ADDR_WIDTH(C_S00_AXI_ADDR_WIDTH),
        .C_S_AXI_DATA_WIDTH(C_S00_AXI_DATA_WIDTH)
    ) u_axi_lite_regs (
        .s_axi_aclk(s00_axi_aclk),
        .s_axi_aresetn(s00_axi_aresetn),
        .s_axi_awaddr(s00_axi_awaddr),
        .s_axi_awvalid(s00_axi_awvalid),
        .s_axi_awready(s00_axi_awready),
        .s_axi_wdata(s00_axi_wdata),
        .s_axi_wstrb(s00_axi_wstrb),
        .s_axi_wvalid(s00_axi_wvalid),
        .s_axi_wready(s00_axi_wready),
        .s_axi_bresp(s00_axi_bresp),
        .s_axi_bvalid(s00_axi_bvalid),
        .s_axi_bready(s00_axi_bready),
        .s_axi_araddr(s00_axi_araddr),
        .s_axi_arvalid(s00_axi_arvalid),
        .s_axi_arready(s00_axi_arready),
        .s_axi_rdata(s00_axi_rdata),
        .s_axi_rresp(s00_axi_rresp),
        .s_axi_rvalid(s00_axi_rvalid),
        .s_axi_rready(s00_axi_rready),
        .scl_in(scl_in),
        .sda_in(sda_in),
        .busy(busy),
        .done(done),
        .data_valid(data_valid),
        .ack_error(ack_error),
        .timeout(timeout),
        .cfg_done(cfg_done),
        .error_code_in(error_code),
        .data0(data0),
        .data1(data1),
        .data2(data2),
        .data3(data3),
        .data4(data4),
        .data5(data5),
        .data6(data6),
        .data7(data7),
        .data8(data8),
        .data9(data9),
        .data10(data10),
        .data11(data11),
        .data12(data12),
        .sample_cnt(sample_cnt),
        .enable(enable),
        .auto_mode(auto_mode),
        .oneshot_start_pulse(oneshot_start_pulse),
        .clear_done_pulse(clear_done_pulse),
        .clear_error_pulse(clear_error_pulse),
        .soft_reset_pulse(soft_reset_pulse),
        .cfg_write_start_pulse(cfg_write_start_pulse),
        .dev_addr(dev_addr),
        .start_reg(start_reg),
        .word_count(word_count),
        .sample_period(sample_period),
        .i2c_clkdiv(i2c_clkdiv),
        .cfg_reg_addr(cfg_reg_addr),
        .cfg_data(cfg_data)
    );
endmodule
