# backend/mips_consts.py

# MIPS Register Map (Name to Number)
REGISTER_MAP = {
    "$zero": 0, "$0": 0,
    "$at": 1, "$1": 1,
    "$v0": 2, "$2": 2,
    "$v1": 3, "$3": 3,
    "$a0": 4, "$4": 4,
    "$a1": 5, "$5": 5,
    "$a2": 6, "$6": 6,
    "$a3": 7, "$7": 7,
    "$t0": 8, "$8": 8,
    "$t1": 9, "$9": 9,
    "$t2": 10, "$10": 10,
    "$t3": 11, "$11": 11,
    "$t4": 12, "$12": 12,
    "$t5": 13, "$13": 13,
    "$t6": 14, "$14": 14,
    "$t7": 15, "$15": 15,
    "$s0": 16, "$16": 16,
    "$s1": 17, "$17": 17,
    "$s2": 18, "$18": 18,
    "$s3": 19, "$19": 19,
    "$s4": 20, "$20": 20,
    "$s5": 21, "$21": 21,
    "$s6": 22, "$22": 22,
    "$s7": 23, "$23": 23,
    "$t8": 24, "$24": 24,
    "$t9": 25, "$25": 25,
    "$k0": 26, "$26": 26,
    "$k1": 27, "$27": 27,
    "$gp": 28, "$28": 28,
    "$sp": 29, "$29": 29,
    "$fp": 30, "$30": 30,
    "$ra": 31, "$31": 31,
}

# Reverse map for disassembler (Number to Preferred Name)
REGISTER_MAP_REV = {v: k for k, v in REGISTER_MAP.items() if k.startswith('$') and k not in ['$0', '$1', '$2', '$3', # etc - choose one canonical name per number
                                                                                                 '$4', '$5', '$6', '$7',
                                                                                                 '$8', '$9', '$10','$11',
                                                                                                 '$12','$13','$14','$15',
                                                                                                 '$16','$17','$18','$19',
                                                                                                 '$20','$21','$22','$23',
                                                                                                 '$24','$25','$26','$27',
                                                                                                 '$28','$29','$30','$31']}
REGISTER_MAP_REV[0] = '$zero' # Ensure $zero is preferred name for 0

# --- Define Formats ---
# R-Type: Specify order of rd, rs, rt, shamt
R_TYPE_FORMATS = {
    # rd, rs, rt
    "add": ["rd", "rs", "rt"], "addu": ["rd", "rs", "rt"], "sub": ["rd", "rs", "rt"],
    "subu": ["rd", "rs", "rt"], "and": ["rd", "rs", "rt"], "or": ["rd", "rs", "rt"],
    "xor": ["rd", "rs", "rt"], "nor": ["rd", "rs", "rt"], "slt": ["rd", "rs", "rt"],
    "sltu": ["rd", "rs", "rt"],
    # rd, rt, rs
    "sllv": ["rd", "rt", "rs"], "srlv": ["rd", "rt", "rs"], "srav": ["rd", "rt", "rs"],
    # rd, rt, shamt
    "sll": ["rd", "rt", "shamt"], "srl": ["rd", "rt", "shamt"], "sra": ["rd", "rt", "shamt"],
    # rs
    "jr": ["rs"], "mthi": ["rs"], "mtlo": ["rs"],
    # rd
    "mfhi": ["rd"], "mflo": ["rd"],
    # rs, rt
    "mult": ["rs", "rt"], "multu": ["rs", "rt"], "div": ["rs", "rt"], "divu": ["rs", "rt"],
    # jalr: rd, rs (or just rs, rd defaults to $ra=31)
    "jalr": ["rd", "rs"],
    "syscall": [], # R-type format, funct 0x0c
    "break": [],   # R-type format, funct 0x0d
}

# I-Type: Specify order of rt, rs, imm/label
I_TYPE_FORMATS = {
    # rt, rs, imm
    "addi": ["rt", "rs", "imm"], "addiu": ["rt", "rs", "imm"], "slti": ["rt", "rs", "imm"],
    "sltiu": ["rt", "rs", "imm"], "andi": ["rt", "rs", "imm"], "ori": ["rt", "rs", "imm"],
    "xori": ["rt", "rs", "imm"],
    # rt, imm(rs) -> parsed as rt, imm, rs
    "lw": ["rt", "imm", "rs"], "sw": ["rt", "imm", "rs"], "lb": ["rt", "imm", "rs"],
    "lbu": ["rt", "imm", "rs"], "lh": ["rt", "imm", "rs"], "lhu": ["rt", "imm", "rs"],
    "sb": ["rt", "imm", "rs"], "sh": ["rt", "imm", "rs"],
    # rt, imm
    "lui": ["rt", "imm"],
    # rs, rt, label
    "beq": ["rs", "rt", "label"], "bne": ["rs", "rt", "label"],
    # rs, label (rt field used for opcode variant)
    "blez": ["rs", "label"], "bgtz": ["rs", "label"], "bltz": ["rs", "label"], "bgez": ["rs", "label"],
    "bltzal": ["rs", "label"], "bgezal": ["rs", "label"],
    # TODO: Add LWC1, SWC1 etc. if supporting floating point
}

