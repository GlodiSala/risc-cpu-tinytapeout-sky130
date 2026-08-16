"""
Assembly code translator for the custom instruction set.

Bit layouts are derived directly from src/ControlUnit.v / src/BranchUnit.v
(the RTL decode logic) and match test/isa_asm.py, the assembler used by the
cocotb test suite — cross-checked against known-good hex from those tests
(e.g. "add R3 R1 R2" -> 0x0650, "cmp R3 R4" -> 0xF700).
"""

import os

op_codes = {
    'add': '0000',
    'addi': '0001',
    'sub': '0010',
    'and': '0011',
    'or': '0100',
    'xor': '0101',
    'loadi': '0110',
    'load': '0111',
    'store': '1000',
    'jmp': '1001',
    'brz': '1010',
    'brnz': '1011',
    'brnn': '1100',
    'shl': '1101',
    'shr': '1110',
    'cmp': '1111'
}


op_operands = {
    'add': ['R', 'R', 'R'],      # RD, RS1, RS2
    'addi': ['R', 'I8'],          # RD, Immediate
    'sub': ['R', 'R', 'R'],      # RD, RS1, RS2
    'and': ['R', 'R', 'R'],      # RD, RS1, RS2
    'or': ['R', 'R', 'R'],       # RD, RS1, RS2
    'xor': ['R', 'R', 'R'],      # RD, RS1, RS2
    'loadi': ['R', 'I8'],         # RD, Immediate
    'load': ['R', 'R', 'I4'],     # RD, RS (Base), Offset
    'store': ['R', 'R', 'I4'],    # RS (Source), RS (Base), Offset
    'jmp': ['I12'],                # Offset
    'brz': ['I12'],                # Offset
    'brnz': ['I12'],               # Offset
    'brnn': ['I12'],               # Offset
    'shl': ['R', 'I4'],            # RD (shifted in place), shift amount
    'shr': ['R', 'I4'],            # RD (shifted in place), shift amount
    'cmp': ['R', 'R']            # RS1, RS2
}

# Bit layout for each mnemonic, matching src/ControlUnit.v exactly. Each
# entry is a list of (operand_index_or_None, bit_width) tuples from MSB to
# LSB, filling the 12 bits after the 4-bit opcode. `None` means a fixed
# padding field (always 0) rather than an operand — several instructions
# have don't-care gaps between fields (e.g. 1 bit between ADDI/LOADI's
# register and immediate), which a naive "concatenate operands in order"
# scheme can't represent.
_LAYOUT = {
    'add':   [(0, 3), (1, 3), (2, 3), (None, 3)],
    'sub':   [(0, 3), (1, 3), (2, 3), (None, 3)],
    'and':   [(0, 3), (1, 3), (2, 3), (None, 3)],
    'or':    [(0, 3), (1, 3), (2, 3), (None, 3)],
    'xor':   [(0, 3), (1, 3), (2, 3), (None, 3)],
    'addi':  [(0, 3), (None, 1), (1, 8)],
    'loadi': [(0, 3), (None, 1), (1, 8)],
    'load':  [(0, 3), (1, 3), (None, 2), (2, 4)],
    'store': [(0, 3), (1, 3), (None, 2), (2, 4)],
    'jmp':   [(0, 12)],
    'brz':   [(0, 12)],
    'brnz':  [(0, 12)],
    'brnn':  [(0, 12)],
    'shl':   [(0, 3), (None, 3), (True, 1), (1, 4), (None, 1)],  # True = immediate-mode flag (always 1: register-mode shift amounts alias this same bit, so only immediate mode is supported)
    'shr':   [(0, 3), (None, 3), (True, 1), (1, 4), (None, 1)],
    'cmp':   [(0, 3), (1, 3), (None, 6)],
}

# TODO: implement pseudo-instructions to add: nop, shl_r, shl_i, shr_r, shr_i

def remove_comments_and_commas(code):
    """
    Removes comments and unnecessary whitespace from the source code.
    
    :param code: The source code as a string.
    :return: Cleaned source code without comments and excessive whitespace.
    """
    lines = code.splitlines()
    cleaned_lines = []
    
    for line in lines:
        # Remove comments
        line = line.split('#')[0].strip() # Remove Python-style comments
        line = line.replace('//', '').strip()  # Remove C-style comments  
        line = line.replace(',', '')  # Remove commas
        if line:  # Only add non-empty lines
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)

def check_formatting(source_code):
    """
    Checks the formatting of the source code.
    :param source_code: The source code as a string.
    :return: True if the formatting is correct, False otherwise.
    """
    to_return = True
    lines = source_code.splitlines()
    for line in lines:
        line = line.strip()
        op_code = line.split()[0]
        if not check_opcode(op_code, line):
            to_return = False
            continue
        if not check_operands(op_code, line):
            to_return = False
    return to_return

def check_opcode(op_code, line):
    if op_code not in op_codes:
        print(f"Error: Unknown operation '{op_code}' in line: {line}")
        return False
    return True

def check_operands(op_code, line):
    operands = line.split()[1:]
    expected = op_operands[op_code]
    if len(operands) != len(expected):
        print(f"Error: Incorrect number of operands for '{op_code}' in line: {line}")
        return False
    for i, operand in enumerate(operands):
        if not check_operand_type(expected[i], operand, i, op_code, line):
            return False
    return True

