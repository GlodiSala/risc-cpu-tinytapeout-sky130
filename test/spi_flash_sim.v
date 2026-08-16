`timescale 1ns/1ps

// Behavioral SPI flash model used by test/tb.v.
//
// Mirrors the protocol implemented by src/ProgramMemory_SPI.v: an 8-bit
// command byte (0x03, unused here beyond framing), a 16-bit address phase
// (6 dummy bits + the 10-bit PC), then a 16-bit data phase, all MSB-first,
// one bit per spi_sck pulse while spi_cs is held low.
//
// Unlike the earlier version of this file, this model tracks the
// transaction purely from the SPI bus signals (cs/sck/mosi) instead of
// reaching into the DUT's internal registers via hierarchical references
// (e.g. `user_project.program_mem.state`). Those internal names don't
// survive synthesis, so the hierarchical version only worked in RTL
// simulation and broke the gate-level CI test (gl_test). This version
// works identically against the RTL and the synthesized netlist.
//
// Command/address bits are sampled on the rising edge of spi_sck, mirroring
// how ProgramMemory_SPI_RAM drives spi_mosi (no extra latching in that
// direction). Data bits are driven on the falling edge, one half-cycle
// ahead of the corresponding rising edge, to give tt_um_cpu's `miso_sync`
// input synchronizer (an extra clk-cycle of latching on the MISO path
// only) enough lead time to have the right value latched when
// ProgramMemory_SPI_RAM actually samples it.
module spi_flash_sim (
    input  wire spi_cs,
    input  wire spi_sck,
    input  wire spi_mosi,
    output reg  spi_miso
);

    localparam CMD_BITS  = 8;
    localparam ADDR_BITS = 16;
    localparam DATA_BITS = 16;

    // Test program, addressed by the full 10-bit PC value sent in the
    // address phase. Widened from the original 16-word (4-bit) model to
    // give self-checking test programs (see test.py) room for a PASS/FAIL
    // tail without hitting an artificial size limit — this is testbench-only
    // storage, so widening it has no effect on the real chip.
    reg [15:0] memory [0:1023];
    integer mem_init_i;
    initial begin
        for (mem_init_i = 0; mem_init_i < 1024; mem_init_i = mem_init_i + 1)
            memory[mem_init_i] = 16'h9000; // JMP +0 (self-loop) as a safe default
        memory[0]  = 16'h620A;  // LOADI R1, 10
        memory[1]  = 16'h6414;  // LOADI R2, 20
        memory[2]  = 16'h0650;  // ADD R3, R1, R2
        memory[3]  = 16'h8600;  // STORE R3, [R0+0]
        memory[4]  = 16'h7800;  // LOAD R4, [R0+0]
        memory[5]  = 16'hF700;  // CMP R3, R4
        memory[6]  = 16'hA002;  // BRZ +2
        memory[7]  = 16'h6BFF;  // LOADI R5, 255
        memory[8]  = 16'h6C64;  // LOADI R6, 100
        memory[9]  = 16'h9FFF;  // JMP -1
    end

    integer    bit_cnt;      // command+address bit counter (0..CMD_BITS+ADDR_BITS-1)
    integer    data_cnt;     // data-phase bit counter (0..DATA_BITS-1)
    reg [15:0] addr_shift;
    reg [15:0] data_word;
    reg        data_phase;

    initial begin
        bit_cnt    = 0;
        data_cnt   = 0;
        addr_shift = 16'h0000;
        data_word  = 16'h0000;
        data_phase = 1'b0;
        spi_miso   = 1'b0;
    end

    // Command + address: sampled on the rising edge, same edge
    // ProgramMemory_SPI_RAM's own spi_mosi output settles on.
    always @(posedge spi_sck or posedge spi_cs) begin
        if (spi_cs) begin
            bit_cnt    <= 0;
            data_phase <= 1'b0;
        end else if (bit_cnt < CMD_BITS) begin
            bit_cnt <= bit_cnt + 1;
        end else if (bit_cnt < CMD_BITS + ADDR_BITS) begin
            addr_shift <= {addr_shift[14:0], spi_mosi};
            if (bit_cnt == CMD_BITS + ADDR_BITS - 1) begin
                data_word  <= memory[{addr_shift[8:0], spi_mosi}];
                data_phase <= 1'b1;
            end
            bit_cnt <= bit_cnt + 1;
        end
    end

    // Data: driven on the falling edge (one half-cycle ahead of the
    // matching rising edge) to compensate for the DUT's MISO synchronizer.
    always @(negedge spi_sck or posedge spi_cs) begin
        if (spi_cs) begin
            data_cnt <= 0;
            spi_miso <= 1'b0;
        end else if (data_phase && data_cnt < DATA_BITS) begin
            spi_miso <= data_word[15 - data_cnt];
            data_cnt <= data_cnt + 1;
        end
    end

endmodule
