`timescale 1ns / 1ps

module jy901_i2c_slave_model (
    input  wire scl,
    inout  wire sda
);
    localparam DEV_ADDR = 7'h50;
    reg sda_drive_low = 1'b0;
    reg [7:0] mem [0:25];
    reg [7:0] byte_value;
    reg [7:0] reg_addr;
    reg [7:0] cfg_low;
    reg [7:0] cfg_high;
    reg [7:0] cfg_reg_addr;
    reg [15:0] cfg_word;
    reg cfg_write_seen;
    reg nack_reg;
    reg nack_addr_read;
    reg nack_cfg_low;
    reg nack_cfg_high;
    reg expect_cfg_write;
    integer i;

    assign sda = sda_drive_low ? 1'b0 : 1'bz;

    initial begin
        mem[0]  = 8'h34; mem[1]  = 8'h12;
        mem[2]  = 8'h78; mem[3]  = 8'h56;
        mem[4]  = 8'hBC; mem[5]  = 8'h9A;
        mem[6]  = 8'h02; mem[7]  = 8'h01;
        mem[8]  = 8'h04; mem[9]  = 8'h03;
        mem[10] = 8'h06; mem[11] = 8'h05;
        mem[12] = 8'h08; mem[13] = 8'h07;
        mem[14] = 8'h0A; mem[15] = 8'h09;
        mem[16] = 8'h0C; mem[17] = 8'h0B;
        mem[18] = 8'h0E; mem[19] = 8'h0D;
        mem[20] = 8'h10; mem[21] = 8'h0F;
        mem[22] = 8'h12; mem[23] = 8'h11;
        mem[24] = 8'h0C; mem[25] = 8'h0D;
        cfg_low = 8'd0;
        cfg_high = 8'd0;
        cfg_reg_addr = 8'd0;
        cfg_word = 16'd0;
        cfg_write_seen = 1'b0;
        nack_reg = 1'b0;
        nack_addr_read = 1'b0;
        nack_cfg_low = 1'b0;
        nack_cfg_high = 1'b0;
        expect_cfg_write = 1'b0;
    end

    task wait_start;
        begin
            @(negedge sda);
            while (scl !== 1'b1) @(negedge sda);
        end
    endtask

    task read_byte;
        output [7:0] value;
        integer bit_idx;
        begin
            value = 8'd0;
            for (bit_idx = 7; bit_idx >= 0; bit_idx = bit_idx - 1) begin
                @(posedge scl);
                value[bit_idx] = sda;
                @(negedge scl);
            end
        end
    endtask

    task send_ack;
        begin
            sda_drive_low = 1'b1;
            @(posedge scl);
            @(negedge scl);
            sda_drive_low = 1'b0;
        end
    endtask

    task send_byte;
        input [7:0] value;
        output master_ack;
        integer bit_idx;
        begin
            for (bit_idx = 7; bit_idx >= 0; bit_idx = bit_idx - 1) begin
                sda_drive_low = ~value[bit_idx];
                @(posedge scl);
                @(negedge scl);
            end
            sda_drive_low = 1'b0;
            @(posedge scl);
            master_ack = (sda == 1'b0);
            @(negedge scl);
        end
    endtask

    reg master_ack;
    initial begin
        sda_drive_low = 1'b0;
        forever begin
            wait_start();
            read_byte(byte_value);
            if (byte_value == {DEV_ADDR, 1'b0}) begin
                send_ack();
                read_byte(reg_addr);
                if (nack_reg) begin
                    sda_drive_low = 1'b0;
                end else begin
                    send_ack();
                    if (expect_cfg_write) begin
                        read_byte(cfg_low);
                        if (nack_cfg_low) begin
                            sda_drive_low = 1'b0;
                        end else begin
                            send_ack();
                            read_byte(cfg_high);
                            if (nack_cfg_high) begin
                                sda_drive_low = 1'b0;
                            end else begin
                                send_ack();
                                cfg_reg_addr = reg_addr;
                                cfg_word = {cfg_high, cfg_low};
                                cfg_write_seen = 1'b1;
                            end
                        end
                    end else begin
                        wait_start();
                        read_byte(byte_value);
                        if (byte_value == {DEV_ADDR, 1'b1}) begin
                            if (nack_addr_read) begin
                                sda_drive_low = 1'b0;
                            end else begin
                                send_ack();
                                for (i = 0; i < 26; i = i + 1) begin
                                    send_byte(mem[i], master_ack);
                                    if (!master_ack) i = 26;
                                end
                            end
                        end
                    end
                end
            end
        end
    end
endmodule
