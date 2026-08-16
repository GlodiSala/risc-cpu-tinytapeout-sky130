module RegisterFile (
    input  wire       clk,
    input  wire       rst,        
    input  wire       write_en,   
    input  wire       enable,     

    input  wire [2:0] addr_wr,    
    input  wire [7:0] data_wr,   
    
    input  wire [2:0] addr1_r,
    input  wire [2:0] addr2_r,

    output wire [7:0] out1_r,
    output wire [7:0] out2_r,

    // Port de lecture asynchrone supplémentaire, utilisé par tt_um_cpu pour
    // exposer un registre au choix sur uo_out (debug externe, observable
    // aussi bien en RTL qu'en gate-level puisque c'est une vraie broche).
    input  wire [2:0] addr3_r,
    output wire [7:0] out3_r
);

    reg [7:0] register_tab [1:7];

    // Lecture asynchrone : R0 renvoie toujours 0
    assign out1_r = (addr1_r == 3'b000) ? 8'b0 : register_tab[addr1_r];
    assign out2_r = (addr2_r == 3'b000) ? 8'b0 : register_tab[addr2_r];
    assign out3_r = (addr3_r == 3'b000) ? 8'b0 : register_tab[addr3_r];

    // Écriture synchrone avec Reset
    integer i;
    always @(posedge clk) begin
        if (rst) begin
            for (i = 1; i < 8; i = i + 1) begin
                register_tab[i] <= 8'b0;
            end
        end else begin
            if (write_en && enable && (addr_wr != 3'b000)) begin
                register_tab[addr_wr] <= data_wr;
            end
        end
    end

endmodule