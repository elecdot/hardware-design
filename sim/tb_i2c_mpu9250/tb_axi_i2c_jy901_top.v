`timescale 1ns / 1ps

module tb_axi_i2c_jy901_top;
    localparam ADDR_CTRL          = 7'h00;
    localparam ADDR_STATUS        = 7'h04;
    localparam ADDR_DEV_ADDR      = 7'h08;
    localparam ADDR_START_REG     = 7'h0C;
    localparam ADDR_WORD_COUNT    = 7'h10;
    localparam ADDR_SAMPLE_PERIOD = 7'h14;
    localparam ADDR_I2C_CLKDIV    = 7'h18;
    localparam ADDR_ERROR_CODE    = 7'h1C;
    localparam ADDR_CFG_REG_ADDR  = 7'h20;
    localparam ADDR_CFG_DATA      = 7'h24;
    localparam ADDR_VERSION       = 7'h28;
    localparam ADDR_AX_RAW        = 7'h40;
    localparam ADDR_AY_RAW        = 7'h44;
    localparam ADDR_TEMP_RAW      = 7'h70;
    localparam ADDR_SAMPLE_CNT    = 7'h74;

    localparam CTRL_ENABLE   = 32'h0000_0001;
    localparam CTRL_ONESHOT  = 32'h0000_0002;
    localparam CTRL_AUTO     = 32'h0000_0004;
    localparam CTRL_CLR_DONE = 32'h0000_0008;
    localparam CTRL_CLR_ERR  = 32'h0000_0010;
    localparam CTRL_SOFT_RST = 32'h0000_0020;
    localparam CTRL_CFG_WR   = 32'h0000_0100;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;

    reg [6:0]  s_axi_awaddr = 7'd0;
    reg [2:0]  s_axi_awprot = 3'd0;
    reg        s_axi_awvalid = 1'b0;
    wire       s_axi_awready;
    reg [31:0] s_axi_wdata = 32'd0;
    reg [3:0]  s_axi_wstrb = 4'h0;
    reg        s_axi_wvalid = 1'b0;
    wire       s_axi_wready;
    wire [1:0] s_axi_bresp;
    wire       s_axi_bvalid;
    reg        s_axi_bready = 1'b0;
    reg [6:0]  s_axi_araddr = 7'd0;
    reg [2:0]  s_axi_arprot = 3'd0;
    reg        s_axi_arvalid = 1'b0;
    wire       s_axi_arready;
    wire [31:0] s_axi_rdata;
    wire [1:0] s_axi_rresp;
    wire       s_axi_rvalid;
    reg        s_axi_rready = 1'b0;

    tri1 i2c_scl;
    tri1 i2c_sda;

    axi_i2c_jy901_v1_0 dut (
        .s00_axi_aclk(clk),
        .s00_axi_aresetn(resetn),
        .s00_axi_awaddr(s_axi_awaddr),
        .s00_axi_awprot(s_axi_awprot),
        .s00_axi_awvalid(s_axi_awvalid),
        .s00_axi_awready(s_axi_awready),
        .s00_axi_wdata(s_axi_wdata),
        .s00_axi_wstrb(s_axi_wstrb),
        .s00_axi_wvalid(s_axi_wvalid),
        .s00_axi_wready(s_axi_wready),
        .s00_axi_bresp(s_axi_bresp),
        .s00_axi_bvalid(s_axi_bvalid),
        .s00_axi_bready(s_axi_bready),
        .s00_axi_araddr(s_axi_araddr),
        .s00_axi_arprot(s_axi_arprot),
        .s00_axi_arvalid(s_axi_arvalid),
        .s00_axi_arready(s_axi_arready),
        .s00_axi_rdata(s_axi_rdata),
        .s00_axi_rresp(s_axi_rresp),
        .s00_axi_rvalid(s_axi_rvalid),
        .s00_axi_rready(s_axi_rready),
        .i2c_scl(i2c_scl),
        .i2c_sda(i2c_sda)
    );

    jy901_i2c_slave_model slave (
        .scl(i2c_scl),
        .sda(i2c_sda)
    );

    task axi_write;
        input [6:0] addr;
        input [31:0] data;
        begin
            @(negedge clk);
            s_axi_awaddr = addr;
            s_axi_awvalid = 1'b1;
            s_axi_wdata = data;
            s_axi_wstrb = 4'hF;
            s_axi_wvalid = 1'b1;
            s_axi_bready = 1'b1;
            wait (s_axi_awready && s_axi_wready);
            @(negedge clk);
            s_axi_awvalid = 1'b0;
            s_axi_wvalid = 1'b0;
            s_axi_wstrb = 4'h0;
            wait (s_axi_bvalid);
            if (s_axi_bresp !== 2'b00) begin
                $display("FAIL: AXI write BRESP addr=0x%02x resp=%0d", addr, s_axi_bresp);
                $finish;
            end
            @(negedge clk);
            s_axi_bready = 1'b0;
        end
    endtask

    task axi_read;
        input [6:0] addr;
        output [31:0] data;
        begin
            @(negedge clk);
            s_axi_araddr = addr;
            s_axi_arvalid = 1'b1;
            s_axi_rready = 1'b1;
            wait (s_axi_arready);
            @(negedge clk);
            s_axi_arvalid = 1'b0;
            wait (s_axi_rvalid);
            data = s_axi_rdata;
            if (s_axi_rresp !== 2'b00) begin
                $display("FAIL: AXI read RRESP addr=0x%02x resp=%0d", addr, s_axi_rresp);
                $finish;
            end
            @(negedge clk);
            s_axi_rready = 1'b0;
        end
    endtask

    task wait_status_done;
        output [31:0] status;
        integer polls;
        begin
            status = 32'd0;
            for (polls = 0; polls < 2000; polls = polls + 1) begin
                axi_read(ADDR_STATUS, status);
                if (status[1]) polls = 2000;
            end
            if (!status[1]) begin
                $display("FAIL: timeout waiting STATUS.done, STATUS=0x%08x", status);
                $finish;
            end
        end
    endtask

    task wait_status_idle;
        output [31:0] status;
        integer polls;
        begin
            status = 32'd0;
            for (polls = 0; polls < 2000; polls = polls + 1) begin
                axi_read(ADDR_STATUS, status);
                if (!status[0]) polls = 2000;
            end
            if (status[0]) begin
                $display("FAIL: timeout waiting STATUS.busy deassert, STATUS=0x%08x", status);
                $finish;
            end
        end
    endtask

    task clear_status_flags;
        begin
            wait_status_idle(status);
            axi_write(ADDR_CTRL, CTRL_ENABLE | CTRL_CLR_DONE | CTRL_CLR_ERR);
            repeat (5) @(negedge clk);
        end
    endtask

    task expect_error_transaction;
        input [7:0] expected_error;
        begin
            clear_status_flags();
            axi_write(ADDR_CTRL, CTRL_ENABLE | CTRL_ONESHOT);
            wait_status_done(status);
            axi_read(ADDR_ERROR_CODE, rd);
            if (!status[3] || status[4] || rd[7:0] !== expected_error) begin
                $display("FAIL: expected error 0x%02x STATUS=0x%08x ERROR=0x%02x",
                         expected_error, status, rd[7:0]);
                $finish;
            end
        end
    endtask

    task expect_cfg_error_transaction;
        input [7:0] expected_error;
        begin
            clear_status_flags();
            axi_write(ADDR_CTRL, CTRL_ENABLE | CTRL_CFG_WR);
            wait_status_done(status);
            axi_read(ADDR_ERROR_CODE, rd);
            if (!status[3] || status[4] || rd[7:0] !== expected_error) begin
                $display("FAIL: expected cfg error 0x%02x STATUS=0x%08x ERROR=0x%02x",
                         expected_error, status, rd[7:0]);
                $finish;
            end
        end
    endtask

    task run_word_count_case;
        input [7:0] words;
        input [31:0] expected_cnt;
        begin
            clear_status_flags();
            axi_write(ADDR_DEV_ADDR, 32'h50);
            axi_write(ADDR_WORD_COUNT, words);
            axi_write(ADDR_CTRL, CTRL_ENABLE | CTRL_ONESHOT);
            wait_status_done(status);
            axi_read(ADDR_SAMPLE_CNT, sample_cnt);
            axi_read(ADDR_AX_RAW, ax_raw);
            if (status[4] || status[3] || !status[2] ||
                sample_cnt !== expected_cnt || ax_raw[15:0] !== 16'h1234) begin
                $display("FAIL: WORD_COUNT case words=%0d STATUS=0x%08x CNT=%0d AX=0x%04x",
                         words, status, sample_cnt, ax_raw[15:0]);
                $finish;
            end
        end
    endtask

    reg [31:0] rd;
    reg [31:0] status;
    reg [31:0] ax_raw;
    reg [31:0] ay_raw;
    reg [31:0] temp_raw;
    reg [31:0] sample_cnt;
    reg [31:0] sample_cnt_before;
    reg [31:0] sample_cnt_after;
    reg [1023:0] vcd_file;

    initial begin
        if (!$value$plusargs("VCD=%s", vcd_file)) begin
            vcd_file = "tb_axi_i2c_jy901_top.vcd";
        end
        $dumpfile(vcd_file);
        $dumpvars(0, tb_axi_i2c_jy901_top);

        repeat (10) @(negedge clk);
        resetn = 1'b1;
        repeat (10) @(negedge clk);

        axi_read(ADDR_VERSION, rd);
        if (rd !== 32'h4A593101) begin
            $display("FAIL: VERSION mismatch, got 0x%08x", rd);
            $finish;
        end

        axi_read(ADDR_DEV_ADDR, rd);
        if (rd[6:0] !== 7'h50) begin
            $display("FAIL: DEV_ADDR reset mismatch, got 0x%08x", rd);
            $finish;
        end

        axi_write(ADDR_I2C_CLKDIV, 32'd4);
        axi_write(ADDR_START_REG, 32'h34);
        axi_write(ADDR_WORD_COUNT, 32'd13);
        axi_write(ADDR_DEV_ADDR, 32'h50);
        axi_write(ADDR_CTRL, CTRL_ENABLE | CTRL_ONESHOT);

        wait_status_done(status);
        if (status[4] || status[3] || !status[2]) begin
            $display("FAIL: normal STATUS invalid, STATUS=0x%08x", status);
            $finish;
        end

        axi_read(ADDR_AX_RAW, ax_raw);
        axi_read(ADDR_AY_RAW, ay_raw);
        axi_read(ADDR_TEMP_RAW, temp_raw);
        axi_read(ADDR_SAMPLE_CNT, sample_cnt);
        if (ax_raw[15:0] !== 16'h1234 || ay_raw[15:0] !== 16'h5678 ||
            temp_raw[15:0] !== 16'h0D0C || sample_cnt !== 32'd1) begin
            $display("FAIL: data mismatch AX=0x%04x AY=0x%04x TEMP=0x%04x CNT=%0d",
                     ax_raw[15:0], ay_raw[15:0], temp_raw[15:0], sample_cnt);
            $finish;
        end

        $display("PASS: AXI top burst read register path completed");

        clear_status_flags();
        axi_read(ADDR_STATUS, status);
        if (status[1] || status[3] || status[4]) begin
            $display("FAIL: clear flags did not clear STATUS=0x%08x", status);
            $finish;
        end
        $display("PASS: AXI top clear_done/clear_error path completed");

        run_word_count_case(8'd1, 32'd2);
        run_word_count_case(8'd0, 32'd3);
        run_word_count_case(8'd20, 32'd4);
        $display("PASS: AXI top WORD_COUNT boundary paths completed");

        clear_status_flags();
        axi_write(ADDR_SAMPLE_PERIOD, 32'd4);
        axi_write(ADDR_DEV_ADDR, 32'h50);
        axi_read(ADDR_SAMPLE_CNT, sample_cnt_before);
        axi_write(ADDR_CTRL, CTRL_ENABLE | CTRL_AUTO);
        repeat (8000) @(negedge clk);
        axi_write(ADDR_CTRL, CTRL_ENABLE);
        axi_read(ADDR_SAMPLE_CNT, sample_cnt_after);
        if (sample_cnt_after < sample_cnt_before + 32'd2) begin
            $display("FAIL: auto_mode did not increment enough before=%0d after=%0d",
                     sample_cnt_before, sample_cnt_after);
            $finish;
        end
        $display("PASS: AXI top auto_mode path completed");

        clear_status_flags();
        slave.expect_cfg_write = 1'b1;
        slave.cfg_write_seen = 1'b0;
        axi_write(ADDR_CFG_REG_ADDR, 32'h1A);
        axi_write(ADDR_CFG_DATA, 32'h55AA);
        axi_write(ADDR_CTRL, CTRL_ENABLE | CTRL_CFG_WR);
        wait_status_done(status);
        if (status[4] || status[3] || !status[5] ||
            !slave.cfg_write_seen || slave.cfg_reg_addr !== 8'h1A ||
            slave.cfg_word !== 16'h55AA) begin
            $display("FAIL: cfg write mismatch STATUS=0x%08x seen=%0d reg=0x%02x word=0x%04x",
                     status, slave.cfg_write_seen, slave.cfg_reg_addr, slave.cfg_word);
            $finish;
        end
        slave.expect_cfg_write = 1'b0;
        $display("PASS: AXI top cfg_write path completed");

        clear_status_flags();
        axi_write(ADDR_DEV_ADDR, 32'h51);
        axi_write(ADDR_CTRL, CTRL_ENABLE | CTRL_ONESHOT);

        wait_status_done(status);
        axi_read(ADDR_ERROR_CODE, rd);
        if (!status[3] || status[4] || rd[7:0] !== 8'h01) begin
            $display("FAIL: AXI top address NACK mismatch STATUS=0x%08x ERROR=0x%02x",
                     status, rd[7:0]);
            $finish;
        end

        $display("PASS: AXI top address NACK register path completed");

        axi_write(ADDR_DEV_ADDR, 32'h50);
        slave.nack_reg = 1'b1;
        expect_error_transaction(8'h02);
        slave.nack_reg = 1'b0;

        slave.nack_addr_read = 1'b1;
        expect_error_transaction(8'h03);
        slave.nack_addr_read = 1'b0;

        slave.expect_cfg_write = 1'b1;
        slave.nack_cfg_low = 1'b1;
        expect_cfg_error_transaction(8'h04);
        slave.nack_cfg_low = 1'b0;

        slave.nack_cfg_high = 1'b1;
        expect_cfg_error_transaction(8'h05);
        slave.nack_cfg_high = 1'b0;
        slave.expect_cfg_write = 1'b0;
        $display("PASS: AXI top extended NACK paths completed");

        axi_write(ADDR_CTRL, CTRL_ENABLE | CTRL_SOFT_RST);
        repeat (5) @(negedge clk);
        axi_read(ADDR_SAMPLE_CNT, sample_cnt);
        axi_read(ADDR_AX_RAW, ax_raw);
        axi_read(ADDR_STATUS, status);
        if (sample_cnt !== 32'd0 || ax_raw[15:0] !== 16'h0000 ||
            status[2] || status[1] || status[3] || status[4]) begin
            $display("FAIL: soft_reset mismatch STATUS=0x%08x CNT=%0d AX=0x%04x",
                     status, sample_cnt, ax_raw[15:0]);
            $finish;
        end
        $display("PASS: AXI top soft_reset path completed");

        $finish;
    end

    initial begin
        #50_000_000;
        $display("FAIL: AXI top simulation timeout");
        $finish;
    end
endmodule
