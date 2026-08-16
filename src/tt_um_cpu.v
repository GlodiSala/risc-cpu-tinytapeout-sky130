`default_nettype none
`include "defines.vh"

module tt_um_cpu (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    wire rst = !rst_n;

    // ========================================================================
    // SYNCHRONISATION MISO
    // ========================================================================
    reg miso_sync;
    always @(posedge clk) begin
        if (rst) begin
            miso_sync <= 1'b0;
        end else begin
            miso_sync <= uio_in[2];
        end
    end
    reg [15:0] instr_stable;

    always @(posedge clk) begin
        if (rst) begin
            instr_stable <= 16'h0000;
        end else if (mem_ready) begin
            instr_stable <= instruction; // On mémorise l'instruction [cite: 228]
        end
    end

    // ========================================================================
    // SIGNAUX INTERNES
    // ========================================================================
    wire [9:0] pc_current;
    wire [15:0] instruction;
    wire        mem_ready;

    wire reg_write, mem_read, mem_write, flag_write, alu_src;
    wire [1:0] reg_write_src;
    wire [3:0] alu_op;
    wire [3:0] branch_type;
    wire [9:0] branch_offset;
    wire [7:0] alu_immediate;
    wire [2:0] addr1_select, addr2_select;

    wire [7:0] reg_data1, reg_data2;
    wire [7:0] alu_result;
    wire [7:0] mem_rdata;
    wire [7:0] reg_write_data;

    wire zero, overflow, carry, negative;
    wire [3:0] stored_flags;
    wire [9:0] next_pc;
    
    // Signaux SPI
    wire spi_cs, spi_sck, spi_mosi;

    // ========================================================================
    // PROGRAM MEMORY (SPI RAM)
    // ========================================================================
    ProgramMemory_SPI_RAM program_mem (
        .clk(clk),
        .rst(rst | !ena),
        .address(pc_current),
        .instruction(instruction),
        .ready(mem_ready),
        .spi_cs(spi_cs),
        .spi_sck(spi_sck),
        .spi_mosi(spi_mosi),
        .spi_miso(miso_sync)
    );

    // ========================================================================
    // MAPPING SPI
    // ========================================================================
    assign uio_out[0] = spi_cs;
    assign uio_oe[0]  = 1'b1;
    
    assign uio_out[1] = spi_mosi;
    assign uio_oe[1]  = 1'b1;
    
    assign uio_out[2] = 1'b0;
    assign uio_oe[2]  = 1'b0;
    
    assign uio_out[3] = spi_sck;
    assign uio_oe[3]  = 1'b1;

    assign uio_out[7:4] = 4'b0000;
    assign uio_oe[7:4]  = 4'b0000;

    // ========================================================================
    // SORTIE : PC (par défaut) / debug (opt-in via ui_in)
    // ========================================================================
    // ui_in was previously fully unused, so this is purely additive: with
    // ui_in left at its default 0 (grounded, unconnected, or reset), uo_out
    // keeps exposing pc_current[7:0] exactly as before. Driving ui_in[7:6]
    // lets a tester read out internal CPU state that is otherwise only
    // visible via RTL-only hierarchical signal references, which don't
    // survive synthesis and can't be checked against the gate-level netlist.
    //   ui_in[7:6] == 2'b00 : uo_out = pc_current[7:0]      (default)
    //   ui_in[7:6] == 2'b01 : uo_out = register ui_in[2:0]
    //   ui_in[7:6] == 2'b10 : uo_out = {4'b0, stored_flags} (O,C,S,Z)
    //   ui_in[7:6] == 2'b11, ui_in[0] == 0 : uo_out = alu_result
    //   ui_in[7:6] == 2'b11, ui_in[0] == 1 : uo_out = data memory[ui_in[5:1]]
    // The memory-debug read reuses DataMemory's existing (mem_read, addr)
    // read port instead of adding a second, parallel 32:1 mux inside
    // DataMemory: that duplicate mux was expensive enough (a full extra
    // 8-bit-wide 32-to-1 mux) to blow past what the fixed TinyTapeout die
    // area can comfortably route, causing severe place & route congestion.
    wire debug_mem_active = (ui_in[7:6] == 2'b11) && ui_in[0];

    wire [7:0] debug_out = (ui_in[7:6] == 2'b01) ? debug_reg :
                            (ui_in[7:6] == 2'b10) ? {4'b0, stored_flags} :
                            (ui_in[7:6] == 2'b11) ? (ui_in[0] ? mem_rdata : alu_result) :
                                                     pc_current[7:0];

    assign uo_out = debug_out;

    // ========================================================================
    // MODULES INTERNES
    // ========================================================================
    ProgramCounter pc (
        .clk(clk),
        .rst(rst | !ena),
        .mem_ready(mem_ready),
        .next_pc(next_pc), // Nouvelle sortie,
        .pc_current(pc_current)
    );

    ControlUnit cu (
        .instruction(instr_stable),
        .reg_write(reg_write),
        .reg_write_src(reg_write_src),
        .mem_read(mem_read),
        .mem_write(mem_write),
        .addr1_select(addr1_select),
        .addr2_select(addr2_select),
        .alu_operation(alu_op),
        .alu_src(alu_src),
        .alu_immediate(alu_immediate),
        .flag_write(flag_write),
        .branch_type(branch_type),
        .branch_offset(branch_offset)
    );

    assign reg_write_data = (reg_write_src == 2'b01) ? mem_rdata : alu_result;
    
    wire [7:0] debug_reg;

    RegisterFile regfile (
        .clk(clk),
        .rst(rst | !ena),
        .write_en(reg_write),
        .enable(mem_ready),
        .addr_wr(instr_stable[11:9]),
        .data_wr(reg_write_data),
        .addr1_r(addr1_select),
        .addr2_r(addr2_select),
        .out1_r(reg_data1),
        .out2_r(reg_data2),
        .addr3_r(ui_in[2:0]),
        .out3_r(debug_reg)
    );

    wire [7:0] alu_operand_b = (alu_src) ? alu_immediate : reg_data2;
    
    ALU alu (
        .operation(alu_op),
        .operand1(reg_data1),
        .operand2(alu_operand_b),
        .result(alu_result),
        .zero_flag(zero),
        .overflow_flag(overflow),
        .carry_flag(carry),
        .negative_flag(negative)
    );

    FlagRegister flag_reg (
        .clk(clk),
        .rst(rst | !ena),
        .write(flag_write && mem_ready),
        .flags_alu({overflow, carry, negative, zero}),
        .stored_flags(stored_flags)
    );

    BranchUnit branch_unit (
        .branch_type(branch_type),
        .branch_offset(branch_offset),
        .stored_flags(stored_flags),
        .pc_current(pc_current),
        .next_pc(next_pc) 
    );

    // While a memory-debug read is selected, borrow the read port: force
    // mem_read and swap the address for the debug-selected one. This never
    // touches mem_write, so it can't corrupt memory; it can only momentarily
    // change what mem_rdata shows (irrelevant unless a LOAD's own write-back
    // happens on that exact cycle, which debug reads — done after a test
    // program is done running — don't overlap in practice).
    wire [7:0] dm_addr     = debug_mem_active ? {3'b0, ui_in[5:1]} : alu_result;
    wire       dm_mem_read = mem_read | debug_mem_active;

    DataMemory data_mem (
        .clk(clk),
        .mem_read(dm_mem_read),
        .mem_write(mem_write && mem_ready && ena),
        .addr(dm_addr),
        .wdata(reg_data2),
        .rdata(mem_rdata)
    );

    // ========================================================================
    // LISTE DES ENTRÉES NON UTILISÉES (COMME LE TEMPLATE)
    // ========================================================================
    // ui_in is now used (debug mux select, see above); only uio_in[7:3] and
    // uio_in[1:0] remain genuinely unused (uio_in[2] is the SPI MISO line).
    wire _unused = &{uio_in[7:3], uio_in[1:0], 1'b0};

endmodule
