`timescale 1 ns / 1 ps

module dht11_axi_v1_0_S00_AXI #
(
    // Users to add parameters here

    // User parameters ends
    // Do not modify the parameters beyond this line

    // Width of S_AXI data bus
    parameter integer C_S_AXI_DATA_WIDTH = 32,

    // Width of S_AXI address bus
    parameter integer C_S_AXI_ADDR_WIDTH = 4
)
(
    // Users to add ports here
    inout wire dht11,
    // User ports ends
    // Do not modify the ports beyond this line

    // Global Clock Signal
    input wire  S_AXI_ACLK,

    // Global Reset Signal. This Signal is Active LOW
    input wire  S_AXI_ARESETN,

    // Write address
    input wire [C_S_AXI_ADDR_WIDTH-1 : 0] S_AXI_AWADDR,

    // Write channel Protection type
    input wire [2 : 0] S_AXI_AWPROT,

    // Write address valid
    input wire  S_AXI_AWVALID,

    // Write address ready
    output wire  S_AXI_AWREADY,

    // Write data
    input wire [C_S_AXI_DATA_WIDTH-1 : 0] S_AXI_WDATA,

    // Write strobes
    input wire [(C_S_AXI_DATA_WIDTH/8)-1 : 0] S_AXI_WSTRB,

    // Write valid
    input wire  S_AXI_WVALID,

    // Write ready
    output wire  S_AXI_WREADY,

    // Write response
    output wire [1 : 0] S_AXI_BRESP,

    // Write response valid
    output wire  S_AXI_BVALID,

    // Response ready
    input wire  S_AXI_BREADY,

    // Read address
    input wire [C_S_AXI_ADDR_WIDTH-1 : 0] S_AXI_ARADDR,

    // Protection type
    input wire [2 : 0] S_AXI_ARPROT,

    // Read address valid
    input wire  S_AXI_ARVALID,

    // Read address ready
    output wire  S_AXI_ARREADY,

    // Read data
    output wire [C_S_AXI_DATA_WIDTH-1 : 0] S_AXI_RDATA,

    // Read response
    output wire [1 : 0] S_AXI_RRESP,

    // Read valid
    output wire  S_AXI_RVALID,

    // Read ready
    input wire  S_AXI_RREADY
);

    // AXI4LITE signals
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

    // Addressing constants
    localparam integer ADDR_LSB = (C_S_AXI_DATA_WIDTH/32) + 1;
    localparam integer OPT_MEM_ADDR_BITS = 1;

    //----------------------------------------------
    //-- Signals for user logic register space
    //----------------------------------------------
    reg [C_S_AXI_DATA_WIDTH-1:0] slv_reg0;
    reg [C_S_AXI_DATA_WIDTH-1:0] slv_reg1;
    reg [C_S_AXI_DATA_WIDTH-1:0] slv_reg2;
    reg [C_S_AXI_DATA_WIDTH-1:0] slv_reg3;

    wire slv_reg_rden;
    wire slv_reg_wren;
    reg [C_S_AXI_DATA_WIDTH-1:0] reg_data_out;
    integer byte_index;
    reg aw_en;

    //----------------------------------------------
    // DHT11 core wires
    //----------------------------------------------
    wire        dht_raw_dbg;
    wire [3:0]  cur_state_dbg;
    wire [5:0]  bit_cnt_dbg;
    wire [21:0] count_1us_dbg;
    wire        recv_phase_dbg;
    wire        dht_sync_dbg;
    wire        dht_us_d0_dbg;
    wire        dht_out_en_dbg;
    wire        dht_out_val_dbg;
    wire [31:0] dht11_data;

    //----------------------------------------------
    // DHT11 core instance
    //----------------------------------------------
    dht11_onewire dht11_core_inst (
        .clk            (S_AXI_ACLK),
        .rst_n          (S_AXI_ARESETN),
        .dht11          (dht11),

        .dht_raw_dbg    (dht_raw_dbg),
        .cur_state_dbg  (cur_state_dbg),
        .bit_cnt_dbg    (bit_cnt_dbg),
        .count_1us_dbg  (count_1us_dbg),
        .recv_phase_dbg (recv_phase_dbg),
        .dht_sync_dbg   (dht_sync_dbg),
        .dht_us_d0_dbg  (dht_us_d0_dbg),
        .dht_out_en_dbg (dht_out_en_dbg),
        .dht_out_val_dbg(dht_out_val_dbg),

        .data_valid     (dht11_data)
    );

    //----------------------------------------------
    // I/O Connections assignments
    //----------------------------------------------
    assign S_AXI_AWREADY = axi_awready;
    assign S_AXI_WREADY  = axi_wready;
    assign S_AXI_BRESP   = axi_bresp;
    assign S_AXI_BVALID  = axi_bvalid;
    assign S_AXI_ARREADY = axi_arready;
    assign S_AXI_RDATA   = axi_rdata;
    assign S_AXI_RRESP   = axi_rresp;
    assign S_AXI_RVALID  = axi_rvalid;

    //----------------------------------------------
    // Implement axi_awready generation
    //----------------------------------------------
    always @(posedge S_AXI_ACLK)
    begin
        if (S_AXI_ARESETN == 1'b0)
        begin
            axi_awready <= 1'b0;
            aw_en <= 1'b1;
        end
        else
        begin
            if (~axi_awready && S_AXI_AWVALID && S_AXI_WVALID && aw_en)
            begin
                axi_awready <= 1'b1;
                aw_en <= 1'b0;
            end
            else if (S_AXI_BREADY && axi_bvalid)
            begin
                aw_en <= 1'b1;
                axi_awready <= 1'b0;
            end
            else
            begin
                axi_awready <= 1'b0;
            end
        end
    end

    //----------------------------------------------
    // Implement axi_awaddr latching
    //----------------------------------------------
    always @(posedge S_AXI_ACLK)
    begin
        if (S_AXI_ARESETN == 1'b0)
        begin
            axi_awaddr <= 0;
        end
        else
        begin
            if (~axi_awready && S_AXI_AWVALID && S_AXI_WVALID && aw_en)
            begin
                axi_awaddr <= S_AXI_AWADDR;
            end
        end
    end

    //----------------------------------------------
    // Implement axi_wready generation
    //----------------------------------------------
    always @(posedge S_AXI_ACLK)
    begin
        if (S_AXI_ARESETN == 1'b0)
        begin
            axi_wready <= 1'b0;
        end
        else
        begin
            if (~axi_wready && S_AXI_WVALID && S_AXI_AWVALID && aw_en)
            begin
                axi_wready <= 1'b1;
            end
            else
            begin
                axi_wready <= 1'b0;
            end
        end
    end

    //----------------------------------------------
    // Implement memory mapped register select and write logic
    //----------------------------------------------
    assign slv_reg_wren = axi_wready && S_AXI_WVALID && axi_awready && S_AXI_AWVALID;

    always @(posedge S_AXI_ACLK)
    begin
        if (S_AXI_ARESETN == 1'b0)
        begin
            slv_reg0 <= 0;
            slv_reg1 <= 0;
            slv_reg2 <= 0;
            slv_reg3 <= 0;
        end
        else
        begin
            if (slv_reg_wren)
            begin
                case (axi_awaddr[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB])
                    2'h0:
                    begin
                        for (byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index + 1)
                        begin
                            if (S_AXI_WSTRB[byte_index] == 1)
                                slv_reg0[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                        end
                    end

                    2'h1:
                    begin
                        for (byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index + 1)
                        begin
                            if (S_AXI_WSTRB[byte_index] == 1)
                                slv_reg1[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                        end
                    end

                    2'h2:
                    begin
                        for (byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index + 1)
                        begin
                            if (S_AXI_WSTRB[byte_index] == 1)
                                slv_reg2[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                        end
                    end

                    2'h3:
                    begin
                        for (byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index + 1)
                        begin
                            if (S_AXI_WSTRB[byte_index] == 1)
                                slv_reg3[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                        end
                    end

                    default:
                    begin
                        slv_reg0 <= slv_reg0;
                        slv_reg1 <= slv_reg1;
                        slv_reg2 <= slv_reg2;
                        slv_reg3 <= slv_reg3;
                    end
                endcase
            end
        end
    end

    //----------------------------------------------
    // Implement write response logic generation
    //----------------------------------------------
    always @(posedge S_AXI_ACLK)
    begin
        if (S_AXI_ARESETN == 1'b0)
        begin
            axi_bvalid <= 0;
            axi_bresp  <= 2'b0;
        end
        else
        begin
            if (axi_awready && S_AXI_AWVALID && ~axi_bvalid && axi_wready && S_AXI_WVALID)
            begin
                axi_bvalid <= 1'b1;
                axi_bresp  <= 2'b0;
            end
            else
            begin
                if (S_AXI_BREADY && axi_bvalid)
                begin
                    axi_bvalid <= 1'b0;
                end
            end
        end
    end

    //----------------------------------------------
    // Implement axi_arready generation
    //----------------------------------------------
    always @(posedge S_AXI_ACLK)
    begin
        if (S_AXI_ARESETN == 1'b0)
        begin
            axi_arready <= 1'b0;
            axi_araddr  <= 0;
        end
        else
        begin
            if (~axi_arready && S_AXI_ARVALID)
            begin
                axi_arready <= 1'b1;
                axi_araddr  <= S_AXI_ARADDR;
            end
            else
            begin
                axi_arready <= 1'b0;
            end
        end
    end

    //----------------------------------------------
    // Implement axi_rvalid generation
    //----------------------------------------------
    always @(posedge S_AXI_ACLK)
    begin
        if (S_AXI_ARESETN == 1'b0)
        begin
            axi_rvalid <= 0;
            axi_rresp  <= 0;
        end
        else
        begin
            if (axi_arready && S_AXI_ARVALID && ~axi_rvalid)
            begin
                axi_rvalid <= 1'b1;
                axi_rresp  <= 2'b0;
            end
            else if (axi_rvalid && S_AXI_RREADY)
            begin
                axi_rvalid <= 1'b0;
            end
        end
    end

    //----------------------------------------------
    // 核心：读取寄存器部分
    //----------------------------------------------
    assign slv_reg_rden = axi_arready & S_AXI_ARVALID & ~axi_rvalid;

    always @(*)
    begin
        case (axi_araddr[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB])
            // 0x00: DHT11 valid data
            // data format: {humidity_int, humidity_dec, temperature_int, temperature_dec}
            2'h0:
                reg_data_out = dht11_data;

            // 0x04: debug/status register
            // [31:28] cur_state
            // [27:22] bit_cnt
            // [21]    dht_raw
            // [20]    dht_sync
            // [19]    dht_us_d0
            // [18]    dht_out_en
            // [17]    dht_out_val
            // [16]    recv_phase
            // [15:0]  reserved
            2'h1:
                reg_data_out = {
                    cur_state_dbg,
                    bit_cnt_dbg,
                    dht_raw_dbg,
                    dht_sync_dbg,
                    dht_us_d0_dbg,
                    dht_out_en_dbg,
                    dht_out_val_dbg,
                    recv_phase_dbg,
                    16'd0
                };

            // 0x08: count_1us debug
            2'h2:
                reg_data_out = {10'd0, count_1us_dbg};

            // 0x0C: reserved writable register
            2'h3:
                reg_data_out = slv_reg3;

            default:
                reg_data_out = 32'd0;
        endcase
    end

    //----------------------------------------------
    // Output register or memory read data
    //----------------------------------------------
    always @(posedge S_AXI_ACLK)
    begin
        if (S_AXI_ARESETN == 1'b0)
        begin
            axi_rdata <= 0;
        end
        else
        begin
            if (slv_reg_rden)
            begin
                axi_rdata <= reg_data_out;
            end
        end
    end

    // Add user logic here

    // User logic ends

endmodule