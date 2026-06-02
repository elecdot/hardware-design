`timescale 1ns/1ps

module tb_tft_lcd_spi_axi;

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

    wire lcd_scl;
    wire lcd_sda;
    wire lcd_res;
    wire lcd_dc;
    wire lcd_blk;

    localparam [4:0] REG_CTRL   = 5'h00;
    localparam [4:0] REG_DATA   = 5'h04;
    localparam [4:0] REG_CLKDIV = 5'h08;
    localparam [4:0] REG_STATUS = 5'h0C;

    tft_lcd_spi_axi_v1_0 dut (
        .lcd_scl(lcd_scl),
        .lcd_sda(lcd_sda),
        .lcd_res(lcd_res),
        .lcd_dc (lcd_dc),
        .lcd_blk(lcd_blk),

        .s00_axi_aclk   (clk),
        .s00_axi_aresetn(rst_n),
        .s00_axi_awaddr (s00_axi_awaddr),
        .s00_axi_awprot (s00_axi_awprot),
        .s00_axi_awvalid(s00_axi_awvalid),
        .s00_axi_awready(s00_axi_awready),
        .s00_axi_wdata  (s00_axi_wdata),
        .s00_axi_wstrb  (s00_axi_wstrb),
        .s00_axi_wvalid (s00_axi_wvalid),
        .s00_axi_wready (s00_axi_wready),
        .s00_axi_bresp  (s00_axi_bresp),
        .s00_axi_bvalid (s00_axi_bvalid),
        .s00_axi_bready (s00_axi_bready),
        .s00_axi_araddr (s00_axi_araddr),
        .s00_axi_arprot (s00_axi_arprot),
        .s00_axi_arvalid(s00_axi_arvalid),
        .s00_axi_arready(s00_axi_arready),
        .s00_axi_rdata  (s00_axi_rdata),
        .s00_axi_rresp  (s00_axi_rresp),
        .s00_axi_rvalid (s00_axi_rvalid),
        .s00_axi_rready (s00_axi_rready)
    );

    always #5 clk = ~clk;

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
                $display("AXI write response error: addr=%h bresp=%b", addr, s00_axi_bresp);
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
                $display("AXI read response error: addr=%h rresp=%b", addr, s00_axi_rresp);
                $finish;
            end
            @(posedge clk);
            s00_axi_rready <= 1'b0;
        end
    endtask

    task wait_done_latched;
        reg [31:0] status;
        begin
            status = 32'h0;
            while ((status & 32'h2) == 32'h0) begin
                axi_read(REG_STATUS, status);
            end
        end
    endtask

    reg [31:0] rd;

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;

        s00_axi_awaddr = 5'h0;
        s00_axi_awprot = 3'h0;
        s00_axi_awvalid = 1'b0;
        s00_axi_wdata = 32'h0;
        s00_axi_wstrb = 4'h0;
        s00_axi_wvalid = 1'b0;
        s00_axi_bready = 1'b0;
        s00_axi_araddr = 5'h0;
        s00_axi_arprot = 3'h0;
        s00_axi_arvalid = 1'b0;
        s00_axi_rready = 1'b0;

        repeat (10) @(posedge clk);
        rst_n = 1'b1;
        repeat (5) @(posedge clk);

        axi_read(REG_CTRL, rd);
        if (rd[3:1] != 3'b110) begin
            $display("Unexpected CTRL reset value: %h", rd);
            $finish;
        end

        axi_read(REG_CLKDIV, rd);
        if (rd[15:0] != 16'd25) begin
            $display("Unexpected CLKDIV reset value: %h", rd);
            $finish;
        end

        axi_write(REG_CLKDIV, 32'd2);

        // Send data byte 0xA5 with DC=1, RES=1, BLK=1.
        axi_write(REG_DATA, 32'h000000A5);
        axi_write(REG_CTRL, 32'h0000000F);
        wait_done_latched();
        if (lcd_dc !== 1'b1 || lcd_res !== 1'b1 || lcd_blk !== 1'b1) begin
            $display("Unexpected LCD control pins after data byte.");
            $finish;
        end

        // Send command byte 0x2A with DC=0, RES=1, BLK=1.
        axi_write(REG_DATA, 32'h0000002A);
        axi_write(REG_CTRL, 32'h0000000D);
        wait_done_latched();
        if (lcd_dc !== 1'b0) begin
            $display("lcd_dc did not stay low for command byte.");
            $finish;
        end

        axi_write(REG_CTRL, 32'h0000001C);
        axi_read(REG_STATUS, rd);
        if (rd[1] !== 1'b0) begin
            $display("clear_done did not clear done_latched: status=%h", rd);
            $finish;
        end

        $display("tb_tft_lcd_spi_axi PASS");
        $finish;
    end

endmodule
