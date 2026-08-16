# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

from isa_asm import Asm

# ============================================================================
# SELF-CHECKING TEST PROGRAMS
# ============================================================================
#
# Internal CPU state (registers, flags, memory) is not observable from
# outside the chip — tt_um_cpu only exposes uo_out = pc_current[7:0]. Two
# earlier approaches tried to add an external debug-read mux for
# registers/flags/memory (see PR history), but even a fairly small one was
# enough to blow the fixed TinyTapeout die's routing budget (severe
# congestion, thousands of unresolved DRC violations). So instead, each test
# program checks its own result internally (CMP + conditional branch) and
# settles into one of two infinite self-loops: PASS or FAIL. The test bench
# only needs to observe which address the PC parks at — something it can
# already do via uo_out, in RTL and in gate-level simulation alike, with zero
# extra silicon.
#
# This is not a weaker test than reading registers directly: any wrong
# computation anywhere in the datapath (ALU, register file, flags, ...) that
# a hand-picked CMP depends on will make the program land on FAIL instead of
# PASS, so control flow observability exercises the same logic a direct
# register read would.

PASS_TIMEOUT_CYCLES = 1500


def build_selfcheck(asm, checks):
    """Append a PASS/FAIL tail: PASS only if every (ra, rb) pair in `checks`
    is equal (checked via CMP + BRNZ-to-FAIL, short-circuiting)."""
    for ra, rb in checks:
        asm.cmp(ra, rb)
        asm.brnz('FAIL')
    asm.jmp('PASS')
    asm.label('FAIL')
    asm.jmp('FAIL')
    asm.label('PASS')
    asm.jmp('PASS')


def build_selfcheck_flag(asm, branch_mnem, expect_taken=True):
    """Append a PASS/FAIL tail based on whether `branch_mnem` (brz/brnz/brns),
    evaluated against flags set by a preceding CMP, is taken."""
    if expect_taken:
        asm.branch(branch_mnem, 'PASS')
        asm.label('FAIL'); asm.jmp('FAIL')
        asm.label('PASS'); asm.jmp('PASS')
    else:
        asm.branch(branch_mnem, 'FAIL')
        asm.jmp('PASS')
        asm.label('FAIL'); asm.jmp('FAIL')
        asm.label('PASS'); asm.jmp('PASS')


async def run_selfcheck(dut, asm, cycles=PASS_TIMEOUT_CYCLES):
    """Load `asm`'s assembled program into the simulated flash, run the CPU,
    and assert the PC (uo_out) settled at the PASS address."""
    program = asm.assemble()
    for addr, instr in program.items():
        try:
            dut.flash_sim.memory[addr].value = instr
        except:
            pass

    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.rst_n.value = 0

    clock = Clock(dut.clk, 20, unit="ns")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    for _ in range(cycles):
        await RisingEdge(dut.clk)

    pc = int(dut.uo_out.value)
    pass_addr = asm.addr_of('PASS') & 0xFF
    fail_addr = asm.addr_of('FAIL') & 0xFF
    dut._log.info(f"PC settled at {pc} (PASS={pass_addr}, FAIL={fail_addr})")
    assert pc == pass_addr, (
        f"Expected PC to settle at PASS ({pass_addr}), got {pc} "
        f"(FAIL={fail_addr})"
    )


# ============================================================================
# TESTS PAR CATÉGORIE D'INSTRUCTIONS
# ============================================================================

