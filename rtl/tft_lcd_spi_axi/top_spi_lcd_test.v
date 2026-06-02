`timescale 1ns/1ps
// -----------------------------------------------------------------------------
// top_spi_lcd_test.v
//
// PYNQ-Z1 + 1.3 inch ST7789 TFT LCD standalone hardware test.
//
// 功能：
//   1. 上电后自动复位 TFT 屏幕
//   2. 自动发送 ST7789 初始化命令
//   3. 自动设置 240x240 显示窗口
//   4. 自动循环填充纯色：红、绿、蓝、白、黑
//
// 注意：
//   这是"纯硬件测试顶层"，不经过 AXI，不经过 Jupyter。
//   目的是先证明 SPI 时序 + PMOD 接线 + 屏幕驱动链路是通的。
// -----------------------------------------------------------------------------

module top_spi_lcd_test (
    input  wire sys_clk,   // PYNQ-Z1 PL 端 125MHz 时钟，约束到 H16

    output wire lcd_scl,   // 接 TFT SCL
    output wire lcd_sda,   // 接 TFT SDA
    output wire lcd_res,   // 接 TFT RES
    output wire lcd_dc,    // 接 TFT DC
    output wire lcd_blk    // 接 TFT BLK
);

    // -------------------------------------------------------------------------
    // 1. 基本参数
    // -------------------------------------------------------------------------
    localparam integer CLK_FREQ_HZ = 125_000_000;

    // SPI 半周期分频值。
    // SCL 频率 = 125MHz / (2 * CLK_DIV_VALUE)
    // 25 对应 2.5MHz，比较稳，线长一点也不容易出问题。
    localparam [15:0] CLK_DIV_VALUE = 16'd25;

    localparam integer DELAY_20MS   = CLK_FREQ_HZ / 50;          // 20ms
    localparam integer DELAY_120MS  = (CLK_FREQ_HZ / 1000) * 120; // 120ms
    localparam integer DELAY_500MS  = CLK_FREQ_HZ / 2;           // 500ms

    localparam integer LCD_W        = 240;
    localparam integer LCD_H        = 240;
    localparam integer FRAME_BYTES  = LCD_W * LCD_H * 2;         // 240*240*2=115200

    // -------------------------------------------------------------------------
    // 2. 内部上电复位
    // -------------------------------------------------------------------------
    // PYNQ-Z1 这个纯 PL 测试顶层暂时不用外部复位按钮。
    // 用一个短计数器产生内部复位，等计数器满后 rst_n=1。
    reg [15:0] por_cnt = 16'd0;
    wire rst_n = &por_cnt;

    always @(posedge sys_clk) begin
        if (!rst_n) begin
            por_cnt <= por_cnt + 16'd1;
        end
    end

    // -------------------------------------------------------------------------
    // 3. SPI master 控制信号
    // -------------------------------------------------------------------------
    (* mark_debug = "true" *) reg  [7:0]  tx_data;
    (* mark_debug = "true" *) reg         tx_dc;
    (* mark_debug = "true" *) reg         tx_start;
    (* mark_debug = "true" *) wire        busy;
    (* mark_debug = "true" *) wire        done;

    reg lcd_res_in;
    reg lcd_blk_in;

    (* mark_debug = "true" *) wire lcd_scl_w;
    (* mark_debug = "true" *) wire lcd_sda_w;
    (* mark_debug = "true" *) wire lcd_dc_w;
    (* mark_debug = "true" *) wire lcd_res_w;
    (* mark_debug = "true" *) wire lcd_blk_w;

    assign lcd_scl = lcd_scl_w;
    assign lcd_sda = lcd_sda_w;
    assign lcd_dc  = lcd_dc_w;
    assign lcd_res = lcd_res_w;
    assign lcd_blk = lcd_blk_w;

    spi_lcd_master #(
        .CLK_DIV_DEFAULT(25)
    ) u_spi_lcd_master (
        .clk        (sys_clk),
        .rst_n      (rst_n),

        .tx_data    (tx_data),
        .tx_dc      (tx_dc),
        .tx_start   (tx_start),
        .clk_div    (CLK_DIV_VALUE),

        .lcd_res_in (lcd_res_in),
        .lcd_blk_in (lcd_blk_in),

        .lcd_scl    (lcd_scl_w),
        .lcd_sda    (lcd_sda_w),
        .lcd_dc     (lcd_dc_w),
        .lcd_res    (lcd_res_w),
        .lcd_blk    (lcd_blk_w),

        .busy       (busy),
        .done       (done)
    );

    // -------------------------------------------------------------------------
    // 4. 顶层测试状态机
    // -------------------------------------------------------------------------
    localparam [3:0] ST_RESET_LOW        = 4'd0;
    localparam [3:0] ST_RESET_HIGH       = 4'd1;
    localparam [3:0] ST_INIT_START       = 4'd2;
    localparam [3:0] ST_INIT_WAIT        = 4'd3;
    localparam [3:0] ST_INIT_DELAY       = 4'd4;
    localparam [3:0] ST_WINDOW_START     = 4'd5;
    localparam [3:0] ST_WINDOW_WAIT      = 4'd6;
    localparam [3:0] ST_FILL_START       = 4'd7;
    localparam [3:0] ST_FILL_WAIT        = 4'd8;
    localparam [3:0] ST_FRAME_DELAY      = 4'd9;

    (* mark_debug = "true" *) reg [3:0]  state;
    (* mark_debug = "true" *) reg [3:0]  init_idx;
    (* mark_debug = "true" *) reg [3:0]  window_idx;
    (* mark_debug = "true" *) reg [17:0] fill_byte_cnt;
    (* mark_debug = "true" *) reg [2:0]  color_idx;

    reg [31:0] delay_cnt;
    reg [31:0] delay_target;

    // -------------------------------------------------------------------------
    // 5. 初始化命令 ROM
    // -------------------------------------------------------------------------
    // init_idx 对应的内容：
    // 0: CMD  0x11  Sleep Out，之后等 120ms
    // 1: CMD  0x36  MADCTL
    // 2: DATA 0x00  显示方向
    // 3: CMD  0x3A  COLMOD
    // 4: DATA 0x05  RGB565, 16-bit/pixel
    // 5: CMD  0x21  Display Inversion On
    // 6: CMD  0x13  Normal Display On，之后短等
    // 7: CMD  0x29  Display On，之后等 120ms

    function [7:0] init_data;
        input [3:0] idx;
        begin
            case (idx)
                4'd0: init_data = 8'h11;
                4'd1: init_data = 8'h36;
                4'd2: init_data = 8'h00;
                4'd3: init_data = 8'h3A;
                4'd4: init_data = 8'h05;
                4'd5: init_data = 8'h21;
                4'd6: init_data = 8'h13;
                4'd7: init_data = 8'h29;
                default: init_data = 8'h00;
            endcase
        end
    endfunction

    function init_dc;
        input [3:0] idx;
        begin
            case (idx)
                4'd2: init_dc = 1'b1; // 0x36 的参数
                4'd4: init_dc = 1'b1; // 0x3A 的参数
                default: init_dc = 1'b0;
            endcase
        end
    endfunction

    function [31:0] init_delay;
        input [3:0] idx;
        begin
            case (idx)
                4'd0: init_delay = DELAY_120MS;
                4'd6: init_delay = DELAY_20MS;
                4'd7: init_delay = DELAY_120MS;
                default: init_delay = 32'd0;
            endcase
        end
    endfunction

    // -------------------------------------------------------------------------
    // 6. 设置窗口命令 ROM
    // -------------------------------------------------------------------------
    // 设置显示窗口：
    //   X: 0~239
    //   Y: 0~239
    //
    // ST7789 命令：
    //   0x2A CASET，列地址
    //   0x2B RASET，行地址
    //   0x2C RAMWR，开始写显存

    function [7:0] window_data;
        input [3:0] idx;
        begin
            case (idx)
                4'd0:  window_data = 8'h2A; // CASET
                4'd1:  window_data = 8'h00; // x_start high
                4'd2:  window_data = 8'h00; // x_start low
                4'd3:  window_data = 8'h00; // x_end high
                4'd4:  window_data = 8'hEF; // x_end low = 239

                4'd5:  window_data = 8'h2B; // RASET
                4'd6:  window_data = 8'h00; // y_start high
                4'd7:  window_data = 8'h00; // y_start low
                4'd8:  window_data = 8'h00; // y_end high
                4'd9:  window_data = 8'hEF; // y_end low = 239

                4'd10: window_data = 8'h2C; // RAMWR
                default: window_data = 8'h00;
            endcase
        end
    endfunction

    function window_dc;
        input [3:0] idx;
        begin
            case (idx)
                4'd1, 4'd2, 4'd3, 4'd4,
                4'd6, 4'd7, 4'd8, 4'd9:
                    window_dc = 1'b1; // 坐标参数
                default:
                    window_dc = 1'b0; // 命令
            endcase
        end
    endfunction

    // -------------------------------------------------------------------------
    // 7. 当前帧颜色
    // -------------------------------------------------------------------------
    // RGB565:
    //   RED   = 0xF800
    //   GREEN = 0x07E0
    //   BLUE  = 0x001F
    //   WHITE = 0xFFFF
    //   BLACK = 0x0000

    function [15:0] current_color;
        input [2:0] idx;
        begin
            case (idx)
                3'd0: current_color = 16'hF800; // red
                3'd1: current_color = 16'h07E0; // green
                3'd2: current_color = 16'h001F; // blue
                3'd3: current_color = 16'hFFFF; // white
                3'd4: current_color = 16'h0000; // black
                default: current_color = 16'hF800;
            endcase
        end
    endfunction

    wire [15:0] color_word = current_color(color_idx);

    // fill_byte_cnt[0] = 0 时发高字节，=1 时发低字节
    wire [7:0] pixel_byte = (fill_byte_cnt[0] == 1'b0) ? color_word[15:8] : color_word[7:0];

    // -------------------------------------------------------------------------
    // 8. 主状态机
    // -------------------------------------------------------------------------
    always @(posedge sys_clk) begin
        if (!rst_n) begin
            state         <= ST_RESET_LOW;

            tx_data       <= 8'h00;
            tx_dc         <= 1'b0;
            tx_start      <= 1'b0;

            lcd_res_in    <= 1'b0;
            lcd_blk_in    <= 1'b0;

            init_idx      <= 4'd0;
            window_idx    <= 4'd0;
            fill_byte_cnt <= 18'd0;
            color_idx     <= 3'd0;

            delay_cnt     <= 32'd0;
            delay_target  <= 32'd0;
        end else begin
            // 默认不启动发送；需要发送时只拉高 1 个 sys_clk 周期
            tx_start <= 1'b0;

            case (state)

                // -------------------------------------------------------------
                // 屏幕硬复位：RES 拉低 20ms
                // -------------------------------------------------------------
                ST_RESET_LOW: begin
                    lcd_res_in <= 1'b0;
                    lcd_blk_in <= 1'b0;

                    if (delay_cnt < DELAY_20MS) begin
                        delay_cnt <= delay_cnt + 32'd1;
                    end else begin
                        delay_cnt <= 32'd0;
                        state     <= ST_RESET_HIGH;
                    end
                end

                // -------------------------------------------------------------
                // 释放复位：RES 拉高，再等 120ms，背光打开
                // -------------------------------------------------------------
                ST_RESET_HIGH: begin
                    lcd_res_in <= 1'b1;
                    lcd_blk_in <= 1'b1;

                    if (delay_cnt < DELAY_120MS) begin
                        delay_cnt <= delay_cnt + 32'd1;
                    end else begin
                        delay_cnt <= 32'd0;
                        init_idx  <= 4'd0;
                        state     <= ST_INIT_START;
                    end
                end

                // -------------------------------------------------------------
                // 发送初始化命令/参数
                // -------------------------------------------------------------
                ST_INIT_START: begin
                    if (!busy) begin
                        tx_data  <= init_data(init_idx);
                        tx_dc    <= init_dc(init_idx);
                        tx_start <= 1'b1;
                        state    <= ST_INIT_WAIT;
                    end
                end

                ST_INIT_WAIT: begin
                    if (done) begin
                        delay_target <= init_delay(init_idx);
                        delay_cnt    <= 32'd0;

                        if (init_delay(init_idx) != 32'd0) begin
                            state <= ST_INIT_DELAY;
                        end else begin
                            if (init_idx == 4'd7) begin
                                window_idx <= 4'd0;
                                state      <= ST_WINDOW_START;
                            end else begin
                                init_idx <= init_idx + 4'd1;
                                state    <= ST_INIT_START;
                            end
                        end
                    end
                end

                ST_INIT_DELAY: begin
                    if (delay_cnt < delay_target) begin
                        delay_cnt <= delay_cnt + 32'd1;
                    end else begin
                        delay_cnt <= 32'd0;

                        if (init_idx == 4'd7) begin
                            window_idx <= 4'd0;
                            state      <= ST_WINDOW_START;
                        end else begin
                            init_idx <= init_idx + 4'd1;
                            state    <= ST_INIT_START;
                        end
                    end
                end

                // -------------------------------------------------------------
                // 每一帧开始前，重新设置显示窗口并发送 RAMWR
                // -------------------------------------------------------------
                ST_WINDOW_START: begin
                    if (!busy) begin
                        tx_data  <= window_data(window_idx);
                        tx_dc    <= window_dc(window_idx);
                        tx_start <= 1'b1;
                        state    <= ST_WINDOW_WAIT;
                    end
                end

                ST_WINDOW_WAIT: begin
                    if (done) begin
                        if (window_idx == 4'd10) begin
                            fill_byte_cnt <= 18'd0;
                            state         <= ST_FILL_START;
                        end else begin
                            window_idx <= window_idx + 4'd1;
                            state      <= ST_WINDOW_START;
                        end
                    end
                end

                // -------------------------------------------------------------
                // 连续发送整屏像素数据
                // -------------------------------------------------------------
                ST_FILL_START: begin
                    if (!busy) begin
                        tx_data  <= pixel_byte;
                        tx_dc    <= 1'b1;      // 像素数据，DC 必须为 1
                        tx_start <= 1'b1;
                        state    <= ST_FILL_WAIT;
                    end
                end

                ST_FILL_WAIT: begin
                    if (done) begin
                        if (fill_byte_cnt == FRAME_BYTES - 1) begin
                            delay_cnt <= 32'd0;
                            state     <= ST_FRAME_DELAY;
                        end else begin
                            fill_byte_cnt <= fill_byte_cnt + 18'd1;
                            state         <= ST_FILL_START;
                        end
                    end
                end

                // -------------------------------------------------------------
                // 一帧显示完，停 500ms，然后换颜色
                // -------------------------------------------------------------
                ST_FRAME_DELAY: begin
                    if (delay_cnt < DELAY_500MS) begin
                        delay_cnt <= delay_cnt + 32'd1;
                    end else begin
                        delay_cnt  <= 32'd0;
                        window_idx <= 4'd0;

                        if (color_idx == 3'd4) begin
                            color_idx <= 3'd0;
                        end else begin
                            color_idx <= color_idx + 3'd1;
                        end

                        state <= ST_WINDOW_START;
                    end
                end

                default: begin
                    state <= ST_RESET_LOW;
                end

            endcase
        end
    end

endmodule