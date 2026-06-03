`timescale 1 ns / 1 ps

module axi_uart_spo2_v1_0_S00_AXI #
(
    parameter integer C_BPS = 9600,
    parameter integer C_SYS_CLK_FRE = 100000000,

    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 5
)
(
    input  wire uart_rxd,
    output wire uart_txd,
    output wire irq,

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

    localparam integer ADDR_LSB = 2;
    localparam integer REG_ADDR_BITS = 2;

    localparam [2:0] REG_CTRL    = 3'd0;
    localparam [2:0] REG_TXDATA  = 3'd1;
    localparam [2:0] REG_STATUS  = 3'd2;
    localparam [2:0] REG_MEASURE = 3'd3;
    localparam [2:0] REG_WAVE    = 3'd4;
    localparam [2:0] REG_FLAGS   = 3'd5;
    localparam [2:0] REG_RAW0    = 3'd6;
    localparam [2:0] REG_RAW1    = 3'd7;

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

    assign S_AXI_AWREADY = axi_awready;
    assign S_AXI_WREADY  = axi_wready;
    assign S_AXI_BRESP   = axi_bresp;
    assign S_AXI_BVALID  = axi_bvalid;
    assign S_AXI_ARREADY = axi_arready;
    assign S_AXI_RDATA   = axi_rdata;
    assign S_AXI_RRESP   = axi_rresp;
    assign S_AXI_RVALID  = axi_rvalid;

    wire write_fire;
    wire read_fire;

    assign write_fire = (~axi_awready) && S_AXI_AWVALID &&
                        (~axi_wready)  && S_AXI_WVALID  &&
                        (~axi_bvalid);

    assign read_fire  = (~axi_arready) && S_AXI_ARVALID &&
                        (~axi_rvalid);

    wire [2:0] write_addr;
    wire [2:0] read_addr;

    assign write_addr = S_AXI_AWADDR[ADDR_LSB + REG_ADDR_BITS : ADDR_LSB];
    assign read_addr  = S_AXI_ARADDR[ADDR_LSB + REG_ADDR_BITS : ADDR_LSB];

    reg [31:0] ctrl_reg;
    reg [7:0]  tx_data_reg;
    reg        tx_start_pulse;

    wire       parser_enable;
    wire       irq_enable;
    wire       frame_mode_7byte;
    wire       clear_sticky_req;

    assign parser_enable   = ctrl_reg[0];
    assign irq_enable      = ctrl_reg[2];
    assign frame_mode_7byte = ctrl_reg[4];

    assign clear_sticky_req = write_fire && (write_addr == REG_CTRL) &&
                              S_AXI_WSTRB[0] && S_AXI_WDATA[1];

    wire [7:0] uart_rx_data_w;
    wire       uart_rx_done_w;
    wire       uart_rx_read_can_w;
    reg        uart_rx_read_done_r;
    wire       tx_busy_w;

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            uart_rx_read_done_r <= 1'b0;
        end else begin
            uart_rx_read_done_r <= uart_rx_done_w;
        end
    end

    uart_rx #(
        .BPS(C_BPS),
        .SYS_CLK_FRE(C_SYS_CLK_FRE)
    ) u_uart_rx (
        .sys_clk(S_AXI_ACLK),
        .sys_rst_n(S_AXI_ARESETN),
        .uart_rxd(uart_rxd),
        .read_done(uart_rx_read_done_r),
        .uart_rx_data(uart_rx_data_w),
        .uart_rx_done(uart_rx_done_w),
        .read_can(uart_rx_read_can_w)
    );

    uart_tx #(
        .BPS(C_BPS),
        .SYS_CLK_FRE(C_SYS_CLK_FRE)
    ) u_uart_tx (
        .sys_clk(S_AXI_ACLK),
        .sys_rst_n(S_AXI_ARESETN),
        .uart_data(tx_data_reg),
        .uart_tx_en(tx_start_pulse),
        .read_can(1'b1),
        .uart_txd(uart_txd),
        .tx_busy(tx_busy_w)
    );

    wire        frame_valid_w;
    wire        frame_error_w;
    wire [3:0]  frame_len_w;
    wire [7:0]  spo2_w;
    wire [7:0]  heart_rate_w;
    wire [7:0]  pleth_w;
    wire [7:0]  bar_graph_w;
    wire [7:0]  perfusion_index_w;
    wire        search_timeout_w;
    wire        sensor_off_w;
    wire        pulse_beep_w;
    wire        sensor_error_w;
    wire        searching_w;
    wire        crc_ok_w;
    wire [6:0]  crc_calc_w;
    wire [6:0]  crc_rx_w;
    wire [31:0] raw0_w;
    wire [31:0] raw1_w;

    spo2_frame_parser u_spo2_frame_parser (
        .clk(S_AXI_ACLK),
        .rst_n(S_AXI_ARESETN),
        .enable(parser_enable),
        .frame_mode_7byte(frame_mode_7byte),
        .rx_data(uart_rx_data_w),
        .rx_valid(uart_rx_done_w),
        .frame_valid(frame_valid_w),
        .frame_error(frame_error_w),
        .frame_len(frame_len_w),
        .spo2(spo2_w),
        .heart_rate(heart_rate_w),
        .pleth(pleth_w),
        .bar_graph(bar_graph_w),
        .perfusion_index(perfusion_index_w),
        .search_timeout(search_timeout_w),
        .sensor_off(sensor_off_w),
        .pulse_beep(pulse_beep_w),
        .sensor_error(sensor_error_w),
        .searching(searching_w),
        .crc_ok(crc_ok_w),
        .crc_calc(crc_calc_w),
        .crc_rx(crc_rx_w),
        .raw0(raw0_w),
        .raw1(raw1_w)
    );

    reg        frame_seen_sticky;
    reg        frame_error_sticky;
    reg        rx_byte_overflow_sticky;
    reg [31:0] frame_count;
    reg [15:0] rx_byte_count;

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            frame_seen_sticky     <= 1'b0;
            frame_error_sticky    <= 1'b0;
            rx_byte_overflow_sticky <= 1'b0;
            frame_count           <= 32'd0;
            rx_byte_count         <= 16'd0;
        end else begin
            if (clear_sticky_req) begin
                frame_seen_sticky       <= 1'b0;
                frame_error_sticky      <= 1'b0;
                rx_byte_overflow_sticky <= 1'b0;
                frame_count             <= 32'd0;
                rx_byte_count           <= 16'd0;
            end else begin
                if (uart_rx_done_w) begin
                    rx_byte_count <= rx_byte_count + 1'b1;
                    if (rx_byte_count == 16'hffff) begin
                        rx_byte_overflow_sticky <= 1'b1;
                    end
                end

                if (frame_valid_w) begin
                    frame_seen_sticky <= 1'b1;
                    frame_count       <= frame_count + 1'b1;
                end

                if (frame_error_w) begin
                    frame_error_sticky <= 1'b1;
                end
            end
        end
    end

    assign irq = irq_enable & frame_seen_sticky;

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            axi_awready <= 1'b0;
            axi_awaddr  <= {C_S_AXI_ADDR_WIDTH{1'b0}};
        end else begin
            if (write_fire) begin
                axi_awready <= 1'b1;
                axi_awaddr  <= S_AXI_AWADDR;
            end else begin
                axi_awready <= 1'b0;
            end
        end
    end

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            axi_wready <= 1'b0;
        end else begin
            if (write_fire) begin
                axi_wready <= 1'b1;
            end else begin
                axi_wready <= 1'b0;
            end
        end
    end

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            axi_bvalid <= 1'b0;
            axi_bresp  <= 2'b00;
        end else begin
            if (write_fire && !axi_bvalid) begin
                axi_bvalid <= 1'b1;
                axi_bresp  <= 2'b00;
            end else if (axi_bvalid && S_AXI_BREADY) begin
                axi_bvalid <= 1'b0;
            end
        end
    end

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            ctrl_reg       <= 32'h0000_0001;
            tx_data_reg    <= 8'd0;
            tx_start_pulse <= 1'b0;
        end else begin
            tx_start_pulse <= 1'b0;

            if (write_fire) begin
                case (write_addr)
                    REG_CTRL: begin
                        if (S_AXI_WSTRB[0]) begin
                            ctrl_reg[0] <= S_AXI_WDATA[0];
                            ctrl_reg[2] <= S_AXI_WDATA[2];
                            ctrl_reg[4] <= S_AXI_WDATA[4];
                        end
                    end

                    REG_TXDATA: begin
                        if (S_AXI_WSTRB[0]) begin
                            tx_data_reg <= S_AXI_WDATA[7:0];
                        end
                        if (S_AXI_WSTRB[1] && S_AXI_WDATA[8] && !tx_busy_w) begin
                            tx_start_pulse <= 1'b1;
                        end
                    end

                    default: begin
                        ctrl_reg       <= ctrl_reg;
                        tx_data_reg    <= tx_data_reg;
                        tx_start_pulse <= tx_start_pulse;
                    end
                endcase
            end
        end
    end

    reg [C_S_AXI_DATA_WIDTH-1:0] reg_data_out;

    always @(*) begin
        case (read_addr)
            REG_CTRL: begin
                reg_data_out = ctrl_reg;
            end

            REG_TXDATA: begin
                reg_data_out = {23'd0, tx_busy_w, tx_data_reg};
            end

            REG_STATUS: begin
                reg_data_out = {
                    9'd0,
                    rx_byte_overflow_sticky,
                    ~tx_busy_w,
                    tx_busy_w,
                    rx_byte_count[3:0],
                    frame_len_w,
                    search_timeout_w,
                    searching_w,
                    sensor_error_w,
                    sensor_off_w,
                    crc_ok_w,
                    frame_error_sticky,
                    frame_seen_sticky
                };
            end

            REG_MEASURE: begin
                reg_data_out = {16'd0, spo2_w, heart_rate_w};
            end

            REG_WAVE: begin
                reg_data_out = {8'd0, perfusion_index_w, bar_graph_w, pleth_w};
            end

            REG_FLAGS: begin
                reg_data_out = {
                    frame_count[15:0],
                    crc_rx_w,
                    crc_calc_w,
                    pulse_beep_w,
                    frame_mode_7byte
                };
            end

            REG_RAW0: begin
                reg_data_out = raw0_w;
            end

            REG_RAW1: begin
                reg_data_out = raw1_w;
            end

            default: begin
                reg_data_out = 32'd0;
            end
        endcase
    end

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            axi_arready <= 1'b0;
            axi_araddr  <= {C_S_AXI_ADDR_WIDTH{1'b0}};
        end else begin
            if (read_fire) begin
                axi_arready <= 1'b1;
                axi_araddr  <= S_AXI_ARADDR;
            end else begin
                axi_arready <= 1'b0;
            end
        end
    end

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            axi_rvalid <= 1'b0;
            axi_rresp  <= 2'b00;
            axi_rdata  <= {C_S_AXI_DATA_WIDTH{1'b0}};
        end else begin
            if (read_fire) begin
                axi_rvalid <= 1'b1;
                axi_rresp  <= 2'b00;
                axi_rdata  <= reg_data_out;
            end else if (axi_rvalid && S_AXI_RREADY) begin
                axi_rvalid <= 1'b0;
            end
        end
    end

endmodule
