`timescale 1ns / 1ps

module axi_lite_regs #(
    parameter C_S_AXI_ADDR_WIDTH = 7,
    parameter C_S_AXI_DATA_WIDTH = 32
) (
    input  wire                              s_axi_aclk,
    input  wire                              s_axi_aresetn,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     s_axi_awaddr,
    input  wire                              s_axi_awvalid,
    output reg                               s_axi_awready,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]     s_axi_wdata,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1:0] s_axi_wstrb,
    input  wire                              s_axi_wvalid,
    output reg                               s_axi_wready,
    output reg  [1:0]                        s_axi_bresp,
    output reg                               s_axi_bvalid,
    input  wire                              s_axi_bready,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]     s_axi_araddr,
    input  wire                              s_axi_arvalid,
    output reg                               s_axi_arready,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]     s_axi_rdata,
    output reg  [1:0]                        s_axi_rresp,
    output reg                               s_axi_rvalid,
    input  wire                              s_axi_rready,

    input  wire                              scl_in,
    input  wire                              sda_in,
    input  wire                              busy,
    input  wire                              done,
    input  wire                              data_valid,
    input  wire                              ack_error,
    input  wire                              timeout,
    input  wire                              cfg_done,
    input  wire [7:0]                        error_code_in,
    input  wire [15:0]                       data0,
    input  wire [15:0]                       data1,
    input  wire [15:0]                       data2,
    input  wire [15:0]                       data3,
    input  wire [15:0]                       data4,
    input  wire [15:0]                       data5,
    input  wire [15:0]                       data6,
    input  wire [15:0]                       data7,
    input  wire [15:0]                       data8,
    input  wire [15:0]                       data9,
    input  wire [15:0]                       data10,
    input  wire [15:0]                       data11,
    input  wire [15:0]                       data12,
    input  wire [31:0]                       sample_cnt,

    output reg                               enable,
    output reg                               auto_mode,
    output reg                               oneshot_start_pulse,
    output reg                               clear_done_pulse,
    output reg                               clear_error_pulse,
    output reg                               soft_reset_pulse,
    output reg                               cfg_write_start_pulse,
    output reg  [6:0]                        dev_addr,
    output reg  [7:0]                        start_reg,
    output reg  [7:0]                        word_count,
    output reg  [31:0]                       sample_period,
    output reg  [15:0]                       i2c_clkdiv,
    output reg  [7:0]                        cfg_reg_addr,
    output reg  [15:0]                       cfg_data
);
    localparam VERSION = 32'h4A593101;

    localparam ADDR_CTRL          = 5'h00;
    localparam ADDR_STATUS        = 5'h01;
    localparam ADDR_DEV_ADDR      = 5'h02;
    localparam ADDR_START_REG     = 5'h03;
    localparam ADDR_WORD_COUNT    = 5'h04;
    localparam ADDR_SAMPLE_PERIOD = 5'h05;
    localparam ADDR_I2C_CLKDIV    = 5'h06;
    localparam ADDR_ERROR_CODE    = 5'h07;
    localparam ADDR_CFG_REG_ADDR  = 5'h08;
    localparam ADDR_CFG_DATA      = 5'h09;
    localparam ADDR_VERSION       = 5'h0A;
    localparam ADDR_DATA_BASE     = 5'h10;
    localparam ADDR_SAMPLE_CNT    = 5'h1D;

    wire write_fire = s_axi_awvalid && s_axi_wvalid && !s_axi_bvalid;
    wire read_fire  = s_axi_arvalid && !s_axi_rvalid;
    wire [4:0] wr_addr = s_axi_awaddr[6:2];
    wire [4:0] rd_addr = s_axi_araddr[6:2];

    reg [31:0] read_mux;

    always @(*) begin
        case (rd_addr)
            ADDR_CTRL:          read_mux = {23'd0, cfg_write_start_pulse, 2'd0, auto_mode, 1'b0, enable};
            ADDR_STATUS:        read_mux = {24'd0, sda_in, scl_in, cfg_done, timeout, ack_error, data_valid, done, busy};
            ADDR_DEV_ADDR:      read_mux = {25'd0, dev_addr};
            ADDR_START_REG:     read_mux = {24'd0, start_reg};
            ADDR_WORD_COUNT:    read_mux = {24'd0, word_count};
            ADDR_SAMPLE_PERIOD: read_mux = sample_period;
            ADDR_I2C_CLKDIV:    read_mux = {16'd0, i2c_clkdiv};
            ADDR_ERROR_CODE:    read_mux = {24'd0, error_code_in};
            ADDR_CFG_REG_ADDR:  read_mux = {24'd0, cfg_reg_addr};
            ADDR_CFG_DATA:      read_mux = {16'd0, cfg_data};
            ADDR_VERSION:       read_mux = VERSION;
            5'h10:              read_mux = {16'd0, data0};
            5'h11:              read_mux = {16'd0, data1};
            5'h12:              read_mux = {16'd0, data2};
            5'h13:              read_mux = {16'd0, data3};
            5'h14:              read_mux = {16'd0, data4};
            5'h15:              read_mux = {16'd0, data5};
            5'h16:              read_mux = {16'd0, data6};
            5'h17:              read_mux = {16'd0, data7};
            5'h18:              read_mux = {16'd0, data8};
            5'h19:              read_mux = {16'd0, data9};
            5'h1A:              read_mux = {16'd0, data10};
            5'h1B:              read_mux = {16'd0, data11};
            5'h1C:              read_mux = {16'd0, data12};
            ADDR_SAMPLE_CNT:    read_mux = sample_cnt;
            default:            read_mux = 32'd0;
        endcase
    end

    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            s_axi_awready <= 1'b0;
            s_axi_wready <= 1'b0;
            s_axi_bresp <= 2'b00;
            s_axi_bvalid <= 1'b0;
            s_axi_arready <= 1'b0;
            s_axi_rdata <= 32'd0;
            s_axi_rresp <= 2'b00;
            s_axi_rvalid <= 1'b0;
            enable <= 1'b0;
            auto_mode <= 1'b0;
            oneshot_start_pulse <= 1'b0;
            clear_done_pulse <= 1'b0;
            clear_error_pulse <= 1'b0;
            soft_reset_pulse <= 1'b0;
            cfg_write_start_pulse <= 1'b0;
            dev_addr <= 7'h50;
            start_reg <= 8'h34;
            word_count <= 8'd13;
            sample_period <= 32'd10_000_000;
            i2c_clkdiv <= 16'd250;
            cfg_reg_addr <= 8'd0;
            cfg_data <= 16'd0;
        end else begin
            oneshot_start_pulse <= 1'b0;
            clear_done_pulse <= 1'b0;
            clear_error_pulse <= 1'b0;
            soft_reset_pulse <= 1'b0;
            cfg_write_start_pulse <= 1'b0;

            s_axi_awready <= write_fire;
            s_axi_wready <= write_fire;
            if (write_fire) begin
                s_axi_bvalid <= 1'b1;
                s_axi_bresp <= 2'b00;
                case (wr_addr)
                    ADDR_CTRL: begin
                        if (s_axi_wstrb[0]) begin
                            enable <= s_axi_wdata[0];
                            oneshot_start_pulse <= s_axi_wdata[1];
                            auto_mode <= s_axi_wdata[2];
                            clear_done_pulse <= s_axi_wdata[3];
                            clear_error_pulse <= s_axi_wdata[4];
                            soft_reset_pulse <= s_axi_wdata[5];
                        end
                        if (s_axi_wstrb[1]) cfg_write_start_pulse <= s_axi_wdata[8];
                    end
                    ADDR_DEV_ADDR:      if (s_axi_wstrb[0]) dev_addr <= s_axi_wdata[6:0];
                    ADDR_START_REG:     if (s_axi_wstrb[0]) start_reg <= s_axi_wdata[7:0];
                    ADDR_WORD_COUNT:    if (s_axi_wstrb[0]) word_count <= s_axi_wdata[7:0];
                    ADDR_SAMPLE_PERIOD: begin
                        if (s_axi_wstrb[0]) sample_period[7:0] <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) sample_period[15:8] <= s_axi_wdata[15:8];
                        if (s_axi_wstrb[2]) sample_period[23:16] <= s_axi_wdata[23:16];
                        if (s_axi_wstrb[3]) sample_period[31:24] <= s_axi_wdata[31:24];
                    end
                    ADDR_I2C_CLKDIV: begin
                        if (s_axi_wstrb[0]) i2c_clkdiv[7:0] <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) i2c_clkdiv[15:8] <= s_axi_wdata[15:8];
                    end
                    ADDR_CFG_REG_ADDR: if (s_axi_wstrb[0]) cfg_reg_addr <= s_axi_wdata[7:0];
                    ADDR_CFG_DATA: begin
                        if (s_axi_wstrb[0]) cfg_data[7:0] <= s_axi_wdata[7:0];
                        if (s_axi_wstrb[1]) cfg_data[15:8] <= s_axi_wdata[15:8];
                    end
                    default: ;
                endcase
            end else if (s_axi_bready) begin
                s_axi_bvalid <= 1'b0;
            end

            s_axi_arready <= read_fire;
            if (read_fire) begin
                s_axi_rvalid <= 1'b1;
                s_axi_rresp <= 2'b00;
                s_axi_rdata <= read_mux;
            end else if (s_axi_rready) begin
                s_axi_rvalid <= 1'b0;
            end
        end
    end
endmodule
