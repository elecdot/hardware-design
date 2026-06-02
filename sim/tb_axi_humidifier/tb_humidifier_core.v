`timescale 1ns / 1ps

module tb_humidifier_core;
    localparam integer CLK_FREQ_HZ = 20;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg enable = 1'b1;
    reg manual_mode = 1'b0;
    reg manual_on = 1'b0;
    reg use_sw_humidity = 1'b1;
    reg clear_counter = 1'b0;
    reg humidity_valid = 1'b0;
    reg [7:0] humidity_hw = 8'd0;
    reg [7:0] sw_humidity = 8'd50;
    reg [7:0] threshold_low = 8'd45;
    reg [7:0] hysteresis = 8'd5;
    reg [15:0] min_on_s = 16'd0;
    reg [15:0] min_off_s = 16'd0;
    reg [15:0] dry_alert_s = 16'd2;

    wire humidifier_on;
    wire [3:0] led;
    wire [7:0] current_humidity;
    wire [1:0] dry_level;
    wire [31:0] dry_seconds;
    wire [31:0] status_code;

    always #5 clk = ~clk;

    humidifier_core #(
        .CLK_FREQ_HZ(CLK_FREQ_HZ)
    ) dut (
        .clk(clk),
        .resetn(resetn),
        .enable(enable),
        .manual_mode(manual_mode),
        .manual_on(manual_on),
        .use_sw_humidity(use_sw_humidity),
        .clear_counter(clear_counter),
        .humidity_valid(humidity_valid),
        .humidity_hw(humidity_hw),
        .sw_humidity(sw_humidity),
        .threshold_low(threshold_low),
        .hysteresis(hysteresis),
        .min_on_s(min_on_s),
        .min_off_s(min_off_s),
        .dry_alert_s(dry_alert_s),
        .humidifier_on(humidifier_on),
        .led(led),
        .current_humidity(current_humidity),
        .dry_level(dry_level),
        .dry_seconds(dry_seconds),
        .status_code(status_code)
    );

    task wait_cycles;
        input integer cycles;
        integer i;
        begin
            for (i = 0; i < cycles; i = i + 1)
                @(posedge clk);
        end
    endtask

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

    initial begin
        resetn = 1'b0;
        wait_cycles(5);
        resetn = 1'b1;
        wait_cycles(5);

        check(humidifier_on == 1'b0, "reset/default humidity should keep humidifier off");
        check(led == 4'b0000, "LEDs should be off when humidifier is off");

        sw_humidity = 8'd35;
        wait_cycles(40);
        check(humidifier_on == 1'b1, "low humidity should turn humidifier on");
        check(led == 4'b1111, "low humidity should turn all LEDs on");

        sw_humidity = 8'd55;
        wait_cycles(40);
        check(humidifier_on == 1'b0, "high humidity should turn humidifier off");
        check(led == 4'b0000, "high humidity should turn LEDs off");

        manual_mode = 1'b1;
        manual_on = 1'b1;
        wait_cycles(5);
        check(humidifier_on == 1'b1, "manual_on should force humidifier on");
        check(led == 4'b1111, "manual_on should force LEDs on");

        manual_on = 1'b0;
        wait_cycles(5);
        check(humidifier_on == 1'b0, "manual off should force humidifier off");
        check(led == 4'b0000, "manual off should force LEDs off");

        $display("tb_humidifier_core PASS");
        $finish;
    end
endmodule
