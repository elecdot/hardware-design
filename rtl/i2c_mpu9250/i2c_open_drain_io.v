`timescale 1ns / 1ps

module i2c_open_drain_io (
    input  wire scl_drive_low,
    input  wire sda_drive_low,
    inout  wire i2c_scl,
    inout  wire i2c_sda,
    output wire scl_in,
    output wire sda_in
);
    assign i2c_scl = scl_drive_low ? 1'b0 : 1'bz;
    assign i2c_sda = sda_drive_low ? 1'b0 : 1'bz;

    assign scl_in = i2c_scl;
    assign sda_in = i2c_sda;
endmodule