# J-Type: Specify order of target
J_TYPE_FORMATS = {
    "j": ["target"], "jal": ["target"],
}


# --- Update Opcode/Funct Maps ---
R_TYPE_FUNCT = {
    "add": 0x20, "addu": 0x21, "sub": 0x22, "subu": 0x23,
    "and": 0x24, "or": 0x25, "xor": 0x26, "nor": 0x27,
    "slt": 0x2a, "sltu": 0x2b,
    "sll": 0x00, "srl": 0x02, "sra": 0x03,
    "sllv": 0x04, "srlv": 0x06, "srav": 0x07,
    "jr": 0x08, "jalr": 0x09,
    "syscall": 0x0c, "break": 0x0d, # Added syscall, break
    "mfhi": 0x10, "mthi": 0x11, "mflo": 0x12, "mtlo": 0x13,
    "mult": 0x18, "multu": 0x19, "div": 0x1a, "divu": 0x1b,
}

I_TYPE_OPCODE = {
    "addi": 0x8, "addiu": 0x9, "slti": 0xa, "sltiu": 0xb,
    "andi": 0xc, "ori": 0xd, "xori": 0xe, "lui": 0xf,
    "lw": 0x23, "lb": 0x20, "lh": 0x21, "lbu": 0x24, "lhu": 0x25,
    "sw": 0x2b, "sb": 0x28, "sh": 0x29,
    "beq": 0x4, "bne": 0x5,
    "blez": 0x6, # rt = 0
    "bgtz": 0x7, # rt = 0
    # REGIMM (opcode 0x1) instructions have rt field specifying variant
    "bltz": 0x1, # rt = 0
    "bgez": 0x1, # rt = 1
    "bltzal": 0x1, # rt = 16 (0x10)
    "bgezal": 0x1, # rt = 17 (0x11)
}

J_TYPE_OPCODE = {
    "j": 0x2, "jal": 0x3,
}

# --- Reverse Maps for Disassembler ---
OPCODE_MAP_REV = {
    0x0: "R-type",
    0x1: "REGIMM",
    **{v: k for k, v in I_TYPE_OPCODE.items() if k not in ["bltz", "bgez", "bltzal", "bgezal"]}, # Use opcode 1 map
    **{v: k for k, v in J_TYPE_OPCODE.items()},
}
OPCODE_MAP_REV[0x6] = 'blez'
OPCODE_MAP_REV[0x7] = 'bgtz'

FUNCT_MAP_REV = {v: k for k, v in R_TYPE_FUNCT.items()}
# Note: syscall/break already added via R_TYPE_FUNCT

REGIMM_RT_MAP_REV = { # For Opcode 0x1
    0x0: 'bltz',
    0x1: 'bgez',
    0x10: 'bltzal', # Added
    0x11: 'bgezal', # Added
}

# --- Pseudo Instructions and Handlers ---
# Map pseudo instruction name to a handler function in MipsAssembler
# These functions will take (parsed_line, symbol_table, current_address)
# and return a list of *base* instruction dictionaries or None on error.

# Placeholder: Define the actual functions in MipsAssembler class
def _expand_move(parsed_line, symbol_table, current_address):
    # move $dst, $src -> add $dst, $src, $zero
    ops = parsed_line["operands"]
    if len(ops) != 2: return None # Error should be added by caller
    dst, src = ops
    return [{"instruction": "add", "operands": [dst, src, "$zero"]}]

def _expand_clear(parsed_line, symbol_table, current_address):
    # clear $dst -> add $dst, $zero, $zero
    ops = parsed_line["operands"]
    if len(ops) != 1: return None
    dst = ops[0]
    return [{"instruction": "add", "operands": [dst, "$zero", "$zero"]}]

def _expand_nop(parsed_line, symbol_table, current_address):
    # nop -> sll $zero, $zero, 0
    return [{"instruction": "sll", "operands": ["$zero", "$zero", "0"]}]

def _expand_li(parsed_line, symbol_table, current_address):
    # li $dst, immediate
    ops = parsed_line["operands"]
    if len(ops) != 2: return None
    dst, imm_str = ops
    try:
        imm_val = int(imm_str, 0)
    except ValueError: return None # Error should be added by caller

    # Check if fits in 16-bit signed immediate (for addiu)
    if -(1 << 15) <= imm_val <= (1 << 15) - 1:
        # addiu $dst, $zero, imm_val
        return [{"instruction": "addiu", "operands": [dst, "$zero", str(imm_val)]}]
    # Check if fits in 16-bit unsigned immediate (for ori) and upper bits are zero
    elif 0 <= imm_val <= 0xFFFF:
        # ori $dst, $zero, imm_val
         return [{"instruction": "ori", "operands": [dst, "$zero", str(imm_val)]}]
    # Needs lui/ori
    else:
        upper = (imm_val >> 16) & 0xFFFF
        lower = imm_val & 0xFFFF
        expanded = []
        # lui $at, upper
        expanded.append({"instruction": "lui", "operands": ["$at", str(upper)]})
        # If lower is non-zero, add ori
        if lower != 0:
            # ori $dst, $at, lower
            expanded.append({"instruction": "ori", "operands": [dst, "$at", str(lower)]})
        # If lower *was* zero, the lui needs to target $dst directly
        elif expanded: # Check if lui was added
             expanded[0]["operands"][0] = dst # Change target of lui to $dst

        return expanded

