`default_nettype none
`timescale 1ns / 1ps

module tb ();

  initial begin
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    #1;
  end

  // Signaux
  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  reg [7:0] uio_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif

  // Signaux SPI
  wire spi_cs   = uio_out[0];
  wire spi_mosi = uio_out[1];
  wire spi_sck  = uio_out[3];
  wire spi_miso;
  
  // Connecter MISO
  assign uio_in[2] = spi_miso;
  assign uio_in[7:3] = 5'b00000;
  assign uio_in[1:0] = 2'b00;

  // DUT
  tt_um_cpu user_project (
`ifdef GL_TEST
      .VPWR(VPWR),
      .VGND(VGND),
`endif
      .ui_in  (ui_in),
      .uo_out (uo_out),
      .uio_in (uio_in),
      .uio_out(uio_out),
      .uio_oe (uio_oe),
      .ena    (ena),
      .clk    (clk),
      .rst_n  (rst_n)
  );
  
  // Simulateur de Flash SPI (suit le protocole depuis le bus, pas de
  // référence hiérarchique vers l'intérieur du DUT — nécessaire pour que
  // ça marche aussi contre la netlist gate-level synthétisée).
  spi_flash_sim flash_sim (
      .spi_cs(spi_cs),
      .spi_sck(spi_sck),
      .spi_mosi(spi_mosi),
      .spi_miso(spi_miso)
  );

endmodule