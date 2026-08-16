`timescale 1ns / 1ps

module RegisterFile_tb();

    // Signaux du Testbench
    reg clk;
    reg rst;
    reg write;
    reg [2:0] addr1_wr;
    reg [7:0] data_wr;
    reg [2:0] addr1_r;
    reg [2:0] addr2_r;
    wire [7:0] out1_r;
    wire [7:0] out2_r;

    // Instanciation de l'UUT (Unit Under Test)
    RegisterFile uut (
        .clk(clk),
        .rst(rst),
        .write_en(write),     // ✅ Renommer
        .enable(1'b1),        // ✅ Ajouter (toujours actif)
        .addr_wr(addr1_wr),   // ✅ Renommer
        .data_wr(data_wr),
        .addr1_r(addr1_r),
        .addr2_r(addr2_r),
        .out1_r(out1_r),
        .out2_r(out2_r) 
        );
    // Génération de l'horloge (100MHz -> Période de 10ns)
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // Task pour simplifier les vérifications
    task check_results(input [7:0] expected1, input [7:0] expected2, input [200*8:1] msg);
    begin
        #1; // Petit délai après le front montant pour laisser les signaux se propager
        if (out1_r === expected1 && out2_r === expected2)
            $display("[PASS] %s | R1=%h, R2=%h", msg, out1_r, out2_r);
        else
            $display("[FAIL] %s | Attendu: %h/%h, Obtenu: %h/%h", msg, expected1, expected2, out1_r, out2_r);
    end
    endtask

    // Séquence de test
    initial begin
        // Initialisation des fichiers de dump pour GTKWave
        $dumpfile("register_file_sim.vcd");
        $dumpvars(0, RegisterFile_tb);

        $display("=== Debut des tests : RegisterFile ===");

        // --- Test 1 : Reset Synchrone ---
        rst = 1; write = 0; 
        addr1_r = 3'd1; addr2_r = 3'd2;
        @(posedge clk); // On attend un front montant pour le reset
        check_results(8'h00, 8'h00, "Reset Initial");

        // --- Test 2 : Ecriture dans R1 et lecture ---
        rst = 0;
        addr1_wr = 3'd1; data_wr = 8'hAA; write = 1;
        addr1_r = 3'd1; 
        @(posedge clk);
        check_results(8'hAA, 8'h00, "Ecriture R1 = AAh");

        // --- Test 3 : Double lecture (R1 et R3) ---
        write = 1;
        addr1_wr = 3'd3; data_wr = 8'h55;
        addr1_r = 3'd1; addr2_r = 3'd3;
        @(posedge clk);
        check_results(8'hAA, 8'h55, "Lecture simultanee R1/R3");

        // --- Test 4 : Tentative d'ecriture dans R0 (Hardwired Zero) ---
        // On essaie d'ecrire FFh dans R0, il doit rester a 00h
        addr1_wr = 3'd0; data_wr = 8'hFF; write = 1;
        addr1_r = 3'd0;
        @(posedge clk);
        check_results(8'h00, 8'h55, "Test R0 reste a zero");

        // --- Test 5 : Maintien des données (Write = 0) ---
        write = 0;
        addr1_wr = 3'd4; data_wr = 8'h12; // On pointe vers R4 mais write=0
        addr1_r = 3'd4;
        @(posedge clk);
        check_results(8'h00, 8'h55, "Maintien des données (Write Disable)");

        $display("=== Fin des tests ===");
        $finish;
    end

endmodule