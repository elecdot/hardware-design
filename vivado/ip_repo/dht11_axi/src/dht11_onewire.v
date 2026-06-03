`timescale 1ns / 1ps

module dht11_onewire #(
    // PYNQ-Z1: clk_0 = 125MHz
    // 125 个 clk 周期 = 1us
    parameter [21:0] POWER_ON_NUM     = 22'd1000000,  // 上电等待 1s
    parameter [21:0] READ_GAP_NUM     = 22'd1000000,  // 两次读取间隔 1s
    parameter [21:0] RELEASE_WAIT_NUM = 22'd30        // 主机释放后等待 30us
)(
    input  wire        clk,
    input  wire        rst_n,

    // DHT11 单总线，BD 外部端口 dht11_0，XDC 约束到 R17
    inout  wire        dht11,

    // ILA 调试信号
    output wire        dht_raw_dbg,
    output wire [3:0]  cur_state_dbg,
    output wire [5:0]  bit_cnt_dbg,
    output wire [21:0] count_1us_dbg,
    output wire        recv_phase_dbg,
    output wire        dht_sync_dbg,
    output wire        dht_us_d0_dbg,
    output wire        dht_out_en_dbg,
    output wire        dht_out_val_dbg,

    // 输出数据：{湿度整数, 湿度小数, 温度整数, 温度小数}
    output reg  [31:0] data_valid
);

    //============================================================
    // 状态定义
    //============================================================
    localparam S_POWER_ON     = 4'd0;
    localparam S_LOW_20MS     = 4'd1;
    localparam S_RELEASE_30US = 4'd2;
    localparam S_WAIT_RESP    = 4'd3;
    localparam S_RESP_LOW     = 4'd4;
    localparam S_RESP_HIGH    = 4'd5;
    localparam S_RECV         = 4'd6;
    localparam S_DONE         = 4'd7;
    localparam S_WAIT_NEXT    = 4'd8;

    //============================================================
    // DHT11 协议时间参数，单位 us
    //============================================================
    localparam [21:0] START_LOW_NUM      = 22'd20000; // 主机拉低 20ms
    localparam [21:0] RESP_WAIT_TIMEOUT  = 22'd1000;  // 等待响应低电平超时
    localparam [21:0] RESP_PULSE_TIMEOUT = 22'd200;   // 响应低/高电平超时
    localparam [21:0] BIT_LOW_TIMEOUT    = 22'd200;   // 等 bit 低电平结束超时
    localparam [21:0] BIT_HIGH_TIMEOUT   = 22'd150;   // bit 高电平超时
    localparam [21:0] BIT_ONE_THRESHOLD  = 22'd50;    // 高电平 > 50us 判为 1

    //============================================================
    // 显式 IOBUF
    //
    // dht_i：真实引脚输入
    // dht_o：FPGA 输出值
    // dht_t：三态控制，1=高阻输入，0=输出
    //============================================================
    wire dht_i;
    wire dht_o;
    wire dht_t;

    reg  dht_out_en;
    reg  dht_out_val;

    assign dht_o = dht_out_val;
    assign dht_t = ~dht_out_en;

    IOBUF dht11_iobuf_inst (
        .I  (dht_o),
        .O  (dht_i),
        .T  (dht_t),
        .IO (dht11)
    );

    assign dht_raw_dbg = dht_i;

    //============================================================
    // 125MHz 分频出 1us tick
    //============================================================
    reg [6:0] div_cnt;
    reg       tick_1us;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            div_cnt  <= 7'd0;
            tick_1us <= 1'b0;
        end else begin
            if (div_cnt == 7'd124) begin
                div_cnt  <= 7'd0;
                tick_1us <= 1'b1;
            end else begin
                div_cnt  <= div_cnt + 1'b1;
                tick_1us <= 1'b0;
            end
        end
    end

    //============================================================
    // 输入同步：真实引脚 dht_i → dht_sync
    //============================================================
    reg dht_meta;
    reg dht_sync;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dht_meta <= 1'b1;
            dht_sync <= 1'b1;
        end else begin
            dht_meta <= dht_i;
            dht_sync <= dht_meta;
        end
    end

    //============================================================
    // 1us 域采样，用于边沿检测
    //============================================================
    reg dht_us_d0;
    reg dht_us_d1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dht_us_d0 <= 1'b1;
            dht_us_d1 <= 1'b1;
        end else if (tick_1us) begin
            dht_us_d1 <= dht_us_d0;
            dht_us_d0 <= dht_sync;
        end
    end

    wire dht_posedge =  dht_us_d0 & ~dht_us_d1;
    wire dht_negedge = ~dht_us_d0 &  dht_us_d1;

    //============================================================
    // 主寄存器
    //============================================================
    reg [3:0]  cur_state;
    reg [21:0] count_1us;
    reg        recv_phase;   // 0: 等 bit 低电平结束；1: 测 bit 高电平宽度
    reg [5:0]  bit_cnt;
    reg [39:0] data_temp;

    wire        bit_is_one;
    wire [39:0] frame_next;
    wire [7:0]  checksum_next;

    assign bit_is_one = (count_1us > BIT_ONE_THRESHOLD);
    assign frame_next = {data_temp[38:0], bit_is_one};

    assign checksum_next = frame_next[39:32] +
                           frame_next[31:24] +
                           frame_next[23:16] +
                           frame_next[15:8];

    //============================================================
    // 状态机
    //============================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cur_state   <= S_POWER_ON;
            count_1us   <= 22'd0;
            dht_out_en  <= 1'b0;
            dht_out_val <= 1'b1;
            recv_phase  <= 1'b0;
            bit_cnt     <= 6'd0;
            data_temp   <= 40'd0;
            data_valid  <= 32'd0;
        end else if (tick_1us) begin
            case (cur_state)

                //================================================
                // 上电等待
                //================================================
                S_POWER_ON: begin
                    dht_out_en  <= 1'b0;
                    dht_out_val <= 1'b1;
                    recv_phase  <= 1'b0;
                    bit_cnt     <= 6'd0;
                    data_temp   <= 40'd0;

                    if (count_1us >= POWER_ON_NUM - 1'b1) begin
                        cur_state <= S_LOW_20MS;
                        count_1us <= 22'd0;
                    end else begin
                        count_1us <= count_1us + 1'b1;
                    end
                end

                //================================================
                // 主机拉低 20ms
                //================================================
                S_LOW_20MS: begin
                    dht_out_en  <= 1'b1;
                    dht_out_val <= 1'b0;

                    if (count_1us >= START_LOW_NUM - 1'b1) begin
                        cur_state   <= S_RELEASE_30US;
                        count_1us   <= 22'd0;
                        dht_out_en  <= 1'b0;  // 释放总线
                        dht_out_val <= 1'b1;
                    end else begin
                        count_1us <= count_1us + 1'b1;
                    end
                end

                //================================================
                // 释放总线，等待 20~40us
                //================================================
                S_RELEASE_30US: begin
                    dht_out_en  <= 1'b0;
                    dht_out_val <= 1'b1;

                    if (count_1us >= RELEASE_WAIT_NUM - 1'b1) begin
                        cur_state <= S_WAIT_RESP;
                        count_1us <= 22'd0;
                    end else begin
                        count_1us <= count_1us + 1'b1;
                    end
                end

                //================================================
                // 等 DHT11 响应低电平
                //
                // 稳定版关键：
                // 不只等下降沿，也接受"进入本状态时线已经为 0"
                //================================================
                S_WAIT_RESP: begin
                    dht_out_en  <= 1'b0;
                    dht_out_val <= 1'b1;

                    if (dht_negedge || (dht_us_d0 == 1'b0)) begin
                        cur_state <= S_RESP_LOW;
                        count_1us <= 22'd0;
                    end else if (count_1us >= RESP_WAIT_TIMEOUT) begin
                        cur_state <= S_DONE;
                        count_1us <= 22'd0;
                    end else begin
                        count_1us <= count_1us + 1'b1;
                    end
                end

                //================================================
                // DHT11 响应低电平，大约 80us
                //
                // 稳定版：
                // 不只等上升沿，也接受"进入本状态时线已经为 1"
                //================================================
                S_RESP_LOW: begin
                    dht_out_en <= 1'b0;

                    if (dht_posedge || (dht_us_d0 == 1'b1)) begin
                        cur_state <= S_RESP_HIGH;
                        count_1us <= 22'd0;
                    end else if (count_1us >= RESP_PULSE_TIMEOUT) begin
                        cur_state <= S_DONE;
                        count_1us <= 22'd0;
                    end else begin
                        count_1us <= count_1us + 1'b1;
                    end
                end

                //================================================
                // DHT11 响应高电平，大约 80us
                //
                // 稳定版：
                // 不只等下降沿，也接受"进入本状态时线已经为 0"
                //================================================
                S_RESP_HIGH: begin
                    dht_out_en <= 1'b0;

                    if (dht_negedge || (dht_us_d0 == 1'b0)) begin
                        cur_state  <= S_RECV;
                        count_1us  <= 22'd0;
                        recv_phase <= 1'b0;
                        bit_cnt    <= 6'd0;
                        data_temp  <= 40'd0;
                    end else if (count_1us >= RESP_PULSE_TIMEOUT) begin
                        cur_state <= S_DONE;
                        count_1us <= 22'd0;
                    end else begin
                        count_1us <= count_1us + 1'b1;
                    end
                end

                //================================================
                // 接收 40bit
                //
                // 每 bit：
                // 50us 低电平 + 高电平
                // 高电平 26~28us 为 0，约 70us 为 1
                //
                // 稳定版：
                // phase0 不只等上升沿，也接受已经为高
                // phase1 不只等下降沿，也接受已经为低
                //================================================
                S_RECV: begin
                    dht_out_en <= 1'b0;

                    if (recv_phase == 1'b0) begin
                        // 等 bit 低电平结束，进入高电平计时
                        if (dht_posedge || (dht_us_d0 == 1'b1)) begin
                            recv_phase <= 1'b1;
                            count_1us  <= 22'd0;
                        end else if (count_1us >= BIT_LOW_TIMEOUT) begin
                            cur_state  <= S_DONE;
                            count_1us  <= 22'd0;
                            recv_phase <= 1'b0;
                            bit_cnt    <= 6'd0;
                        end else begin
                            count_1us <= count_1us + 1'b1;
                        end
                    end else begin
                        // 测 bit 高电平宽度，下降沿/变低后判 0/1
                        if (dht_negedge || (dht_us_d0 == 1'b0)) begin
                            data_temp <= frame_next;
                            count_1us <= 22'd0;

                            if (bit_cnt == 6'd39) begin
                                if (checksum_next == frame_next[7:0]) begin
                                    data_valid <= frame_next[39:8];
                                end

                                cur_state  <= S_DONE;
                                recv_phase <= 1'b0;
                                bit_cnt    <= 6'd0;
                            end else begin
                                bit_cnt    <= bit_cnt + 1'b1;
                                recv_phase <= 1'b0;
                            end
                        end else if (count_1us >= BIT_HIGH_TIMEOUT) begin
                            cur_state  <= S_DONE;
                            count_1us  <= 22'd0;
                            recv_phase <= 1'b0;
                            bit_cnt    <= 6'd0;
                        end else begin
                            count_1us <= count_1us + 1'b1;
                        end
                    end
                end

                //================================================
                // 一轮结束
                //================================================
                S_DONE: begin
                    dht_out_en  <= 1'b0;
                    dht_out_val <= 1'b1;
                    recv_phase  <= 1'b0;
                    bit_cnt     <= 6'd0;
                    data_temp   <= 40'd0;
                    count_1us   <= 22'd0;
                    cur_state   <= S_WAIT_NEXT;
                end

                //================================================
                // 等待下一次读取
                //================================================
                S_WAIT_NEXT: begin
                    dht_out_en  <= 1'b0;
                    dht_out_val <= 1'b1;
                    recv_phase  <= 1'b0;

                    if (count_1us >= READ_GAP_NUM - 1'b1) begin
                        cur_state <= S_LOW_20MS;
                        count_1us <= 22'd0;
                    end else begin
                        count_1us <= count_1us + 1'b1;
                    end
                end

                default: begin
                    cur_state   <= S_POWER_ON;
                    count_1us   <= 22'd0;
                    dht_out_en  <= 1'b0;
                    dht_out_val <= 1'b1;
                    recv_phase  <= 1'b0;
                    bit_cnt     <= 6'd0;
                    data_temp   <= 40'd0;
                end

            endcase
        end
    end

    //============================================================
    // Debug 输出
    //============================================================
    assign cur_state_dbg   = cur_state;
    assign bit_cnt_dbg     = bit_cnt;
    assign count_1us_dbg   = count_1us;
    assign recv_phase_dbg  = recv_phase;
    assign dht_sync_dbg    = dht_sync;
    assign dht_us_d0_dbg   = dht_us_d0;
    assign dht_out_en_dbg  = dht_out_en;
    assign dht_out_val_dbg = dht_out_val;

endmodule