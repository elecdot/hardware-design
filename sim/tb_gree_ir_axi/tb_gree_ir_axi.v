`timescale 1ns/1ps

module tb_gree_ir_axi;

    reg clk;
    reg rst_n;

    reg  [4:0]  s00_axi_awaddr;
    reg  [2:0]  s00_axi_awprot;
    reg         s00_axi_awvalid;
    wire        s00_axi_awready;
    reg  [31:0] s00_axi_wdata;
    reg  [3:0]  s00_axi_wstrb;
    reg         s00_axi_wvalid;
    wire        s00_axi_wready;
    wire [1:0]  s00_axi_bresp;
    wire        s00_axi_bvalid;
    reg         s00_axi_bready;
    reg  [4:0]  s00_axi_araddr;
    reg  [2:0]  s00_axi_arprot;
    reg         s00_axi_arvalid;
    wire        s00_axi_arready;
    wire [31:0] s00_axi_rdata;
    wire [1:0]  s00_axi_rresp;
    wire        s00_axi_rvalid;
    reg         s00_axi_rready;

    wire ir_pwm;

    localparam [4:0] REG_CONTROL  = 5'h00;
    localparam [4:0] REG_STATUS   = 5'h04;
    localparam [4:0] REG_CMD_LOW  = 5'h08;
    localparam [4:0] REG_CMD_HIGH = 5'h0C;
    localparam [4:0] REG_PRESET   = 5'h10;
    localparam [4:0] REG_DEBUG    = 5'h14;

    localparam [31:0] STATUS_BUSY  = 32'h0000_0001;
    localparam [31:0] STATUS_DONE  = 32'h0000_0002;
    localparam [31:0] STATUS_ERROR = 32'h0000_0004;

    reg [31:0] expected_low [1:7];
    reg [31:0] expected_high [1:7];
    reg [31:0] rd;
    integer i;

    gree_ir_axi_v1_0 #(
        .CORE_CLK_FREQ(1_000_000),
        .CORE_CLK_1US(1),
        .CORE_CARRIER_HZ(100_000)
    ) dut (
        .ir_pwm(ir_pwm),

        .s00_axi_aclk(clk),
        .s00_axi_aresetn(rst_n),
        .s00_axi_awaddr(s00_axi_awaddr),
        .s00_axi_awprot(s00_axi_awprot),
        .s00_axi_awvalid(s00_axi_awvalid),
        .s00_axi_awready(s00_axi_awready),
        .s00_axi_wdata(s00_axi_wdata),
        .s00_axi_wstrb(s00_axi_wstrb),
        .s00_axi_wvalid(s00_axi_wvalid),
        .s00_axi_wready(s00_axi_wready),
        .s00_axi_bresp(s00_axi_bresp),
        .s00_axi_bvalid(s00_axi_bvalid),
        .s00_axi_bready(s00_axi_bready),
        .s00_axi_araddr(s00_axi_araddr),
        .s00_axi_arprot(s00_axi_arprot),
        .s00_axi_arvalid(s00_axi_arvalid),
        .s00_axi_arready(s00_axi_arready),
        .s00_axi_rdata(s00_axi_rdata),
        .s00_axi_rresp(s00_axi_rresp),
        .s00_axi_rvalid(s00_axi_rvalid),
        .s00_axi_rready(s00_axi_rready)
    );

    always #5 clk = ~clk;

    task fail;
        input [255:0] message;
        begin
            $display("tb_gree_ir_axi FAIL: %0s", message);
            $finish;
        end
    endtask

    task expect_equal;
        input [255:0] label;
        input [31:0] actual;
        input [31:0] expected;
        begin
            if (actual !== expected) begin
                $display("tb_gree_ir_axi FAIL: %0s actual=0x%08h expected=0x%08h",
                         label, actual, expected);
                $finish;
            end
        end
    endtask

    task axi_write;
        input [4:0] addr;
        input [31:0] data;
        begin
            @(posedge clk);
            s00_axi_awaddr  <= addr;
            s00_axi_wdata   <= data;
            s00_axi_wstrb   <= 4'hF;
            s00_axi_awvalid <= 1'b1;
            s00_axi_wvalid  <= 1'b1;
            s00_axi_bready  <= 1'b1;

            while (!(s00_axi_awready && s00_axi_wready)) @(posedge clk);
            @(posedge clk);
            s00_axi_awvalid <= 1'b0;
            s00_axi_wvalid  <= 1'b0;

            while (!s00_axi_bvalid) @(posedge clk);
            if (s00_axi_bresp != 2'b00) begin
                $display("AXI write response error: addr=0x%02h bresp=%b",
                         addr, s00_axi_bresp);
                $finish;
            end
            @(posedge clk);
            s00_axi_bready <= 1'b0;
        end
    endtask

    task axi_read;
        input [4:0] addr;
        output [31:0] data;
        begin
            @(posedge clk);
            s00_axi_araddr  <= addr;
            s00_axi_arvalid <= 1'b1;
            s00_axi_rready  <= 1'b1;

            while (!s00_axi_arready) @(posedge clk);
            @(posedge clk);
            s00_axi_arvalid <= 1'b0;

            while (!s00_axi_rvalid) @(posedge clk);
            data = s00_axi_rdata;
            if (s00_axi_rresp != 2'b00) begin
                $display("AXI read response error: addr=0x%02h rresp=%b",
                         addr, s00_axi_rresp);
                $finish;
            end
            @(posedge clk);
            s00_axi_rready <= 1'b0;
        end
    endtask

    task wait_status_set;
        input [31:0] mask;
        input integer timeout_cycles;
        integer n;
        begin
            for (n = 0; n < timeout_cycles; n = n + 1) begin
                axi_read(REG_STATUS, rd);
                if ((rd & mask) == mask) begin
                    n = timeout_cycles;
                end
            end
            if ((rd & mask) != mask) begin
                $display("tb_gree_ir_axi FAIL: timeout waiting for status mask 0x%08h, last=0x%08h",
                         mask, rd);
                $finish;
            end
        end
    endtask

    task start_and_expect_done;
        begin
            axi_write(REG_STATUS, STATUS_DONE | STATUS_ERROR);
            axi_write(REG_CONTROL, 32'h0000_0001);
            wait_status_set(STATUS_BUSY, 100);
            wait_status_set(STATUS_DONE, 4000);
            axi_read(REG_STATUS, rd);
            if ((rd & STATUS_BUSY) != 32'd0)
                fail("busy should be low after TX done");
            if ((rd & STATUS_ERROR) != 32'd0)
                fail("error should remain low during normal TX");
            axi_write(REG_STATUS, STATUS_DONE);
            axi_read(REG_STATUS, rd);
            if ((rd & STATUS_DONE) != 32'd0)
                fail("done latch should clear with STATUS bit1 write");
        end
    endtask

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        s00_axi_awaddr = 5'd0;
        s00_axi_awprot = 3'd0;
        s00_axi_awvalid = 1'b0;
        s00_axi_wdata = 32'd0;
        s00_axi_wstrb = 4'h0;
        s00_axi_wvalid = 1'b0;
        s00_axi_bready = 1'b0;
        s00_axi_araddr = 5'd0;
        s00_axi_arprot = 3'd0;
        s00_axi_arvalid = 1'b0;
        s00_axi_rready = 1'b0;

        expected_low[1]  = 32'h0008_0016;
        expected_high[1] = 32'h0900_40A4;
        expected_low[2]  = 32'h0008_001C;
        expected_high[2] = 32'h0500_40A4;
        expected_low[3]  = 32'h0008_0016;
        expected_high[3] = 32'h0100_40A4;
        expected_low[4]  = 32'h0008_000E;
        expected_high[4] = 32'h0900_40A4;
        expected_low[5]  = 32'h0008_001E;
        expected_high[5] = 32'h0500_40A4;
        expected_low[6]  = 32'h0008_0000;
        expected_high[6] = 32'h0D00_40A4;
        expected_low[7]  = 32'h0008_0010;
        expected_high[7] = 32'h0300_40A4;

        for (i = 0; i < 980; i = i + 1) begin
            dut.gree_ir_axi_v1_0_S00_AXI_inst.ir_core.sample_cycles_rom[i] = 24'd3;
        end

        repeat (6) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        axi_read(REG_PRESET, rd);
        expect_equal("reset preset", rd, 32'd1);
        axi_read(REG_CMD_LOW, rd);
        expect_equal("reset cmd_low", rd, expected_low[1]);
        axi_read(REG_CMD_HIGH, rd);
        expect_equal("reset cmd_high", rd, expected_high[1]);
        axi_read(REG_STATUS, rd);
        expect_equal("reset status", rd, 32'd0);

        for (i = 1; i <= 7; i = i + 1) begin
            axi_write(REG_PRESET, i[31:0]);
            axi_read(REG_PRESET, rd);
            expect_equal("preset register", rd, i[31:0]);
            axi_read(REG_CMD_LOW, rd);
            expect_equal("preset cmd_low", rd, expected_low[i]);
            axi_read(REG_CMD_HIGH, rd);
            expect_equal("preset cmd_high", rd, expected_high[i]);
        end

        axi_write(REG_PRESET, 32'd5);
        start_and_expect_done();

        axi_write(REG_PRESET, 32'd1);
        axi_write(REG_CONTROL, 32'h0000_0001);
        wait_status_set(STATUS_BUSY, 100);
        axi_write(REG_CONTROL, 32'h0000_0001);
        wait_status_set(STATUS_ERROR, 100);
        axi_write(REG_STATUS, STATUS_ERROR);
        axi_read(REG_STATUS, rd);
        if ((rd & STATUS_ERROR) != 32'd0)
            fail("error latch should clear with STATUS bit2 write");
        axi_write(REG_CONTROL, 32'h0000_0002);
        repeat (4) @(posedge clk);
        axi_read(REG_STATUS, rd);
        if ((rd & (STATUS_BUSY | STATUS_DONE | STATUS_ERROR)) != 32'd0)
            fail("soft reset should clear busy/done/error status");

        axi_write(REG_PRESET, 32'd9);
        axi_read(REG_PRESET, rd);
        expect_equal("invalid preset stored as compatibility mode", rd, 32'd0);
        axi_read(REG_CMD_LOW, rd);
        expect_equal("invalid preset fallback cmd_low", rd, expected_low[1]);
        axi_read(REG_CMD_HIGH, rd);
        expect_equal("invalid preset fallback cmd_high", rd, expected_high[1]);

        axi_read(REG_DEBUG, rd);

        $display("tb_gree_ir_axi PASS");
        $finish;
    end

endmodule
