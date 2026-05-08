`timescale 1ns / 1ps

module tb_i2c_master_timeout;
    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg start = 1'b0;
    wire scl_drive_low;
    wire sda_drive_low;
    wire busy;
    wire done;
    wire ack_error;
    wire timeout;
    wire [7:0] error_code;
    wire rx_valid;
    wire [4:0] rx_index;
    wire [7:0] rx_data;

    tri1 i2c_scl;
    tri1 i2c_sda;

    always #5 clk = ~clk;

    assign i2c_scl = scl_drive_low ? 1'b0 : 1'bz;
    assign i2c_sda = sda_drive_low ? 1'b0 : 1'bz;

    i2c_master_core #(
        .MAX_READ_BYTES(26),
        .TIMEOUT_CYCLES(32'd20)
    ) dut (
        .clk(clk),
        .resetn(resetn),
        .start(start),
        .cfg_write(1'b0),
        .dev_addr(7'h50),
        .start_reg(8'h34),
        .read_len(8'd26),
        .cfg_reg_addr(8'd0),
        .cfg_data(16'd0),
        .clkdiv(16'd1000),
        .scl_in(i2c_scl),
        .sda_in(i2c_sda),
        .scl_drive_low(scl_drive_low),
        .sda_drive_low(sda_drive_low),
        .busy(busy),
        .done(done),
        .ack_error(ack_error),
        .timeout(timeout),
        .error_code(error_code),
        .rx_valid(rx_valid),
        .rx_index(rx_index),
        .rx_data(rx_data)
    );

    initial begin
        $dumpfile("tb_i2c_master_timeout.vcd");
        $dumpvars(0, tb_i2c_master_timeout);
        repeat (5) @(negedge clk);
        resetn = 1'b1;
        repeat (5) @(negedge clk);
        start = 1'b1;
        @(negedge clk);
        start = 1'b0;

        wait (done);
        repeat (2) @(posedge clk);
        if (!timeout || ack_error || error_code !== 8'h10) begin
            $display("FAIL: timeout path mismatch timeout=%0d ack_error=%0d error_code=0x%02x",
                     timeout, ack_error, error_code);
            $finish;
        end

        $display("PASS: I2C master timeout path completed");
        $finish;
    end

    initial begin
        #1_000_000;
        $display("FAIL: timeout testbench hung");
        $finish;
    end
endmodule
