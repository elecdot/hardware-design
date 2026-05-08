`timescale 1ns / 1ps

module tb_jy901_sampler;
    reg clk = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;

    tri1 i2c_scl;
    tri1 i2c_sda;

    reg enable = 1'b0;
    reg soft_reset = 1'b0;
    reg oneshot_start = 1'b0;
    reg auto_mode = 1'b0;
    reg cfg_write_start = 1'b0;
    reg clear_done = 1'b0;
    reg clear_error = 1'b0;
    reg [6:0] dev_addr = 7'h50;
    reg [7:0] start_reg = 8'h34;
    reg [7:0] word_count = 8'd13;
    reg [31:0] sample_period = 32'd1000;
    reg [15:0] i2c_clkdiv = 16'd4;
    reg [7:0] cfg_reg_addr = 8'd0;
    reg [15:0] cfg_data = 16'd0;

    wire scl_in;
    wire sda_in;
    wire scl_drive_low;
    wire sda_drive_low;
    wire busy;
    wire done;
    wire data_valid;
    wire ack_error;
    wire timeout;
    wire cfg_done;
    wire [7:0] error_code;
    wire [15:0] data0;
    wire [15:0] data1;
    wire [15:0] data2;
    wire [15:0] data3;
    wire [15:0] data4;
    wire [15:0] data5;
    wire [15:0] data6;
    wire [15:0] data7;
    wire [15:0] data8;
    wire [15:0] data9;
    wire [15:0] data10;
    wire [15:0] data11;
    wire [15:0] data12;
    wire [31:0] sample_cnt;

    assign scl_in = i2c_scl;
    assign sda_in = i2c_sda;
    assign i2c_scl = scl_drive_low ? 1'b0 : 1'bz;
    assign i2c_sda = sda_drive_low ? 1'b0 : 1'bz;

    jy901_sampler dut (
        .clk(clk),
        .resetn(resetn),
        .enable(enable),
        .soft_reset(soft_reset),
        .oneshot_start(oneshot_start),
        .auto_mode(auto_mode),
        .cfg_write_start(cfg_write_start),
        .clear_done(clear_done),
        .clear_error(clear_error),
        .dev_addr(dev_addr),
        .start_reg(start_reg),
        .word_count(word_count),
        .sample_period(sample_period),
        .i2c_clkdiv(i2c_clkdiv),
        .cfg_reg_addr(cfg_reg_addr),
        .cfg_data(cfg_data),
        .scl_in(scl_in),
        .sda_in(sda_in),
        .scl_drive_low(scl_drive_low),
        .sda_drive_low(sda_drive_low),
        .i2c_busy(busy),
        .done(done),
        .data_valid(data_valid),
        .ack_error(ack_error),
        .timeout(timeout),
        .cfg_done(cfg_done),
        .error_code(error_code),
        .data0(data0),
        .data1(data1),
        .data2(data2),
        .data3(data3),
        .data4(data4),
        .data5(data5),
        .data6(data6),
        .data7(data7),
        .data8(data8),
        .data9(data9),
        .data10(data10),
        .data11(data11),
        .data12(data12),
        .sample_cnt(sample_cnt)
    );

    jy901_i2c_slave_model slave (
        .scl(i2c_scl),
        .sda(i2c_sda)
    );

    initial begin
        $dumpfile("tb_jy901_sampler.vcd");
        $dumpvars(0, tb_jy901_sampler);
        repeat (10) @(negedge clk);
        resetn = 1'b1;
        repeat (10) @(negedge clk);

        enable = 1'b1;
        oneshot_start = 1'b1;
        @(negedge clk);
        oneshot_start = 1'b0;

        wait (done);
        repeat (5) @(posedge clk);

        if (ack_error || timeout) begin
            $display("FAIL: unexpected error ack_error=%0d timeout=%0d error_code=0x%02x",
                     ack_error, timeout, error_code);
            $finish;
        end
        if (!data_valid || sample_cnt != 32'd1) begin
            $display("FAIL: data_valid/sample_cnt invalid data_valid=%0d sample_cnt=%0d",
                     data_valid, sample_cnt);
            $finish;
        end
        if (data0 !== 16'h1234 || data1 !== 16'h5678 || data12 !== 16'h0D0C) begin
            $display("FAIL: data mismatch AX=0x%04x AY=0x%04x TEMP=0x%04x",
                     data0, data1, data12);
            $finish;
        end

        $display("PASS: JY901 burst read simulation completed");

        clear_done = 1'b1;
        clear_error = 1'b1;
        @(negedge clk);
        clear_done = 1'b0;
        clear_error = 1'b0;
        repeat (5) @(negedge clk);

        dev_addr = 7'h51;
        oneshot_start = 1'b1;
        @(negedge clk);
        oneshot_start = 1'b0;

        wait (done);
        repeat (5) @(posedge clk);

        if (!ack_error || timeout || error_code !== 8'h01) begin
            $display("FAIL: expected address-write NACK ack_error=%0d timeout=%0d error_code=0x%02x",
                     ack_error, timeout, error_code);
            $finish;
        end

        $display("PASS: JY901 address NACK simulation completed");
        $finish;
    end

    initial begin
        #5_000_000;
        $display("FAIL: simulation timeout");
        $finish;
    end
endmodule
