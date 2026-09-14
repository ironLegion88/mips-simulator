# backend/mips_simulator.py
import logging
import struct # For packing/unpacking bytes to/from byte representations
import time # For potential run loop timing/yielding
from collections import defaultdict # For efficient sparse memory representation

# Set up logger for this module
logger = logging.getLogger(__name__)

# Define common memory region start addresses (MIPS convention)
TEXT_START = 0x00400000
DATA_START = 0x10010000
STACK_START = 0x7ffffffc # Stack grows downwards from just below 0x80000000
MAX_STEPS = 1000000 # Safety limit for run loop to prevent accidental infinite loops

class MipsSimulator:
    """
    Simulates the execution of MIPS R3000 instructions.
    Manages registers, memory, and program counter.
    Handles a common subset of instructions and syscalls.
    """
    def __init__(self):
        """Initializes the simulator."""
        self.reset()

    def reset(self):
        """Resets the simulator to its initial state before loading a program."""
        # General Purpose Registers (GPRs) initialized to 0
        self.registers = [0] * 32
        # Program Counter: starts at the typical text segment base
        self.pc = TEXT_START
        # Special registers for multiplication/division results
        self.hi = 0
        self.lo = 0
        # Memory: Using defaultdict for sparse memory. Uninitialized bytes default to 0.
        # Keys are byte addresses, values are integer byte values (0-255).
        self.memory = defaultdict(lambda: 0)

        # Program storage
        self.instructions = [] # Holds the loaded machine code as integers
        self.instruction_map = {} # Maps PC address -> index in self.instructions for quick fetching

        # Store loaded segments info (optional, but useful for context/debugging)
        self.text_segment = bytearray() # Raw bytes of the text segment
        self.data_segment = bytearray() # Raw bytes of the initial data segment
        self.text_base = TEXT_START     # Starting address of loaded text
        self.data_base = DATA_START     # Starting address of loaded data

        # Simulation state flags
        self.state = "idle" # Possible states: idle, loaded, running, paused, finished, error, input_wait
        self.error_message = None # Stores description if state becomes 'error'
        self.exit_code = None # Stores exit code if program finishes via exit syscall
        self.termination_reason = None # Stores reason for 'finished' state

        # For handling simulated I/O (syscalls)
        self.persistent_output = "" # Accumulates output across steps
        self.output_buffer = ""     # Per-step output (used by get_state)
        self.input_needed = False   # Flag set when a read syscall is encountered
        self.input_buffer = ""      # Buffer to hold input provided by external source (e.g., frontend)

        # Heap simulation for sbrk syscall
        # program_break marks the end of the allocated data/heap area
        self.program_break = DATA_START # Initially set, updated after loading data

        # For run loop control
        self.steps_executed = 0
        self.pause_requested = False

        logger.info("Simulator reset complete.")

    def _sign_extend_imm(self, imm, bits=16):
        """ Sign extend a 'bits'-bit immediate value represented as an integer. """
        sign_bit = 1 << (bits - 1) # Calculate the mask for the sign bit
        # Check if the sign bit is set within the original number of bits
        if (imm & sign_bit) != 0:
            # If set, extend the sign by subtracting 2^bits
            return imm - (1 << bits)
        else:
            # If not set, the value is positive and already correct
            return imm

    # --- Memory Access Methods ---

    def _check_alignment(self, address, num_bytes):
        """Checks if memory address is aligned for the given access size (2 or 4 bytes)."""
        if num_bytes == 2 and address % 2 != 0:
            logger.warning(f"Alignment Error: Half-word access at unaligned address 0x{address:08x}")
            return False
        if num_bytes == 4 and address % 4 != 0:
            logger.warning(f"Alignment Error: Word access at unaligned address 0x{address:08x}")
            return False
        return True

    def read_memory(self, address, num_bytes):
        """
        Reads 1, 2, or 4 bytes from memory as a SIGNED value.
        Handles basic alignment checks. Returns integer value or 0 on error.
        """
        if not self._check_alignment(address, num_bytes):
            self.state = "error"
            self.error_message = f"Unaligned memory read at 0x{address:08x} for {num_bytes} bytes"
            logger.error(self.error_message)
            return 0

        try:
            # Read the required bytes from the memory dictionary
            value_bytes = bytearray(self.memory[address + i] for i in range(num_bytes))

            # Unpack bytes into a signed integer based on size (using little-endian format '<')
            if num_bytes == 1: return struct.unpack('<b', value_bytes)[0] # lb
            elif num_bytes == 2: return struct.unpack('<h', value_bytes)[0] # lh
            elif num_bytes == 4: return struct.unpack('<i', value_bytes)[0] # lw
            else: raise ValueError(f"Invalid number of bytes to read: {num_bytes}")

        except KeyError: # Should not happen with defaultdict
             logger.warning(f"Reading potentially uninitialized memory at 0x{address:08x}")
             return 0
        except Exception as e:
             self.state = "error"
             self.error_message = f"Memory read error at 0x{address:08x}: {e}"
             logger.error(self.error_message, exc_info=True)
             return 0

    def read_memory_unsigned(self, address, num_bytes):
         """
         Reads 1, 2, or 4 bytes from memory as an UNSIGNED value.
         Handles basic alignment checks. Returns integer value or 0 on error.
         """
         if not self._check_alignment(address, num_bytes):
             self.state = "error"
             self.error_message = f"Unaligned memory read at 0x{address:08x} for {num_bytes} bytes"
             logger.error(self.error_message)
             return 0

         try:
             value_bytes = bytearray(self.memory[address + i] for i in range(num_bytes))
             # Unpack bytes into an unsigned integer based on size (using little-endian format '<')
             if num_bytes == 1: return struct.unpack('<B', value_bytes)[0] # lbu
             elif num_bytes == 2: return struct.unpack('<H', value_bytes)[0] # lhu
             elif num_bytes == 4: return struct.unpack('<I', value_bytes)[0] # lwu (often pseudo)
             else: raise ValueError(f"Invalid number of bytes to read unsigned: {num_bytes}")

         except KeyError:
             logger.warning(f"Reading potentially uninitialized memory at 0x{address:08x}")
             return 0
         except Exception as e:
             self.state = "error"
             self.error_message = f"Memory read error at 0x{address:08x}: {e}"
             logger.error(self.error_message, exc_info=True)
             return 0

    def write_memory(self, address, value, num_bytes):
        """
        Writes 1, 2, or 4 bytes to memory. Handles basic alignment checks.
        The provided 'value' is treated according to the size specifier (b, h, i).
        Returns True on success, False on error.
        """
        if not self._check_alignment(address, num_bytes):
            self.state = "error"
            self.error_message = f"Unaligned memory write at 0x{address:08x} for {num_bytes} bytes"
            logger.error(self.error_message)
            return False

        try:
            # Pack the integer value into bytes based on size (using little-endian format '<')
            value_bytes = None
            if num_bytes == 1: value_bytes = struct.pack('<b', value) # sb
            elif num_bytes == 2: value_bytes = struct.pack('<h', value) # sh
            elif num_bytes == 4: value_bytes = struct.pack('<i', value) # sw
            else: raise ValueError(f"Invalid number of bytes to write: {num_bytes}")

            # Write the packed bytes into the memory dictionary
            for i in range(num_bytes):
                self.memory[address + i] = value_bytes[i]
            return True # Indicate success

        except struct.error as e:
            # Catch packing errors (value out of range for the specified type)
            self.state = "error"
            self.error_message = f"Memory write error at 0x{address:08x}: Value '{value}' out of range for {num_bytes} byte(s). ({e})"
            logger.error(self.error_message)
            return False
        except Exception as e:
             # Catch other potential errors
             self.state = "error"
             self.error_message = f"Memory write error at 0x{address:08x}: {e}"
             logger.error(self.error_message, exc_info=True)
             return False

    # --- Program Loading ---

    def load_program(self, machine_code_hex, data_segment_hex, base_text=TEXT_START, base_data=DATA_START):
        """Loads assembled code (list of hex strings) and data (hex string) into the simulator."""
        self.reset() # Ensure clean state
        self.text_base = base_text
        self.data_base = base_data
        self.pc = self.text_base # Set initial PC
        self.instruction_map = {}
        self.text_segment = bytearray()

        logger.info(f"Loading program. Text base: 0x{base_text:08x}, Data base: 0x{base_data:08x}")

        # Load instructions into instruction list and memory
        current_addr = self.text_base
        try:
            for i, hex_code in enumerate(machine_code_hex):
                if not hex_code: continue
                hex_code_clean = hex_code if hex_code.startswith('0x') else '0x' + hex_code
                int_code = int(hex_code_clean, 16)
                self.instructions.append(int_code)
                self.instruction_map[current_addr] = i
                instr_bytes = int_code.to_bytes(4, byteorder='little', signed=False) # Store as unsigned bytes
                for j in range(4):
                    self.memory[current_addr + j] = instr_bytes[j]
                self.text_segment.extend(instr_bytes)
                current_addr += 4
            logger.info(f"Loaded {len(self.instructions)} instructions into text segment (0x{self.text_base:08x} - 0x{current_addr:08x}).")
        except ValueError as e:
            self.state = "error"
            self.error_message = f"Invalid machine code hex format during load: '{e}'"
            logger.error(self.error_message)
            return False

        # Load data segment into memory
        try:
            self.data_segment = bytearray.fromhex(data_segment_hex if data_segment_hex else '')
            current_addr = self.data_base
            for i in range(len(self.data_segment)):
                self.memory[current_addr + i] = self.data_segment[i]
            self.program_break = self.data_base + len(self.data_segment) # Set heap start
            logger.info(f"Loaded {len(self.data_segment)} bytes into data segment (0x{self.data_base:08x} - 0x{self.program_break:08x}).")
        except ValueError as e:
            self.state = "error"
            self.error_message = f"Invalid data segment hex format during load: '{e}'"
            logger.error(self.error_message)
            return False

        # Initialize stack pointer
        self.registers[29] = STACK_START # $sp

        self.state = "loaded" # Ready to run/step
        self.steps_executed = 0 # Reset step count
        self.pause_requested = False # Clear pause flag
        return True # Loading successful

    # --- Simulation Control ---

    def step(self):
        """
        Executes a single MIPS instruction located at the current PC.
        Updates simulator state (PC, registers, memory, status).
        Returns the updated state dictionary.
        """
        # Check if simulator is in a valid state for stepping
        if self.state not in ["loaded", "paused", "running", "input_wait"]:
            logger.warning(f"Cannot step, simulator state is '{self.state}'")
            return self.get_state()

        # Check if pause was requested during a run
        # Note: step() itself doesn't handle pause_requested directly anymore, run() does.

        # --- Fetch ---
        if self.pc % 4 != 0:
             self.state = "error"
             self.error_message = f"PC unaligned: 0x{self.pc:08x}"
             logger.error(self.error_message)
             return self.get_state()

        instr_index = self.instruction_map.get(self.pc)
        program_end_addr = self.text_base + len(self.instructions) * 4

        if instr_index is None: # PC outside loaded instructions
             if self.pc >= DATA_START: # Executing data/stack?
                  self.state = "error"
                  self.error_message = f"PC attempted to execute from data/stack/invalid region: 0x{self.pc:08x}"
                  logger.error(self.error_message)
             else: # Ran off end of loaded code
                  self.state = "finished"
                  self.exit_code = 0
                  self.termination_reason = "Execution ran off the end of the program."
                  logger.info(self.termination_reason)
             return self.get_state()

        instruction = self.instructions[instr_index]

        # --- Decode ---
        opcode = (instruction >> 26) & 0x3F
        rs = (instruction >> 21) & 0x1F
        rt = (instruction >> 16) & 0x1F
        rd = (instruction >> 11) & 0x1F
        shamt = (instruction >> 6) & 0x1F
        funct = instruction & 0x3F
        imm = instruction & 0xFFFF
        imm_signed = self._sign_extend_imm(imm, 16)
        addr = instruction & 0x03FFFFFF

        # --- Execute ---
        pc_next = self.pc + 4 # Default next PC
        self.output_buffer = "" # Clear output buffer for THIS step only
        self.error_message = None # Clear previous non-fatal error messages
        branch_taken = False
        self.steps_executed += 1 # Increment step count

        # Store previous state before execution for potential error recovery/logging
        prev_pc = self.pc

        logger.debug(f"Step {self.steps_executed}: PC=0x{self.pc:08x}, Instr=0x{instruction:08x}, Opcode=0x{opcode:02x}")

        # Use temporary variables for register reads for clarity
        reg_rs_val = self.registers[rs]
        reg_rt_val = self.registers[rt]

        try:
            # --- R-Type Instructions (opcode == 0) ---
            if opcode == 0:
                if funct == 0x20: # add $rd, $rs, $rt (Add Signed, trap on overflow)
                    result = reg_rs_val + reg_rt_val
                    if (reg_rs_val ^ result) & (reg_rt_val ^ result) & 0x80000000: self._runtime_error("Arithmetic overflow")
                    else: self._set_register(rd, to_signed_32(result))
                elif funct == 0x21: # addu $rd, $rs, $rt (Add Unsigned)
                    self._set_register(rd, (reg_rs_val + reg_rt_val))
                elif funct == 0x22: # sub $rd, $rs, $rt (Subtract Signed, trap on overflow)
                    result = reg_rs_val - reg_rt_val
                    if (reg_rs_val ^ reg_rt_val) & (reg_rs_val ^ result) & 0x80000000: self._runtime_error("Arithmetic overflow")
                    else: self._set_register(rd, to_signed_32(result))
                elif funct == 0x23: # subu $rd, $rs, $rt (Subtract Unsigned)
                    self._set_register(rd, (reg_rs_val - reg_rt_val))
                elif funct == 0x24: self._set_register(rd, reg_rs_val & reg_rt_val) # and
                elif funct == 0x25: self._set_register(rd, reg_rs_val | reg_rt_val) # or
                elif funct == 0x26: self._set_register(rd, reg_rs_val ^ reg_rt_val) # xor
                elif funct == 0x27: self._set_register(rd, ~(reg_rs_val | reg_rt_val)) # nor
                elif funct == 0x2a: self._set_register(rd, 1 if to_signed_32(reg_rs_val) < to_signed_32(reg_rt_val) else 0) # slt
                elif funct == 0x2b: self._set_register(rd, 1 if (reg_rs_val & 0xFFFFFFFF) < (reg_rt_val & 0xFFFFFFFF) else 0) # sltu
                elif funct == 0x00: # sll $rd, $rt, shamt
                     if instruction != 0: self._set_register(rd, reg_rt_val << shamt)
                elif funct == 0x02: # srl $rd, $rt, shamt
                     unsigned_rt = reg_rt_val & 0xFFFFFFFF; self._set_register(rd, unsigned_rt >> shamt)
                elif funct == 0x03: # sra $rd, $rt, shamt
                     signed_rt = to_signed_32(reg_rt_val); self._set_register(rd, signed_rt >> shamt)
                elif funct == 0x04: # sllv $rd, $rt, $rs
                     shift_amount = reg_rs_val & 0x1F; self._set_register(rd, reg_rt_val << shift_amount)
                elif funct == 0x06: # srlv $rd, $rt, $rs
                     shift_amount = reg_rs_val & 0x1F; unsigned_rt = reg_rt_val & 0xFFFFFFFF; self._set_register(rd, unsigned_rt >> shift_amount)
                elif funct == 0x07: # srav $rd, $rt, $rs
                     shift_amount = reg_rs_val & 0x1F; signed_rt = to_signed_32(reg_rt_val); self._set_register(rd, signed_rt >> shift_amount)
                elif funct == 0x08: # jr $rs
                     target_addr = reg_rs_val
                     if target_addr % 4 != 0: self._runtime_error(f"Jump Register target address unaligned: 0x{target_addr:08x}")
                     else: pc_next = target_addr; branch_taken = True
                elif funct == 0x09: # jalr $rd, $rs
                     target_addr = reg_rs_val
                     if target_addr % 4 != 0: self._runtime_error(f"Jump and Link Register target address unaligned: 0x{target_addr:08x}")
                     else:
                          return_addr = self.pc + 8; dest_reg = rd if rd != 0 else 31
                          self._set_register(dest_reg, return_addr)
                          pc_next = target_addr; branch_taken = True
                elif funct == 0x10: self._set_register(rd, self.hi) # mfhi
                elif funct == 0x11: self.hi = reg_rs_val # mthi
                elif funct == 0x12: self._set_register(rd, self.lo) # mflo
                elif funct == 0x13: self.lo = reg_rs_val # mtlo
                elif funct == 0x18: # mult $rs, $rt
                     result = to_signed_32(reg_rs_val) * to_signed_32(reg_rt_val)
                     self.lo = result & 0xFFFFFFFF; self.hi = (result >> 32) & 0xFFFFFFFF
                elif funct == 0x19: # multu $rs, $rt
                     result = (reg_rs_val & 0xFFFFFFFF) * (reg_rt_val & 0xFFFFFFFF)
                     self.lo = result & 0xFFFFFFFF; self.hi = (result >> 32) & 0xFFFFFFFF
                elif funct == 0x1a: # div $rs, $rt
                     rs_signed = to_signed_32(reg_rs_val); rt_signed = to_signed_32(reg_rt_val)
                     if rt_signed == 0: self._runtime_error("Division by zero")
                     else:
                          quotient = int(rs_signed / rt_signed); remainder = rs_signed % rt_signed
                          # Adjust remainder sign for MIPS convention if needed (implementation detail)
                          if (remainder != 0) and ((rs_signed < 0) != (rt_signed < 0)):
                              # This standard remainder logic might differ slightly from MIPS spec edge cases
                              pass
                          self.lo = quotient & 0xFFFFFFFF; self.hi = remainder & 0xFFFFFFFF
                elif funct == 0x1b: # divu $rs, $rt
                     rs_unsigned = reg_rs_val & 0xFFFFFFFF; rt_unsigned = reg_rt_val & 0xFFFFFFFF
                     if rt_unsigned == 0: self._runtime_error("Division by zero")
                     else:
                          self.lo = (rs_unsigned // rt_unsigned) & 0xFFFFFFFF
                          self.hi = (rs_unsigned % rt_unsigned) & 0xFFFFFFFF
                elif funct == 0x0c: pc_next = self._execute_syscall() # syscall
                elif funct == 0x0d: self._runtime_error("BREAK instruction encountered", is_break=True) # break
                else: self._unimplemented_instruction(instruction, "R-Type", funct=funct)

            # --- J-Type ---
            elif opcode in [0x2, 0x3]: # j, jal
                target_addr = (addr << 2) | (self.pc & 0xF0000000)
                if opcode == 0x3: self._set_register(31, self.pc + 8) # $ra
                pc_next = target_addr; branch_taken = True

            # --- Branch Instructions ---
            elif opcode == 0x4: # beq $rs, $rt, offset
                 if reg_rs_val == reg_rt_val: pc_next = self.pc + 4 + (imm_signed * 4); branch_taken = True
            elif opcode == 0x5: # bne $rs, $rt, offset
                 if reg_rs_val != reg_rt_val: pc_next = self.pc + 4 + (imm_signed * 4); branch_taken = True
            elif opcode == 0x6: # blez $rs, offset
                 if to_signed_32(reg_rs_val) <= 0: pc_next = self.pc + 4 + (imm_signed * 4); branch_taken = True
            elif opcode == 0x7: # bgtz $rs, offset
                 if to_signed_32(reg_rs_val) > 0: pc_next = self.pc + 4 + (imm_signed * 4); branch_taken = True
            # --- REGIMM (opcode == 1) ---
            elif opcode == 0x1:
                 if rt == 0x0: # bltz $rs, offset
                     if to_signed_32(reg_rs_val) < 0: pc_next = self.pc + 4 + (imm_signed * 4); branch_taken = True
                 elif rt == 0x1: # bgez $rs, offset
                     if to_signed_32(reg_rs_val) >= 0: pc_next = self.pc + 4 + (imm_signed * 4); branch_taken = True
                 elif rt == 0x10: # bltzal $rs, offset
                     if to_signed_32(reg_rs_val) < 0:
                         self._set_register(31, self.pc + 8); pc_next = self.pc + 4 + (imm_signed * 4); branch_taken = True
                 elif rt == 0x11: # bgezal $rs, offset
                     if to_signed_32(reg_rs_val) >= 0:
                         self._set_register(31, self.pc + 8); pc_next = self.pc + 4 + (imm_signed * 4); branch_taken = True
                 else: self._unimplemented_instruction(instruction, "REGIMM", rt=rt)

            # --- Other I-Type Instructions ---
            elif opcode == 0x8: # addi $rt, $rs, imm_signed
                 result = reg_rs_val + imm_signed
                 if (reg_rs_val ^ result) & (imm_signed ^ result) & 0x80000000: self._runtime_error("Arithmetic overflow")
                 else: self._set_register(rt, to_signed_32(result))
            elif opcode == 0x9: # addiu $rt, $rs, imm_signed
                 self._set_register(rt, reg_rs_val + imm_signed)
            elif opcode == 0xa: # slti $rt, $rs, imm_signed
                 self._set_register(rt, 1 if to_signed_32(reg_rs_val) < imm_signed else 0)
            elif opcode == 0xb: # sltiu $rt, $rs, imm_unsigned (compare rs unsigned with SIGNED immediate)
                 # MIPS spec comparison is unsigned rs < signed immediate
                 self._set_register(rt, 1 if (reg_rs_val & 0xFFFFFFFF) < imm_signed else 0)
            elif opcode == 0xc: self._set_register(rt, reg_rs_val & imm)    # andi
            elif opcode == 0xd: self._set_register(rt, reg_rs_val | imm)    # ori
            elif opcode == 0xe: self._set_register(rt, reg_rs_val ^ imm)    # xori
            elif opcode == 0xf: self._set_register(rt, imm << 16)           # lui
            elif opcode == 0x20: # lb $rt, offset($rs)
                 mem_addr = (reg_rs_val + imm_signed); value = self.read_memory(mem_addr, 1)
                 if self.state != 'error': self._set_register(rt, value)
            elif opcode == 0x21: # lh $rt, offset($rs)
                 mem_addr = (reg_rs_val + imm_signed); value = self.read_memory(mem_addr, 2)
                 if self.state != 'error': self._set_register(rt, value)
            elif opcode == 0x23: # lw $rt, offset($rs)
                 mem_addr = (reg_rs_val + imm_signed); value = self.read_memory(mem_addr, 4)
                 if self.state != 'error': self._set_register(rt, value)
            elif opcode == 0x24: # lbu $rt, offset($rs)
                 mem_addr = (reg_rs_val + imm_signed); value = self.read_memory_unsigned(mem_addr, 1)
                 if self.state != 'error': self._set_register(rt, value)
            elif opcode == 0x25: # lhu $rt, offset($rs)
                 mem_addr = (reg_rs_val + imm_signed); value = self.read_memory_unsigned(mem_addr, 2)
                 if self.state != 'error': self._set_register(rt, value)
            elif opcode == 0x28: # sb $rt, offset($rs)
                 mem_addr = (reg_rs_val + imm_signed); self.write_memory(mem_addr, reg_rt_val, 1)
            elif opcode == 0x29: # sh $rt, offset($rs)
                 mem_addr = (reg_rs_val + imm_signed); self.write_memory(mem_addr, reg_rt_val, 2)
            elif opcode == 0x2b: # sw $rt, offset($rs)
                 mem_addr = (reg_rs_val + imm_signed); self.write_memory(mem_addr, reg_rt_val, 4)
            # --- Unimplemented ---
            else:
                self._unimplemented_instruction(instruction, "I/J-Type", opcode=opcode)


            # --- Post-Execution: Update PC & State ---
            self.registers[0] = 0 # Ensure $zero is always zero

            # Advance PC unless an error occurred or program finished/waiting
            if self.state not in ["error", "finished", "input_wait"]:
                self.pc = pc_next
                # State remains 'running' if called from run loop, otherwise becomes 'paused'
                # The run() method handles setting state back to 'paused' when loop ends.
                if self.state != "running":
                     self.state = "paused"

            # Logging for flow control
            if branch_taken: logger.debug(f"Branch/Jump taken. New PC=0x{self.pc:08x}")
            elif self.state == "paused" or self.state == "running": logger.debug(f"Instruction executed. New PC=0x{self.pc:08x}")

        except Exception as e:
             # Catch unexpected runtime exceptions during execution logic
             self._runtime_error(f"Runtime exception: {e}")
             logger.error(f"Runtime exception at PC 0x{prev_pc:08x}", exc_info=True) # Log traceback
             self.pc = prev_pc # Keep PC at the instruction causing the error

        return self.get_state() # Return the simulator's current state

    def _set_register(self, reg_index, value):
        """Internal helper to set a register value, ensuring $zero ($0) is ignored and value is 32-bit."""
        if 0 < reg_index < 32:
             unsigned_value = value & 0xFFFFFFFF # Mask to 32 bits
             self.registers[reg_index] = unsigned_value
             logger.debug(f"Set Register ${reg_index} = 0x{unsigned_value:08x} ({to_signed_32(unsigned_value)})")
        elif reg_index == 0: pass # Ignore writes to $zero
        else: logger.error(f"Attempted to write to invalid register index {reg_index}")

    def _runtime_error(self, message, is_break=False):
        """Sets the simulator state to error."""
        self.state = "error"
        self.error_message = message
        if is_break:
             logger.warning(f"BREAK encountered at PC 0x{self.pc:08x}: {message}")
        else:
             logger.error(f"Runtime Error at PC 0x{self.pc:08x}: {message}")

    def _execute_syscall(self):
        """Handles MIPS syscalls based on $v0. Appends to persistent_output. Returns next PC."""
        syscall_code = self.registers[2] # Get syscall code from $v0
        pc_next = self.pc + 4 # Default: PC advances after syscall

        logger.debug(f"Syscall triggered: code={syscall_code}")
        # Note: persistent_output is appended to, output_buffer (per-step) is cleared in step()

        try:
            if syscall_code == 1: # print_int ($a0)
                val_to_print = to_signed_32(self.registers[4])
                output_str = str(val_to_print); self.persistent_output += output_str
                logger.info(f"Syscall print_int: {val_to_print}")
            elif syscall_code == 4: # print_string (address in $a0)
                 address = self.registers[4]; string_bytes = bytearray(); max_len = 1024; count = 0
                 while count < max_len:
                     byte_val = self.memory[address + count];
                     if byte_val == 0: break
                     string_bytes.append(byte_val); count += 1
                 else: self._runtime_error(f"Syscall print_string exceeded max length ({max_len}) or no null terminator found starting at 0x{address:08x}")
                 if self.state != "error":
                      decoded_string = string_bytes.decode('ascii') # Assume ASCII
                      self.persistent_output += decoded_string
                      logger.info(f"Syscall print_string: '{decoded_string}'")
            elif syscall_code == 5: # read_int (result in $v0)
                 logger.info("Syscall read_int: Waiting for input.")
                 self.state = "input_wait"; self.input_needed = True; pc_next = self.pc # Halt PC
            elif syscall_code == 8: # read_string (addr in $a0, len in $a1)
                 logger.info(f"Syscall read_string: Waiting for input (buffer @ 0x{self.registers[4]:08x}, max len {self.registers[5]}).")
                 self.state = "input_wait"; self.input_needed = True; pc_next = self.pc # Halt PC
            elif syscall_code == 9: # sbrk (allocate heap memory, amount in $a0)
                 amount = to_signed_32(self.registers[4])
                 logger.info(f"Syscall sbrk: Requesting {amount} bytes.")
                 allocated_address = self.program_break # Return current break
                 self.program_break += amount # Increase break point
                 self._set_register(2, allocated_address) # $v0 = allocated address
                 if self.program_break >= self.registers[29]: # Basic heap/stack collision check
                     self._runtime_error(f"sbrk failed: Heap collided with stack (break=0x{self.program_break:08x}, sp=0x{self.registers[29]:08x})")
            elif syscall_code == 10: # exit
                 self.state = "finished"; self.exit_code = 0; self.termination_reason = "Program exited via syscall 10."
                 logger.info(self.termination_reason); pc_next = self.pc # Stop PC
            elif syscall_code == 11: # print_char ($a0)
                 char_val = self.registers[4] & 0xFF # Lower byte
                 output_char = chr(char_val); self.persistent_output += output_char
                 logger.info(f"Syscall print_char: '{output_char}' (ASCII {char_val})")
            elif syscall_code == 17: # exit2 (with exit code in $a0)
                 self.state = "finished"; self.exit_code = to_signed_32(self.registers[4])
                 self.termination_reason = f"Program exited via syscall 17 with code {self.exit_code}."
                 logger.info(self.termination_reason); pc_next = self.pc # Stop PC
            else:
                 # --- FIX: Treat unimplemented syscall as error ---
                 self._runtime_error(f"Unimplemented syscall: {syscall_code}")
                 pc_next = self.pc # Stop PC on error
                 # --- END FIX ---

        # Catch exceptions during syscall execution (e.g., memory access errors in print_string)
        except UnicodeDecodeError:
             self._runtime_error(f"Syscall print_string found non-ASCII data at address 0x{self.registers[4]:08x}")
             pc_next = self.pc # Stop PC
        except KeyError: # Should not happen with defaultdict
             self._runtime_error(f"Syscall accessed potentially invalid memory address")
             pc_next = self.pc # Stop PC
        except Exception as e:
             self._runtime_error(f"Error during syscall {syscall_code}: {e}")
             pc_next = self.pc # Stop PC

        return pc_next # Return the calculated next PC value

    def provide_input(self, input_data):
        """Provides input data to the simulator when it's waiting."""
        if self.state != "input_wait" or not self.input_needed:
            logger.warning("Provide_input called when simulator was not waiting for input.")
            return False # Indicate input was not processed

        syscall_code = self.registers[2] # Check which syscall was waiting
        success = False
        try:
            if syscall_code == 5: # read_int
                value = int(input_data.strip()) # Attempt to parse integer
                if not (-(1 << 31) <= value < (1 << 31)): raise ValueError("Input integer out of 32-bit signed range")
                self._set_register(2, value) # Store result in $v0
                self.persistent_output += input_data.strip() + "\n" # Echo input
                success = True
                logger.info(f"Syscall read_int: Received '{input_data}', stored {value} in $v0.")
            elif syscall_code == 8: # read_string
                 buffer_addr = self.registers[4]; max_len = self.registers[5]
                 self.persistent_output += input_data # Echo raw input (newline handling depends on input source)
                 # self.persistent_output += "\n" # Optional: Add newline automatically
                 input_to_store = input_data[:max_len-1] # Truncate
                 logger.info(f"Syscall read_string: Received '{input_data}', storing '{input_to_store}' (max len {max_len})")
                 byte_count = 0
                 for char in input_to_store:
                     if not self.write_memory(buffer_addr + byte_count, ord(char), 1): raise MemoryError("Failed to write character")
                     byte_count += 1
                 if not self.write_memory(buffer_addr + byte_count, 0, 1): raise MemoryError("Failed to write null terminator") # Null term
                 success = True
            else:
                 logger.error(f"Provide_input called while waiting, but syscall code {syscall_code} is not a read syscall.")
                 self.error_message = f"Input provided for non-input syscall {syscall_code}"
                 # Don't set success=True, keep waiting? Or error? Keep waiting for now.

            if success:
                 self.input_needed = False
                 self.state = "paused" # Ready for next step
                 self.pc += 4 # Advance PC past the syscall instruction
                 self.error_message = None # Clear any previous input format error message
                 return True # Indicate input was successfully processed

        except ValueError as e: # Catch parsing errors (e.g., int("abc"))
            logger.error(f"Invalid input provided for syscall {syscall_code}: '{input_data}'. Error: {e}")
            self.error_message = f"Invalid input format for syscall {syscall_code}: {e}" # Report format error
            # --- FIX: Clear $v0 on invalid read_int input ---
            if syscall_code == 5:
                self._set_register(2, 0) # Clear $v0 on failed read_int
            # --- END FIX ---
            self.input_needed = True # Still need input
            self.state = "input_wait" # Remain waiting
            return False # Indicate input was NOT successfully processed
        except Exception as e: # Catch memory errors or others
            self._runtime_error(f"Error processing provided input for syscall {syscall_code}: {e}")
            # Keep state as error, don't advance PC
            return False # Indicate input processing failed

        return False # Fallback, should not be reached if success or exception occurs

    def run(self, step_limit=MAX_STEPS):
        """Runs the simulation continuously until pause, finish, error, input needed, or step limit."""
        if self.state not in ["loaded", "paused"]:
            logger.warning(f"Cannot run, simulator state is '{self.state}'")
            return self.get_state()

        logger.info(f"Running simulation... (Limit: {step_limit} steps)")
        self.state = "running" # Set state to running
        self.pause_requested = False # Ensure pause flag is clear
        start_time = time.time()

        steps_taken_this_run = 0
        # --- FIX: Check pause request *before* step and refine loop condition ---
        while steps_taken_this_run < step_limit:
            # Check conditions that stop the run loop BEFORE executing the step
            if self.state != "running": break # e.g., became error/finished/input_wait inside previous step
            if self.pause_requested:
                self.state = "paused" # Update state if pause was requested
                self.pause_requested = False # Clear the flag
                logger.info("Run loop paused by request.")
                break # Exit loop

            # Execute one step. step() will update self.state if needed.
            self.step()
            steps_taken_this_run += 1

            # Exit loop immediately if step caused finish/error/input_wait
            if self.state != "running": break
        # --- END FIX ---

        end_time = time.time()

        # Check if loop terminated due to step limit while still running
        if steps_taken_this_run >= step_limit and self.state == "running":
            self.state = "paused" # Force pause if limit reached
            self.error_message = f"Run stopped: Maximum simulation steps ({step_limit}) exceeded."
            logger.warning(self.error_message) # Log limit reached

        # Final log message based on why the loop stopped
        if self.state == "paused" and not self.error_message: # Ensure error message isn't overwritten
            logger.info(f"Run paused. Steps this run: {steps_taken_this_run}.")
        elif self.state == "finished":
            logger.info(f"Run finished. Reason: {self.termination_reason}. Steps this run: {steps_taken_this_run}.")
        elif self.state == "error":
             logger.info(f"Run stopped due to error after {steps_taken_this_run} steps.")
        elif self.state == "input_wait":
            logger.info(f"Run paused for input after {steps_taken_this_run} steps.")


        logger.info(f"Run complete. Final State: {self.state}. Total steps: {self.steps_executed}. Time: {end_time - start_time:.3f}s")
        self.pause_requested = False # Ensure flag is clear
        return self.get_state()

    def request_pause(self):
        """Signals the run loop to pause at the next convenient point."""
        if self.state == "running":
            self.pause_requested = True
            logger.info("Pause requested for running simulation.")


    def get_state(self):
        """Returns a dictionary representing the current state of the simulator."""
        # --- Prepare Memory View ---
        mem_view = {}
        MAX_MEM_WORDS = 256 # Limit total words shown
        # Define desired view ranges, limit sizes
        data_view_start = self.data_base
        data_view_end_desired = min(self.data_base + 256, self.program_break + 128)
        data_view_end = min(data_view_end_desired, data_view_start + (MAX_MEM_WORDS // 2) * 4)
        stack_view_top = STACK_START + 4
        sp_val = self.registers[29]
        # Calculate stack bottom safely
        if sp_val <= 0 or sp_val > STACK_START + 4: stack_view_bottom_desired = STACK_START - 128
        else: stack_view_bottom_desired = sp_val - 128
        stack_view_bottom = max(0, stack_view_bottom_desired)
        stack_view_bottom = min(stack_view_bottom, stack_view_top)
        if (stack_view_top - stack_view_bottom) // 4 > (MAX_MEM_WORDS // 2):
             stack_view_bottom = stack_view_top - (MAX_MEM_WORDS // 2) * 4
             stack_view_bottom = max(0, stack_view_bottom)

        logger.debug(f"Memory View Ranges: Data=[0x{data_view_start:08x}-0x{data_view_end:08x}), Stack=[0x{stack_view_bottom:08x}-0x{stack_view_top:08x})")

        # Add data segment view words (aligned)
        word_count = 0
        for addr in range(data_view_start, data_view_end, 4):
             if addr % 4 == 0 :
                # Reading memory might fail, handle gracefully
                try: mem_view[addr] = self.read_memory(addr, 4)
                except: mem_view[addr] = 0 # Default on error?
                word_count += 1
                if word_count >= (MAX_MEM_WORDS // 2): break

        # Add stack view words (aligned)
        stack_word_count = 0
        max_stack_words = MAX_MEM_WORDS - word_count
        addr_range = range(stack_view_bottom, stack_view_top, 4)
        for addr in addr_range:
             if addr % 4 == 0 and addr >= 0 and addr < 0x80000000 and stack_word_count < max_stack_words:
                 if addr not in mem_view:
                      try: mem_view[addr] = self.read_memory(addr, 4)
                      except: mem_view[addr] = 0
                      stack_word_count += 1
             if stack_word_count >= max_stack_words: break

        logger.debug(f"Memory view generated with {len(mem_view)} entries.")

        # --- Return State Dictionary ---
        state_data = {
            "pc": self.pc,
            "registers": self.registers[:], # Return a copy
            "hi": self.hi,
            "lo": self.lo,
            "state": self.state,
            "error": self.error_message,
            "exit_code": self.exit_code,
            "output": self.persistent_output, # Return accumulated output
            "input_needed": self.input_needed,
            "memory_view": mem_view
        }
        # Add termination reason only if finished
        if self.state == "finished":
            state_data["termination_reason"] = self.termination_reason

        return state_data

# --- End MipsSimulator Class ---

# Helper function to convert unsigned 32-bit int to signed int
def to_signed_32(unsigned_val):
    """Converts a 32-bit unsigned value (0 to 0xFFFFFFFF) to its signed equivalent."""
    # Ensure value is treated as 32-bit unsigned first
    unsigned_val &= 0xFFFFFFFF
    if unsigned_val >= (1 << 31): # Check if sign bit (bit 31) is set
        # Calculate two's complement negative value
        return unsigned_val - (1 << 32)
    else:
        # Value is positive
        return unsigned_val