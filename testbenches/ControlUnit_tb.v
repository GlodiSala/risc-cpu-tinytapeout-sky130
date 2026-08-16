`include "defines.vh"

module ControlUnit_tb();

    reg [15:0] instruction;
    wire reg_write;
    wire [1:0] reg_write_src;
    wire [2:0] addr1_select;
    wire [2:0] addr2_select;
    wire mem_read, mem_write;
    wire [3:0] alu_operation;
    wire alu_src;
    wire [7:0] alu_immediate;
    wire flag_write;
    wire is_branch;
    wire [3:0] branch_type;
    wire [15:0] branch_offset;
    
    // Instanciation
    ControlUnit uut (
        .instruction(instruction),
        .reg_write(reg_write),
        .reg_write_src(reg_write_src),
        .addr1_select(addr1_select),
        .addr2_select(addr2_select),
        .mem_read(mem_read),
        .mem_write(mem_write),
        .alu_operation(alu_operation),
        .alu_src(alu_src),
        .alu_immediate(alu_immediate),
        .flag_write(flag_write),
        .is_branch(is_branch),
        .branch_type(branch_type),
        .branch_offset(branch_offset)
    );
    
    task test_instruction(
        input [15:0] instr,
        input [200*8:1] test_name
    );
    begin
        instruction = instr;
        #5;
        
        $display("--- %s ---", test_name);
        $display("Instruction: %b (%h)", instr, instr);
        $display("Opcode: %b | RegWr: %b | ASrc: %b | FWr: %b", 
                 instr[15:12], reg_write, alu_src, flag_write);
        $display("Addr1: %d | Addr2: %d | AluImm: %h", 
                 addr1_select, addr2_select, alu_immediate);
        if (is_branch) 
            $display("Branch: YES | Offset: %h", branch_offset);
        if (mem_read || mem_write)
            $display("Memory: R=%b W=%b | Src: %b", mem_read, mem_write, reg_write_src);
        $display("");
    end
    endtask
    
    initial begin
        $dumpfile("simulation.vcd");
        $dumpvars(0, ControlUnit_tb);
        
        $display("=== Test ControlUnit ===\n");
        
        // ========== R-TYPE INSTRUCTIONS ==========
        // Format: OPCODE(4) | RD(3) | RS1(3) | RS2(3) | unused(3)
        
        // ADD R3, R1, R2
        test_instruction(16'b0000_011_001_010_000, "ADD R3, R1, R2");
        
        // SUB R5, R3, R4
        test_instruction(16'b0010_101_011_100_000, "SUB R5, R3, R4");
        
        // XOR R2, R1, R3
        test_instruction(16'b0101_010_001_011_000, "XOR R2, R1, R3");

        // ========== I-TYPE INSTRUCTIONS ==========
        // Format: OPCODE(4) | RD(3) | IMMEDIATE(9) for ADDI
        //         OPCODE(4) | RD(3) | IMMEDIATE(9) for LOADI
        
        // ADDI R2, +85 (0x55)
        // Bits: 0001 | 010 | 001010101 (85 en 9 bits)
        test_instruction({4'b0001, 3'd2, 9'd85}, "ADDI R2, 85");
        
        // ADDI R1, -5 (complément à 2 sur 9 bits = 0x1FB)
        test_instruction({4'b0001, 3'd1, 9'h1FB}, "ADDI R1, -5");
        
        // LOADI R1, 10
        test_instruction({4'b0110, 3'd1, 9'd10}, "LOADI R1, 10");
        
        // LOADI R3, -1 (0x1FF en 9 bits)
        test_instruction({4'b0110, 3'd3, 9'h1FF}, "LOADI R3, -1");

        // ========== MEMORY INSTRUCTIONS ==========
        // Format: OPCODE(4) | RD(3) | RS1(3) | OFFSET(4) | unused(2)
        
        // LOAD R1, [R0+10]
        test_instruction({4'b0111, 3'd1, 3'd0, 4'd10, 2'b00}, "LOAD R1, [R0+10]");
        
        // LOAD R2, [R3+15]
        test_instruction({4'b0111, 3'd2, 3'd3, 4'd15, 2'b00}, "LOAD R2, [R3+15]");
        
        // STORE R1, [R0+10]
        test_instruction({4'b1000, 3'd1, 3'd0, 4'd10, 2'b00}, "STORE R1, [R0+10]");
        
        // STORE R4, [R2+8]
        test_instruction({4'b1000, 3'd4, 3'd2, 4'd8, 2'b00}, "STORE R4, [R2+8]");

        // ========== BRANCH INSTRUCTIONS ==========
        // Format: OPCODE(4) | OFFSET(12) - sign extended
        
        // JUMP +10
        test_instruction({4'b1001, 12'd10}, "JUMP +10");
        
        // JUMP -4 (0xFFC en 12 bits)
        test_instruction({4'b1001, 12'hFFC}, "JUMP -4");
        
        // BRZ +20
        test_instruction({4'b1010, 12'd20}, "BRZ +20");
        
        // BRNZ -8
        test_instruction({4'b1011, 12'hFF8}, "BRNZ -8");

        // ========== COMPARE ==========
        // Format: OPCODE(4) | RS1(3) | RS2(3) | unused(6)
        
        // CMP R1, R2
        test_instruction({4'b1111, 3'd1, 3'd2, 6'b000000}, "CMP R1, R2");
        
        // CMP R5, R3
        test_instruction({4'b1111, 3'd5, 3'd3, 6'b000000}, "CMP R5, R3");

        // ========== SHIFT INSTRUCTIONS ==========
        // Format: OPCODE(4) | RD(3) | RS(3) | IMM(4) | Imm?(1) | unused(1)
        
        // SHL R1, R2 (shift by register)
        test_instruction({4'b1101, 3'd1, 3'd2, 4'b0000, 1'b0, 1'b0}, "SHL R1, R2");
        
        // SHL R3, #5 (shift by immediate)
        test_instruction({4'b1101, 3'd3, 3'b000, 4'd5, 1'b1, 1'b0}, "SHL R3, #5");
        
        // SHR R2, R4
        test_instruction({4'b1110, 3'd2, 3'd4, 4'b0000, 1'b0, 1'b0}, "SHR R2, R4");

        $display("=== Fin des Tests ===");
        $finish;
    end

endmodule