def check_operand_type(expected_type, operand, idx, op_code, line):
    if expected_type == 'R':
        return check_register_operand(operand, idx, op_code, line)
    else:
        exepcted_immediate_length = expected_type[1:]
        exepcted_immediate_length = int(exepcted_immediate_length)
        return check_immediate_operand(operand, idx, op_code, line, exepcted_immediate_length)
    return True

def check_register_operand(operand, idx, op_code, line):
    if not operand.startswith('R'):
        print(f"Error: Expected register for operand {idx+1} in '{op_code}' but got '{operand}' in line: {line}")
        return False
    # Only 8 registers (R0-R7) exist in hardware — addr fields are 3 bits
    # wide (src/register_file.v, src/ControlUnit.v).
    if not operand[1:].isdigit() or int(operand[1:]) < 0 or int(operand[1:]) > 7:
        print(f"Error: Invalid register number '{operand}' (must be R0-R7) in line: {line}")
        return False
    return True

def check_immediate_operand(operand, idx, op_code, line, exepcted_length):
    # exepcted_length is the number of bits expected for the immediate value
    if not (operand.isdigit() or operand.startswith('0b') or operand.startswith('0x')):
        print(f"Error: Expected immediate value for operand {idx+1} in '{op_code}' but got '{operand}' in line: {line}")
        return False
    if operand.startswith('0b'):
        return check_binary_immediate(operand, line, exepcted_length)
    elif operand.startswith('0x'):
        return check_hex_immediate(operand, line, exepcted_length)
    else:
        return check_decimal_immediate(operand, line, exepcted_length)

def check_val_fits_in_bits(value, expected_length):
    # The value must be an integer
    if not isinstance(value, int):
        print(f"Error: Value '{value}' is not an integer.")
        return False
    # Check if the value fits in the expected number of bits
    val_bin = bin(value)[2:]  # Get binary representation without '0b'
    return len(val_bin) <= expected_length

def check_binary_immediate(operand, line, expected_length):
    if not all(c in '01' for c in operand[2:]) or not check_val_fits_in_bits(int(operand[2:], 2), expected_length):
        print(f"Error: Invalid binary immediate '{operand}' in line: {line}")
        return False
    return True

def check_hex_immediate(operand, line, expected_length):
    if not all(c in '0123456789ABCDEF' for c in operand[2:].upper()):
        print(f"Error: Invalid hex immediate '{operand}' in line: {line}")
        return False
    # Check if number as binary fits in expected length
    if not check_val_fits_in_bits(int(operand[2:], 16), expected_length):
        print(f"Error: Hex immediate '{operand}' exceeds expected length in line: {line}")
        return False
    return True

def check_decimal_immediate(operand, line, exepcted_length):
    if not operand.isdigit() or int(operand) < 0:
        print(f"Error: Invalid decimal immediate '{operand}' in line: {line}")
        return False
    # Check if number as binary fits in expected length
    if not check_val_fits_in_bits(int(operand), exepcted_length):  # Assuming 4 bits per digit
        print(f"Error: Decimal immediate '{operand}' exceeds expected length in line: {line}")
        return False
    return True

def parse_operand_value(operand, operand_type):
    """Parses a register ('R3' -> 3) or immediate (decimal/0b.../0x...) operand."""
    if operand_type == 'R':
        return int(operand[1:])
    if operand.startswith('0b'):
        return int(operand[2:], 2)
    if operand.startswith('0x'):
        return int(operand[2:], 16)
    return int(operand)

def translate_line(line):
    op_code = line.split()[0]
    operands = line.split()[1:]
    operand_types = op_operands[op_code]

    values = [parse_operand_value(op, operand_types[i]) for i, op in enumerate(operands)]

    output = op_codes[op_code]  # 4-bit opcode
    for field_ref, width in _LAYOUT[op_code]:
        if field_ref is None:
            value = 0
        elif field_ref is True:
            value = 1
        else:
            value = values[field_ref] & ((1 << width) - 1)
        output += format(value, f'0{width}b')

    assert len(output) == 16, f"Internal error: {op_code} encoded to {len(output)} bits, expected 16"
    return output

def translate_code(source_code):
    source_code = remove_comments_and_commas(source_code)
    if not check_formatting(source_code):
        return "Error: Formatting issues found."

    assembly_code = []
    lines = source_code.splitlines()
    output_lines = []
    for line in lines:
        translated = translate_line(line)
        if translated:
            output_lines.append(translated)

    return '\n'.join(output_lines)

def translate_file(source_file, output_file):
    """
    Translates a source file into assembly code and writes it to an output file.
    
    :param source_file: Path to the source file containing the custom instruction set code.
    :param output_file: Path to the output file where the assembly code will be written.
    """
    with open(source_file, 'r') as infile:
        source_code = infile.read()
    
    assembly_code = translate_code(source_code)
    
    with open(output_file, 'w') as outfile:
        outfile.write(assembly_code)

def main():
    """ Translates all the files in /Source, and outputs them to /Assembly as .txt files. """
    source_dir = 'Compiler/Source'
    output_dir = 'Compiler/Output'

    print("Starting translation of source files...\n")
    
    if not os.path.exists(output_dir):
        print("Output directory does not exist...\n")
        return
    
    if not os.path.isdir(source_dir):
        print("Source directory does not exist...\n")
        return
    
    for filename in os.listdir(source_dir):
        if filename.endswith('.txt'):
            print(f"Translating {filename}...")
            source_file = os.path.join(source_dir, filename)
            output_file = os.path.join(output_dir, filename).replace('.txt', '.asm')
            translate_file(source_file, output_file)
    
    print("Translation complete.")

if __name__ == "__main__":
    main()
