# Modules source (RTL lives in src/)
SRC = src
MODULES = $(SRC)/ALU.v $(SRC)/BranchUnit.v $(SRC)/ControlUnit.v $(SRC)/DataMemory.v \
          $(SRC)/FlagRegister.v $(SRC)/ProgramCounter.v $(SRC)/ProgramMemory_SPI.v \
          $(SRC)/register_file.v $(SRC)/defines.vh

# Flags Icarus Verilog
IVFLAGS = -g2005-sv -I. -I$(SRC)

# Testbenches individuels
ALU_TB = ALU_tb.v
BRANCH_TB = BranchUnit_tb.v
CONTROL_TB = ControlUnit_tb.v
DATA_TB = DataMemory_tb.v
FLAG_TB = FlagRegister_tb.v
PC_TB = ProgramCounter_tb.v
SPI_TB = ProgramMemory_SPI_tb.v
REG_TB = register_file_tb.v
CPU_TB = tt_um_CPU_tb.v $(SRC)/tt_um_cpu.v

# Règles
all: help

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets disponibles:"
	@echo "  alu       - Tester l'ALU"
	@echo "  branch    - Tester BranchUnit"
	@echo "  control   - Tester ControlUnit"
	@echo "  data      - Tester DataMemory"
	@echo "  flag      - Tester FlagRegister"
	@echo "  pc        - Tester ProgramCounter"
	@echo "  spi       - Tester ProgramMemory_SPI"
	@echo "  reg       - Tester RegisterFile"
	@echo "  cpu       - Tester CPU complet"
	@echo "  clean     - Nettoyer les fichiers de simulation"

alu: $(MODULES) $(ALU_TB)
	iverilog $(IVFLAGS) -o sim.vvp $(MODULES) $(ALU_TB)
	vvp sim.vvp
	@echo "Simulation terminée. Lancez 'gtkwave simulation.vcd' pour visualiser."

branch: $(MODULES) $(BRANCH_TB)
	iverilog $(IVFLAGS) -o sim.vvp $(MODULES) $(BRANCH_TB)
	vvp sim.vvp

control: $(MODULES) $(CONTROL_TB)
	iverilog $(IVFLAGS) -o sim.vvp $(MODULES) $(CONTROL_TB)
	vvp sim.vvp

data: $(MODULES) $(DATA_TB)
	iverilog $(IVFLAGS) -o sim.vvp $(MODULES) $(DATA_TB)
	vvp sim.vvp

flag: $(MODULES) $(FLAG_TB)
	iverilog $(IVFLAGS) -o sim.vvp $(MODULES) $(FLAG_TB)
	vvp sim.vvp

pc: $(MODULES) $(PC_TB)
	iverilog $(IVFLAGS) -o sim.vvp $(MODULES) $(PC_TB)
	vvp sim.vvp

spi: $(MODULES) $(SPI_TB)
	iverilog $(IVFLAGS) -o sim.vvp $(MODULES) $(SPI_TB)
	vvp sim.vvp

reg: $(MODULES) $(REG_TB)
	iverilog $(IVFLAGS) -o sim.vvp $(MODULES) $(REG_TB)
	vvp sim.vvp

cpu: $(MODULES) $(CPU_TB)
	iverilog $(IVFLAGS) -o sim.vvp $(MODULES) $(CPU_TB)
	vvp sim.vvp
	@echo "Simulation terminée. Lancez 'gtkwave cpu_simulation.vcd' pour visualiser."

clean:
	rm -f sim.vvp *.vcd

.PHONY: all help clean alu branch control data flag pc spi reg cpu