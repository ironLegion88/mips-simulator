class MipsCoproc0:
    """
    Simulates MIPS Coprocessor 0 (System Control Coprocessor).
    Handles exception routing and core system registers.
    """
    def __init__(self):
        # Register mappings based on standard MIPS architecture:
        # 8: BadVAddr
        # 12: Status
        # 13: Cause
        # 14: EPC
        self.registers = {
            8: 0,
            12: 0,
            13: 0,
            14: 0,
        }

    def read_reg(self, reg_num):
        """Reads from a CP0 register."""
        return self.registers.get(reg_num, 0)

    def write_reg(self, reg_num, value):
        """Writes to a CP0 register."""
        if reg_num in self.registers:
            self.registers[reg_num] = value & 0xFFFFFFFF

    def trigger_exception(self, exc_code, epc_val, bad_vaddr=0):
        """
        Populates Coprocessor 0 registers for a given exception.
        exc_code: MIPS Exception Code (e.g., 4=AdEL, 5=AdES, 8=Sys, 9=Bp, 12=Ov, 15=FPE)
        epc_val: The program counter at the time of the exception.
        bad_vaddr: The offending address for address errors.
        """
        # Save Program Counter
        self.registers[14] = epc_val & 0xFFFFFFFF
        
        # Save Bad Virtual Address if applicable (e.g. unaligned access)
        if bad_vaddr != 0:
            self.registers[8] = bad_vaddr & 0xFFFFFFFF
            
        # Update Cause register (ExcCode is in bits 2-6)
        current_cause = self.registers[13]
        # Clear bits 2-6
        current_cause &= 0xFFFFFF83
        # Set new ExcCode
        current_cause |= ((exc_code & 0x1F) << 2)
        self.registers[13] = current_cause
