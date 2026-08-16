"""
Assembly code translator for the custom instruction set.

⚠️ KNOWN BUG — do not trust this tool's output yet: it encodes register
operands as 4 bits (`format(reg_num, '04b')`), but the actual hardware
(src/ControlUnit.v) only has 8 registers addressed with 3-bit fields. For
any R-type instruction this produces a completely different bit pattern
than what the CPU decodes — e.g. this translator encodes
"add R3 R1 R2" as 0x0312, but the real, RTL-verified encoding (used
throughout the test suite) is 0x0650. Several immediate-field layouts
(e.g. LOADI's 1-bit gap between the register and immediate fields) are
also not modeled.

For a verified reference implementation of this ISA's encoding, see
test/isa_asm.py, whose formulas are derived directly from
ControlUnit.v/BranchUnit.v and cross-checked against known-good hex from
the test programs (all passing, including on the gate-level netlist).
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
    'load': ['R', 'R', 'I4'],     # RD, RS1 (Base), Offset
    'store': ['R', 'R', 'I4'],    # RS2 (Source), RS1 (Base), Offset
    'jmp': ['I12'],                # Offset
    'brz': ['I12'],                # Offset
    'brnz': ['I12'],               # Offset
    'brnn': ['I12'],               # Offset
    'shl': ['R', 'R', 'I1', 'I3'], # RD, RS1, imm?, imm
    'shr': ['R', 'R', 'I1', 'I3'], # RD, RS1, imm?, imm
    'cmp': ['R', 'R']            # RS1, RS2
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
    if not operand[1:].isdigit() or int(operand[1:]) < 0 or int(operand[1:]) > 15:
        print(f"Error: Invalid register number '{operand}' in line: {line}")
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

def translate_line(line):
    op_code = line.split()[0]
    operands = line.split()[1:]
    output = op_codes[op_code] # Start with the opcode

    operands_types = op_operands[op_code]

    for i, operand in enumerate(operands):
        if operands_types[i] == 'R':
            # Register operand
            reg_num = int(operand[1:])
            output += format(reg_num, '04b')
        else:
            target_length = int(operands_types[i][1:])
            imm_as_int = 0
            if operand.startswith('0b'):
                imm_as_int = int(operand[2:], 2)
            elif operand.startswith('0x'):
                imm_as_int = int(operand[2:], 16)
            else:
                imm_as_int = int(operand)
            output += format(imm_as_int, f'0{target_length}b')


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
