`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Module Name: humidifier_core
// Description : Humidity threshold control core for a humidifier/LED actuator.
//               It receives humidity value from DHT11 driver or from software,
//               filters it, applies hysteresis and minimum ON/OFF time, then
//               outputs humidifier_on. On PYNQ-Z1, LEDs simulate the actuator:
//               humidifier_on=1 -> all LEDs on; humidifier_on=0 -> all LEDs off.
//////////////////////////////////////////////////////////////////////////////////

module humidifier_core #(
    parameter integer CLK_FREQ_HZ = 100_000_000
)(
    input  wire        clk,
    input  wire        resetn,

    // control
    input  wire        enable,          // 1: automatic control enabled
    input  wire        manual_mode,     // 1: ignore threshold and use manual_on
    input  wire        manual_on,       // valid when manual_mode=1
    input  wire        use_sw_humidity, // 1: use sw_humidity; 0: use hardware humidity
    input  wire        clear_counter,   // 1 clock pulse: clear dry_seconds

    // humidity input from DHT11 module
    input  wire        humidity_valid,  // 1 clock pulse when humidity_hw is updated
    input  wire [7:0]  humidity_hw,     // relative humidity value, 0~100

    // humidity input from AXI/Jupyter for independent demo
    input  wire [7:0]  sw_humidity,     // software-provided humidity, 0~100

    // parameters
    input  wire [7:0]  threshold_low,   // turn ON when humidity <= this value
    input  wire [7:0]  hysteresis,      // turn OFF when humidity >= threshold_low + hysteresis
    input  wire [15:0] min_on_s,        // minimum ON time, seconds
    input  wire [15:0] min_off_s,       // minimum OFF time, seconds
    input  wire [15:0] dry_alert_s,     // running duration to enter level 3

    // outputs
    output reg         humidifier_on,
    output reg  [3:0]  led,
    output reg  [7:0]  current_humidity,
    output reg  [1:0]  dry_level,       // 0 normal, 1 dry, 2 very dry, 3 long-running dry
    output reg  [31:0] dry_seconds,
    output reg  [31:0] status_code
);

    localparam integer SEC_CNT_WIDTH = 32;

    reg [SEC_CNT_WIDTH-1:0] sec_cnt;
    reg one_sec_tick;

    // Low-pass filter: filtered = 3/4 old + 1/4 new
    reg        filter_inited;
    reg [9:0]  filtered_humidity_x4; // humidity * 4
    wire [7:0] selected_humidity = use_sw_humidity ? sw_humidity : humidity_hw;
    wire       selected_valid    = use_sw_humidity ? 1'b1 : humidity_valid;

    wire [8:0] threshold_off_ext = {1'b0, threshold_low} + {1'b0, hysteresis};
    wire [7:0] threshold_off = (threshold_off_ext > 9'd100) ? 8'd100 : threshold_off_ext[7:0];
    wire [7:0] threshold_very_dry = (threshold_low > 8'd5) ? (threshold_low - 8'd5) : 8'd0;

    reg [31:0] on_seconds;
    reg [31:0] off_seconds;

    // generate 1-second tick
    always @(posedge clk) begin
        if (!resetn) begin
            sec_cnt      <= 0;
            one_sec_tick <= 1'b0;
        end else begin
            if (sec_cnt >= CLK_FREQ_HZ - 1) begin
                sec_cnt      <= 0;
                one_sec_tick <= 1'b1;
            end else begin
                sec_cnt      <= sec_cnt + 1'b1;
                one_sec_tick <= 1'b0;
            end
        end
    end

    // humidity filtering
    always @(posedge clk) begin
        if (!resetn) begin
            filter_inited        <= 1'b0;
            filtered_humidity_x4 <= 10'd0;
            current_humidity     <= 8'd50;
        end else if (selected_valid) begin
            if (!filter_inited) begin
                filter_inited        <= 1'b1;
                filtered_humidity_x4 <= {2'b00, selected_humidity} << 2;
                current_humidity     <= selected_humidity;
            end else begin
                filtered_humidity_x4 <= ((filtered_humidity_x4 * 3) + ({2'b00, selected_humidity} << 2)) >> 2;
                current_humidity     <= (((filtered_humidity_x4 * 3) + ({2'b00, selected_humidity} << 2)) >> 4);
            end
        end
    end

    // second counters
    always @(posedge clk) begin
        if (!resetn) begin
            on_seconds  <= 32'd0;
            off_seconds <= 32'd0;
            dry_seconds <= 32'd0;
        end else if (clear_counter) begin
            dry_seconds <= 32'd0;
        end else if (one_sec_tick) begin
            if (humidifier_on) begin
                on_seconds  <= on_seconds + 1'b1;
                off_seconds <= 32'd0;
                dry_seconds <= dry_seconds + 1'b1;
            end else begin
                off_seconds <= off_seconds + 1'b1;
                on_seconds  <= 32'd0;
            end
        end
    end

    // main control with hysteresis and min on/off time
    always @(posedge clk) begin
        if (!resetn) begin
            humidifier_on <= 1'b0;
        end else if (!enable) begin
            humidifier_on <= 1'b0;
        end else if (manual_mode) begin
            humidifier_on <= manual_on;
        end else begin
            if (!humidifier_on) begin
                if ((current_humidity <= threshold_low) && (off_seconds >= min_off_s))
                    humidifier_on <= 1'b1;
            end else begin
                if ((current_humidity >= threshold_off) && (on_seconds >= min_on_s))
                    humidifier_on <= 1'b0;
            end
        end
    end

    // dry level and LED output
    always @(posedge clk) begin
        if (!resetn) begin
            dry_level   <= 2'd0;
            led         <= 4'b0000;
            status_code <= 32'h0000_0000;
        end else begin
            if (!enable) begin
                dry_level <= 2'd0;
            end else if (humidifier_on && (dry_seconds >= dry_alert_s)) begin
                dry_level <= 2'd3;
            end else if (current_humidity <= threshold_very_dry) begin
                dry_level <= 2'd2;
            end else if (current_humidity <= threshold_low) begin
                dry_level <= 2'd1;
            end else begin
                dry_level <= 2'd0;
            end

            led <= (enable && humidifier_on) ? 4'b1111 : 4'b0000;
            status_code <= {8'hA5, 7'd0, humidifier_on, 6'd0, dry_level, current_humidity};
        end
    end

endmodule
