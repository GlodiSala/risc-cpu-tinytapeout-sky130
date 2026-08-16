`include "defines.vh"

module BranchUnit_tb();

    reg [15:0] pc_current;
    reg [3:0]  branch_type;
    reg [15:0] branch_offset;
    reg [3:0]  stored_flags;      // ✅ 4 bits
    wire       branch_taken;      // ✅ Sortie du module
    wire [15:0] branch_target;    // ✅ Sortie du module
    
    // Instanciation
    BranchUnit uut (
        .branch_type(branch_type),
        .branch_offset(branch_offset),
        .stored_flags(stored_flags),
        .pc_current(pc_current),
        .branch_taken(branch_taken),
        .branch_target(branch_target)
    );
    
    task test_branch(
        input [15:0] pc_in,
        input [3:0]  br_type,
        input [15:0] br_offset,
        input [3:0]  flags,
        input [15:0] exp_target,
        input        exp_taken,
        input [200*8:1] name
    );
    begin
        pc_current    = pc_in;
        branch_type   = br_type;
        branch_offset = br_offset;
        stored_flags  = flags;
        #5; 
        
        if (branch_target === exp_target && branch_taken === exp_taken)
            $display("[PASS] %s | PC: %h -> %h (Taken=%b)", name, pc_in, branch_target, branch_taken);
        else
            $display("[FAIL] %s | Expected: %h (Taken=%b), Got: %h (Taken=%b)", 
                     name, exp_target, exp_taken, branch_target, branch_taken);
    end
    endtask
    
    initial begin
        $dumpfile("simulation.vcd");
        $dumpvars(0, BranchUnit_tb);
        $display("=== Debut Tests BranchUnit ===");
        
        // Test 1: JMP inconditionnel (PC+1+offset)
        test_branch(16'h0010, `OP_JMP, 16'h0005, 4'b0000, 16'h0016, 1'b1, "JMP Positive");
        
        // Test 2: BRZ - Pris (Zero=1 → stored_flags[0]=1)
        test_branch(16'h0100, `OP_BRZ, 16'h000A, 4'b0001, 16'h010B, 1'b1, "BRZ Taken");
        
        // Test 3: BRZ - Non Pris (Zero=0)
        test_branch(16'h0200, `OP_BRZ, 16'h0008, 4'b0000, 16'h0209, 1'b0, "BRZ Not Taken");
        
        // Test 4: BRNZ - Pris (Zero=0 → NOT stored_flags[0])
        test_branch(16'h0300, `OP_BRNZ, 16'h0010, 4'b0000, 16'h0311, 1'b1, "BRNZ Taken");
        
        // Test 5: BRNS - Pris (Negative=0 → NOT stored_flags[1])
        test_branch(16'h0400, `OP_BRNS, 16'h0020, 4'b0000, 16'h0421, 1'b1, "BRNS Taken");
        
        // Test 6: Offset négatif (Sign-extend)
        test_branch(16'h1000, `OP_JMP, 16'hFFFE, 4'b0000, 16'h0FFF, 1'b1, "JMP Negative");

        $display("=== Tests Termines ===");
        $finish;
    end
endmodule