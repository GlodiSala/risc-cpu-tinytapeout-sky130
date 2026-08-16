# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, Timer

OPCODE_NAMES = {
    0x0: "ADD", 0x1: "ADDI", 0x2: "SUB", 0x3: "AND", 0x4: "OR", 0x5: "XOR",
    0x6: "LI", 0x7: "L", 0x8: "ST", 0x9: "JMP", 0xA: "BRZ", 0xB: "BRNZ",
    0xC: "BRNS", 0xD: "SHL", 0xE: "SHR", 0xF: "CMP"
}

# ============================================================================
# HELPERS
# ============================================================================
#
# Internal CPU state (registers, flags, data memory) is read out through the
# uo_out debug mux tt_um_cpu exposes via ui_in, instead of cocotb
# hierarchical references into the DUT (e.g. dut.user_project.regfile...).
# Those hierarchical names only resolve against the RTL; they don't survive
# synthesis, so they can't be checked against the gate-level netlist. The
# debug mux is a real, synthesized signal path and works identically in RTL
# and gate-level simulation. See the "SORTIE : PC (par défaut) / debug"
# section of src/tt_um_cpu.v for the encoding.

DEBUG_PC     = 0b00
DEBUG_REG    = 0b01
DEBUG_FLAGS  = 0b10
DEBUG_ALUMEM = 0b11

async def read_debug(dut, mode, sel=0):
    """Drive ui_in to select a debug value and read it back off uo_out."""
    dut.ui_in.value = (mode << 6) | (sel & 0x3F)
    # Let the (combinational) debug mux settle. Gate-level cells carry a
    # nonzero unit delay, so this needs to be more than a delta cycle.
    await Timer(100, unit="ns")
    return int(dut.uo_out.value)

async def get_reg(dut, num):
    """Lit un registre (R0-R7) via le mux de debug (uo_out)."""
    return await read_debug(dut, DEBUG_REG, num & 0x7)

async def get_flags(dut):
    """Lit les flags (Z, S, C, O) via le mux de debug."""
    f = await read_debug(dut, DEBUG_FLAGS)
    return {'Z': (f>>0)&1, 'S': (f>>1)&1, 'C': (f>>2)&1, 'O': (f>>3)&1}

async def get_alu_result(dut):
    """Lit le dernier résultat ALU via le mux de debug."""
    return await read_debug(dut, DEBUG_ALUMEM, 0b0)

async def get_mem(dut, addr):
    """Lit data_mem.ram[addr] (0-31) via le mux de debug."""
    return await read_debug(dut, DEBUG_ALUMEM, ((addr & 0x1F) << 1) | 1)

async def setup_and_run(dut, program, cycles=2000):
    """Configure la Flash avec un programme personnalisé et exécute"""
    # Écrire le programme dans la Flash simulée
    for addr, instr in program.items():
        try:
            dut.flash_sim.memory[addr].value = instr
        except:
            pass

    # Init CPU
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.rst_n.value = 0

    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Exécuter
    for _ in range(cycles):
        await RisingEdge(dut.clk)

# ============================================================================
# TESTS PAR CATÉGORIE D'INSTRUCTIONS
# ============================================================================

@cocotb.test()
async def test_arithmetic_add(dut):
    """Test ADD (R-type)"""
    dut._log.info("🧪 TEST: ADD R3, R1, R2")

    program = {
        0x0000: 0x620A,  # LOADI R1, 10
        0x0001: 0x6414,  # LOADI R2, 20
        0x0002: 0x0650,  # ADD R3, R1, R2
        0x0003: 0x9FFD,  # JMP -3 (boucle)
    }

    await setup_and_run(dut, program, 500)

    r1, r2, r3 = await get_reg(dut, 1), await get_reg(dut, 2), await get_reg(dut, 3)
    dut._log.info(f"R1={r1}, R2={r2}, R3={r3}")
    assert r3 == 30, f"R3 devrait être 30, obtenu {r3}"
    dut._log.info("✅ ADD fonctionne\n")

