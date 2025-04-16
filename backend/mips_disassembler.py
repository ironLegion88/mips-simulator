# backend/mips_disassembler.py
from backend.mips_consts import (
    REGISTER_MAP_REV, OPCODE_MAP_REV, FUNCT_MAP_REV, REGIMM_RT_MAP_REV, J_TYPE_OPCODE
)
import logging

logger = logging.getLogger(__name__)

class MipsDisassembler:
    def __init__(self):
        self.errors = [] # Store errors encountered during disassembly

    def _get_reg_name(self, reg_num):
        """Gets the canonical register name ($zero, $t0, etc.) from number."""
        return REGISTER_MAP_REV.get(reg_num, f"$?{reg_num}") # Fallback for unknown

    def _sign_extend_imm(self, imm, bits=16):
        """ Sign extend a 'bits'-bit immediate value represented as an integer. """
        sign_bit = 1 << (bits - 1)
        if (imm & sign_bit) != 0: # Check if sign bit is set
            # Perform sign extension using two's complement arithmetic
            return imm - (1 << bits)
        return imm

    def disassemble_instruction(self, machine_code_int, pc=0x00400000):
        """ Disassembles a single 32-bit machine code integer. Uses PC for branch/jump label calculation. """
        self.errors = [] # Clear errors for this specific instruction

        if not isinstance(machine_code_int, int):
             self.errors.append({"message": "Invalid machine code format, expected integer"})
             return "Error: Invalid input type"

        opcode = (machine_code_int >> 26) & 0x3F
        rs = (machine_code_int >> 21) & 0x1F
        rt = (machine_code_int >> 16) & 0x1F
        rd = (machine_code_int >> 11) & 0x1F
        shamt = (machine_code_int >> 6) & 0x1F
        funct = machine_code_int & 0x3F
        imm = machine_code_int & 0xFFFF
        addr = machine_code_int & 0x03FFFFFF # 26-bit address field for J-type

        # Pre-calculate common values
        rs_name = self._get_reg_name(rs)
        rt_name = self._get_reg_name(rt)
        rd_name = self._get_reg_name(rd)
        signed_imm = self._sign_extend_imm(imm)
        unsigned_imm = imm

        # --- R-type (opcode 0) ---
        if opcode == 0:
            mnemonic = FUNCT_MAP_REV.get(funct)
            # Handle special cases like NOP first
            if machine_code_int == 0: return "nop" # sll $zero, $zero, 0
            if mnemonic == 'syscall': return "syscall"
            if mnemonic == 'break': return "break"

            if mnemonic:
                # Determine format based on known R-type mnemonics
                if mnemonic in ["add", "addu", "sub", "subu", "and", "or", "xor", "nor", "slt", "sltu"]:
                    # Format: instr $rd, $rs, $rt
                    return f"{mnemonic} {rd_name}, {rs_name}, {rt_name}"
                elif mnemonic in ["sllv", "srlv", "srav"]:
                    # Format: instr $rd, $rt, $rs
                     return f"{mnemonic} {rd_name}, {rt_name}, {rs_name}"
                elif mnemonic in ["sll", "srl", "sra"]:
                    # Format: instr $rd, $rt, shamt
                     return f"{mnemonic} {rd_name}, {rt_name}, {shamt}"
                elif mnemonic == "jr":
                    # Format: jr $rs
                    return f"jr {rs_name}"
                elif mnemonic == "jalr":
                    # Format: jalr $rd, $rs (default rd=$ra=31)
                    if rd == 31: return f"jalr {rs_name}"
                    else: return f"jalr {rd_name}, {rs_name}"
                elif mnemonic in ["mthi", "mtlo"]:
                    # Format: instr $rs
                    return f"{mnemonic} {rs_name}"
                elif mnemonic in ["mfhi", "mflo"]:
                     # Format: instr $rd
                    return f"{mnemonic} {rd_name}"
                elif mnemonic in ["mult", "multu", "div", "divu"]:
                    # Format: instr $rs, $rt
                    return f"{mnemonic} {rs_name}, {rt_name}"
                else:
                    # Fallback for recognized funct but unknown format
                    logger.warning(f"Disassembly format unknown for R-type mnemonic '{mnemonic}' (funct=0x{funct:02x})")
                    return f"{mnemonic} RType(rd={rd},rs={rs},rt={rt},shamt={shamt})"
            else:
                # Unrecognized funct code
                return f"Unknown R-type (funct=0x{funct:02x})"

        # --- J-type (opcode 2 or 3) ---
        elif opcode in J_TYPE_OPCODE.values(): # j, jal
            mnemonic = OPCODE_MAP_REV.get(opcode, f"Opcode {opcode}")
            # Calculate pseudo-absolute target address by combining with PC's upper bits
            target_addr = (addr << 2) | (pc & 0xF0000000)
            return f"{mnemonic} 0x{target_addr:08x}"

        # --- REGIMM (opcode 1) ---
        elif opcode == 0x1:
            mnemonic = REGIMM_RT_MAP_REV.get(rt) # Use rt field to determine instruction
            if mnemonic:
                 # Calculate branch target address: PC + 4 + (offset * 4)
                 branch_target = pc + 4 + (signed_imm * 4)
                 # For AL variants, link register ($ra) is implicit
                 return f"{mnemonic} {rs_name}, 0x{branch_target:08x}" # Show target addr
                 # Or optionally show offset: return f"{mnemonic} {rs_name}, {signed_imm * 4}"
            else:
                 return f"Unknown REGIMM instruction (opcode=0x1, rt={rt})"

        # --- I-type (other opcodes) ---
        else:
            mnemonic = OPCODE_MAP_REV.get(opcode)
            if mnemonic:
                 # Determine format based on mnemonic
                 if mnemonic in ["addi", "slti"]: # Signed immediate arithmetic/compare
                     return f"{mnemonic} {rt_name}, {rs_name}, {signed_imm}"
                 elif mnemonic in ["addiu"]: # Often disassembled signed, though operation isn't trapping
                      return f"{mnemonic} {rt_name}, {rs_name}, {signed_imm}"
                 elif mnemonic in ["sltiu"]: # Unsigned immediate compare
                      return f"{mnemonic} {rt_name}, {rs_name}, {unsigned_imm}"
                 elif mnemonic in ["andi", "ori", "xori"]: # Logical operations with zero-extended immediate
                      # Conventionally show immediate in hex for logical ops
                      return f"{mnemonic} {rt_name}, {rs_name}, 0x{unsigned_imm:x}"
                 elif mnemonic == "lui":
                      # Format: lui $rt, imm
                      return f"lui {rt_name}, 0x{unsigned_imm:x}"
                 elif mnemonic in ["lw", "sw", "lb", "lbu", "lh", "lhu", "sb", "sh"]: # Memory access
                      # Format: instr $rt, offset($rs)
                      return f"{mnemonic} {rt_name}, {signed_imm}({rs_name})"
                 elif mnemonic in ["beq", "bne"]: # Branch conditional
                      # Format: instr $rs, $rt, label (target_address)
                      branch_target = pc + 4 + (signed_imm * 4)
                      return f"{mnemonic} {rs_name}, {rt_name}, 0x{branch_target:08x}"
                 elif mnemonic in ["blez", "bgtz"]: # Branch on zero/greater than zero
                      # Format: instr $rs, label (target_address) (rt field is 0)
                      branch_target = pc + 4 + (signed_imm * 4)
                      return f"{mnemonic} {rs_name}, 0x{branch_target:08x}"
                 # Add lwl, lwr, swl, swr if implementing
                 else:
                    # Fallback for recognized opcode but unknown format
                    logger.warning(f"Disassembly format unknown for I-type mnemonic '{mnemonic}' (opcode=0x{opcode:02x})")
                    return f"{mnemonic} IType(rs={rs},rt={rt},imm=0x{imm:x})"
            else:
                # Unrecognized opcode
                return f"Unknown Instruction (opcode=0x{opcode:02x})"

    def disassemble(self, machine_code_hex_lines):
        """ Main method to disassemble list of hex strings. Returns dict with 'assembly_code' and 'errors'. """
        assembly_lines = []
        self.errors = [] # Clear errors from previous runs
        # Assume base address for PC calculations if needed for context
        current_pc = 0x00400000 # Base text address for context

        for i, hex_line in enumerate(machine_code_hex_lines):
            line_num = i + 1
            try:
                # Sanitize input hex string
                hex_line = hex_line.strip().lower()
                if not hex_line: continue # Skip empty lines
                if hex_line.startswith("0x"): hex_line = hex_line[2:]

                # Validate hex format and length
                if len(hex_line) > 8: raise ValueError(f"Invalid hex length: '{hex_line}' (max 8 digits)")
                if not all(c in '0123456789abcdef' for c in hex_line): raise ValueError(f"Invalid hex character found: '{hex_line}'")

                # Pad if necessary (e.g., user enters 'c' instead of '0000000c')
                machine_code_int = int(hex_line.zfill(8), 16) # Pad with leading zeros to 8 digits

                # Disassemble the single instruction, passing current PC
                asm_line = self.disassemble_instruction(machine_code_int, current_pc)

                if self.errors: # Check if disassemble_instruction added errors for this line
                    # Use the specific error message if available
                    assembly_lines.append(f"Error line {line_num}: {self.errors[-1]['message']}")
                else:
                    assembly_lines.append(asm_line)

                current_pc += 4 # Increment PC for the next instruction's context

            except ValueError as e:
                self.errors.append({"line": line_num, "message": f"Invalid hex format/value: {e}"})
                assembly_lines.append(f"Error line {line_num}: Invalid hex input")
            except Exception as e:
                 logger.error(f"Unexpected error during disassembly on line {line_num}: {e}", exc_info=True)
                 self.errors.append({"line": line_num, "message": f"Internal error during disassembly: {e}"})
                 assembly_lines.append(f"Error line {line_num}: Internal error")

        return {"assembly_code": "\n".join(assembly_lines), "errors": self.errors}