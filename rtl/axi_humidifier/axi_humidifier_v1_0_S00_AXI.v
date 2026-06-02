`timescale 1 ns / 1 ps
//////////////////////////////////////////////////////////////////////////////////
// AXI4-Lite slave wrapper for humidifier_core.
// Register map:
// 0x00 CTRL      bit0 enable, bit1 manual_mode, bit2 manual_on,
//                bit3 use_sw_humidity, bit4 clear_counter(write pulse)
// 0x04 SW_HUM    [7:0] software humidity value
// 0x08 THRESH    [7:0] threshold_low, [15:8] hysteresis, [31:16] dry_alert_s
// 0x0C TIMING    [15:0] min_on_s, [31:16] min_off_s
// 0x10 STATUS    read-only: [7:0] current_humidity, [8] humidifier_on,
//                [10:9] dry_level, [15:12] leds, [31:16] status_code[15:0]
// 0x14 DRY_SEC   read-only dry seconds
// 0x18 VERSION   read-only 0x20260601
//////////////////////////////////////////////////////////////////////////////////

module axi_humidifier_v1_0_S00_AXI #(
    parameter integer C_S_AXI_DATA_WIDTH = 32,
    parameter integer C_S_AXI_ADDR_WIDTH = 5,
    parameter integer CLK_FREQ_HZ = 100_000_000
)(
    input  wire        humidity_hw_valid,
    input  wire [7:0]  humidity_hw,
    output wire        humidifier_led,
    output wire [3:0]  humidifier_leds,

    input  wire                              S_AXI_ACLK,
    input  wire                              S_AXI_ARESETN,
    input  wire [C_S_AXI_ADDR_WIDTH-1 : 0]   S_AXI_AWADDR,
    input  wire [2 : 0]                      S_AXI_AWPROT,
    input  wire                              S_AXI_AWVALID,
    output reg                               S_AXI_AWREADY,
    input  wire [C_S_AXI_DATA_WIDTH-1 : 0]   S_AXI_WDATA,
    input  wire [(C_S_AXI_DATA_WIDTH/8)-1:0] S_AXI_WSTRB,
    input  wire                              S_AXI_WVALID,
    output reg                               S_AXI_WREADY,
    output wire [1 : 0]                      S_AXI_BRESP,
    output reg                               S_AXI_BVALID,
    input  wire                              S_AXI_BREADY,
    input  wire [C_S_AXI_ADDR_WIDTH-1 : 0]   S_AXI_ARADDR,
    input  wire [2 : 0]                      S_AXI_ARPROT,
    input  wire                              S_AXI_ARVALID,
    output reg                               S_AXI_ARREADY,
    output reg [C_S_AXI_DATA_WIDTH-1 : 0]    S_AXI_RDATA,
    output wire [1 : 0]                      S_AXI_RRESP,
    output reg                               S_AXI_RVALID,
    input  wire                              S_AXI_RREADY
);

    localparam integer ADDR_LSB = (C_S_AXI_DATA_WIDTH/32) + 1; // 2 for 32-bit
    localparam integer OPT_MEM_ADDR_BITS = 2; // 8 registers max

    reg [C_S_AXI_ADDR_WIDTH-1:0] axi_awaddr;
    reg [C_S_AXI_ADDR_WIDTH-1:0] axi_araddr;

    reg [31:0] slv_reg0; // CTRL
    reg [31:0] slv_reg1; // SW_HUM
    reg [31:0] slv_reg2; // THRESH
    reg [31:0] slv_reg3; // TIMING

    wire slv_reg_wren;
    wire slv_reg_rden;
    reg  [31:0] reg_data_out;
    integer byte_index;

    wire        enable          = slv_reg0[0];
    wire        manual_mode     = slv_reg0[1];
    wire        manual_on       = slv_reg0[2];
    wire        use_sw_humidity = slv_reg0[3];
    reg         clear_counter_pulse;

    wire [7:0]  sw_humidity     = slv_reg1[7:0];
    wire [7:0]  threshold_low   = slv_reg2[7:0];
    wire [7:0]  hysteresis      = slv_reg2[15:8];
    wire [15:0] dry_alert_s     = slv_reg2[31:16];
    wire [15:0] min_on_s        = slv_reg3[15:0];
    wire [15:0] min_off_s       = slv_reg3[31:16];

    wire        core_humidifier_on;
    wire [7:0]  current_humidity;
    wire [1:0]  dry_level;
    wire [31:0] dry_seconds;
    wire [31:0] status_code;

    assign S_AXI_BRESP = 2'b00;
    assign S_AXI_RRESP = 2'b00;
    assign humidifier_led = core_humidifier_on;

    // AWREADY
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_AWREADY <= 1'b0;
            axi_awaddr    <= 0;
        end else begin
            if (~S_AXI_AWREADY && S_AXI_AWVALID && S_AXI_WVALID) begin
                S_AXI_AWREADY <= 1'b1;
                axi_awaddr    <= S_AXI_AWADDR;
            end else begin
                S_AXI_AWREADY <= 1'b0;
            end
        end
    end

    // WREADY
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_WREADY <= 1'b0;
        end else begin
            if (~S_AXI_WREADY && S_AXI_WVALID && S_AXI_AWVALID)
                S_AXI_WREADY <= 1'b1;
            else
                S_AXI_WREADY <= 1'b0;
        end
    end

    assign slv_reg_wren = S_AXI_WREADY && S_AXI_WVALID && S_AXI_AWREADY && S_AXI_AWVALID;

    // Register write and defaults
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            slv_reg0 <= 32'h0000_0009; // enable=1, use_sw_humidity=1 for independent demo
            slv_reg1 <= 32'h0000_0032; // sw humidity = 50
            slv_reg2 <= 32'h000A_052D; // dry_alert_s=10, hysteresis=5, threshold_low=45
            slv_reg3 <= 32'h0000_0000; // min_off_s=0, min_on_s=0 for direct LED demo
            clear_counter_pulse <= 1'b0;
        end else begin
            clear_counter_pulse <= 1'b0;
            if (slv_reg_wren) begin
                case (axi_awaddr[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB])
                    3'h0: begin
                        for (byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1)
                            if (S_AXI_WSTRB[byte_index])
                                slv_reg0[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                        slv_reg0[4] <= 1'b0;
                        if (S_AXI_WSTRB[0] && S_AXI_WDATA[4])
                            clear_counter_pulse <= 1'b1;
                    end
                    3'h1: begin
                        for (byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1)
                            if (S_AXI_WSTRB[byte_index])
                                slv_reg1[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                    end
                    3'h2: begin
                        for (byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1)
                            if (S_AXI_WSTRB[byte_index])
                                slv_reg2[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                    end
                    3'h3: begin
                        for (byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1)
                            if (S_AXI_WSTRB[byte_index])
                                slv_reg3[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
                    end
                    default: ;
                endcase
            end
        end
    end

    // BVALID
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_BVALID <= 1'b0;
        end else begin
            if (S_AXI_AWREADY && S_AXI_AWVALID && ~S_AXI_BVALID && S_AXI_WREADY && S_AXI_WVALID)
                S_AXI_BVALID <= 1'b1;
            else if (S_AXI_BREADY && S_AXI_BVALID)
                S_AXI_BVALID <= 1'b0;
        end
    end

    // ARREADY
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_ARREADY <= 1'b0;
            axi_araddr    <= 0;
        end else begin
            if (~S_AXI_ARREADY && S_AXI_ARVALID) begin
                S_AXI_ARREADY <= 1'b1;
                axi_araddr    <= S_AXI_ARADDR;
            end else begin
                S_AXI_ARREADY <= 1'b0;
            end
        end
    end

    assign slv_reg_rden = S_AXI_ARREADY & S_AXI_ARVALID & ~S_AXI_RVALID;

    // Read mux
    always @(*) begin
        case (axi_araddr[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB])
            3'h0: reg_data_out = slv_reg0;
            3'h1: reg_data_out = slv_reg1;
            3'h2: reg_data_out = slv_reg2;
            3'h3: reg_data_out = slv_reg3;
            3'h4: reg_data_out = {status_code[15:0], humidifier_leds, 1'b0, dry_level, core_humidifier_on, current_humidity};
            3'h5: reg_data_out = dry_seconds;
            3'h6: reg_data_out = 32'h2026_0601;
            default: reg_data_out = 32'h0000_0000;
        endcase
    end

    // RVALID / RDATA
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            S_AXI_RVALID <= 1'b0;
            S_AXI_RDATA  <= 0;
        end else begin
            if (slv_reg_rden) begin
                S_AXI_RVALID <= 1'b1;
                S_AXI_RDATA  <= reg_data_out;
            end else if (S_AXI_RVALID && S_AXI_RREADY) begin
                S_AXI_RVALID <= 1'b0;
            end
        end
    end

    humidifier_core #(
        .CLK_FREQ_HZ(CLK_FREQ_HZ)
    ) u_humidifier_core (
        .clk(S_AXI_ACLK),
        .resetn(S_AXI_ARESETN),
        .enable(enable),
        .manual_mode(manual_mode),
        .manual_on(manual_on),
        .use_sw_humidity(use_sw_humidity),
        .clear_counter(clear_counter_pulse),
        .humidity_valid(humidity_hw_valid),
        .humidity_hw(humidity_hw),
        .sw_humidity(sw_humidity),
        .threshold_low(threshold_low),
        .hysteresis(hysteresis),
        .min_on_s(min_on_s),
        .min_off_s(min_off_s),
        .dry_alert_s(dry_alert_s),
        .humidifier_on(core_humidifier_on),
        .led(humidifier_leds),
        .current_humidity(current_humidity),
        .dry_level(dry_level),
        .dry_seconds(dry_seconds),
        .status_code(status_code)
    );

endmodule
