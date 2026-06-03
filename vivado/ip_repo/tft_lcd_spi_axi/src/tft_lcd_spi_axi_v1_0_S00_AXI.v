`timescale 1 ns / 1 ps
// -----------------------------------------------------------------------------
// tft_lcd_spi_axi_v1_0_S00_AXI.v
//
// AXI4-Lite slave + SPI LCD byte transmitter.
//
// Register map:
//   0x00 CTRL
//        bit0 : start, write 1 to send one byte
//        bit1 : dc, 0=command, 1=data
//        bit2 : lcd_res, 0=reset, 1=normal
//        bit3 : lcd_blk, 0=backlight off, 1=backlight on
//        bit4 : clear_done, write 1 to clear done_latched
//
//   0x04 DATA
//        bit[7:0] : tx_data
//
//   0x08 CLKDIV
//        bit[15:0] : SPI clock divider
//        SCL = S_AXI_ACLK / (2 * CLKDIV)
//
//   0x0C STATUS
//        bit0 : busy
//        bit1 : done_latched
//        bit2 : done_pulse
//        bit3 : lcd_res state
//        bit4 : lcd_blk state
//        bit5 : dc state
// -----------------------------------------------------------------------------

module tft_lcd_spi_axi_v1_0_S00_AXI #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 5
)(
    // TFT LCD physical interface
    output wire lcd_scl,
    output wire lcd_sda,
    output wire lcd_res,
    output wire lcd_dc,
    output wire lcd_blk,

    // AXI4-Lite slave interface
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

    // -------------------------------------------------------------------------
    // AXI internal signals
    // -------------------------------------------------------------------------
    reg [C_S_AXI_ADDR_WIDTH-1 : 0] axi_awaddr;
    reg                            axi_awready;
    reg                            axi_wready;
    reg [1 : 0]                    axi_bresp;
    reg                            axi_bvalid;
    reg [C_S_AXI_ADDR_WIDTH-1 : 0] axi_araddr;
    reg                            axi_arready;
    reg [C_S_AXI_DATA_WIDTH-1 : 0] axi_rdata;
    reg [1 : 0]                    axi_rresp;
    reg                            axi_rvalid;

    localparam integer ADDR_LSB = (C_S_AXI_DATA_WIDTH/32) + 1;
    localparam integer OPT_MEM_ADDR_BITS = 2; // 8 registers -> address bits [4:2]

    reg aw_en;

    assign S_AXI_AWREADY = axi_awready;
    assign S_AXI_WREADY  = axi_wready;
    assign S_AXI_BRESP   = axi_bresp;
    assign S_AXI_BVALID  = axi_bvalid;
    assign S_AXI_ARREADY = axi_arready;
    assign S_AXI_RDATA   = axi_rdata;
    assign S_AXI_RRESP   = axi_rresp;
    assign S_AXI_RVALID  = axi_rvalid;

    // -------------------------------------------------------------------------
    // User registers
    // -------------------------------------------------------------------------
    reg [31:0] ctrl_reg;
    reg [31:0] data_reg;
    reg [31:0] clkdiv_reg;

    reg        tx_start_pulse;
    reg        done_latched;

    wire       spi_busy;
    wire       spi_done;

    wire [31:0] status_word;

    assign status_word = {
        26'd0,
        ctrl_reg[1],      // bit5 dc state
        ctrl_reg[3],      // bit4 lcd_blk state
        ctrl_reg[2],      // bit3 lcd_res state
        spi_done,         // bit2 done pulse
        done_latched,     // bit1 done latched
        spi_busy          // bit0 busy
    };

    // -------------------------------------------------------------------------
    // AXI write address channel
    // -------------------------------------------------------------------------
    always @(posedge S_AXI_ACLK) begin
        if (S_AXI_ARESETN == 1'b0) begin
            axi_awready <= 1'b0;
            aw_en       <= 1'b1;
        end else begin
            if (~axi_awready && S_AXI_AWVALID && S_AXI_WVALID && aw_en) begin
                axi_awready <= 1'b1;
                aw_en       <= 1'b0;
            end else if (S_AXI_BREADY && axi_bvalid) begin
                aw_en       <= 1'b1;
                axi_awready <= 1'b0;
            end else begin
                axi_awready <= 1'b0;
            end
        end
    end

    always @(posedge S_AXI_ACLK) begin
        if (S_AXI_ARESETN == 1'b0) begin
            axi_awaddr <= {C_S_AXI_ADDR_WIDTH{1'b0}};
        end else begin
            if (~axi_awready && S_AXI_AWVALID && S_AXI_WVALID && aw_en) begin
                axi_awaddr <= S_AXI_AWADDR;
            end
        end
    end

    // -------------------------------------------------------------------------
    // AXI write data channel
    // -------------------------------------------------------------------------
    always @(posedge S_AXI_ACLK) begin
        if (S_AXI_ARESETN == 1'b0) begin
            axi_wready <= 1'b0;
        end else begin
            if (~axi_wready && S_AXI_WVALID && S_AXI_AWVALID && aw_en) begin
                axi_wready <= 1'b1;
            end else begin
                axi_wready <= 1'b0;
            end
        end
    end

    wire slv_reg_wren;
    assign slv_reg_wren = axi_wready && S_AXI_WVALID && axi_awready && S_AXI_AWVALID;

    wire [2:0] wr_addr;
    assign wr_addr = axi_awaddr[ADDR_LSB+OPT_MEM_ADDR_BITS : ADDR_LSB];

    integer byte_index;

    // -------------------------------------------------------------------------
    // User register write logic
    // -------------------------------------------------------------------------
    always @(posedge S_AXI_ACLK) begin
        if (S_AXI_ARESETN == 1'b0) begin
            ctrl_reg       <= 32'h0000_000C; // res=1, blk=1
            data_reg       <= 32'h0000_0000;
            clkdiv_reg     <= 32'h0000_0019; // decimal 25
            tx_start_pulse <= 1'b0;
            done_latched   <= 1'b0;
        end else begin
            tx_start_pulse <= 1'b0;

            if (spi_done) begin
                done_latched <= 1'b1;
            end

            if (slv_reg_wren) begin
                case (wr_addr)

                    // CTRL register
                    3'h0: begin
                        // bit0 is write-only pulse
                        if (S_AXI_WSTRB[0]) begin
                            ctrl_reg[1] <= S_AXI_WDATA[1]; // dc
                            ctrl_reg[2] <= S_AXI_WDATA[2]; // res
                            ctrl_reg[3] <= S_AXI_WDATA[3]; // blk

                            if (S_AXI_WDATA[0] && !spi_busy) begin
                                tx_start_pulse <= 1'b1;
                                done_latched   <= 1'b0;
                            end

                            if (S_AXI_WDATA[4]) begin
                                done_latched <= 1'b0;
                            end
                        end
                    end

                    // DATA register
                    3'h1: begin
                        for (byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index + 1) begin
                            if (S_AXI_WSTRB[byte_index] == 1) begin
                                data_reg[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                            end
                        end
                    end

                    // CLKDIV register
                    3'h2: begin
                        for (byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index + 1) begin
                            if (S_AXI_WSTRB[byte_index] == 1) begin
                                clkdiv_reg[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                            end
                        end
                    end

                    default: begin
                        // Reserved addresses: do nothing
                    end

                endcase
            end
        end
    end

    // -------------------------------------------------------------------------
    // AXI write response channel
    // -------------------------------------------------------------------------
    always @(posedge S_AXI_ACLK) begin
        if (S_AXI_ARESETN == 1'b0) begin
            axi_bvalid <= 1'b0;
            axi_bresp  <= 2'b0;
        end else begin
            if (axi_awready && S_AXI_AWVALID && ~axi_bvalid && axi_wready && S_AXI_WVALID) begin
                axi_bvalid <= 1'b1;
                axi_bresp  <= 2'b00; // OKAY
            end else begin
                if (S_AXI_BREADY && axi_bvalid) begin
                    axi_bvalid <= 1'b0;
                end
            end
        end
    end

    // -------------------------------------------------------------------------
    // AXI read address channel
    // -------------------------------------------------------------------------
    always @(posedge S_AXI_ACLK) begin
        if (S_AXI_ARESETN == 1'b0) begin
            axi_arready <= 1'b0;
            axi_araddr  <= {C_S_AXI_ADDR_WIDTH{1'b0}};
        end else begin
            if (~axi_arready && S_AXI_ARVALID) begin
                axi_arready <= 1'b1;
                axi_araddr  <= S_AXI_ARADDR;
            end else begin
                axi_arready <= 1'b0;
            end
        end
    end

    // -------------------------------------------------------------------------
    // AXI read data channel
    // -------------------------------------------------------------------------
    always @(posedge S_AXI_ACLK) begin
        if (S_AXI_ARESETN == 1'b0) begin
            axi_rvalid <= 1'b0;
            axi_rresp  <= 2'b0;
        end else begin
            if (axi_arready && S_AXI_ARVALID && ~axi_rvalid) begin
                axi_rvalid <= 1'b1;
                axi_rresp  <= 2'b00; // OKAY
            end else if (axi_rvalid && S_AXI_RREADY) begin
                axi_rvalid <= 1'b0;
            end
        end
    end

    wire slv_reg_rden;
    assign slv_reg_rden = axi_arready & S_AXI_ARVALID & ~axi_rvalid;

    wire [2:0] rd_addr;
    assign rd_addr = axi_araddr[ADDR_LSB+OPT_MEM_ADDR_BITS : ADDR_LSB];

    reg [31:0] reg_data_out;

    always @(*) begin
        case (rd_addr)
            3'h0: reg_data_out = ctrl_reg;
            3'h1: reg_data_out = data_reg;
            3'h2: reg_data_out = clkdiv_reg;
            3'h3: reg_data_out = status_word;
            default: reg_data_out = 32'h0000_0000;
        endcase
    end

    always @(posedge S_AXI_ACLK) begin
        if (S_AXI_ARESETN == 1'b0) begin
            axi_rdata <= 32'h0000_0000;
        end else begin
            if (slv_reg_rden) begin
                axi_rdata <= reg_data_out;
            end
        end
    end

    // -------------------------------------------------------------------------
    // SPI LCD master instance
    // -------------------------------------------------------------------------
    spi_lcd_master #(
        .CLK_DIV_DEFAULT(25)
    ) u_spi_lcd_master (
        .clk       (S_AXI_ACLK),
        .rst_n     (S_AXI_ARESETN),

        .tx_data   (data_reg[7:0]),
        .tx_dc     (ctrl_reg[1]),
        .tx_start  (tx_start_pulse),
        .clk_div   (clkdiv_reg[15:0]),

        .lcd_res_in(ctrl_reg[2]),
        .lcd_blk_in(ctrl_reg[3]),

        .lcd_scl   (lcd_scl),
        .lcd_sda   (lcd_sda),
        .lcd_dc    (lcd_dc),
        .lcd_res   (lcd_res),
        .lcd_blk   (lcd_blk),

        .busy      (spi_busy),
        .done      (spi_done)
    );

endmodule