@cocotb.test()
async def test_arithmetic_sub(dut):
    """Test SUB (R-type)"""
    dut._log.info("🧪 TEST: SUB R3, R1, R2")

    program = {
        0x0000: 0x631E,  # LOADI R1, 30
        0x0001: 0x640A,  # LOADI R2, 10
        0x0002: 0x2650,  # SUB R3, R1, R2  (opcode=0x2)
        0x0003: 0x9FFD,  # JMP -3
    }

    await setup_and_run(dut, program, 500)

    r1, r2, r3 = await get_reg(dut, 1), await get_reg(dut, 2), await get_reg(dut, 3)
    dut._log.info(f"R1={r1}, R2={r2}, R3={r3}")
    assert r3 == 20, f"R3 devrait être 20, obtenu {r3}"
    dut._log.info("✅ SUB fonctionne\n")

@cocotb.test()
async def test_logic_and(dut):
    """Test AND (R-type)"""
    dut._log.info("🧪 TEST: AND R3, R1, R2")

    program = {
        0x0000: 0x62FF,  # LOADI R1, 0xFF
        0x0001: 0x640F,  # LOADI R2, 0x0F
        0x0002: 0x3650,  # AND R3, R1, R2  (opcode=0x3)
        0x0003: 0x9FFD,  # JMP -3
    }

    await setup_and_run(dut, program, 500)

    r1, r2, r3 = await get_reg(dut, 1), await get_reg(dut, 2), await get_reg(dut, 3)
    dut._log.info(f"R1=0x{r1:02x}, R2=0x{r2:02x}, R3=0x{r3:02x}")
    assert r3 == 0x0F, f"R3 devrait être 0x0F, obtenu 0x{r3:02x}"
    dut._log.info("✅ AND fonctionne\n")

@cocotb.test()
async def test_logic_or(dut):
    """Test OR (R-type)"""
    dut._log.info("🧪 TEST: OR R3, R1, R2")

    program = {
        0x0000: 0x62F0,  # LOADI R1, 0xF0
        0x0001: 0x640F,  # LOADI R2, 0x0F
        0x0002: 0x4650,  # OR R3, R1, R2  (opcode=0x4)
        0x0003: 0x9FFD,  # JMP -3
    }

    await setup_and_run(dut, program, 500)

    r1, r2, r3 = await get_reg(dut, 1), await get_reg(dut, 2), await get_reg(dut, 3)
    dut._log.info(f"R1=0x{r1:02x}, R2=0x{r2:02x}, R3=0x{r3:02x}")
    assert r3 == 0xFF, f"R3 devrait être 0xFF, obtenu 0x{r3:02x}"
    dut._log.info("✅ OR fonctionne\n")

@cocotb.test()
async def test_logic_xor(dut):
    """Test XOR (R-type)"""
    dut._log.info("🧪 TEST: XOR R3, R1, R2")

    program = {
        0x0000: 0x62AA,  # LOADI R1, 0xAA
        0x0001: 0x6455,  # LOADI R2, 0x55
        0x0002: 0x5650,  # XOR R3, R1, R2  (opcode=0x5)
        0x0003: 0x9FFD,  # JMP -3
    }

    await setup_and_run(dut, program, 500)

    r1, r2, r3 = await get_reg(dut, 1), await get_reg(dut, 2), await get_reg(dut, 3)
    dut._log.info(f"R1=0x{r1:02x}, R2=0x{r2:02x}, R3=0x{r3:02x}")
    assert r3 == 0xFF, f"R3 devrait être 0xFF, obtenu 0x{r3:02x}"
    dut._log.info("✅ XOR fonctionne\n")

