// filepath: Testbenches/test_DataMemoryTestBench.v
`timescale 1ns / 1ps

module test_DataMemory_tb;

    // Testbench signals
    reg clk;
    reg we;
    reg [7:0] addr;
    reg [7:0] din;
    wire [7:0] dout;

    // Test tracking variables
    integer test_count = 0;
    integer pass_count = 0;
    integer fail_count = 0;

    // Instantiate the Unit Under Test (UUT)
    DataMemory uut (
    .clk(clk),
    .mem_read(1'b1),      
    .mem_write(we),       
    .addr(addr),
    .wdata(din),          
    .rdata(dout)         
);

    // Clock generation - 100MHz (10ns period)
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // Task to write data to memory
    task write_memory;
        input [7:0] address;
        input [7:0] data;
        begin
            @(posedge clk);
            addr = address;
            din = data;
            we = 1;
            @(posedge clk);
            we = 0;
        end
    endtask

    // Task to read data and check the result, accounting for 1-cycle read latency
    task read_and_check;
        input [7:0] address;
        input [7:0] expected_data;
        // input string test_name; // Removed for Verilog-2001 compatibility
        begin
            // Cycle 1: Present the address to the memory
            addr = address;
            we = 0;
            @(posedge clk);

            // Cycle 2: Data for 'address' is now available on 'dout'
            @(posedge clk);
            #1; // Allow for propagation delay before sampling

            // Perform the check
            test_count = test_count + 1;
            if (dout === expected_data) begin
                pass_count = pass_count + 1;
                $display("PASS: Read Check (Addr: 0x%h, Expected: 0x%h, Got: 0x%h)", address, expected_data, dout);
            end else begin
                fail_count = fail_count + 1;
                $display("FAIL: Read Check (Addr: 0x%h, Expected: 0x%h, Got: 0x%h)", address, expected_data, dout);
            end
        end
    endtask

    // Main test sequence
    integer i, j;
    initial begin
        // Initialize inputs
        we = 0;
        addr = 8'h00;
        din = 8'h00;

        // Wait for global reset/initialization
        #20;

        $display("Starting Corrected DataMemory Testbench...");
        $display("==================================================");

        // Test 1: Read from initialized memory (should be 0x00)
        $display("\nTest 1: Read from initialized memory locations");
        read_and_check(8'h00, 8'h00);
        read_and_check(8'h01, 8'h00);

        // Test 2: Basic write and read back
        $display("\nTest 2: Basic write and read operations");
        write_memory(8'h0A, 8'hAA);
        read_and_check(8'h0A, 8'hAA);

        write_memory(8'h5B, 8'h55);
        read_and_check(8'h5B, 8'h55);

        // Test 3: Verify previous data unchanged
        $display("\nTest 3: Verify data persistence");
        read_and_check(8'h0A, 8'hAA);

        // Test 4: Overwrite existing data
        $display("\nTest 4: Overwrite existing data");
        write_memory(8'h0A, 8'h33);
        read_and_check(8'h0A, 8'h33);

        // Test 5: Test various data patterns
        $display("\nTest 5: Test various data patterns");
        write_memory(8'h10, 8'h00);
        read_and_check(8'h10, 8'h00);
        write_memory(8'h11, 8'hFF);
        read_and_check(8'h11, 8'hFF);

        // Test 6: Test boundary addresses
        $display("\nTest 6: Test boundary addresses");
        write_memory(8'h00, 8'hA0);
        read_and_check(8'h00, 8'hA0);
        write_memory(8'hFF, 8'hB1);
        read_and_check(8'hFF, 8'hB1);

        // Test 7: Test write enable functionality
        $display("\nTest 7: Test write enable control");
        write_memory(8'h20, 8'h77);
        read_and_check(8'h20, 8'h77);
        // Attempt to write with WE disabled
        @(posedge clk);
        addr = 8'h20;
        din = 8'h88;
        we = 0;
        @(posedge clk); // Cycle where write would occur
        read_and_check(8'h20, 8'h77);

        // Test 8: Sequential address test
        $display("\nTest 8: Sequential address pattern");
        for (i = 0; i < 16; i = i + 1) begin
            write_memory(8'h40 + i, 8'h10 + i);
        end
        for (i = 0; i < 16; i = i + 1) begin
            read_and_check(8'h40 + i, 8'h10 + i);
        end

        // Test 9: Address independence test
        $display("\nTest 9: Address independence verification");
        for (i = 0; i < 8; i = i + 1) begin
            write_memory(8'h80 + i, 8'hC0 + i);
        end
        // Read them back in a different order to verify no crosstalk
        read_and_check(8'h87, 8'hC7);
        read_and_check(8'h80, 8'hC0);
        read_and_check(8'h83, 8'hC3);

        // Test 10: Memory stress test
        $display("\nTest 10: Memory stress test");
        for (i = 0; i < 64; i = i + 1) begin
            write_memory(i, i ^ 8'h5A); // Use a different pattern
        end
        j = 0; // Local error counter for this test
        for (i = 0; i < 64; i = i + 1) begin
            // We cannot use read_and_check here as it increments test_count
            // This whole block is one test.
            addr = i;
            we = 0;
            @(posedge clk);
            @(posedge clk);
            #1;
            if (dout !== (i ^ 8'h5A)) begin
                j = j + 1;
            end
        end
        test_count = test_count + 1;
        if (j == 0) begin
            pass_count = pass_count + 1;
            $display("PASS: Memory stress test");
        end else begin
            fail_count = fail_count + 1;
            $display("FAIL: Memory stress test (%0d errors)", j);
        end

        // Final summary
        $display("\n==================================================");
        $display("TEST SUMMARY");
        $display("==================================================");
        if (test_count > 0) begin
            $display("Total Checks: %0d", test_count);
            $display("Passed      : %0d", pass_count);
            $display("Failed      : %0d", fail_count);
            $display("Success Rate: %0d%%", (pass_count * 100) / test_count);
            if (fail_count == 0) begin
                $display("\n🎉 ALL TESTS PASSED! 🎉");
            end else begin
                $display("\n❌ SOME TESTS FAILED!");
            end
        end else begin
            $display("No tests were run.");
        end
        $display("==================================================");

        #50;

        // Custom additional test 
        #5
        we = 1;
        addr = 8'h0A; // Arbitrary address
        din = 8'hFF; // Arbitrary data
        #10
        
        // Check that dout is equal to FF
        if (dout === 8'hFF) begin
            $display("Custom Test: PASS - dout is 0x%02h", dout);
        end else begin
            $display("Custom Test: FAIL - Expected dout to be 0xFF, but got 0x%02h", dout);
        end
        $finish;
    end

    // Monitor for debugging
    initial begin
        $monitor("Time: %0t | clk: %b | we: %b | addr: 0x%02h | din: 0x%02h | dout: 0x%02h",
                 $time, clk, we, addr, din, dout);
    end

    // Generate waveform dump
    initial begin
        $dumpfile("DataMemory_tb_corrected.vcd");
        $dumpvars(0, test_DataMemory_tb);
    end

endmodule