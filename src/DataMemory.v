module DataMemory (
    input wire clk,
    input wire mem_read,   // Signal de lecture du ControlUnit
    input wire mem_write,  // Signal d'écriture du ControlUnit
    input wire [7:0] addr, // Adresse 8 bits venant de l'ALU
    input wire [7:0] wdata,// Donnée venant du RegisterFile
    output reg [7:0] rdata, // Donnée renvoyée au RegisterFile

    // Port de lecture asynchrone supplémentaire, toujours actif (pas
    // conditionné par mem_read), utilisé par tt_um_cpu pour exposer une
    // case mémoire au choix sur uo_out (debug externe, observable aussi
    // bien en RTL qu'en gate-level).
    input  wire [4:0] debug_addr,
    output wire [7:0] debug_rdata
);

    // RAM de 16 octets (16 mots de 8 bits = 128 bits au total)
    reg [7:0] ram [0:31];

    integer i;
    initial begin
        for (i = 0; i < 31; i = i + 1) begin
            ram[i] = 8'h00;
        end
    end

    always @(posedge clk) begin
        if (mem_write) begin
            ram[addr[4:0]] <= wdata;
        end
    end

    // Lecture asynchrone (combinatoire)
    assign rdata = mem_read ? ram[addr[4:0]] : 8'h00;

    // Lecture debug : toujours active, indépendante de mem_read.
    assign debug_rdata = ram[debug_addr];

    wire [2:0] _unused_addr = addr[7:5];

endmodule