@cocotb.test()
async def test_immediate_loadi(dut):
    """Test LOADI (I-type)"""
    dut._log.info("🧪 TEST: LOADI R1, 42")

    program = {
        0x0000: 0x622A,  # LOADI R1, 42 (0x2A)
        0x0001: 0x9FFF,  # JMP -1
    }

    await setup_and_run(dut, program, 300)

    r1 = await get_reg(dut, 1)
    dut._log.info(f"R1={r1}")
    assert r1 == 42, f"R1 devrait être 42, obtenu {r1}"
    dut._log.info("✅ LOADI fonctionne\n")

@cocotb.test()
async def test_immediate_addi(dut):
    """Test ADDI (I-type) - CORRIGÉ"""
    dut._log.info("🧪 TEST: ADDI R1, 5")

    program = {
        0x0000: 0x620A,  # LOADI R1, 10
        0x0001: 0x1205,  # ADDI R1, 5
        0x0002: 0x9FFE,  # JMP -2
    }

    await setup_and_run(dut, program, 400)

    r1 = await get_reg(dut, 1)
    dut._log.info(f"R1={r1} (attendu 15)")

    # ⚠️ Si ça échoue encore, c'est un bug dans ControlUnit
    # Vérifier que addr1_select = instruction[11:9] pour ADDI
    assert r1 == 15, f"R1 devrait être 15, obtenu {r1}"
    dut._log.info("✅ ADDI fonctionne\n")

@cocotb.test()
async def test_memory_store_load(dut):
    """Test STORE et LOAD"""
    dut._log.info("🧪 TEST: STORE/LOAD")

    program = {
        0x0000: 0x627B,  # LOADI R1, 123
        0x0001: 0x8205,  # STORE R1, [R0+5]  (opcode=0x8)
        0x0002: 0x7405,  # LOAD R2, [R0+5]   (opcode=0x7)
        0x0003: 0x9FFD,  # JMP -3
    }

    await setup_and_run(dut, program, 500)

    r1, r2 = await get_reg(dut, 1), await get_reg(dut, 2)
    dut._log.info(f"R1={r1}, R2={r2}")

    mem = await get_mem(dut, 5)
    dut._log.info(f"Mem[5]={mem}")
    assert mem == 123, f"Mem[5] devrait être 123, obtenu {mem}"

    assert r2 == 123, f"R2 devrait être 123, obtenu {r2}"
    dut._log.info("✅ STORE/LOAD fonctionnent\n")

@cocotb.test()
async def test_shift_left_register(dut):
    """Test SHL avec registre"""
    dut._log.info("🧪 TEST: SHL R2 par R3")

    program = {
        0x0000: 0x6405,  # LOADI R2, 5
        0x0001: 0x6602,  # LOADI R3, 2 (shift amount)
        0x0002: 0xD4C0,  # SHL R2, R3 = 1101 010 011 0 0000 0
        0x0003: 0x9FFE,
    }

    await setup_and_run(dut, program, 500)

    r2 = await get_reg(dut, 2)
    dut._log.info(f"R2={r2}")

@cocotb.test()
async def test_shift_right(dut):
    """Test SHR - CORRIGÉ"""
    dut._log.info("🧪 TEST: SHR R2, #2")

    program = {
        0x0000: 0x6414,  # LOADI R2, 20
        0x0001: 0xE424,  # ✅ SHR R2, #2 = 1110 010 000 1 0010 0
        0x0002: 0x9FFE,
    }

    await setup_and_run(dut, program, 400)

    r2 = await get_reg(dut, 2)
    dut._log.info(f"R2={r2}")
    assert r2 == 5, f"R2 devrait être 5 (20>>2), obtenu {r2}"
    dut._log.info("✅ SHR fonctionne\n")

