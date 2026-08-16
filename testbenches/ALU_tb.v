`include "defines.vh"

module ALU_tb();

    reg [3:0] operation;
    reg [7:0] operand1, operand2;
    wire [7:0] result;
    wire zero_flag, overflow_flag, carry_flag, negative_flag;

    ALU uut (
        .operation(operation),
        .operand1(operand1),
        .operand2(operand2),
        .result(result),
        .zero_flag(zero_flag),
        .overflow_flag(overflow_flag),
        .carry_flag(carry_flag),
        .negative_flag(negative_flag)  // ✅ Ajouter
    );
    
    // Task mise à jour pour inclure le Carry
    task test_alu(
        input [3:0] op,
        input [7:0] op1,
        input [7:0] op2,
        input [7:0] exp_res,
        input exp_z,
        input exp_c, // Expected Carry
        input exp_o, // Expected Overflow
        input [200*8:1] name
    );
    begin
        operation = op;
        operand1 = op1;
        operand2 = op2;
        #5; 
        
        if (result === exp_res && zero_flag === exp_z && 
            carry_flag === exp_c && overflow_flag === exp_o) begin
            $display("[PASS] %s | R:%d Z:%b C:%b O:%b", name, result, zero_flag, carry_flag, overflow_flag);
        end else begin
            $display("[FAIL] %s | Got: R:%d Z:%b C:%b O:%b | Exp: R:%d Z:%b C:%b O:%b", 
                     name, result, zero_flag, carry_flag, overflow_flag, 
                     exp_res, exp_z, exp_c, exp_o);
        end
        #5;
    end
    endtask
    
    initial begin
        $dumpfile("simulation.vcd");
        $dumpvars(0, ALU_tb);

        $display("=== Début des Tests ALU ===");
        
        // --- Tests Addition ---
        // Classique
        test_alu(`OP_ADD, 8'd10, 8'd5, 8'd15, 0, 0, 0, "ADD Simple");
        // Carry seul (Non-signé : 255 + 1 = 256, donc 0 et Carry out)
        test_alu(`OP_ADD, 8'd255, 8'd1, 8'd0, 1, 1, 0, "ADD Carry Out");
        // Overflow seul (Signé : 127 + 1 = -128, donc Overflow car le signe change)
        test_alu(`OP_ADD, 8'd127, 8'd1, 8'd128, 0, 0, 1, "ADD Signed Overflow");

        // --- Tests Soustraction ---
        // Classique
        test_alu(`OP_SUB, 8'd10, 8'd5, 8'd5, 0, 1, 0, "SUB Simple");
        // Carry en SUB (0 - 1 = 255, pas de Carry en complément à deux)
        test_alu(`OP_SUB, 8'd0, 8'd1, 8'd255, 0, 0, 0, "SUB Underflow");

        // --- Tests Logiques ---
        test_alu(`OP_AND, 8'hAA, 8'hF0, 8'hA0, 0, 0, 0, "AND Hex");
        test_alu(`OP_XOR, 8'hFF, 8'hFF, 8'h00, 1, 0, 0, "XOR Zero");

        $display("=== Fin des Tests ===");
        $finish;
    end

endmodule