module FlagRegister_tb();

    reg clk;
    reg rst;
    reg write;
    reg [3:0] flags_alu;
    wire [3:0] stored_flags;
    
    // Instanciation de l'UUT (Unit Under Test) [cite: 1]
    FlagRegister uut (
        .clk(clk),
        .rst(rst),
        .write(write),
        .flags_alu(flags_alu),
        .stored_flags(stored_flags)
    );
    
    // Generation de l'horloge (Periode de 10 unites de temps)
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end
    
    // Task pour automatiser les tests
    task test_flags(
        input [2:0] input_flags,
        input       write_enable,
        input [2:0] expected_flags,
        input [200*8:1] test_name
    );
    begin
        flags_alu = input_flags;
        write = write_enable;
        @(posedge clk); // On attend le front montant pour l'ecriture synchrone 
        #1;             // Petit delai pour laisser la propagation se faire
        
        if (stored_flags === expected_flags)
            $display("[PASS] %s | Attendu: %b, Obtenu: %b", test_name, expected_flags, stored_flags);
        else
            $display("[FAIL] %s | Attendu: %b, Obtenu: %b", test_name, expected_flags, stored_flags);
        
        write = 0;      // On desactive l'ecriture par defaut
    end
    endtask
    
    initial begin
        $dumpfile("simulation.vcd");
        $dumpvars(0, FlagRegister_tb);
        $display("=== Debut Test FlagRegister ===");
        
        // --- 1. Test du Reset Synchrone ---
        rst = 1; write = 1; flags_alu = 3'b111;
        @(posedge clk); // Le reset etant synchrone, il faut un coup d'horloge 
        #1;
        if (stored_flags === 3'b000)
            $display("[PASS] Reset - Flags mis a 000");
        else
            $display("[FAIL] Reset - Obtenu: %b", stored_flags);
        
        rst = 0; // Fin du reset
        
        // --- 2. Test Ecriture des drapeaux ---
        test_flags(3'b001, 1'b1, 3'b001, "Ecriture Zero Flag");
        test_flags(3'b010, 1'b1, 3'b010, "Ecriture Overflow Flag");
        test_flags(3'b100, 1'b1, 3'b100, "Ecriture Carry Flag");
        
        // --- 3. Test Maintien (Write Disable) ---
        // On essaie d'ecrire 111 mais write=0, donc doit rester a 100
        test_flags(3'b111, 1'b0, 3'b100, "Maintien de la valeur");

        // --- 4. Test Overwrite ---
        test_flags(3'b011, 1'b1, 3'b011, "Ecriture Multiple");

        $display("=== Fin des Tests ===");
        $finish;
    end

endmodule