def _expand_la(parsed_line, symbol_table, current_address):
    # la $dst, label
    ops = parsed_line["operands"]
    if len(ops) != 2: return None
    dst, label = ops
    if label not in symbol_table: return None # Error should be added by caller
    addr = symbol_table[label]
    upper = (addr >> 16) & 0xFFFF
    lower = addr & 0xFFFF

    expanded = []
    # lui $at, upper
    expanded.append({"instruction": "lui", "operands": ["$at", str(upper)]})
    # If lower is non-zero, add ori
    if lower != 0:
        # ori $dst, $at, lower
        expanded.append({"instruction": "ori", "operands": [dst, "$at", str(lower)]})
    # If lower *was* zero, the lui needs to target $dst directly
    elif expanded: # Check if lui was added
        expanded[0]["operands"][0] = dst # Change target of lui to $dst

    return expanded

# Branch pseudo-instructions
def _expand_branch_pseudo(base_instr, condition_instr, invert_branch, parsed_line, symbol_table, current_address):
    # Generic handler for blt, bgt, ble, bge
    ops = parsed_line["operands"]
    if len(ops) != 3: return None
    rs, rt, label = ops

    expanded = []
    # 1. Perform comparison (slt)
    # slt $at, rs, rt  OR slt $at, rt, rs depending on condition
    expanded.append({"instruction": condition_instr, "operands": ["$at", rs, rt]})
    # 2. Branch based on $at
    # bne $at, $zero, label OR beq $at, $zero, label
    branch_instr = "beq" if invert_branch else "bne"
    expanded.append({"instruction": branch_instr, "operands": ["$at", "$zero", label]})
    return expanded

def _expand_blt(parsed_line, symbol_table, current_address):
    # blt rs, rt, label -> slt $at, rs, rt; bne $at, $zero, label
    return _expand_branch_pseudo("blt", "slt", False, parsed_line, symbol_table, current_address)

def _expand_bgt(parsed_line, symbol_table, current_address):
     # bgt rs, rt, label -> slt $at, rt, rs; bne $at, $zero, label (rs > rt is same as rt < rs)
    ops = parsed_line["operands"]
    if len(ops) != 3: return None
    rs, rt, label = ops
    # Swap rs and rt for the slt instruction
    return _expand_branch_pseudo("bgt", "slt", False, {"operands": [rt, rs, label]}, symbol_table, current_address)


def _expand_ble(parsed_line, symbol_table, current_address):
    # ble rs, rt, label -> slt $at, rt, rs; beq $at, $zero, label (rs <= rt is same as NOT rt < rs)
    ops = parsed_line["operands"]
    if len(ops) != 3: return None
    rs, rt, label = ops
     # Swap rs and rt for the slt instruction, and invert the branch condition
    return _expand_branch_pseudo("ble", "slt", True, {"operands": [rt, rs, label]}, symbol_table, current_address)


def _expand_bge(parsed_line, symbol_table, current_address):
     # bge rs, rt, label -> slt $at, rs, rt; beq $at, $zero, label (rs >= rt is same as NOT rs < rt)
    return _expand_branch_pseudo("bge", "slt", True, parsed_line, symbol_table, current_address)


PSEUDO_INSTRUCTIONS = {
    "move": "_expand_move", "clear": "_expand_clear", "nop": "_expand_nop",
    "li": "_expand_li", "la": "_expand_la",
    "blt": "_expand_blt", "bgt": "_expand_bgt", "ble": "_expand_ble", "bge": "_expand_bge",
    # Add more if desired (e.g., abs, neg, not, beqz, bnez...)
}

# Map handler keys to actual functions (defined above or within MipsAssembler)
# This separation allows functions to be defined elsewhere if needed.
PSEUDO_HANDLERS = {
    "_expand_move": _expand_move, "_expand_clear": _expand_clear, "_expand_nop": _expand_nop,
    "_expand_li": _expand_li, "_expand_la": _expand_la,
    "_expand_blt": _expand_blt, "_expand_bgt": _expand_bgt, "_expand_ble": _expand_ble, "_expand_bge": _expand_bge,
}

# --- Directives Set ---
DIRECTIVES = {
    ".data", ".text", ".globl", ".extern",
    ".word", ".byte", ".half", ".space", ".asciiz", ".ascii", ".align" # Added .ascii
}