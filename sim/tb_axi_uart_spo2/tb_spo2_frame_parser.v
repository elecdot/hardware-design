`timescale 1ns / 1ps

module tb_spo2_frame_parser;
    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg enable = 1'b1;
    reg frame_mode_7byte = 1'b0;
    reg [7:0] rx_data = 8'd0;
    reg rx_valid = 1'b0;

    wire frame_valid;
    wire frame_error;
    wire [3:0] frame_len;
    wire [7:0] spo2;
    wire [7:0] heart_rate;
    wire [7:0] pleth;
    wire [7:0] bar_graph;
    wire [7:0] perfusion_index;
    wire search_timeout;
    wire sensor_off;
    wire pulse_beep;
    wire sensor_error;
    wire searching;
    wire crc_ok;
    wire [6:0] crc_calc;
    wire [6:0] crc_rx;
    wire [31:0] raw0;
    wire [31:0] raw1;

    always #5 clk = ~clk;

    spo2_frame_parser dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .frame_mode_7byte(frame_mode_7byte),
        .rx_data(rx_data),
        .rx_valid(rx_valid),
        .frame_valid(frame_valid),
        .frame_error(frame_error),
        .frame_len(frame_len),
        .spo2(spo2),
        .heart_rate(heart_rate),
        .pleth(pleth),
        .bar_graph(bar_graph),
        .perfusion_index(perfusion_index),
        .search_timeout(search_timeout),
        .sensor_off(sensor_off),
        .pulse_beep(pulse_beep),
        .sensor_error(sensor_error),
        .searching(searching),
        .crc_ok(crc_ok),
        .crc_calc(crc_calc),
        .crc_rx(crc_rx),
        .raw0(raw0),
        .raw1(raw1)
    );

    task check;
        input condition;
        input [255:0] message;
        begin
            if (!condition) begin
                $display("ERROR: %0s", message);
                $finish;
            end
        end
    endtask

    task send_byte;
        input [7:0] value;
        begin
            @(negedge clk);
            rx_data = value;
            rx_valid = 1'b1;
            @(negedge clk);
            rx_valid = 1'b0;
            rx_data = 8'd0;
        end
    endtask

    initial begin
        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        frame_mode_7byte = 1'b0;
        send_byte(8'h80);
        send_byte(8'h22);
        send_byte(8'h01);
        send_byte(8'h4C);
        send_byte(8'h62);
        @(posedge clk);
        check(frame_valid == 1'b1, "5-byte frame_valid missing");
        check(frame_error == 1'b0, "5-byte frame_error asserted");
        check(frame_len == 4'd5, "5-byte frame_len mismatch");
        check(heart_rate == 8'd76, "5-byte heart_rate mismatch");
        check(spo2 == 8'd98, "5-byte SpO2 mismatch");
        check(pleth == 8'h22, "5-byte pleth mismatch");
        check(bar_graph == 8'h01, "5-byte bar_graph mismatch");
        check(crc_ok == 1'b1, "5-byte crc_ok should be true");
        check(raw0 == 32'h4C01_2280, "5-byte raw0 mismatch");
        check(raw1 == 32'h0000_0062, "5-byte raw1 mismatch");

        repeat (3) @(posedge clk);
        frame_mode_7byte = 1'b1;
        send_byte(8'h80);
        send_byte(8'h20);
        send_byte(8'h02);
        send_byte(8'h48);
        send_byte(8'h61);
        send_byte(8'h05);
        send_byte(8'h50);
        @(posedge clk);
        check(frame_valid == 1'b1, "7-byte frame_valid missing");
        check(frame_error == 1'b0, "7-byte frame_error asserted");
        check(frame_len == 4'd7, "7-byte frame_len mismatch");
        check(heart_rate == 8'd72, "7-byte heart_rate mismatch");
        check(spo2 == 8'd97, "7-byte SpO2 mismatch");
        check(perfusion_index == 8'd5, "7-byte PI mismatch");
        check(crc_calc == 7'h50, "7-byte crc_calc mismatch");
        check(crc_rx == 7'h50, "7-byte crc_rx mismatch");
        check(crc_ok == 1'b1, "7-byte crc_ok mismatch");
        check(raw0 == 32'h4802_2080, "7-byte raw0 mismatch");
        check(raw1 == 32'h0050_0561, "7-byte raw1 mismatch");

        $display("tb_spo2_frame_parser PASS");
        $finish;
    end

    initial begin
        #10_000;
        $display("ERROR: SpO2 frame parser smoke timeout");
        $finish;
    end
endmodule
