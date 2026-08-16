module ProgramCounter_tb();

    reg clk;
    reg rst;
    reg mem_ready;
    reg branch_en;
    reg [15:0] branch_addr;
    wire [15:0] pc_current;
    
    // Instanciation
    ProgramCounter uut (
        .clk(clk),
        .rst(rst),
        .mem_ready(mem_ready),
        .branch_en(branch_en),
        .branch_addr(branch_addr),
        .pc_current(pc_current)
    );
    
    // Horloge
    initial begin
        clk = 0;
        forever #5 clk = ~clk;  
    end
    
    task check_pc(input [15:0] expected, input [200*8:1] test_name);
    begin
        @(posedge clk);
        #1;
        if (pc_current === expected)
            $display("[PASS] %s: PC = %h", test_name, pc_current);
        else
            $display("[FAIL] %s: PC = %h (Attendu %h)", test_name, pc_current, expected);
    end
    endtask
    
    initial begin
        $dumpfile("simulation.vcd");
        $dumpvars(0, ProgramCounter_tb);
        
        $display("=== Test ProgramCounter ===");
        
        // Test 1: Reset
        rst = 1; mem_ready = 1; branch_en = 0; branch_addr = 16'h0000;
        check_pc(16'h0000, "Reset Initial");
        
        // Test 2: Increment normal
        rst = 0; mem_ready = 1; branch_en = 0;
        check_pc(16'h0001, "Increment +1");
        check_pc(16'h0002, "Increment +2");
        
        // Test 3: Branch (Jump)
        branch_en = 1; branch_addr = 16'hA000;
        check_pc(16'hA000, "Jump A000");
        
        // Test 4: Stall (mem_ready=0)
        mem_ready = 0; branch_en = 0;
        check_pc(16'hA000, "Stall (PC freeze)");
        check_pc(16'hA000, "Stall continue");
        
        // Test 5: Resume
        mem_ready = 1;
        check_pc(16'hA001, "Resume +1");
        
        $display("=== Tests termines ===");
        $finish;
    end

endmodule