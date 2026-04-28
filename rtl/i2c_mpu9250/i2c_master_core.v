`timescale 1ns / 1ps

module i2c_master_core #(
    parameter MAX_READ_BYTES = 26,
    parameter TIMEOUT_CYCLES = 32'd20_000_000
) (
    input  wire        clk,
    input  wire        resetn,

    input  wire        start,
    input  wire        cfg_write,
    input  wire [6:0]  dev_addr,
    input  wire [7:0]  start_reg,
    input  wire [7:0]  read_len,
    input  wire [7:0]  cfg_reg_addr,
    input  wire [15:0] cfg_data,
    input  wire [15:0] clkdiv,

    input  wire        scl_in,
    input  wire        sda_in,
    output reg         scl_drive_low,
    output reg         sda_drive_low,

    output reg         busy,
    output reg         done,
    output reg         ack_error,
    output reg         timeout,
    output reg  [7:0]  error_code,

    output reg         rx_valid,
    output reg  [4:0]  rx_index,
    output reg  [7:0]  rx_data
);
    localparam ERR_NONE       = 8'h00;
    localparam ERR_ACK_ADDR_W = 8'h01;
    localparam ERR_ACK_REG    = 8'h02;
    localparam ERR_ACK_ADDR_R = 8'h03;
    localparam ERR_ACK_CFG_L  = 8'h04;
    localparam ERR_ACK_CFG_H  = 8'h05;
    localparam ERR_TIMEOUT    = 8'h10;
    localparam [7:0] MAX_READ_BYTES_U8 = MAX_READ_BYTES;

    localparam ST_IDLE       = 5'd0;
    localparam ST_START_A    = 5'd1;
    localparam ST_START_B    = 5'd2;
    localparam ST_START_C    = 5'd3;
    localparam ST_WRITE_LOW  = 5'd4;
    localparam ST_WRITE_HIGH = 5'd5;
    localparam ST_ACK_LOW    = 5'd6;
    localparam ST_ACK_HIGH   = 5'd7;
    localparam ST_READ_LOW   = 5'd8;
    localparam ST_READ_HIGH  = 5'd9;
    localparam ST_MACK_LOW   = 5'd10;
    localparam ST_MACK_HIGH  = 5'd11;
    localparam ST_STOP_A     = 5'd12;
    localparam ST_STOP_B     = 5'd13;
    localparam ST_STOP_C     = 5'd14;
    localparam ST_DONE       = 5'd15;
    localparam ST_ERROR      = 5'd16;
    localparam ST_RESTART_A  = 5'd17;
    localparam ST_RESTART_B  = 5'd18;
    localparam ST_RESTART_C  = 5'd19;

    localparam STEP_ADDR_W = 3'd0;
    localparam STEP_REG    = 3'd1;
    localparam STEP_ADDR_R = 3'd2;
    localparam STEP_CFG_L  = 3'd3;
    localparam STEP_CFG_H  = 3'd4;
    localparam STEP_READ   = 3'd5;

    reg [4:0]  state;
    reg [2:0]  step;
    reg [7:0]  tx_byte;
    reg [7:0]  shifter;
    reg [3:0]  bit_cnt;
    reg [4:0]  byte_cnt;
    reg [7:0]  latched_read_len;
    reg [15:0] div_cnt;
    reg [31:0] timeout_cnt;
    reg        cfg_write_latched;

    wire [15:0] div_limit = (clkdiv == 16'd0) ? 16'd1 : clkdiv;
    wire        last_read_byte = (byte_cnt == (latched_read_len[4:0] - 5'd1));

    reg tick;
    always @(posedge clk) begin
        if (!resetn) begin
            div_cnt <= 16'd0;
            tick <= 1'b0;
        end else if (state == ST_IDLE) begin
            div_cnt <= 16'd0;
            tick <= 1'b0;
        end else if (div_cnt >= div_limit - 16'd1) begin
            div_cnt <= 16'd0;
            tick <= 1'b1;
        end else begin
            div_cnt <= div_cnt + 16'd1;
            tick <= 1'b0;
        end
    end

    task begin_write;
        input [7:0] value;
        begin
            tx_byte <= value;
            bit_cnt <= 4'd7;
            state <= ST_WRITE_LOW;
        end
    endtask

    task fail_with;
        input [7:0] code;
        begin
            ack_error <= (code != ERR_TIMEOUT);
            timeout <= (code == ERR_TIMEOUT);
            error_code <= code;
            state <= ST_ERROR;
        end
    endtask

    always @(posedge clk) begin
        if (!resetn) begin
            state <= ST_IDLE;
            step <= STEP_ADDR_W;
            tx_byte <= 8'd0;
            shifter <= 8'd0;
            bit_cnt <= 4'd0;
            byte_cnt <= 5'd0;
            latched_read_len <= 8'd0;
            cfg_write_latched <= 1'b0;
            scl_drive_low <= 1'b0;
            sda_drive_low <= 1'b0;
            busy <= 1'b0;
            done <= 1'b0;
            ack_error <= 1'b0;
            timeout <= 1'b0;
            error_code <= ERR_NONE;
            rx_valid <= 1'b0;
            rx_index <= 5'd0;
            rx_data <= 8'd0;
            timeout_cnt <= 32'd0;
        end else begin
            rx_valid <= 1'b0;
            done <= 1'b0;

            if (busy && state != ST_DONE && state != ST_ERROR && timeout_cnt >= TIMEOUT_CYCLES) begin
                fail_with(ERR_TIMEOUT);
            end else begin
                if (busy && state != ST_DONE && state != ST_ERROR) begin
                    timeout_cnt <= timeout_cnt + 32'd1;
                end

                case (state)
                ST_IDLE: begin
                    busy <= 1'b0;
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= 1'b0;
                    timeout_cnt <= 32'd0;
                    if (start) begin
                        busy <= 1'b1;
                        ack_error <= 1'b0;
                        timeout <= 1'b0;
                        error_code <= ERR_NONE;
                        cfg_write_latched <= cfg_write;
                        latched_read_len <= (read_len > MAX_READ_BYTES_U8) ? MAX_READ_BYTES_U8 :
                                            ((read_len == 8'd0) ? 8'd1 : read_len);
                        byte_cnt <= 5'd0;
                        step <= STEP_ADDR_W;
                        state <= ST_START_A;
                    end
                end

                ST_START_A: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= 1'b0;
                    if (tick) state <= ST_START_B;
                end

                ST_START_B: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= 1'b1;
                    if (tick) state <= ST_START_C;
                end

                ST_START_C: begin
                    scl_drive_low <= 1'b1;
                    sda_drive_low <= 1'b1;
                    if (tick) begin_write({dev_addr, (step == STEP_ADDR_R)});
                end

                ST_RESTART_A: begin
                    scl_drive_low <= 1'b1;
                    sda_drive_low <= 1'b0;
                    if (tick) state <= ST_RESTART_B;
                end

                ST_RESTART_B: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= 1'b0;
                    if (tick) state <= ST_RESTART_C;
                end

                ST_RESTART_C: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= 1'b1;
                    if (tick) state <= ST_START_C;
                end

                ST_WRITE_LOW: begin
                    scl_drive_low <= 1'b1;
                    sda_drive_low <= ~tx_byte[bit_cnt];
                    if (tick) state <= ST_WRITE_HIGH;
                end

                ST_WRITE_HIGH: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= ~tx_byte[bit_cnt];
                    if (tick) begin
                        if (bit_cnt == 4'd0) begin
                            state <= ST_ACK_LOW;
                        end else begin
                            bit_cnt <= bit_cnt - 4'd1;
                            state <= ST_WRITE_LOW;
                        end
                    end
                end

                ST_ACK_LOW: begin
                    scl_drive_low <= 1'b1;
                    sda_drive_low <= 1'b0;
                    if (tick) state <= ST_ACK_HIGH;
                end

                ST_ACK_HIGH: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= 1'b0;
                    if (tick) begin
                        if (sda_in) begin
                            case (step)
                                STEP_ADDR_W: fail_with(ERR_ACK_ADDR_W);
                                STEP_REG:    fail_with(ERR_ACK_REG);
                                STEP_ADDR_R: fail_with(ERR_ACK_ADDR_R);
                                STEP_CFG_L:  fail_with(ERR_ACK_CFG_L);
                                STEP_CFG_H:  fail_with(ERR_ACK_CFG_H);
                                default:     fail_with(ERR_ACK_REG);
                            endcase
                        end else begin
                            case (step)
                                STEP_ADDR_W: begin
                                    step <= STEP_REG;
                                    begin_write(cfg_write_latched ? cfg_reg_addr : start_reg);
                                end
                                STEP_REG: begin
                                    if (cfg_write_latched) begin
                                        step <= STEP_CFG_L;
                                        begin_write(cfg_data[7:0]);
                                    end else begin
                                        step <= STEP_ADDR_R;
                                        state <= ST_RESTART_A;
                                    end
                                end
                                STEP_ADDR_R: begin
                                    step <= STEP_READ;
                                    bit_cnt <= 4'd7;
                                    shifter <= 8'd0;
                                    state <= ST_READ_LOW;
                                end
                                STEP_CFG_L: begin
                                    step <= STEP_CFG_H;
                                    begin_write(cfg_data[15:8]);
                                end
                                STEP_CFG_H: begin
                                    state <= ST_STOP_A;
                                end
                                default: begin
                                    state <= ST_STOP_A;
                                end
                            endcase
                        end
                    end
                end

                ST_READ_LOW: begin
                    scl_drive_low <= 1'b1;
                    sda_drive_low <= 1'b0;
                    if (tick) state <= ST_READ_HIGH;
                end

                ST_READ_HIGH: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= 1'b0;
                    if (tick) begin
                        shifter[bit_cnt] <= sda_in;
                        if (bit_cnt == 4'd0) begin
                            rx_valid <= 1'b1;
                            rx_index <= byte_cnt;
                            rx_data <= {shifter[7:1], sda_in};
                            state <= ST_MACK_LOW;
                        end else begin
                            bit_cnt <= bit_cnt - 4'd1;
                            state <= ST_READ_LOW;
                        end
                    end
                end

                ST_MACK_LOW: begin
                    scl_drive_low <= 1'b1;
                    sda_drive_low <= ~last_read_byte;
                    if (tick) state <= ST_MACK_HIGH;
                end

                ST_MACK_HIGH: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= ~last_read_byte;
                    if (tick) begin
                        if (last_read_byte) begin
                            state <= ST_STOP_A;
                        end else begin
                            byte_cnt <= byte_cnt + 5'd1;
                            bit_cnt <= 4'd7;
                            shifter <= 8'd0;
                            state <= ST_READ_LOW;
                        end
                    end
                end

                ST_STOP_A: begin
                    scl_drive_low <= 1'b1;
                    sda_drive_low <= 1'b1;
                    if (tick) state <= ST_STOP_B;
                end

                ST_STOP_B: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= 1'b1;
                    if (tick) state <= ST_STOP_C;
                end

                ST_STOP_C: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= 1'b0;
                    if (tick) state <= ST_DONE;
                end

                ST_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= ST_IDLE;
                end

                ST_ERROR: begin
                    scl_drive_low <= 1'b0;
                    sda_drive_low <= 1'b0;
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= ST_IDLE;
                end

                default: state <= ST_IDLE;
                endcase
            end
        end
    end
endmodule
