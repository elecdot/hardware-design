`timescale 1ns / 1ps

module uart_rx #(
    parameter integer BPS = 9600,
    parameter integer SYS_CLK_FRE = 100000000
)(
    input  wire       sys_clk,
    input  wire       sys_rst_n,
    input  wire       uart_rxd,
    input  wire       read_done,
    output reg  [7:0] uart_rx_data,
    output reg        uart_rx_done,
    output reg        read_can
);

    localparam integer BPS_CNT = (SYS_CLK_FRE + BPS / 2) / BPS;

    reg        uart_rx_d0;
    reg        uart_rx_d1;

    (* mark_debug = "true" *) reg [15:0] clk_cnt;
    (* mark_debug = "true" *) reg [3:0]  rx_cnt;
    (* mark_debug = "true" *) reg        rx_flag;
    (* mark_debug = "true" *) reg [7:0]  uart_rx_data_reg;

    (* mark_debug = "true" *) wire       neg_uart_rx_data;

    assign neg_uart_rx_data = uart_rx_d1 & (~uart_rx_d0);

    always @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            uart_rx_d0 <= 1'b1;
            uart_rx_d1 <= 1'b1;
        end else begin
            uart_rx_d0 <= uart_rxd;
            uart_rx_d1 <= uart_rx_d0;
        end
    end

    always @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            rx_flag  <= 1'b0;
            read_can <= 1'b0;
        end else begin
            if (neg_uart_rx_data && !rx_flag) begin
                rx_flag <= 1'b1;
            end else if ((rx_cnt == 4'd9) && (clk_cnt == BPS_CNT / 2)) begin
                rx_flag  <= 1'b0;
                read_can <= 1'b1;
            end else if (read_done) begin
                read_can <= 1'b0;
            end
        end
    end

    always @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            clk_cnt <= 16'd0;
            rx_cnt  <= 4'd0;
        end else if (rx_flag) begin
            if (clk_cnt < BPS_CNT - 1) begin
                clk_cnt <= clk_cnt + 1'b1;
            end else begin
                clk_cnt <= 16'd0;
                rx_cnt  <= rx_cnt + 1'b1;
            end
        end else begin
            clk_cnt <= 16'd0;
            rx_cnt  <= 4'd0;
        end
    end

    always @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            uart_rx_data_reg <= 8'd0;
        end else if (rx_flag && (clk_cnt == BPS_CNT / 2)) begin
            case (rx_cnt)
                4'd1: uart_rx_data_reg[0] <= uart_rx_d1;
                4'd2: uart_rx_data_reg[1] <= uart_rx_d1;
                4'd3: uart_rx_data_reg[2] <= uart_rx_d1;
                4'd4: uart_rx_data_reg[3] <= uart_rx_d1;
                4'd5: uart_rx_data_reg[4] <= uart_rx_d1;
                4'd6: uart_rx_data_reg[5] <= uart_rx_d1;
                4'd7: uart_rx_data_reg[6] <= uart_rx_d1;
                4'd8: uart_rx_data_reg[7] <= uart_rx_d1;
                default: ;
            endcase
        end
    end

    always @(posedge sys_clk or negedge sys_rst_n) begin
        if (!sys_rst_n) begin
            uart_rx_done <= 1'b0;
            uart_rx_data <= 8'd0;
        end else if ((rx_cnt == 4'd9) && (clk_cnt == BPS_CNT / 2)) begin
            uart_rx_done <= 1'b1;
            uart_rx_data <= uart_rx_data_reg;
        end else begin
            uart_rx_done <= 1'b0;
        end
    end

endmodule