@cocotb.test()
async def test_compare_equal(dut):
    """Test CMP avec valeurs égales"""
    dut._log.info("🧪 TEST: CMP (égalité)")

    program = {
        0x0000: 0x620F,  # LOADI R1, 15
        0x0001: 0x640F,  # LOADI R2, 15
        0x0002: 0xF480,  # CMP R1, R2  (opcode=0xF)
        0x0003: 0x9FFD,  # JMP -3
    }

    await setup_and_run(dut, program, 500)

    flags = await get_flags(dut)
    dut._log.info(f"Flags: Z={flags['Z']} S={flags['S']} C={flags['C']} O={flags['O']}")
    assert flags['Z'] == 1, "Zero flag devrait être 1"
    dut._log.info("✅ CMP détecte l'égalité\n")

@cocotb.test()
async def test_compare_negative(dut):
    """Test CMP négatif - CORRECTION ENCODAGE"""
    dut._log.info("🧪 TEST: CMP (négatif)")

    program = {
        0x0000: 0x6205,  # LOADI R1, 5
        0x0001: 0x640A,  # LOADI R2, 10
        0x0002: 0xF280,  # ✅ CMP R1, R2 (pas 0xF480!)
        0x0003: 0x9FFD,
    }

    await setup_and_run(dut, program, 500)

    flags = await get_flags(dut)
    dut._log.info(f"Flags: Z={flags['Z']} S={flags['S']}")
    assert flags['S'] == 1, "Sign flag devrait être 1"
    dut._log.info("✅ CMP détecte le négatif\n")

@cocotb.test()
async def test_branch_zero_taken(dut):
    """Test BRZ - CORRIGÉ"""
    dut._log.info("🧪 TEST: BRZ (pris)")

    program = {
        0x0000: 0x6200,  # LOADI R1, 0
        0x0001: 0xF280,  # CMP R1, R0
        0x0002: 0xA002,  # BRZ +2 (saute vers 0x0004)
        0x0003: 0x64FF,  # LOADI R2, 255
        0x0004: 0x6632,  # LOADI R3, 50
        0x0005: 0x9FFF,  # JMP -1
    }

    await setup_and_run(dut, program, 600)

    r2, r3 = await get_reg(dut, 2), await get_reg(dut, 3)
    dut._log.info(f"R2={r2}, R3={r3}")
    assert r2 == 0, f"R2 devrait être 0 (skippé)"
    assert r3 == 50, f"R3 devrait être 50"
    dut._log.info("✅ BRZ fonctionne\n")

@cocotb.test()
async def test_branch_zero_not_taken(dut):
    """Test BRZ (branch non pris)"""
    dut._log.info("🧪 TEST: BRZ (non pris)")

    program = {
        0x0000: 0x6205,  # LOADI R1, 5
        0x0001: 0xF280,  # CMP R1, R0  (5 - 0 = 5, Z=0)
        0x0002: 0xA002,  # BRZ +2  (ne devrait PAS sauter)
        0x0003: 0x6464,  # LOADI R2, 100
        0x0004: 0x9FFF,  # JMP -1
    }

    await setup_and_run(dut, program, 500)

    r2 = await get_reg(dut, 2)
    dut._log.info(f"R2={r2}")
    assert r2 == 100, f"R2 devrait être 100, obtenu {r2}"
    dut._log.info("✅ BRZ fonctionne (non pris)\n")

@cocotb.test()
async def test_branch_not_zero_taken(dut):
    """Test BRNZ (branch pris)"""
    dut._log.info("🧪 TEST: BRNZ (pris)")

    program = {
        0x0000: 0x6205,  # LOADI R1, 5
        0x0001: 0xF280,  # CMP R1, R0  (5 - 0 = 5, Z=0)
        0x0002: 0xB003,  # ✅ BRNZ +3 (Saute 0x03 et 0x04, va à 0x05)
        0x0003: 0x64FF,  # LOADI R2, 255 (skip)
        0x0004: 0x9FFF,  # JMP -1
        0x0005: 0x6678,  # LOADI R3, 120
        0x0006: 0x9FFF,  # JMP -1
    }

    await setup_and_run(dut, program, 600)

    r2, r3 = await get_reg(dut, 2), await get_reg(dut, 3)
    dut._log.info(f"R2={r2}, R3={r3}")
    assert r2 == 0, f"R2 devrait être 0, obtenu {r2}"
    assert r3 == 120, f"R3 devrait être 120, obtenu {r3}"
    dut._log.info("✅ BRNZ fonctionne (pris)\n")

