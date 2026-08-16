`timescale 1ns/1ps

module ProgramMemory_SPI_tb;

    // --- 1. SIGNAUX DU TESTBENCH ---
    reg clk;
    reg rst;
    reg [15:0] address;
    wire [15:0] instruction;
    wire ready;
    
    // Signaux physiques simulés (ceux qu'on verrait sur l'oscilloscope)
    wire spi_cs;
    wire spi_sclk;
    wire spi_io0; // Le fil physique bidirectionnel
    wire spi_io1; // Le fil physique bidirectionnel

    // --- NOUVEAUX SIGNAUX INTERNES (Pour connecter au module séparé) ---
    wire spi_io0_o, spi_io0_oe, spi_io0_i;
    wire spi_io1_o, spi_io1_oe, spi_io1_i;

    // Simulation de la Flash (Le "Robot")
    reg flash_active;      
    reg [15:0] current_data; 
    reg f_io0, f_io1;      

    // --- 2. LOGIQUE TRI-STATE (C'est ici que la magie opère) ---
    
    // A. Côté MODULE (CPU) : Si le module veut parler (oe=1), il pilote le fil.
    assign spi_io0 = spi_io0_oe ? spi_io0_o : 1'bz;
    assign spi_io1 = spi_io1_oe ? spi_io1_o : 1'bz;

    // B. Côté FLASH : Si la Flash veut parler (active=1), elle pilote le fil.
    assign spi_io0 = flash_active ? f_io0 : 1'bz;
    assign spi_io1 = flash_active ? f_io1 : 1'bz;

    // C. BOUCLAGE (Loopback) : Le module lit ce qu'il y a sur le fil physique
    assign spi_io0_i = spi_io0;
    assign spi_io1_i = spi_io1;

    // --- 3. INSTANCIATION DU MODULE (Mise à jour avec les nouveaux ports) ---
    ProgramMemory_SPI uut (
        .clk(clk),
        .rst(rst),
        .address(address),
        .instruction(instruction),
        .ready(ready),
        .spi_cs(spi_cs),
        .spi_sclk(spi_sclk),
        
        // Connexion des ports éclates
        .spi_io0_o(spi_io0_o),
        .spi_io0_oe(spi_io0_oe),
        .spi_io0_i(spi_io0_i),
        
        .spi_io1_o(spi_io1_o),
        .spi_io1_oe(spi_io1_oe),
        .spi_io1_i(spi_io1_i)
    );

    // --- 4. HORLOGE ---
    always #25 clk = ~clk;

    // =========================================================
    // 5. LE ROBOT FLASH (Reste identique, il voit les fils physiques)
    // =========================================================
    always @(negedge spi_sclk) begin
        // La Flash ne parle que si CS est bas ET que la FSM écoute (STATE_READ = 4)
        // Note: On utilise uut.state pour tricher et savoir quand la FSM écoute
        if (spi_cs == 0 && uut.state == 3'd4) begin
            flash_active = 1;
            
            // --- LIVE FETCH ---
            case (address)
                16'h1234: current_data = 16'hABCD;
                16'h1235: current_data = 16'h5566;
                16'h9000: current_data = 16'hDEAD;
                default:  current_data = 16'h0000;
            endcase

            // --- ENVOI MSB FIRST ---
            f_io1 = current_data[15 - (2 * uut.bit_cnt)];     // Bit Impair
            f_io0 = current_data[15 - (2 * uut.bit_cnt) - 1]; // Bit Pair
            
        end else begin
            flash_active = 0; 
        end
    end

    // =========================================================
    // 6. SCÉNARIO DE TEST (Identique)
    // =========================================================
    initial begin
        $dumpfile("simulation.vcd");
        $dumpvars(0, ProgramMemory_SPI_tb);
        
        clk = 0; 
        rst = 1; 
        flash_active = 0;
        address = 16'h1234; 

        $display("--- DEMARRAGE SIMULATION ---");
        #100 rst = 0;
        
        // --- TEST 1 : COLD START ---
        $display("[%0t] TEST 1: Demande 0x1234", $time);
        wait(ready == 1);
        
        if (instruction !== 16'hABCD) $display("ERREUR ! Recu: %h", instruction);
        else $display("SUCCES ! Recu: %h", instruction);

        // --- TEST 2 : BURST MODE ---
        #50; 
        $display("[%0t] TEST 2: Demande 0x1235 (Burst)", $time);
        address = 16'h1235;

        wait(ready == 0); 
        wait(ready == 1);
        
        if (instruction !== 16'h5566) $display("ERREUR ! Recu: %h", instruction);
        else $display("SUCCES ! Recu: %h", instruction);

        // --- TEST 3 : JUMP ---
        #100;
        $display("[%0t] TEST 3: Jump vers 0x9000", $time);
        address = 16'h9000;
        
        wait(ready == 0);
        wait(ready == 1);
        
        if (instruction !== 16'hDEAD) $display("ERREUR ! Recu: %h", instruction);
        else $display("SUCCES ! Recu: %h", instruction);

        $display("--- FIN DE SIMULATION ---");
        $finish;
    end

    // Timeout
    initial begin
        #50000;
        $display("!!! TIMEOUT !!!");
        $finish;
    end

endmodule