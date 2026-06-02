`timescale 1ns / 1ps

module IOBUF (
    input  wire I,
    output wire O,
    input  wire T,
    inout  wire IO
);
    assign IO = T ? 1'bz : I;
    assign O = IO;
endmodule

module tb_dht11_onewire_smoke;
    reg clk = 1'b0;
    reg rst_n = 1'b0;

    tri1 dht11;
    reg tb_drive_en = 1'b0;
    reg tb_drive_val = 1'b1;

    wire dht_raw_dbg;
    wire [3:0] cur_state_dbg;
    wire [5:0] bit_cnt_dbg;
    wire [21:0] count_1us_dbg;
    wire recv_phase_dbg;
    wire dht_sync_dbg;
    wire dht_us_d0_dbg;
    wire dht_out_en_dbg;
    wire dht_out_val_dbg;
    wire [31:0] data_valid;

    localparam [31:0] EXPECTED_DATA = 32'h3700_1900;

    assign dht11 = tb_drive_en ? tb_drive_val : 1'bz;

    always #4 clk = ~clk;

    dht11_onewire #(
        .POWER_ON_NUM(22'd1000),
        .READ_GAP_NUM(22'd2000)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .dht11(dht11),
        .dht_raw_dbg(dht_raw_dbg),
        .cur_state_dbg(cur_state_dbg),
        .bit_cnt_dbg(bit_cnt_dbg),
        .count_1us_dbg(count_1us_dbg),
        .recv_phase_dbg(recv_phase_dbg),
        .dht_sync_dbg(dht_sync_dbg),
        .dht_us_d0_dbg(dht_us_d0_dbg),
        .dht_out_en_dbg(dht_out_en_dbg),
        .dht_out_val_dbg(dht_out_val_dbg),
        .data_valid(data_valid)
    );

    task send_bit;
        input bitval;
        begin
            tb_drive_en = 1'b1;
            tb_drive_val = 1'b0;
            #(50_017);

            tb_drive_val = 1'b1;
            if (bitval)
                #(70_017);
            else
                #(26_017);
        end
    endtask

    task send_byte;
        input [7:0] dat;
        integer i;
        begin
            for (i = 7; i >= 0; i = i - 1)
                send_bit(dat[i]);
        end
    endtask

    task send_frame;
        input [7:0] humi_int;
        input [7:0] humi_dec;
        input [7:0] temp_int;
        input [7:0] temp_dec;
        reg [7:0] checksum;
        begin
            checksum = humi_int + humi_dec + temp_int + temp_dec;

            send_byte(humi_int);
            send_byte(humi_dec);
            send_byte(temp_int);
            send_byte(temp_dec);
            send_byte(checksum);

            tb_drive_en = 1'b1;
            tb_drive_val = 1'b0;
            #(50_017);
            tb_drive_en = 1'b0;
            tb_drive_val = 1'b1;
        end
    endtask

    initial begin
        #100;
        rst_n = 1'b1;
    end

    initial begin
        forever begin
            wait (dht11 === 1'b0);
            #(18_000_000);
            if (dht11 === 1'b0) begin
                wait (dht11 === 1'b1);
                #(30_017);
                tb_drive_en = 1'b1;
                tb_drive_val = 1'b0;
                #(80_017);
                tb_drive_val = 1'b1;
                #(80_017);
                send_frame(8'd55, 8'd0, 8'd25, 8'd0);
            end
        end
    end

    initial begin
        wait (data_valid == EXPECTED_DATA);
        $display("tb_dht11_onewire_smoke PASS data_valid=%h", data_valid);
        $finish;
    end

    initial begin
        #80_000_000;
        $display(
            "ERROR: DHT11 smoke timeout data_valid=%h state=%0d bit_cnt=%0d",
            data_valid,
            cur_state_dbg,
            bit_cnt_dbg
        );
        $finish;
    end
endmodule
