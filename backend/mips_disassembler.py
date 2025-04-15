# backend/mips_disassembler.py
from backend.mips_consts import (
    REGISTER_MAP_REV, OPCODE_MAP_REV, FUNCT_MAP_REV, REGIMM_RT_MAP_REV, J_TYPE_OPCODE
)

class MipsDisassembler:
    def __init__(self):
        self.errors = []

    def _get_reg_name(self, reg_num):
        return REGISTER_MAP_REV.get(reg_num, f"$?{reg_num}") # Fallback for unknown

    def _sign_extend_imm(self, imm, bits=16):
        """ Sign extend a 'bits'-bit immediate value. """
        sign_bit = 1 << (bits - 1)
        if imm & sign_bit: # If negative
            return imm - (1 << bits)
        return imm

    def disassemble_instruction(self, machine_code_int, pc=0): # Add optional PC for branch labels
        """ Disassembles a single 32-bit machine code integer. """
        self.errors = []

        if not isinstance(machine_code_int, int):
             self.errors.append({"message": "Invalid machine code format, expected integer"})
             return "Error"

        opcode = (machine_code_int >> 26) & 0x3F
        rs = (machine_code_int >> 21) & 0x1F
        rt = (machine_code_int >> 16) & 0x1F
        rd = (machine_code_int >> 11) & 0x1F
        shamt = (machine_code_int >> 6) & 0x1F
        funct = machine_code_int & 0x3F
        imm = machine_code_int & 0xFFFF
        addr = machine_code_int & 0x03FFFFFF

        rs_name = self._get_reg_name(rs)
        rt_name = self._get_reg_name(rt)
        rd_name = self._get_reg_name(rd)
        signed_imm = self._sign_extend_imm(imm)
        unsigned_imm = imm # For logical operations, lui

        # --- R-type ---
        if opcode == 0:
            mnemonic = FUNCT_MAP_REV.get(funct)
            if mnemonic == 'syscall': return "syscall"
            if mnemonic == 'nop' or machine_code_int == 0: return "nop" # Handle nop explicitly

            if mnemonic:
                if mnemonic in ["add", "addu", "sub", "subu", "and", "or", "xor", "nor", "slt", "sltu", "sllv", "srlv", "srav"]:
                    return f"{mnemonic} {rd_name}, {rs_name}, {rt_name}"
                elif mnemonic in ["sll", "srl", "sra"]:
                     return f"{mnemonic} {rd_name}, {rt_name}, {shamt}"
                elif mnemonic == "jr": return f"jr {rs_name}"
                elif mnemonic == "jalr":
                    # Default rd is $ra (31)
                    if rd == 31: return f"jalr {rs_name}"
                    else: return f"jalr {rd_name}, {rs_name}"
                elif mnemonic in ["mthi", "mtlo"]: return f"{mnemonic} {rs_name}"
                elif mnemonic in ["mfhi", "mflo"]: return f"{mnemonic} {rd_name}"
                elif mnemonic in ["mult", "multu", "div", "divu"]: return f"{mnemonic} {rs_name}, {rt_name}"
                else: return f"Unknown R-type (funct=0x{funct:02x})"
            else: return f"Unknown R-type (funct=0x{funct:02x})"

        # --- J-type ---
        elif opcode in J_TYPE_OPCODE.values(): # j, jal
            mnemonic = OPCODE_MAP_REV.get(opcode, f"op={opcode}")
            # Calculate pseudo-absolute target address
            target_addr = (addr << 2) | (pc & 0xF0000000) # Combine with PC's upper 4 bits
            return f"{mnemonic} 0x{target_addr:08x}"

        # --- REGIMM --- (bltz, bgez, etc.)
        elif opcode == 0x1:
            mnemonic = REGIMM_RT_MAP_REV.get(rt) # rt field distinguishes instructions here
            if mnemonic:
                 branch_target = pc + 4 + (signed_imm * 4)
                 return f"{mnemonic} {rs_name}, 0x{branch_target:08x}" # Show target addr
                 # return f"{mnemonic} {rs_name}, {signed_imm*4}" # Or show offset
            else: return f"Unknown REGIMM instruction (opcode=0x1, rt={rt})"

        # --- I-type ---
        else:
            mnemonic = OPCODE_MAP_REV.get(opcode)
            if mnemonic:
                 if mnemonic in ["addi", "slti"]: # Signed immediates
                     return f"{mnemonic} {rt_name}, {rs_name}, {signed_imm}"
                 elif mnemonic in ["addiu"]: # addiu often shown signed by convention
                     return f"{mnemonic} {rt_name}, {rs_name}, {signed_imm}"
                 elif mnemonic in ["sltiu"]: # Unsigned compare immediate
                     return f"{mnemonic} {rt_name}, {rs_name}, {unsigned_imm}"
                 elif mnemonic in ["andi", "ori", "xori"]: # Logical, unsigned immediate
                      return f"{mnemonic} {rt_name}, {rs_name}, 0x{unsigned_imm:x}"
                 elif mnemonic == "lui":
                      return f"lui {rt_name}, 0x{unsigned_imm:x}"
                 elif mnemonic in ["lw", "sw", "lb", "lbu", "lh", "lhu", "sb", "sh"]: # Memory ops
                      return f"{mnemonic} {rt_name}, {signed_imm}({rs_name})"
                 elif mnemonic in ["beq", "bne", "blez", "bgtz"]: # Branch ops
                      # blez/bgtz were handled by opcode map directly
                      branch_target = pc + 4 + (signed_imm * 4)
                      if mnemonic in ["beq", "bne"]:
                           return f"{mnemonic} {rs_name}, {rt_name}, 0x{branch_target:08x}"
                      else: # blez, bgtz (rt field is 0)
                           return f"{mnemonic} {rs_name}, 0x{branch_target:08x}"
                 else: return f"Unknown I-type (opcode=0x{opcode:02x})"
            else: return f"Unknown Instruction (opcode=0x{opcode:02x})"

    def disassemble(self, machine_code_hex_lines):
        """ Main method to disassemble list of hex strings. """
        assembly_lines = []
        self.errors = []
        # Assume base address if needed for labels, though standalone disassembly often doesn't use PC
        current_pc = 0x00400000 # Base text address for context (optional)

        for i, hex_line in enumerate(machine_code_hex_lines):
            line_num = i + 1
            try:
                hex_line = hex_line.strip().lower()
                if not hex_line: continue
                if hex_line.startswith("0x"): hex_line = hex_line[2:]
                if len(hex_line) != 8: raise ValueError(f"Invalid hex length: '{hex_line}'")

                machine_code_int = int(hex_line, 16)
                asm_line = self.disassemble_instruction(machine_code_int, current_pc)

                if self.errors: assembly_lines.append(f"Error: {self.errors[-1]['message']}")
                else: assembly_lines.append(asm_line)

                current_pc += 4 # Increment PC for next instruction context

            except ValueError as e:
                self.errors.append({"line": line_num, "message": f"Invalid hex value: {e}"})
                assembly_lines.append(f"Error: Invalid hex input")
            except Exception as e:
                 self.errors.append({"line": line_num, "message": f"Internal error: {e}"})
                 assembly_lines.append(f"Error: Internal error")

        return {"assembly_code": "\n".join(assembly_lines), "errors": self.errors}