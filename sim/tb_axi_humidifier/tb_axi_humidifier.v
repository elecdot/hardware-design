`timescale 1ns / 1ps

module tb_axi_humidifier;
    localparam integer C_AXI_ADDR_WIDTH = 5;
    localparam integer C_AXI_DATA_WIDTH = 32;
    localparam integer CLK_FREQ_HZ = 20;

    reg clk = 1'b0;
    reg resetn = 1'b0;

    reg humidity_hw_valid = 1'b0;
    reg [7:0] humidity_hw = 8'd0;
    wire humidifier_led;
    wire [3:0] humidifier_leds;

    reg [C_AXI_ADDR_WIDTH-1:0] awaddr = 0;
    reg [2:0] awprot = 0;
    reg awvalid = 1'b0;
    wire awready;
    reg [C_AXI_DATA_WIDTH-1:0] wdata = 0;
    reg [(C_AXI_DATA_WIDTH/8)-1:0] wstrb = 4'hF;
    reg wvalid = 1'b0;
    wire wready;
    wire [1:0] bresp;
    wire bvalid;
    reg bready = 1'b0;
    reg [C_AXI_ADDR_WIDTH-1:0] araddr = 0;
    reg [2:0] arprot = 0;
    reg arvalid = 1'b0;
    wire arready;
    wire [C_AXI_DATA_WIDTH-1:0] rdata;
    wire [1:0] rresp;
    wire rvalid;
    reg rready = 1'b0;

    always #5 clk = ~clk;

    axi_humidifier_v1_0 #(
        .C_S00_AXI_DATA_WIDTH(C_AXI_DATA_WIDTH),
        .C_S00_AXI_ADDR_WIDTH(C_AXI_ADDR_WIDTH),
        .CLK_FREQ_HZ(CLK_FREQ_HZ)
    ) dut (
        .humidity_hw_valid(humidity_hw_valid),
        .humidity_hw(humidity_hw),
        .humidifier_led(humidifier_led),
        .humidifier_leds(humidifier_leds),
        .s00_axi_aclk(clk),
        .s00_axi_aresetn(resetn),
        .s00_axi_awaddr(awaddr),
        .s00_axi_awprot(awprot),
        .s00_axi_awvalid(awvalid),
        .s00_axi_awready(awready),
        .s00_axi_wdata(wdata),
        .s00_axi_wstrb(wstrb),
        .s00_axi_wvalid(wvalid),
        .s00_axi_wready(wready),
        .s00_axi_bresp(bresp),
        .s00_axi_bvalid(bvalid),
        .s00_axi_bready(bready),
        .s00_axi_araddr(araddr),
        .s00_axi_arprot(arprot),
        .s00_axi_arvalid(arvalid),
        .s00_axi_arready(arready),
        .s00_axi_rdata(rdata),
        .s00_axi_rresp(rresp),
        .s00_axi_rvalid(rvalid),
        .s00_axi_rready(rready)
    );

    task wait_cycles;
        input integer cycles;
        integer i;
        begin
            for (i = 0; i < cycles; i = i + 1)
                @(posedge clk);
        end
    endtask

    task check;
        input condition;
        input [255:0] message;
        begin
            if (!condition) begin
                $display("ERROR: %0s", message);
                $finish;
            end
        end
    endtask

    task axi_write;
        input [C_AXI_ADDR_WIDTH-1:0] addr;
        input [31:0] data;
        begin
            @(posedge clk);
            awaddr <= addr;
            wdata <= data;
            wstrb <= 4'hF;
            awvalid <= 1'b1;
            wvalid <= 1'b1;
            bready <= 1'b1;
            wait(awready && wready);
            @(posedge clk);
            awvalid <= 1'b0;
            wvalid <= 1'b0;
            wait(bvalid);
            @(posedge clk);
            bready <= 1'b0;
        end
    endtask

    task axi_read;
        input [C_AXI_ADDR_WIDTH-1:0] addr;
        output [31:0] data;
        begin
            @(posedge clk);
            araddr <= addr;
            arvalid <= 1'b1;
            rready <= 1'b1;
            wait(arready);
            @(posedge clk);
            arvalid <= 1'b0;
            wait(rvalid);
            data = rdata;
            @(posedge clk);
            rready <= 1'b0;
        end
    endtask

    reg [31:0] readback;

    initial begin
        resetn = 1'b0;
        wait_cycles(5);
        resetn = 1'b1;
        wait_cycles(5);

        axi_read(5'h18, readback);
        check(readback == 32'h2026_0601, "VERSION register mismatch");

        axi_write(5'h04, 32'd35);
        wait_cycles(50);
        axi_read(5'h10, readback);
        check(readback[8] == 1'b1, "low software humidity should turn humidifier on");
        check(readback[15:12] == 4'b1111, "low software humidity should turn LEDs on");

        axi_write(5'h04, 32'd55);
        wait_cycles(50);
        axi_read(5'h10, readback);
        check(readback[8] == 1'b0, "high software humidity should turn humidifier off");
        check(readback[15:12] == 4'b0000, "high software humidity should turn LEDs off");

        axi_write(5'h00, 32'h0000_000F);
        wait_cycles(5);
        axi_read(5'h10, readback);
        check(readback[8] == 1'b1, "manual mode should turn humidifier on");

        $display("tb_axi_humidifier PASS");
        $finish;
    end
endmodule
