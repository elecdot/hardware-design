`timescale 1ns / 1ps

module uart_tx #(
    parameter integer BPS = 9600,
    parameter integer SYS_CLK_FRE = 100000000
)(
    input  wire       sys_clk,
    input  wire       sys_rst_n,
    input  wire [7:0] uart_data,
    input  wire       uart_tx_en,
    input  wire       read_can,
    output reg        uart_txd,
    output wire       tx_busy
);

    localparam integer BPS_CNT = (SYS_CLK_FRE + BPS / 2) / BPS;

    reg        uart_tx_en_d0;
    reg        uart_tx_en_d1;

    (* mark_debug = "true" *) reg        tx_flag;
    (* mark_debug = "true" *) reg [7:0]  uart_data_reg;
    (* mark_debug = "true" *) reg [15:0] clk_cnt;
    (* mark_debug = "true" *) reg [3:0]  tx_cnt;

    wire pos_uart_en_txd;

    assign pos_uart_en_txd = uart_tx_en_d0 & (~uart_tx_en_d1);

    assign tx_busy = tx_flag;

    always @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            uart_tx_en_d0 <= 1'b0;
            uart_tx_en_d1 <= 1'b0;
        end else begin
            uart_tx_en_d0 <= uart_tx_en;
            uart_tx_en_d1 <= uart_tx_en_d0;
        end
    end

    always @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            tx_flag       <= 1'b0;
            uart_data_reg <= 8'd0;
        end else begin
            if (pos_uart_en_txd && read_can && !tx_flag) begin
                tx_flag       <= 1'b1;
                uart_data_reg <= uart_data;
            end else if ((tx_cnt == 4'd9) && (clk_cnt == BPS_CNT - 1)) begin
                tx_flag       <= 1'b0;
                uart_data_reg <= 8'd0;
            end
        end
    end

    always @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            clk_cnt <= 16'd0;
            tx_cnt  <= 4'd0;
        end else if (tx_flag) begin
            if (clk_cnt < BPS_CNT - 1) begin
                clk_cnt <= clk_cnt + 1'b1;
            end else begin
                clk_cnt <= 16'd0;
                tx_cnt  <= tx_cnt + 1'b1;
            end
        end else begin
            clk_cnt <= 16'd0;
            tx_cnt  <= 4'd0;
        end
    end

    always @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            uart_txd <= 1'b1;
        end else if (tx_flag) begin
            case (tx_cnt)
                4'd0: uart_txd <= 1'b0;              // 起始位
                4'd1: uart_txd <= uart_data_reg[0];  // 数据位 bit0
                4'd2: uart_txd <= uart_data_reg[1];
                4'd3: uart_txd <= uart_data_reg[2];
                4'd4: uart_txd <= uart_data_reg[3];
                4'd5: uart_txd <= uart_data_reg[4];
                4'd6: uart_txd <= uart_data_reg[5];
                4'd7: uart_txd <= uart_data_reg[6];
                4'd8: uart_txd <= uart_data_reg[7];  // 数据位 bit7
                4'd9: uart_txd <= 1'b1;              // 停止位
                default: uart_txd <= 1'b1;
            endcase
        end else begin
            uart_txd <= 1'b1;
        end
    end

endmodule