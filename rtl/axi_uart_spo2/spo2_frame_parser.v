`timescale 1ns / 1ps

module spo2_frame_parser (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       enable,
    input  wire       frame_mode_7byte,
    input  wire [7:0] rx_data,
    input  wire       rx_valid,

    output reg        frame_valid,
    output reg        frame_error,
    output reg  [3:0] frame_len,
    output reg  [7:0] spo2,
    output reg  [7:0] heart_rate,
    output reg  [7:0] pleth,
    output reg  [7:0] bar_graph,
    output reg  [7:0] perfusion_index,
    output reg        search_timeout,
    output reg        sensor_off,
    output reg        pulse_beep,
    output reg        sensor_error,
    output reg        searching,
    output reg        crc_ok,
    output reg  [6:0] crc_calc,
    output reg  [6:0] crc_rx,
    output reg [31:0] raw0,
    output reg [31:0] raw1
);

    reg [7:0] buf0;
    reg [7:0] buf1;
    reg [7:0] buf2;
    reg [7:0] buf3;
    reg [7:0] buf4;
    reg [7:0] buf5;
    reg [7:0] buf6;
    reg [2:0] byte_index;
    reg       in_frame;

    wire [6:0] crc_sum_7byte;
    assign crc_sum_7byte = buf0[6:0] + buf1[6:0] + buf2[6:0] +
                           buf3[6:0] + buf4[6:0] + buf5[6:0];

    task latch_5byte_frame;
    input [7:0] byte4_now;
    begin
        frame_valid     <= 1'b1;
        frame_error     <= 1'b0;
        frame_len       <= 4'd5;
        search_timeout  <= buf0[4];
        sensor_off      <= buf0[5];
        pulse_beep      <= buf0[6];
        sensor_error    <= buf2[4];
        searching       <= buf2[5];
        pleth           <= {1'b0, buf1[6:0]};
        bar_graph       <= {4'd0, buf2[3:0]};
        heart_rate      <= {buf2[6], buf3[6:0]};
        spo2            <= {1'b0, byte4_now[6:0]};
        perfusion_index <= 8'd0;
        crc_calc        <= 7'd0;
        crc_rx          <= 7'd0;
        crc_ok          <= 1'b1;
        raw0            <= {buf3, buf2, buf1, buf0};
        raw1            <= {24'd0, byte4_now};
    end
    endtask

    task latch_7byte_frame;
    input [7:0] byte6_now;
    begin
        frame_valid     <= 1'b1;
        frame_error     <= 1'b0;
        frame_len       <= 4'd7;
        search_timeout  <= buf0[4];
        sensor_off      <= buf0[5];
        pulse_beep      <= buf0[6];
        sensor_error    <= buf2[4];
        searching       <= buf2[5];
        pleth           <= {1'b0, buf1[6:0]};
        bar_graph       <= {4'd0, buf2[3:0]};
        heart_rate      <= {buf2[6], buf3[6:0]};
        spo2            <= {1'b0, buf4[6:0]};
        perfusion_index <= {buf0[3], buf5[6:0]};
        crc_calc        <= crc_sum_7byte;
        crc_rx          <= byte6_now[6:0];
        crc_ok          <= (crc_sum_7byte == byte6_now[6:0]);
        raw0            <= {buf3, buf2, buf1, buf0};
        raw1            <= {8'd0, byte6_now, buf5, buf4};
    end
    endtask

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            buf0            <= 8'd0;
            buf1            <= 8'd0;
            buf2            <= 8'd0;
            buf3            <= 8'd0;
            buf4            <= 8'd0;
            buf5            <= 8'd0;
            buf6            <= 8'd0;
            byte_index      <= 3'd0;
            in_frame        <= 1'b0;
            frame_valid     <= 1'b0;
            frame_error     <= 1'b0;
            frame_len       <= 4'd0;
            spo2            <= 8'd0;
            heart_rate      <= 8'd0;
            pleth           <= 8'd0;
            bar_graph       <= 8'd0;
            perfusion_index <= 8'd0;
            search_timeout  <= 1'b0;
            sensor_off      <= 1'b0;
            pulse_beep      <= 1'b0;
            sensor_error    <= 1'b0;
            searching       <= 1'b0;
            crc_ok          <= 1'b0;
            crc_calc        <= 7'd0;
            crc_rx          <= 7'd0;
            raw0            <= 32'd0;
            raw1            <= 32'd0;
        end else begin
            frame_valid <= 1'b0;
            frame_error <= 1'b0;

            if (!enable) begin
                byte_index <= 3'd0;
                in_frame   <= 1'b0;
            end else if (rx_valid) begin
                if (rx_data[7]) begin
                    buf0       <= rx_data;
                    byte_index <= 3'd1;
                    in_frame   <= 1'b1;
                end else if (in_frame) begin
                    case (byte_index)
                        3'd1: buf1 <= rx_data;
                        3'd2: buf2 <= rx_data;
                        3'd3: buf3 <= rx_data;
                        3'd4: buf4 <= rx_data;
                        3'd5: buf5 <= rx_data;
                        3'd6: buf6 <= rx_data;
                        default: ;
                    endcase

                    if (!frame_mode_7byte && (byte_index == 3'd4)) begin
                        buf4 <= rx_data;
                        latch_5byte_frame(rx_data);
                        byte_index <= 3'd0;
                        in_frame   <= 1'b0;
                    end else if (frame_mode_7byte && (byte_index == 3'd6)) begin
                        buf6 <= rx_data;
                        latch_7byte_frame(rx_data);
                        byte_index <= 3'd0;
                        in_frame   <= 1'b0;
                    end else begin
                        byte_index <= byte_index + 1'b1;
                    end
                end else begin
                    frame_error <= 1'b1;
                end
            end
        end
    end

endmodule