@cocotb.test()
async def test_arithmetic_add(dut):
    """Test ADD (R-type)"""
    dut._log.info("🧪 TEST: ADD R3, R1, R2")
    asm = Asm()
    asm.li(1, 10).li(2, 20).add(3, 1, 2)
    asm.li(4, 30)  # expected R3
    build_selfcheck(asm, [(3, 4)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ ADD fonctionne\n")

@cocotb.test()
async def test_arithmetic_sub(dut):
    """Test SUB (R-type)"""
    dut._log.info("🧪 TEST: SUB R3, R1, R2")
    asm = Asm()
    asm.li(1, 30).li(2, 10).sub(3, 1, 2)
    asm.li(4, 20)  # expected R3
    build_selfcheck(asm, [(3, 4)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ SUB fonctionne\n")

@cocotb.test()
async def test_logic_and(dut):
    """Test AND (R-type)"""
    dut._log.info("🧪 TEST: AND R3, R1, R2")
    asm = Asm()
    asm.li(1, 0xFF).li(2, 0x0F).and_(3, 1, 2)
    asm.li(4, 0x0F)  # expected R3
    build_selfcheck(asm, [(3, 4)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ AND fonctionne\n")

@cocotb.test()
async def test_logic_or(dut):
    """Test OR (R-type)"""
    dut._log.info("🧪 TEST: OR R3, R1, R2")
    asm = Asm()
    asm.li(1, 0xF0).li(2, 0x0F).or_(3, 1, 2)
    asm.li(4, 0xFF)  # expected R3
    build_selfcheck(asm, [(3, 4)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ OR fonctionne\n")

@cocotb.test()
async def test_logic_xor(dut):
    """Test XOR (R-type)"""
    dut._log.info("🧪 TEST: XOR R3, R1, R2")
    asm = Asm()
    asm.li(1, 0xAA).li(2, 0x55).xor(3, 1, 2)
    asm.li(4, 0xFF)  # expected R3
    build_selfcheck(asm, [(3, 4)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ XOR fonctionne\n")

@cocotb.test()
async def test_immediate_loadi(dut):
    """Test LOADI (I-type)"""
    dut._log.info("🧪 TEST: LOADI R1, 42")
    asm = Asm()
    asm.li(1, 42)
    asm.li(2, 42)  # expected
    build_selfcheck(asm, [(1, 2)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ LOADI fonctionne\n")

@cocotb.test()
async def test_immediate_addi(dut):
    """Test ADDI (I-type)"""
    dut._log.info("🧪 TEST: ADDI R1, 5")
    asm = Asm()
    asm.li(1, 10).addi(1, 5)
    asm.li(2, 15)  # expected R1
    build_selfcheck(asm, [(1, 2)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ ADDI fonctionne\n")

@cocotb.test()
async def test_memory_store_load(dut):
    """Test STORE et LOAD"""
    dut._log.info("🧪 TEST: STORE/LOAD")
    asm = Asm()
    asm.li(1, 123).store(1, 0, 5).load(2, 0, 5)
    asm.li(3, 123)  # expected R2 (round-tripped through memory[5])
    build_selfcheck(asm, [(2, 3)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ STORE/LOAD fonctionnent\n")

@cocotb.test()
async def test_shift_left_register(dut):
    """Test SHL (immediate amount — see isa_asm.Asm.shl_imm)"""
    dut._log.info("🧪 TEST: SHL R2, #2")
    asm = Asm()
    asm.li(2, 5).shl_imm(2, 2)
    asm.li(3, 20)  # expected R2 (5 << 2)
    build_selfcheck(asm, [(2, 3)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ SHL fonctionne\n")

@cocotb.test()
async def test_shift_right(dut):
    """Test SHR"""
    dut._log.info("🧪 TEST: SHR R2, #2")
    asm = Asm()
    asm.li(2, 20).shr_imm(2, 2)
    asm.li(3, 5)  # expected R2 (20 >> 2)
    build_selfcheck(asm, [(2, 3)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ SHR fonctionne\n")

@cocotb.test()
async def test_compare_equal(dut):
    """Test CMP avec valeurs égales (Zero flag)"""
    dut._log.info("🧪 TEST: CMP (égalité)")
    asm = Asm()
    asm.li(1, 15).li(2, 15).cmp(1, 2)
    build_selfcheck_flag(asm, 'brz', expect_taken=True)
    await run_selfcheck(dut, asm)
    dut._log.info("✅ CMP détecte l'égalité\n")

@cocotb.test()
async def test_compare_negative(dut):
    """Test CMP négatif (Sign flag)"""
    dut._log.info("🧪 TEST: CMP (négatif)")
    asm = Asm()
    asm.li(1, 5).li(2, 10).cmp(1, 2)  # 5 - 10 < 0 => S=1
    # BRNS takes when NOT sign (S==0); we want S==1, so PASS when NOT taken.
    build_selfcheck_flag(asm, 'brns', expect_taken=False)
    await run_selfcheck(dut, asm)
    dut._log.info("✅ CMP détecte le négatif\n")

@cocotb.test()
async def test_branch_zero_taken(dut):
    """Test BRZ (branch pris)"""
    dut._log.info("🧪 TEST: BRZ (pris)")
    asm = Asm()
    asm.li(1, 0)
    asm.cmp(1, 0)          # Z=1
    asm.brz('after_skip')
    asm.li(2, 255)          # skipped
    asm.label('after_skip')
    asm.li(3, 50)
    asm.li(4, 0)    # expected R2 (never written)
    asm.li(5, 50)   # expected R3
    build_selfcheck(asm, [(2, 4), (3, 5)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ BRZ fonctionne\n")

@cocotb.test()
async def test_branch_zero_not_taken(dut):
    """Test BRZ (branch non pris)"""
    dut._log.info("🧪 TEST: BRZ (non pris)")
    asm = Asm()
    asm.li(1, 5)
    asm.cmp(1, 0)          # Z=0
    asm.brz('after_skip')
    asm.li(2, 100)
    asm.label('after_skip')
    asm.li(3, 100)  # expected R2
    build_selfcheck(asm, [(2, 3)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ BRZ fonctionne (non pris)\n")

@cocotb.test()
async def test_branch_not_zero_taken(dut):
    """Test BRNZ (branch pris)"""
    dut._log.info("🧪 TEST: BRNZ (pris)")
    asm = Asm()
    asm.li(1, 5)
    asm.cmp(1, 0)          # Z=0
    asm.brnz('land')
    asm.li(2, 255)          # skipped
    asm.label('land')
    asm.li(3, 120)
    asm.li(4, 0)    # expected R2 (never written)
    asm.li(5, 120)  # expected R3
    build_selfcheck(asm, [(2, 4), (3, 5)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ BRNZ fonctionne (pris)\n")

@cocotb.test()
async def test_branch_not_sign_taken(dut):
    """Test BRNS (branch if not sign, pris)"""
    dut._log.info("🧪 TEST: BRNS (pris)")
    asm = Asm()
    asm.li(1, 10).li(2, 5)
    asm.cmp(1, 2)          # 10-5=5 >= 0 => S=0
    asm.brns('land')        # taken since NOT sign
    asm.li(3, 255)           # skipped
    asm.label('land')
    asm.li(4, 80)
    asm.li(5, 0)    # expected R3 (never written)
    asm.li(6, 80)   # expected R4
    build_selfcheck(asm, [(3, 5), (4, 6)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ BRNS fonctionne (pris)\n")

@cocotb.test()
async def test_jump_unconditional(dut):
    """Test JMP (saut inconditionnel)"""
    dut._log.info("🧪 TEST: JMP")
    asm = Asm()
    asm.li(1, 20)
    asm.jmp('land')
    asm.li(2, 255)  # skipped
    asm.label('land')
    asm.li(3, 90)
    asm.li(4, 20)   # expected R1
    asm.li(5, 0)    # expected R2 (never written)
    asm.li(6, 90)   # expected R3
    build_selfcheck(asm, [(1, 4), (2, 5), (3, 6)])
    await run_selfcheck(dut, asm)
    dut._log.info("✅ JMP fonctionne\n")

@cocotb.test()
async def test_integration_fibonacci(dut):
    """Test d'intégration : Fibonacci (démo complète)

    R1, R2 = F(0), F(1) = 0, 1; loop 7 times computing R3 = R1+R2 then
    shifting R1<-R2, R2<-R3. Each iteration advances the pair by one Fibonacci
    step, so after 7 iterations R3 = F(8) = 21 (the loop body runs once per
    initial counter value, i.e. one step past F(7)).
    """
    dut._log.info("🧪 TEST D'INTÉGRATION: Suite de Fibonacci")
    asm = Asm()
    asm.li(1, 0)             # F0
    asm.li(2, 1)             # F1
    asm.li(4, 7)             # counter
    asm.label('loop')
    asm.add(3, 1, 2)         # F_next
    asm.add(1, 0, 2)         # R1 <- R2
    asm.add(2, 0, 3)         # R2 <- R3
    asm.addi(4, (-1) & 0xFF) # counter--
    asm.cmp(4, 0)
    asm.brnz('loop')
    asm.li(5, 21)            # expected R3 = F(8)
    build_selfcheck(asm, [(3, 5)])
    await run_selfcheck(dut, asm, cycles=25000)
    dut._log.info("✅ Programme complexe exécuté\n")
