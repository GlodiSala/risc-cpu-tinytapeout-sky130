module DataMemory (
    input wire clk,
    input wire mem_read,   // Signal de lecture du ControlUnit
    input wire mem_write,  // Signal d'écriture du ControlUnit
    input wire [7:0] addr, // Adresse 8 bits venant de l'ALU
    input wire [7:0] wdata,// Donnée venant du RegisterFile
    output reg [7:0] rdata // Donnée renvoyée au RegisterFile
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

    wire [2:0] _unused_addr = addr[7:5];

endmodule
