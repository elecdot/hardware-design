`timescale 1ns / 1ps

module jy901_hw_debug_top #(
    parameter integer CLK_HZ = 125_000_000,
    parameter integer I2C_HZ = 100_000,
    parameter integer SAMPLE_PERIOD_CYCLES = CLK_HZ / 2,
    parameter integer START_ON_RESET = 1,
    parameter [6:0] DEBUG_DEV_ADDR = 7'h50
) (
    input  wire       clk,
    input  wire       resetn,

    inout  wire       i2c_scl,
    inout  wire       i2c_sda,

    output wire [3:0] led
);
    localparam [15:0] I2C_CLKDIV    = CLK_HZ / (2 * I2C_HZ);
    localparam [31:0] SAMPLE_PERIOD = SAMPLE_PERIOD_CYCLES;

    (* mark_debug = "true" *) reg [1:0] resetn_sync = 2'b00;
    (* mark_debug = "true" *) wire resetn_i = resetn_sync[1];
    (* mark_debug = "true" *) reg startup_seen = 1'b0;
    (* mark_debug = "true" *) wire startup_oneshot =
        (START_ON_RESET != 0) && resetn_i && !startup_seen;

    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            resetn_sync <= 2'b00;
        end else begin
            resetn_sync <= {resetn_sync[0], 1'b1};
        end
    end

    always @(posedge clk) begin
        if (!resetn_i) begin
            startup_seen <= 1'b0;
        end else if (!startup_seen) begin
            startup_seen <= 1'b1;
        end
    end

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
    wire [1:0] sampler_state_raw;
    wire [31:0] period_cnt_raw;
    wire core_start_raw;
    wire core_done_raw;
    wire [4:0] core_state_raw;
    wire [2:0] core_step_raw;
    wire [7:0] core_tx_byte_raw;
    wire [3:0] core_bit_cnt_raw;
    wire [4:0] core_byte_cnt_raw;
    wire [7:0] core_latched_read_len_raw;
    wire [15:0] core_div_cnt_raw;
    wire core_tick_raw;
    wire core_last_read_byte_raw;
    wire core_scl_in_raw;
    wire core_sda_in_raw;

    (* mark_debug = "true" *) reg [1:0] sampler_state_dbg;
    (* mark_debug = "true" *) reg [31:0] period_cnt_dbg;
    (* mark_debug = "true" *) reg core_start_dbg;
    (* mark_debug = "true" *) reg core_done_dbg;
    (* mark_debug = "true" *) reg [4:0] core_state_dbg;
    (* mark_debug = "true" *) reg [2:0] core_step_dbg;
    (* mark_debug = "true" *) reg [7:0] core_tx_byte_dbg;
    (* mark_debug = "true" *) reg [3:0] core_bit_cnt_dbg;
    (* mark_debug = "true" *) reg [4:0] core_byte_cnt_dbg;
    (* mark_debug = "true" *) reg [7:0] core_latched_read_len_dbg;
    (* mark_debug = "true" *) reg [15:0] core_div_cnt_dbg;
    (* mark_debug = "true" *) reg core_tick_dbg;
    (* mark_debug = "true" *) reg core_last_read_byte_dbg;
    (* mark_debug = "true" *) reg core_scl_in_dbg;
    (* mark_debug = "true" *) reg core_sda_in_dbg;

    always @(posedge clk) begin
        if (!resetn_i) begin
            scl_in_dbg     <= 1'b1;
            sda_in_dbg     <= 1'b1;
            error_code_dbg <= 8'd0;
            cfg_done_dbg   <= 1'b0;
            sampler_state_dbg         <= 2'd0;
            period_cnt_dbg            <= 32'd0;
            core_start_dbg            <= 1'b0;
            core_done_dbg             <= 1'b0;
            core_state_dbg            <= 5'd0;
            core_step_dbg             <= 3'd0;
            core_tx_byte_dbg          <= 8'd0;
            core_bit_cnt_dbg          <= 4'd0;
            core_byte_cnt_dbg         <= 5'd0;
            core_latched_read_len_dbg <= 8'd0;
            core_div_cnt_dbg          <= 16'd0;
            core_tick_dbg             <= 1'b0;
            core_last_read_byte_dbg   <= 1'b0;
            core_scl_in_dbg           <= 1'b1;
            core_sda_in_dbg           <= 1'b1;
        end else begin
            scl_in_dbg     <= scl_in;
            sda_in_dbg     <= sda_in;
            error_code_dbg <= error_code;
            cfg_done_dbg   <= cfg_done;
            sampler_state_dbg         <= sampler_state_raw;
            period_cnt_dbg            <= period_cnt_raw;
            core_start_dbg            <= core_start_raw;
            core_done_dbg             <= core_done_raw;
            core_state_dbg            <= core_state_raw;
            core_step_dbg             <= core_step_raw;
            core_tx_byte_dbg          <= core_tx_byte_raw;
            core_bit_cnt_dbg          <= core_bit_cnt_raw;
            core_byte_cnt_dbg         <= core_byte_cnt_raw;
            core_latched_read_len_dbg <= core_latched_read_len_raw;
            core_div_cnt_dbg          <= core_div_cnt_raw;
            core_tick_dbg             <= core_tick_raw;
            core_last_read_byte_dbg   <= core_last_read_byte_raw;
            core_scl_in_dbg           <= core_scl_in_raw;
            core_sda_in_dbg           <= core_sda_in_raw;
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
        .resetn(resetn_i),

        .enable(1'b1),
        .soft_reset(1'b0),
        .oneshot_start(startup_oneshot),
        .auto_mode(1'b1),
        .cfg_write_start(1'b0),
        .clear_done(1'b0),
        .clear_error(1'b0),

        .dev_addr(DEBUG_DEV_ADDR),
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
        .sample_cnt(sample_cnt),
        .dbg_state(sampler_state_raw),
        .dbg_period_cnt(period_cnt_raw),
        .dbg_core_start(core_start_raw),
        .dbg_core_done(core_done_raw),
        .dbg_core_state(core_state_raw),
        .dbg_core_step(core_step_raw),
        .dbg_core_tx_byte(core_tx_byte_raw),
        .dbg_core_bit_cnt(core_bit_cnt_raw),
        .dbg_core_byte_cnt(core_byte_cnt_raw),
        .dbg_core_latched_read_len(core_latched_read_len_raw),
        .dbg_core_div_cnt(core_div_cnt_raw),
        .dbg_core_tick(core_tick_raw),
        .dbg_core_last_read_byte(core_last_read_byte_raw),
        .dbg_core_scl_in(core_scl_in_raw),
        .dbg_core_sda_in(core_sda_in_raw)
    );

    assign led[0] = i2c_busy;
    assign led[1] = done;
    assign led[2] = data_valid;
    assign led[3] = ack_error | timeout;

endmodule