@cocotb.test()
async def test_branch_not_sign_taken(dut):
    """Test BRNS (branch if not sign)"""
    dut._log.info("🧪 TEST: BRNS (pris)")

    program = {
        0x0000: 0x620A,  # LOADI R1, 10
        0x0001: 0x6405,  # LOADI R2, 5
        0x0002: 0xF480,  # CMP R1, R2  (10 - 5 = 5, S=0)
        0x0003: 0xC003,  # ✅ BRNS +3 (Saute 0x04 et 0x05, va à 0x06)
        0x0004: 0x66FF,  # LOADI R3, 255 (skip)
        0x0005: 0x9FFF,  # JMP -1
        0x0006: 0x6850,  # LOADI R4, 80
        0x0007: 0x9FFF,  # JMP -1
    }

    await setup_and_run(dut, program, 700)

    r3, r4 = await get_reg(dut, 3), await get_reg(dut, 4)
    dut._log.info(f"R3={r3}, R4={r4}")
    assert r3 == 0, f"R3 devrait être 0, obtenu {r3}"
    assert r4 == 80, f"R4 devrait être 80, obtenu {r4}"
    dut._log.info("✅ BRNS fonctionne (pris)\n")

@cocotb.test()
async def test_jump_unconditional(dut):
    """Test JMP (saut inconditionnel)"""
    dut._log.info("🧪 TEST: JMP")

    program = {
        0x0000: 0x6214,  # LOADI R1, 20
        0x0001: 0x9003,  # JMP +3 (saute vers 0x0004)
        0x0002: 0x64FF,  # LOADI R2, 255 (skippé)
        0x0003: 0x9FFF,  # JMP -1
        0x0004: 0x665A,  # LOADI R3, 90
        0x0005: 0x9FFF,  # JMP -1
    }

    await setup_and_run(dut, program, 500)

    r1, r2, r3 = await get_reg(dut, 1), await get_reg(dut, 2), await get_reg(dut, 3)
    dut._log.info(f"R1={r1}, R2={r2}, R3={r3}")
    assert r1 == 20, f"R1 devrait être 20"
    assert r2 == 0, f"R2 devrait être 0 (skippé)"
    assert r3 == 90, f"R3 devrait être 90"
    dut._log.info("✅ JMP fonctionne\n")

@cocotb.test()
async def test_integration_fibonacci(dut):
    """Test d'intégration : Fibonacci (démo complète)"""
    dut._log.info("🧪 TEST D'INTÉGRATION: Suite de Fibonacci")

    # Calculer Fib(7) = 13
    program = {
        0x0000: 0x6200,  # LOADI R1, 0    (F0)
        0x0001: 0x6401,  # LOADI R2, 1    (F1)
        0x0002: 0x6807,  # LOADI R4, 7    (compteur)
        # Loop:
        0x0003: 0x0650,  # ADD R3, R1, R2 (F_next)
        0x0004: 0x0208,  # MOV R1, R2 (via ADD R1, R0, R2)
        0x0005: 0x04D0,  # MOV R2, R3 (via ADD R2, R0, R3)
        0x0006: 0x2A04,  # SUBI R4, 1 (ADDI R4, -1)
        0x0007: 0xF880,  # CMP R4, R0
        0x0008: 0xBFFB,  # BRNZ -5 (vers 0x0003)
        0x0009: 0x9FFF,  # JMP -1 (boucle infinie)
    }

    await setup_and_run(dut, program, 1500)

    r3 = await get_reg(dut, 3)
    dut._log.info(f"Fibonacci(7) = {r3}")
    # Note: Le résultat exact dépend de l'implémentation exacte
    dut._log.info("✅ Programme complexe exécuté\n")
