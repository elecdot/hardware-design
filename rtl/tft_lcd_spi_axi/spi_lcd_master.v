`timescale 1ns/1ps
// -----------------------------------------------------------------------------
// spi_lcd_master.v
// 8-bit SPI write-only master for ST7789 TFT LCD modules.
//
// 默认按 ST7789 TFT 常见写法：SPI Mode 3 风格
//   - SCL 空闲为高电平
//   - SCL 下降沿期间准备 SDA
//   - SCL 上升沿时 ST7789 采样 SDA
//
// 外部 LCD 引脚：
//   lcd_scl : 接屏幕 SCL
//   lcd_sda : 接屏幕 SDA
//   lcd_dc  : 接屏幕 DC，0=命令，1=数据/参数/像素
//   lcd_res : 接屏幕 RES，0=复位，1=正常
//   lcd_blk : 接屏幕 BLK，0=关背光，1=开背光
//
// 注意：你的 7 针模块没有 CS 引脚，所以这里不输出 CS。
// 如果你手上实际是 8 针模块，后面可以加 lcd_cs_n 并常态拉低。
// -----------------------------------------------------------------------------

module spi_lcd_master #(
    parameter integer CLK_DIV_DEFAULT = 10
    // 半个 SCL 周期对应多少个 clk 周期。
    // 如果 clk=100MHz，CLK_DIV_DEFAULT=10：
    // SCL = 100MHz / (2 * 10) = 5MHz
)(
    input  wire        clk,
    input  wire        rst_n,

    input  wire [7:0]  tx_data,      // 要发送的 8 位数据
    input  wire        tx_dc,        // 0=命令，1=数据
    input  wire        tx_start,     // 发送启动信号，上升沿有效
    input  wire [15:0] clk_div,      // 分频参数，0 表示使用默认值

    input  wire        lcd_res_in,   // 0=复位屏幕，1=正常
    input  wire        lcd_blk_in,   // 0=关背光，1=开背光

    output reg         lcd_scl,
    output reg         lcd_sda,
    output reg         lcd_dc,
    output reg         lcd_res,
    output reg         lcd_blk,

    output reg         busy,
    output reg         done          // 一个 clk 周期的完成脉冲
);

    localparam [1:0] ST_IDLE     = 2'd0;
    localparam [1:0] ST_TRANSFER = 2'd1;
    localparam [1:0] ST_DONE     = 2'd2;

    reg [1:0]  state;
    reg [7:0]  shift_reg;
    reg [2:0]  bit_idx;
    reg        phase;
    reg [15:0] div_cnt;
    reg        tx_start_d;

    wire start_pulse = tx_start & ~tx_start_d;
    wire [15:0] div_value = (clk_div == 16'd0) ? CLK_DIV_DEFAULT[15:0] : clk_div;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state      <= ST_IDLE;
            shift_reg  <= 8'h00;
            bit_idx    <= 3'd7;
            phase      <= 1'b0;
            div_cnt    <= 16'd0;
            tx_start_d <= 1'b0;

            lcd_scl    <= 1'b1;  // Mode 3：空闲为高
            lcd_sda    <= 1'b0;
            lcd_dc     <= 1'b1;
            lcd_res    <= 1'b1;
            lcd_blk    <= 1'b0;

            busy       <= 1'b0;
            done       <= 1'b0;
        end else begin
            tx_start_d <= tx_start;
            done       <= 1'b0;

            // RES 和 BLK 不属于 SPI 移位流程，可以随时由外部控制
            lcd_res <= lcd_res_in;
            lcd_blk <= lcd_blk_in;

            case (state)

                ST_IDLE: begin
                    busy    <= 1'b0;
                    lcd_scl <= 1'b1;
                    phase   <= 1'b0;
                    div_cnt <= 16'd0;

                    if (start_pulse) begin
                        shift_reg <= tx_data;
                        lcd_dc    <= tx_dc;
                        bit_idx   <= 3'd7;
                        busy      <= 1'b1;
                        state     <= ST_TRANSFER;
                    end
                end

                ST_TRANSFER: begin
                    busy <= 1'b1;

                    if (div_cnt < div_value - 1'b1) begin
                        div_cnt <= div_cnt + 1'b1;
                    end else begin
                        div_cnt <= 16'd0;

                        if (phase == 1'b0) begin
                            // 阶段 0：产生下降沿，把当前 bit 放到 SDA 上。
                            lcd_scl <= 1'b0;
                            lcd_sda <= shift_reg[bit_idx];
                            phase   <= 1'b1;
                        end else begin
                            // 阶段 1：产生上升沿，屏幕在这里采样 SDA。
                            lcd_scl <= 1'b1;
                            phase   <= 1'b0;

                            if (bit_idx == 3'd0) begin
                                state <= ST_DONE;
                            end else begin
                                bit_idx <= bit_idx - 1'b1;
                            end
                        end
                    end
                end

                ST_DONE: begin
                    busy    <= 1'b0;
                    done    <= 1'b1;
                    lcd_scl <= 1'b1;
                    state   <= ST_IDLE;
                end

                default: begin
                    state <= ST_IDLE;
                end

            endcase
        end
    end

endmodule