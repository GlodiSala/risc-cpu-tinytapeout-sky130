# SPDX-License-Identifier: Apache-2.0
"""
Tiny two-pass assembler for the CPU's ISA, with label support.

Encodings below are derived directly from src/ControlUnit.v / src/BranchUnit.v
(the actual RTL decode logic), not from Compiler/AssemblyTranslator.py, whose
field widths (e.g. 12-bit branch offsets) don't match what the RTL actually
decodes (10-bit branch_offset). Each encoding formula here has been
cross-checked against known-good hex from the original hand-written test
programs (e.g. 0x0650 for "ADD R3, R1, R2", 0xF700 for "CMP R3, R4").
"""

OP = {
    'add': 0x0, 'addi': 0x1, 'sub': 0x2, 'and': 0x3, 'or': 0x4, 'xor': 0x5,
    'li': 0x6, 'l': 0x7, 'st': 0x8, 'jmp': 0x9, 'brz': 0xA, 'brnz': 0xB,
    'brns': 0xC, 'shl': 0xD, 'shr': 0xE, 'cmp': 0xF,
}

_R_TYPE = {'add', 'sub', 'and', 'or', 'xor'}
_BRANCH = {'jmp', 'brz', 'brnz', 'brns'}


class Asm:
    """Builds a {address: 16-bit instruction} program from mnemonic calls.

    All builder methods return self, so calls can be chained. Branch/jump
    targets may be an absolute address (int) or a label name (str) defined
    via .label(); forward references are fine since encoding happens in
    .assemble(), after all labels are known.
    """

    def __init__(self):
        self._ops = []      # list of (mnemonic, args)
        self._labels = {}   # name -> address

    def label(self, name):
        self._labels[name] = len(self._ops)
        return self

    def addr_of(self, label):
        return self._labels[label]

    # R-type: Rd = Rs1 <op> Rs2
    def add(self, rd, rs1, rs2):  self._ops.append(('add', (rd, rs1, rs2))); return self
    def sub(self, rd, rs1, rs2):  self._ops.append(('sub', (rd, rs1, rs2))); return self
    def and_(self, rd, rs1, rs2): self._ops.append(('and', (rd, rs1, rs2))); return self
    def or_(self, rd, rs1, rs2):  self._ops.append(('or', (rd, rs1, rs2))); return self
    def xor(self, rd, rs1, rs2):  self._ops.append(('xor', (rd, rs1, rs2))); return self

    # Immediate
    def li(self, rd, imm):    self._ops.append(('li', (rd, imm))); return self
    def addi(self, rd, imm):  self._ops.append(('addi', (rd, imm))); return self

    # Compare (sets flags only)
    def cmp(self, rs1, rs2): self._ops.append(('cmp', (rs1, rs2))); return self

    # Branches (target: label name or absolute address)
    def jmp(self, target):  self._ops.append(('jmp', (target,))); return self
    def brz(self, target):  self._ops.append(('brz', (target,))); return self
    def brnz(self, target): self._ops.append(('brnz', (target,))); return self
    def brns(self, target): self._ops.append(('brns', (target,))); return self

    def branch(self, mnem, target):
        """Emit brz/brnz/brns/jmp by name (useful for generic helpers)."""
        getattr(self, mnem)(target)
        return self

    # Shifts (immediate amount only — register-mode shift amount aliases
    # with the immediate-mode flag bit in this ISA's encoding, so it's not
    # used here)
    def shl_imm(self, rd, shamt): self._ops.append(('shl', (rd, shamt))); return self
    def shr_imm(self, rd, shamt): self._ops.append(('shr', (rd, shamt))); return self

    # Memory
    def load(self, rd, rbase, off):    self._ops.append(('l', (rd, rbase, off))); return self
    def store(self, rsrc, rbase, off): self._ops.append(('st', (rsrc, rbase, off))); return self

    def assemble(self):
        return {addr: self._encode(addr, mnem, args)
                for addr, (mnem, args) in enumerate(self._ops)}

    def _encode(self, addr, mnem, args):
        op = OP[mnem]
        if mnem in _R_TYPE:
            rd, rs1, rs2 = args
            return (op << 12) | (rd << 9) | (rs1 << 6) | (rs2 << 3)
        if mnem in ('li', 'addi'):
            rd, imm = args
            return (op << 12) | (rd << 9) | (imm & 0xFF)
        if mnem == 'cmp':
            rs1, rs2 = args
            return (op << 12) | (rs1 << 9) | (rs2 << 6)
        if mnem in _BRANCH:
            target = args[0]
            if isinstance(target, str):
                target = self._labels[target]
            offset = (target - addr) & 0xFFF
            return (op << 12) | offset
        if mnem in ('shl', 'shr'):
            rd, shamt = args
            return (op << 12) | (rd << 9) | (1 << 5) | ((shamt & 0xF) << 1)
        if mnem == 'l':
            rd, rbase, off = args
            return (op << 12) | (rd << 9) | (rbase << 6) | (off & 0xF)
        if mnem == 'st':
            rsrc, rbase, off = args
            return (op << 12) | (rsrc << 9) | (rbase << 6) | (off & 0xF)
        raise ValueError(f"unknown mnemonic {mnem!r}")
