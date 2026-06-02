`timescale 1ns / 1ps

module tb_dht11;

    reg clk;
    reg rst_n;

    tri1 dht11;            // 空闲默认上拉为1
    reg tb_drive_en;
    reg tb_drive_val;

    wire [31:0] data_valid;

    assign dht11 = tb_drive_en ? tb_drive_val : 1'bz;

    //========================================================
    // DUT：仿真时缩短等待时间
    //========================================================
    dht11_onewire #(
        .POWER_ON_NUM(22'd1000),   // 1000us
        .READ_GAP_NUM(22'd2000)    // 2000us
    ) uut (
        .clk(clk),
        .rst_n(rst_n),
        .dht11(dht11),
        .data_valid(data_valid)
    );

    //========================================================
    // 125MHz 时钟
    //========================================================
    initial begin
        clk = 1'b0;
        forever #4 clk = ~clk;
    end

    //========================================================
    // 发送1位：低50us + 高26us/70us
    //========================================================
    task send_bit;
        input bitval;
        begin
            tb_drive_en  = 1'b1;
            tb_drive_val = 1'b0;
            #(50_017);

            tb_drive_val = 1'b1;
            if (bitval)
                #(70_017);   // 1
            else
                #(26_017);   // 0
        end
    endtask

    //========================================================
    // 高位先发一个字节
    //========================================================
    task send_byte;
        input [7:0] dat;
        integer i;
        begin
            for (i = 7; i >= 0; i = i - 1)
                send_bit(dat[i]);
        end
    endtask

    //========================================================
    // 发送一整帧DHT11数据
    //========================================================
    task send_frame;
        input [7:0] humi_int;
        input [7:0] humi_dec;
        input [7:0] temp_int;
        input [7:0] temp_dec;
        reg   [7:0] checksum;
        begin
            checksum = humi_int + humi_dec + temp_int + temp_dec;

            send_byte(humi_int);
            send_byte(humi_dec);
            send_byte(temp_int);
            send_byte(temp_dec);
            send_byte(checksum);

            // 补一个结束低电平，让 DUT 能看到最后一个下降沿
            tb_drive_en  = 1'b1;
            tb_drive_val = 1'b0;
            #(50_017);

            // 释放总线
            tb_drive_en  = 1'b0;
            tb_drive_val = 1'b1;
        end
    endtask

    //========================================================
    // 基本复位
    //========================================================
    initial begin
        rst_n        = 1'b0;
        tb_drive_en  = 1'b0;
        tb_drive_val = 1'b1;

        #100;
        rst_n = 1'b1;
    end

    //========================================================
    // DHT11 响应模型：每一轮发送不同数据
    //========================================================
    time t_low_start;
    time t_low_end;

    integer frame_idx;
    reg [7:0] humi_int;
    reg [7:0] temp_int;

    initial begin
        frame_idx = 0;

        forever begin
            // 等主机拉低
            wait (dht11 === 1'b0);
            t_low_start = $time;

            // 等主机释放
            wait (dht11 === 1'b1);
            t_low_end = $time;

            // 只有主机低电平足够长才响应
            if ((t_low_end - t_low_start) >= 18_000_000) begin
                #(30_017);

                // 响应低80us
                tb_drive_en  = 1'b1;
                tb_drive_val = 1'b0;
                #(80_017);

                // 响应高80us
                tb_drive_val = 1'b1;
                #(80_017);

                // 每轮换一组数据
                // 第1轮：55% / 25℃
                // 第2轮：56% / 26℃
                // 第3轮：57% / 27℃
                humi_int = 8'd55 + frame_idx;
                temp_int = 8'd25 + frame_idx;

                send_frame(humi_int, 8'd0, temp_int, 8'd0);

                frame_idx = frame_idx + 1;
            end
        end
    end

    //========================================================
    // 打印观察
    //========================================================
    initial begin
        $monitor("[%0t ns] cur data_valid = %h", $time, data_valid);
    end

    //========================================================
    // 结束仿真
    //========================================================
    initial begin
        #120_000_000;   // 120ms，可看到多轮
        $stop;
    end

endmodule