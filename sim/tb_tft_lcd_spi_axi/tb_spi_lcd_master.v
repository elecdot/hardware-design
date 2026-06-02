`timescale 1ns/1ps

module tb_spi_lcd_master;

    reg clk;
    reg rst_n;

    reg [7:0] tx_data;
    reg       tx_dc;
    reg       tx_start;
    reg [15:0] clk_div;

    reg lcd_res_in;
    reg lcd_blk_in;

    wire lcd_scl;
    wire lcd_sda;
    wire lcd_dc;
    wire lcd_res;
    wire lcd_blk;
    wire busy;
    wire done;

    spi_lcd_master #(
        .CLK_DIV_DEFAULT(4)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),

        .tx_data(tx_data),
        .tx_dc(tx_dc),
        .tx_start(tx_start),
        .clk_div(clk_div),

        .lcd_res_in(lcd_res_in),
        .lcd_blk_in(lcd_blk_in),

        .lcd_scl(lcd_scl),
        .lcd_sda(lcd_sda),
        .lcd_dc(lcd_dc),
        .lcd_res(lcd_res),
        .lcd_blk(lcd_blk),

        .busy(busy),
        .done(done)
    );

    // 100MHz 时钟，周期 10ns
    always #5 clk = ~clk;

    task send_byte;
        input [7:0] data;
        input       dc;
        begin
            @(negedge clk);
            tx_data  = data;
            tx_dc    = dc;
            tx_start = 1'b1;

            @(negedge clk);
            tx_start = 1'b0;

            wait(done == 1'b1);
            @(negedge clk);
        end
    endtask

    initial begin
        clk        = 1'b0;
        rst_n      = 1'b0;

        tx_data    = 8'h00;
        tx_dc      = 1'b0;
        tx_start   = 1'b0;
        clk_div    = 16'd4;

        lcd_res_in = 1'b1;
        lcd_blk_in = 1'b1;

        // 复位一段时间
        #100;
        rst_n = 1'b1;

        #100;

        // 测试 1：
        // 发送命令 0x2A，也就是 CASET。
        // 期望：
        //   lcd_dc = 0
        //   lcd_sda 在 8 个采样上升沿依次为 0 0 1 0 1 0 1 0
        send_byte(8'h2A, 1'b0);

        #200;

        // 测试 2：
        // 发送数据 0x55。
        // 期望：
        //   lcd_dc = 1
        //   lcd_sda 在 8 个采样上升沿依次为 0 1 0 1 0 1 0 1
        send_byte(8'h55, 1'b1);

        #500;

        $finish;
    end

endmodule