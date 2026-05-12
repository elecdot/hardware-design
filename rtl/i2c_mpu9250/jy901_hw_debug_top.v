`timescale 1ns / 1ps

module jy901_hw_debug_top #(
    parameter integer CLK_HZ = 125_000_000,
    parameter integer I2C_HZ = 100_000
) (
    input  wire       clk,
    input  wire       resetn,

    inout  wire       i2c_scl,
    inout  wire       i2c_sda,

    output wire [3:0] led
);
    localparam [15:0] I2C_CLKDIV    = CLK_HZ / (2 * I2C_HZ);
    localparam [31:0] SAMPLE_PERIOD = CLK_HZ / 2;   // 约 0.5 s 采样一次

    (* mark_debug = "true" *) wire scl_drive_low;
    (* mark_debug = "true" *) wire sda_drive_low;

    (* mark_debug = "true" *) wire i2c_busy;
    (* mark_debug = "true" *) wire done;
    (* mark_debug = "true" *) wire data_valid;
    (* mark_debug = "true" *) wire ack_error;
    (* mark_debug = "true" *) wire timeout;

    (* mark_debug = "true" *) wire [15:0] data0;
    (* mark_debug = "true" *) wire [15:0] data1;
    (* mark_debug = "true" *) wire [15:0] data2;
    (* mark_debug = "true" *) wire [15:0] data3;
    (* mark_debug = "true" *) wire [15:0] data4;
    (* mark_debug = "true" *) wire [15:0] data5;
    (* mark_debug = "true" *) wire [15:0] data6;
    (* mark_debug = "true" *) wire [15:0] data7;
    (* mark_debug = "true" *) wire [15:0] data8;
    (* mark_debug = "true" *) wire [15:0] data9;
    (* mark_debug = "true" *) wire [15:0] data10;
    (* mark_debug = "true" *) wire [15:0] data11;
    (* mark_debug = "true" *) wire [15:0] data12;

    (* mark_debug = "true" *) wire [31:0] sample_cnt;
    wire scl_in;
    wire sda_in;
    wire [7:0] error_code;
    wire cfg_done;

    (* mark_debug = "true" *) reg scl_in_dbg;
    (* mark_debug = "true" *) reg sda_in_dbg;
    (* mark_debug = "true" *) reg [7:0] error_code_dbg;
    (* mark_debug = "true" *) reg cfg_done_dbg;

    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            scl_in_dbg     <= 1'b1;
            sda_in_dbg     <= 1'b1;
            error_code_dbg <= 8'd0;
            cfg_done_dbg   <= 1'b0;
        end else begin
            scl_in_dbg     <= scl_in;
            sda_in_dbg     <= sda_in;
            error_code_dbg <= error_code;
            cfg_done_dbg   <= cfg_done;
        end
    end

    i2c_open_drain_io u_i2c_open_drain_io (
        .scl_drive_low(scl_drive_low),
        .sda_drive_low(sda_drive_low),
        .i2c_scl(i2c_scl),
        .i2c_sda(i2c_sda),
        .scl_in(scl_in),
        .sda_in(sda_in)
    );

    jy901_sampler u_jy901_sampler (
        .clk(clk),
        .resetn(resetn),

        .enable(1'b1),
        .soft_reset(1'b0),
        .oneshot_start(1'b0),
        .auto_mode(1'b1),
        .cfg_write_start(1'b0),
        .clear_done(1'b0),
        .clear_error(1'b0),

        .dev_addr(7'h50),
        .start_reg(8'h34),
        .word_count(8'd13),
        .sample_period(SAMPLE_PERIOD),
        .i2c_clkdiv(I2C_CLKDIV),
        .cfg_reg_addr(8'd0),
        .cfg_data(16'd0),

        .scl_in(scl_in),
        .sda_in(sda_in),
        .scl_drive_low(scl_drive_low),
        .sda_drive_low(sda_drive_low),

        .i2c_busy(i2c_busy),
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

    assign led[0] = i2c_busy;
    assign led[1] = done;
    assign led[2] = data_valid;
    assign led[3] = ack_error | timeout;

endmodule