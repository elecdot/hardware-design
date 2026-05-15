`timescale 1ns / 1ps

module jy901_sampler #(
    parameter WORD_SLOTS = 13
) (
    input  wire        clk,
    input  wire        resetn,
    input  wire        enable,
    input  wire        soft_reset,
    input  wire        oneshot_start,
    input  wire        auto_mode,
    input  wire        cfg_write_start,
    input  wire        clear_done,
    input  wire        clear_error,

    input  wire [6:0]  dev_addr,
    input  wire [7:0]  start_reg,
    input  wire [7:0]  word_count,
    input  wire [31:0] sample_period,
    input  wire [15:0] i2c_clkdiv,
    input  wire [7:0]  cfg_reg_addr,
    input  wire [15:0] cfg_data,

    input  wire        scl_in,
    input  wire        sda_in,
    output wire        scl_drive_low,
    output wire        sda_drive_low,

    output wire        i2c_busy,
    output reg         done,
    output reg         data_valid,
    output reg         ack_error,
    output reg         timeout,
    output reg         cfg_done,
    output reg  [7:0]  error_code,
    output reg  [15:0] data0,
    output reg  [15:0] data1,
    output reg  [15:0] data2,
    output reg  [15:0] data3,
    output reg  [15:0] data4,
    output reg  [15:0] data5,
    output reg  [15:0] data6,
    output reg  [15:0] data7,
    output reg  [15:0] data8,
    output reg  [15:0] data9,
    output reg  [15:0] data10,
    output reg  [15:0] data11,
    output reg  [15:0] data12,
    output reg  [31:0] sample_cnt,

    output wire [1:0]  dbg_state,
    output wire [31:0] dbg_period_cnt,
    output wire        dbg_core_start,
    output wire        dbg_core_done,
    output wire [4:0]  dbg_core_state,
    output wire [2:0]  dbg_core_step,
    output wire [7:0]  dbg_core_tx_byte,
    output wire [3:0]  dbg_core_bit_cnt,
    output wire [4:0]  dbg_core_byte_cnt,
    output wire [7:0]  dbg_core_latched_read_len,
    output wire [15:0] dbg_core_div_cnt,
    output wire        dbg_core_tick,
    output wire        dbg_core_last_read_byte,
    output wire        dbg_core_scl_in,
    output wire        dbg_core_sda_in
);
    localparam ST_IDLE      = 2'd0;
    localparam ST_START     = 2'd1;
    localparam ST_WAIT_CORE = 2'd2;
    localparam [7:0] WORD_SLOTS_U8 = WORD_SLOTS;

    reg [1:0] state;
    reg [31:0] period_cnt;
    reg core_start;
    reg core_cfg_write;
    reg pending_cfg;
    reg [7:0] byte_buf [0:25];
    integer i;

    wire core_done;
    wire core_ack_error;
    wire core_timeout;
    wire [7:0] core_error_code;
    wire rx_valid;
    wire [4:0] rx_index;
    wire [7:0] rx_data;
    wire [7:0] effective_word_count = (word_count == 8'd0) ? 8'd1 :
                                      ((word_count > WORD_SLOTS_U8) ? WORD_SLOTS_U8 : word_count);
    wire [7:0] read_len = effective_word_count << 1;

    assign dbg_state      = state;
    assign dbg_period_cnt = period_cnt;
    assign dbg_core_start = core_start;
    assign dbg_core_done  = core_done;

    i2c_master_core #(
        .MAX_READ_BYTES(WORD_SLOTS * 2)
    ) u_i2c_master_core (
        .clk(clk),
        .resetn(resetn & ~soft_reset),
        .start(core_start),
        .cfg_write(core_cfg_write),
        .dev_addr(dev_addr),
        .start_reg(start_reg),
        .read_len(read_len),
        .cfg_reg_addr(cfg_reg_addr),
        .cfg_data(cfg_data),
        .clkdiv(i2c_clkdiv),
        .scl_in(scl_in),
        .sda_in(sda_in),
        .scl_drive_low(scl_drive_low),
        .sda_drive_low(sda_drive_low),
        .busy(i2c_busy),
        .done(core_done),
        .ack_error(core_ack_error),
        .timeout(core_timeout),
        .error_code(core_error_code),
        .rx_valid(rx_valid),
        .rx_index(rx_index),
        .rx_data(rx_data),
        .dbg_state(dbg_core_state),
        .dbg_step(dbg_core_step),
        .dbg_tx_byte(dbg_core_tx_byte),
        .dbg_bit_cnt(dbg_core_bit_cnt),
        .dbg_byte_cnt(dbg_core_byte_cnt),
        .dbg_latched_read_len(dbg_core_latched_read_len),
        .dbg_div_cnt(dbg_core_div_cnt),
        .dbg_tick(dbg_core_tick),
        .dbg_last_read_byte(dbg_core_last_read_byte),
        .dbg_scl_in(dbg_core_scl_in),
        .dbg_sda_in(dbg_core_sda_in)
    );

    task latch_word;
        input [4:0] index;
        input [15:0] value;
        begin
            case (index)
                5'd0:  data0  <= value;
                5'd1:  data1  <= value;
                5'd2:  data2  <= value;
                5'd3:  data3  <= value;
                5'd4:  data4  <= value;
                5'd5:  data5  <= value;
                5'd6:  data6  <= value;
                5'd7:  data7  <= value;
                5'd8:  data8  <= value;
                5'd9:  data9  <= value;
                5'd10: data10 <= value;
                5'd11: data11 <= value;
                5'd12: data12 <= value;
                default: ;
            endcase
        end
    endtask

    always @(posedge clk) begin
        if (!resetn || soft_reset) begin
            state <= ST_IDLE;
            period_cnt <= 32'd0;
            core_start <= 1'b0;
            core_cfg_write <= 1'b0;
            pending_cfg <= 1'b0;
            done <= 1'b0;
            data_valid <= 1'b0;
            ack_error <= 1'b0;
            timeout <= 1'b0;
            cfg_done <= 1'b0;
            error_code <= 8'd0;
            sample_cnt <= 32'd0;
            data0 <= 16'd0; data1 <= 16'd0; data2 <= 16'd0; data3 <= 16'd0;
            data4 <= 16'd0; data5 <= 16'd0; data6 <= 16'd0; data7 <= 16'd0;
            data8 <= 16'd0; data9 <= 16'd0; data10 <= 16'd0; data11 <= 16'd0;
            data12 <= 16'd0;
            for (i = 0; i < 26; i = i + 1) byte_buf[i] <= 8'd0;
        end else begin
            core_start <= 1'b0;

            if (clear_done) begin
                done <= 1'b0;
                cfg_done <= 1'b0;
            end
            if (clear_error) begin
                ack_error <= 1'b0;
                timeout <= 1'b0;
                error_code <= 8'd0;
            end

            if (rx_valid && rx_index < 26) begin
                byte_buf[rx_index] <= rx_data;
            end

            if (enable && auto_mode && state == ST_IDLE) begin
                if (period_cnt >= sample_period) begin
                    period_cnt <= 32'd0;
                end else begin
                    period_cnt <= period_cnt + 32'd1;
                end
            end else if (!auto_mode) begin
                period_cnt <= 32'd0;
            end

            case (state)
                ST_IDLE: begin
                    if (enable && cfg_write_start) begin
                        pending_cfg <= 1'b1;
                        state <= ST_START;
                    end else if (enable && oneshot_start) begin
                        pending_cfg <= 1'b0;
                        state <= ST_START;
                    end else if (enable && auto_mode && period_cnt >= sample_period) begin
                        pending_cfg <= 1'b0;
                        state <= ST_START;
                    end
                end

                ST_START: begin
                    done <= 1'b0;
                    cfg_done <= 1'b0;
                    core_cfg_write <= pending_cfg;
                    core_start <= 1'b1;
                    state <= ST_WAIT_CORE;
                end

                ST_WAIT_CORE: begin
                    if (core_done) begin
                        done <= 1'b1;
                        ack_error <= core_ack_error;
                        timeout <= core_timeout;
                        error_code <= core_error_code;
                        if (!core_ack_error && !core_timeout) begin
                            if (pending_cfg) begin
                                cfg_done <= 1'b1;
                            end else begin
                                for (i = 0; i < WORD_SLOTS; i = i + 1) begin
                                    if (i < effective_word_count) latch_word(i, {byte_buf[(i << 1) + 1], byte_buf[i << 1]});
                                end
                                data_valid <= 1'b1;
                                sample_cnt <= sample_cnt + 32'd1;
                            end
                        end
                        state <= ST_IDLE;
                    end
                end

                default: state <= ST_IDLE;
            endcase
        end
    end
endmodule
