`timescale 1ns/1ns

module gree_ir_axi_v1_0_S00_AXI #
(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 5,
    parameter integer CORE_CLK_FREQ      = 100_000_000,
    parameter integer CORE_CLK_1US       = 100,
    parameter integer CORE_CARRIER_HZ    = 38_000
)
(
    output wire ir_pwm,

    input  wire                                  S_AXI_ACLK,
    input  wire                                  S_AXI_ARESETN,
    input  wire [C_S_AXI_ADDR_WIDTH-1 : 0]       S_AXI_AWADDR,
    input  wire [2 : 0]                          S_AXI_AWPROT,
    input  wire                                  S_AXI_AWVALID,
    output wire                                  S_AXI_AWREADY,
    input  wire [C_S_AXI_DATA_WIDTH-1 : 0]       S_AXI_WDATA,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1 : 0]   S_AXI_WSTRB,
    input  wire                                  S_AXI_WVALID,
    output wire                                  S_AXI_WREADY,
    output wire [1 : 0]                          S_AXI_BRESP,
    output wire                                  S_AXI_BVALID,
    input  wire                                  S_AXI_BREADY,
    input  wire [C_S_AXI_ADDR_WIDTH-1 : 0]       S_AXI_ARADDR,
    input  wire [2 : 0]                          S_AXI_ARPROT,
    input  wire                                  S_AXI_ARVALID,
    output wire                                  S_AXI_ARREADY,
    output wire [C_S_AXI_DATA_WIDTH-1 : 0]       S_AXI_RDATA,
    output wire [1 : 0]                          S_AXI_RRESP,
    output wire                                  S_AXI_RVALID,
    input  wire                                  S_AXI_RREADY
);

localparam integer ADDR_LSB = (C_S_AXI_DATA_WIDTH / 32) + 1;
localparam integer OPT_MEM_ADDR_BITS = 2; // 6 registers, 0x00 through 0x14

localparam [2:0] REG_CONTROL  = 3'd0; // 0x00
localparam [2:0] REG_STATUS   = 3'd1; // 0x04
localparam [2:0] REG_CMD_LOW  = 3'd2; // 0x08
localparam [2:0] REG_CMD_HIGH = 3'd3; // 0x0C
localparam [2:0] REG_PRESET   = 3'd4; // 0x10
localparam [2:0] REG_DEBUG    = 3'd5; // 0x14

// Low 64 bits of the seven 67-bit YB0F2 preset identifiers. The complete
// transmit waveforms are stored in gree_ir_core.v.
localparam [63:0] CMD_POWER_ON  = 64'h090040A400080016; // preset 1, 0x1090040A400080016
localparam [63:0] CMD_POWER_OFF = 64'h050040A40008001C; // preset 2, 0x8050040A40008001C
localparam [63:0] CMD_TEMP_24   = 64'h010040A400080016; // preset 3, 0x9010040A400080016
localparam [63:0] CMD_TEMP_25   = 64'h090040A40008000E; // preset 4, 0x9090040A40008000E
localparam [63:0] CMD_TEMP_26   = 64'h050040A40008001E; // preset 5, 0x9050040A40008001E
localparam [63:0] CMD_TEMP_27   = 64'h0D0040A400080000; // preset 6, 0x90D0040A400080000
localparam [63:0] CMD_TEMP_28   = 64'h030040A400080010; // preset 7, 0x9030040A400080010

reg [C_S_AXI_ADDR_WIDTH-1 : 0] axi_awaddr;
reg axi_awready;
reg axi_wready;
reg [1 : 0] axi_bresp;
reg axi_bvalid;
reg [C_S_AXI_ADDR_WIDTH-1 : 0] axi_araddr;
reg axi_arready;
reg [C_S_AXI_DATA_WIDTH-1 : 0] axi_rdata;
reg [1 : 0] axi_rresp;
reg axi_rvalid;
reg aw_en;

reg [31:0] slv_reg0_control;
reg [31:0] slv_reg2_cmd_low;
reg [31:0] slv_reg3_cmd_high;
reg [31:0] slv_reg4_preset;

reg core_start_pulse;
reg soft_reset_pulse;
reg done_latched;
reg error_latched;

wire slv_reg_wren;
wire slv_reg_rden;
wire [2:0] write_reg_index;
wire [2:0] read_reg_index;
wire [31:0] status_reg;
wire [31:0] debug_reg;
wire [31:0] reg_data_out;
wire core_busy;
wire core_done;
wire [3:0] debug_state;
wire [9:0] debug_bit_cnt;
wire core_rst_n;
wire [2:0] core_preset;

assign S_AXI_AWREADY = axi_awready;
assign S_AXI_WREADY  = axi_wready;
assign S_AXI_BRESP   = axi_bresp;
assign S_AXI_BVALID  = axi_bvalid;
assign S_AXI_ARREADY = axi_arready;
assign S_AXI_RDATA   = axi_rdata;
assign S_AXI_RRESP   = axi_rresp;
assign S_AXI_RVALID  = axi_rvalid;

assign slv_reg_wren = axi_wready && S_AXI_WVALID && axi_awready && S_AXI_AWVALID;
assign slv_reg_rden = axi_arready && S_AXI_ARVALID && !axi_rvalid;
assign write_reg_index = axi_awaddr[ADDR_LSB + OPT_MEM_ADDR_BITS : ADDR_LSB];
assign read_reg_index = axi_araddr[ADDR_LSB + OPT_MEM_ADDR_BITS : ADDR_LSB];

assign status_reg = {29'd0, error_latched, done_latched, core_busy};
assign debug_reg = {14'd0, debug_bit_cnt, 4'd0, debug_state};
assign core_rst_n = S_AXI_ARESETN && !soft_reset_pulse;
assign core_preset = (slv_reg4_preset >= 32'd1 && slv_reg4_preset <= 32'd7) ? slv_reg4_preset[2:0] : 3'd1;

assign reg_data_out =
    (read_reg_index == REG_CONTROL)  ? slv_reg0_control :
    (read_reg_index == REG_STATUS)   ? status_reg :
    (read_reg_index == REG_CMD_LOW)  ? slv_reg2_cmd_low :
    (read_reg_index == REG_CMD_HIGH) ? slv_reg3_cmd_high :
    (read_reg_index == REG_PRESET)   ? slv_reg4_preset :
    (read_reg_index == REG_DEBUG)    ? debug_reg :
    32'd0;

gree_ir_core #(
    .CLK_FREQ(CORE_CLK_FREQ),
    .CLK_1US(CORE_CLK_1US),
    .CARRIER_HZ(CORE_CARRIER_HZ)
) ir_core (
    .clk(S_AXI_ACLK),
    .rst_n(core_rst_n),
    .start(core_start_pulse),
    .preset(core_preset),
    .busy(core_busy),
    .done(core_done),
    .ir_pwm(ir_pwm),
    .debug_state(debug_state),
    .debug_bit_cnt(debug_bit_cnt)
);

always @(posedge S_AXI_ACLK) begin
    if(!S_AXI_ARESETN) begin
        axi_awready <= 1'b0;
        aw_en <= 1'b1;
    end else begin
        if(!axi_awready && S_AXI_AWVALID && S_AXI_WVALID && aw_en) begin
            axi_awready <= 1'b1;
            aw_en <= 1'b0;
        end else if(S_AXI_BREADY && axi_bvalid) begin
            aw_en <= 1'b1;
            axi_awready <= 1'b0;
        end else begin
            axi_awready <= 1'b0;
        end
    end
end

always @(posedge S_AXI_ACLK) begin
    if(!S_AXI_ARESETN)
        axi_awaddr <= 0;
    else if(!axi_awready && S_AXI_AWVALID && S_AXI_WVALID && aw_en)
        axi_awaddr <= S_AXI_AWADDR;
end

always @(posedge S_AXI_ACLK) begin
    if(!S_AXI_ARESETN)
        axi_wready <= 1'b0;
    else if(!axi_wready && S_AXI_WVALID && S_AXI_AWVALID && aw_en)
        axi_wready <= 1'b1;
    else
        axi_wready <= 1'b0;
end

always @(posedge S_AXI_ACLK) begin
    if(!S_AXI_ARESETN) begin
        slv_reg0_control <= 32'd0;
        slv_reg2_cmd_low <= CMD_POWER_ON[31:0];
        slv_reg3_cmd_high <= CMD_POWER_ON[63:32];
        slv_reg4_preset <= 32'd1;
        core_start_pulse <= 1'b0;
        soft_reset_pulse <= 1'b0;
        done_latched <= 1'b0;
        error_latched <= 1'b0;
    end else begin
        slv_reg0_control <= 32'd0;
        core_start_pulse <= 1'b0;
        soft_reset_pulse <= 1'b0;

        if(core_done)
            done_latched <= 1'b1;

        if(slv_reg_wren) begin
            case(write_reg_index)
                REG_CONTROL: begin
                    slv_reg0_control <= S_AXI_WDATA;
                    core_start_pulse <= S_AXI_WDATA[0] && !core_busy;
                    soft_reset_pulse <= S_AXI_WDATA[1];
                    if(S_AXI_WDATA[1]) begin
                        done_latched <= 1'b0;
                        error_latched <= 1'b0;
                    end
                    if(S_AXI_WDATA[0] && core_busy)
                        error_latched <= 1'b1;
                end

                REG_STATUS: begin
                    // Write 1 to STATUS bit[1] to clear done_latched.
                    if(S_AXI_WDATA[1])
                        done_latched <= 1'b0;
                    if(S_AXI_WDATA[2])
                        error_latched <= 1'b0;
                end

                REG_CMD_LOW: begin
                    if(S_AXI_WSTRB[0]) slv_reg2_cmd_low[7:0]   <= S_AXI_WDATA[7:0];
                    if(S_AXI_WSTRB[1]) slv_reg2_cmd_low[15:8]  <= S_AXI_WDATA[15:8];
                    if(S_AXI_WSTRB[2]) slv_reg2_cmd_low[23:16] <= S_AXI_WDATA[23:16];
                    if(S_AXI_WSTRB[3]) slv_reg2_cmd_low[31:24] <= S_AXI_WDATA[31:24];
                    slv_reg4_preset <= 32'd0;
                end

                REG_CMD_HIGH: begin
                    if(S_AXI_WSTRB[0]) slv_reg3_cmd_high[7:0]   <= S_AXI_WDATA[7:0];
                    if(S_AXI_WSTRB[1]) slv_reg3_cmd_high[15:8]  <= S_AXI_WDATA[15:8];
                    if(S_AXI_WSTRB[2]) slv_reg3_cmd_high[23:16] <= S_AXI_WDATA[23:16];
                    if(S_AXI_WSTRB[3]) slv_reg3_cmd_high[31:24] <= S_AXI_WDATA[31:24];
                    slv_reg4_preset <= 32'd0;
                end

                REG_PRESET: begin
                    case(S_AXI_WDATA)
                        32'd1: begin
                            slv_reg4_preset <= 32'd1;
                            slv_reg2_cmd_low <= CMD_POWER_ON[31:0];
                            slv_reg3_cmd_high <= CMD_POWER_ON[63:32];
                        end
                        32'd2: begin
                            slv_reg4_preset <= 32'd2;
                            slv_reg2_cmd_low <= CMD_POWER_OFF[31:0];
                            slv_reg3_cmd_high <= CMD_POWER_OFF[63:32];
                        end
                        32'd3: begin
                            slv_reg4_preset <= 32'd3;
                            slv_reg2_cmd_low <= CMD_TEMP_24[31:0];
                            slv_reg3_cmd_high <= CMD_TEMP_24[63:32];
                        end
                        32'd4: begin
                            slv_reg4_preset <= 32'd4;
                            slv_reg2_cmd_low <= CMD_TEMP_25[31:0];
                            slv_reg3_cmd_high <= CMD_TEMP_25[63:32];
                        end
                        32'd5: begin
                            slv_reg4_preset <= 32'd5;
                            slv_reg2_cmd_low <= CMD_TEMP_26[31:0];
                            slv_reg3_cmd_high <= CMD_TEMP_26[63:32];
                        end
                        32'd6: begin
                            slv_reg4_preset <= 32'd6;
                            slv_reg2_cmd_low <= CMD_TEMP_27[31:0];
                            slv_reg3_cmd_high <= CMD_TEMP_27[63:32];
                        end
                        32'd7: begin
                            slv_reg4_preset <= 32'd7;
                            slv_reg2_cmd_low <= CMD_TEMP_28[31:0];
                            slv_reg3_cmd_high <= CMD_TEMP_28[63:32];
                        end
                        default: begin
                            slv_reg4_preset <= 32'd0;
                        end
                    endcase
                end

                default: begin
                end
            endcase
        end
    end
end

always @(posedge S_AXI_ACLK) begin
    if(!S_AXI_ARESETN) begin
        axi_bvalid <= 1'b0;
        axi_bresp <= 2'b00;
    end else begin
        if(axi_awready && S_AXI_AWVALID && !axi_bvalid && axi_wready && S_AXI_WVALID) begin
            axi_bvalid <= 1'b1;
            axi_bresp <= 2'b00;
        end else if(S_AXI_BREADY && axi_bvalid) begin
            axi_bvalid <= 1'b0;
        end
    end
end

always @(posedge S_AXI_ACLK) begin
    if(!S_AXI_ARESETN) begin
        axi_arready <= 1'b0;
        axi_araddr <= 0;
    end else begin
        if(!axi_arready && S_AXI_ARVALID) begin
            axi_arready <= 1'b1;
            axi_araddr <= S_AXI_ARADDR;
        end else begin
            axi_arready <= 1'b0;
        end
    end
end

always @(posedge S_AXI_ACLK) begin
    if(!S_AXI_ARESETN) begin
        axi_rvalid <= 1'b0;
        axi_rresp <= 2'b00;
    end else begin
        if(slv_reg_rden) begin
            axi_rvalid <= 1'b1;
            axi_rresp <= 2'b00;
        end else if(axi_rvalid && S_AXI_RREADY) begin
            axi_rvalid <= 1'b0;
        end
    end
end

always @(posedge S_AXI_ACLK) begin
    if(!S_AXI_ARESETN)
        axi_rdata <= 0;
    else if(slv_reg_rden)
        axi_rdata <= reg_data_out;
end

endmodule
