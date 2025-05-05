# backend/mips_simulator.py
import logging
import struct # For packing/unpacking bytes to/from byte representations
from collections import defaultdict # For efficient sparse memory representation

# Set up logger for this module
logger = logging.getLogger(__name__)

# Define common memory region start addresses (MIPS convention)
TEXT_START = 0x00400000
DATA_START = 0x10010000
STACK_START = 0x7ffffffc # Stack grows downwards from just below 0x80000000

class MipsSimulator:
    """
    Simulates the execution of MIPS R3000 instructions.
    Manages registers, memory, and program counter.
    Handles a subset of instructions and syscalls.
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
        self.persistent_output = "" # Buffer for accumulating output across steps
        self.output_buffer = "" # Per-step output (optional, could remove if not needed)
        self.input_needed = False # Flag set when a read syscall is encountered
        self.input_buffer = ""    # Buffer to hold input provided by external source (e.g., frontend)

        # Heap simulation for sbrk syscall
        # program_break marks the end of the allocated data/heap area
        self.program_break = DATA_START # Initially set, updated after loading data

        logger.info("Simulator reset complete.")

    def _sign_extend_imm(self, imm, bits=16):
        """ Sign extend a 'bits'-bit immediate value represented as an integer. """
        sign_bit = 1 << (bits - 1) # Calculate the mask for the sign bit
        # Check if the sign bit is set within the original number of bits
        if (imm & sign_bit) != 0:
            # If set, extend the sign by subtracting 2^bits
            # This calculates the correct negative value in Python's arbitrary-precision integers
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
        # Byte access (num_bytes=1) is always aligned
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
            return 0 # Return default value on error

        try:
            # Read the required bytes from the memory dictionary
            value_bytes = bytearray(self.memory[address + i] for i in range(num_bytes))

            # Unpack bytes into a signed integer based on size (using little-endian format '<')
            if num_bytes == 1: # lb (load byte)
                return struct.unpack('<b', value_bytes)[0]
            elif num_bytes == 2: # lh (load half-word)
                return struct.unpack('<h', value_bytes)[0]
            elif num_bytes == 4: # lw (load word)
                 return struct.unpack('<i', value_bytes)[0]
            else:
                raise ValueError(f"Invalid number of bytes to read: {num_bytes}")

        except KeyError:
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
             # Read the required bytes
             value_bytes = bytearray(self.memory[address + i] for i in range(num_bytes))

             # Unpack bytes into an unsigned integer based on size (using little-endian format '<')
             if num_bytes == 1: # lbu (load byte unsigned)
                 return struct.unpack('<B', value_bytes)[0]
             elif num_bytes == 2: # lhu (load half-word unsigned)
                 return struct.unpack('<H', value_bytes)[0]
             elif num_bytes == 4: # lwu (load word unsigned - usually pseudo)
                 return struct.unpack('<I', value_bytes)[0]
             else:
                 raise ValueError(f"Invalid number of bytes to read unsigned: {num_bytes}")

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
        The provided 'value' is treated as a signed integer.
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
            if num_bytes == 1: # sb (store byte)
                value_bytes = struct.pack('<b', value)
            elif num_bytes == 2: # sh (store half-word)
                value_bytes = struct.pack('<h', value)
            elif num_bytes == 4: # sw (store word)
                value_bytes = struct.pack('<i', value)
            else:
                raise ValueError(f"Invalid number of bytes to write: {num_bytes}")

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
        self.reset() # Start from a clean state
        self.text_base = base_text
        self.data_base = base_data
        self.pc = self.text_base # Set initial PC
        self.instruction_map = {} # Clear instruction map
        self.text_segment = bytearray() # Clear text segment bytes

        logger.info(f"Loading program. Text base: 0x{base_text:08x}, Data base: 0x{base_data:08x}")

        # --- Load instructions into instruction list and memory ---
        current_addr = self.text_base
        try:
            for i, hex_code in enumerate(machine_code_hex):
                if not hex_code: continue # Skip empty strings if any
                # Convert hex string (ensure '0x' prefix for robustness) to integer
                hex_code_clean = hex_code if hex_code.startswith('0x') else '0x' + hex_code
                int_code = int(hex_code_clean, 16)

                self.instructions.append(int_code)       # Store integer instruction
                self.instruction_map[current_addr] = i   # Map address to index

                # Store instruction bytes into simulated memory (little-endian)
                instr_bytes = int_code.to_bytes(4, byteorder='little', signed=False)
                for j in range(4):
                    self.memory[current_addr + j] = instr_bytes[j]

                self.text_segment.extend(instr_bytes) # Store raw bytes of text segment
                current_addr += 4
            logger.info(f"Loaded {len(self.instructions)} instructions into text segment (0x{self.text_base:08x} - 0x{current_addr:08x}).")
        except ValueError as e:
            self.state = "error"
            self.error_message = f"Invalid machine code hex format during load: '{e}'"
            logger.error(self.error_message)
            return False # Loading failed

        # --- Load data segment into memory ---
        try:
            # Convert hex string to bytearray, handle empty string
            self.data_segment = bytearray.fromhex(data_segment_hex if data_segment_hex else '')
            current_addr = self.data_base
            # Copy data bytes into simulated memory
            for i in range(len(self.data_segment)):
                self.memory[current_addr + i] = self.data_segment[i]

            # Set the initial program break (heap start) right after the loaded data
            self.program_break = self.data_base + len(self.data_segment)
            logger.info(f"Loaded {len(self.data_segment)} bytes into data segment (0x{self.data_base:08x} - 0x{self.program_break:08x}).")
        except ValueError as e:
            self.state = "error"
            self.error_message = f"Invalid data segment hex format during load: '{e}'"
            logger.error(self.error_message)
            return False # Loading failed

        # Initialize stack pointer to the conventional top of the user stack
        self.registers[29] = STACK_START # $sp

        self.state = "loaded" # Program is ready to run
        return True # Loading successful

    # --- Simulation Control ---

    def step(self):
        """
        Executes a single MIPS instruction located at the current PC.
        Updates simulator state (PC, registers, memory, status).
        Returns the updated state dictionary.
        """
        # Check if simulator is in a state where stepping is allowed
        if self.state not in ["loaded", "paused", "running", "input_wait"]:
            logger.warning(f"Cannot step, simulator state is '{self.state}'")
            return self.get_state()

        # --- Fetch ---
        # Check PC alignment before fetching
        if self.pc % 4 != 0:
             self.state = "error"
             self.error_message = f"PC unaligned: 0x{self.pc:08x}"
             logger.error(self.error_message)
             return self.get_state()

        # Get instruction index from address using the map
        instr_index = self.instruction_map.get(self.pc)

        # Check if PC points outside the loaded instruction range
        program_end_addr = self.text_base + len(self.instructions) * 4
        if instr_index is None: # PC is not pointing to a loaded instruction address
             # Check if PC is trying to execute data/stack/invalid region
             if self.pc >= DATA_START: # Simple check
                  self.state = "error"
                  self.error_message = f"PC attempted to execute from data/stack/invalid region: 0x{self.pc:08x}"
                  logger.error(self.error_message)
             else:
                  # Treat running off the end of explicitly loaded instructions as 'finished'
                  self.state = "finished"
                  self.exit_code = 0 # Default exit code
                  self.termination_reason = "Execution ran off the end of the program." # Add reason
                  logger.info(f"Execution finished normally by running off end of text segment at PC 0x{self.pc:08x}")
             return self.get_state() # Return final state

        # Fetch the integer instruction code if PC is valid
        instruction = self.instructions[instr_index]

        # --- Decode ---
        # Extract fields from the 32-bit instruction
        opcode = (instruction >> 26) & 0x3F
        rs = (instruction >> 21) & 0x1F     # Source register 1
        rt = (instruction >> 16) & 0x1F     # Source register 2 / Dest (I-type) / Opcode extension (REGIMM)
        rd = (instruction >> 11) & 0x1F     # Destination register (R-type)
        shamt = (instruction >> 6) & 0x1F   # Shift amount
        funct = instruction & 0x3F          # Function code (R-type)
        imm = instruction & 0xFFFF          # Immediate value (unsigned 16-bit)
        imm_signed = self._sign_extend_imm(imm, 16) # Sign-extended immediate
        addr = instruction & 0x03FFFFFF     # Address field (J-type)

        # --- Execute ---
        pc_next = self.pc + 4 # Default PC for the next instruction (unless jump/branch taken)
        self.output_buffer = "" # Clear only the output buffer for THIS step
        self.error_message = None # Clear previous non-fatal error messages
        branch_taken = False # Flag to indicate if PC was changed by jump/branch

        logger.debug(f"Step: PC=0x{self.pc:08x}, Instr=0x{instruction:08x}, Opcode=0x{opcode:02x}")

        try:
            # Determine instruction type and execute
            # --- R-Type Instructions (opcode == 0) ---
            if opcode == 0:
                # Decode based on function code (funct)
                if funct == 0x21: # addu $rd, $rs, $rt (Add Unsigned)
                    result = (self.registers[rs] + self.registers[rt]) & 0xFFFFFFFF
                    self._set_register(rd, result)
                elif funct == 0x23: # subu $rd, $rs, $rt (Subtract Unsigned)
                    result = (self.registers[rs] - self.registers[rt]) & 0xFFFFFFFF
                    self._set_register(rd, result)
                elif funct == 0x24: # and $rd, $rs, $rt
                     self._set_register(rd, self.registers[rs] & self.registers[rt])
                elif funct == 0x25: # or $rd, $rs, $rt
                     self._set_register(rd, self.registers[rs] | self.registers[rt])
                elif funct == 0x00: # sll $rd, $rt, shamt (Shift Left Logical)
                     if instruction != 0: # Check if it's actually NOP
                        result = (self.registers[rt] << shamt) & 0xFFFFFFFF
                        self._set_register(rd, result)
                     # If instruction is 0 (NOP), do nothing
                elif funct == 0x02: # srl $rd, $rt, shamt (Shift Right Logical)
                     unsigned_rt = self.registers[rt] & 0xFFFFFFFF # Ensure unsigned before shift
                     self._set_register(rd, unsigned_rt >> shamt)
                # --- Jump Register ---
                elif funct == 0x08: # jr $rs (Jump Register)
                     target_addr = self.registers[rs]
                     if target_addr % 4 != 0: # Check alignment of jump target
                         self.state = "error"
                         self.error_message = f"Jump Register target address unaligned: 0x{target_addr:08x}"
                     else:
                         pc_next = target_addr
                         branch_taken = True # PC is changing
                # --- Jump and Link Register ---
                elif funct == 0x09: # jalr $rd, $rs (or jalr $rs -> rd defaults to 31)
                     target_addr = self.registers[rs]
                     if target_addr % 4 != 0: # Check alignment
                          self.state = "error"
                          self.error_message = f"Jump and Link Register target address unaligned: 0x{target_addr:08x}"
                     else:
                          # Save return address (PC + 8) in rd (default $ra=31)
                          return_addr = self.pc + 8
                          dest_reg = rd if rd != 0 else 31 # Use rd if specified, else $ra
                          self._set_register(dest_reg, return_addr)
                          pc_next = target_addr
                          branch_taken = True # PC is changing
                # --- Syscall ---
                elif funct == 0x0c: # syscall
                     pc_next = self._execute_syscall() # Syscall handles state changes & might change pc_next

                # --- Add other R-types here ---
                # Examples: sra, sllv, srlv, srav, xor, nor, slt, sltu, mult, div, mfhi, mflo, mthi, mtlo, break...
                else:
                    self._unimplemented_instruction(instruction, "R-Type", funct=funct)

            # --- J-Type Instructions (opcode == 2 or 3) ---
            elif opcode in [0x2, 0x3]: # j, jal
                # Calculate target address: Upper 4 bits of PC | (26-bit address field << 2)
                target_addr = (addr << 2) | (self.pc & 0xF0000000)
                if opcode == 0x3: # jal (Jump And Link)
                    # Save return address (PC + 8) in $ra ($31)
                    self._set_register(31, self.pc + 8)
                # Update PC for the *next* cycle
                pc_next = target_addr
                branch_taken = True # PC is changing

            # --- Branch Instructions ---
            elif opcode == 0x4: # beq $rs, $rt, offset
                 if self.registers[rs] == self.registers[rt]:
                     pc_next = self.pc + 4 + (imm_signed * 4) # Calculate target addr
                     branch_taken = True
            elif opcode == 0x5: # bne $rs, $rt, offset
                 if self.registers[rs] != self.registers[rt]:
                     pc_next = self.pc + 4 + (imm_signed * 4)
                     branch_taken = True
            elif opcode == 0x6: # blez $rs, offset (Branch <= 0)
                 # Compare rs as signed value
                 if to_signed_32(self.registers[rs]) <= 0:
                     pc_next = self.pc + 4 + (imm_signed * 4)
                     branch_taken = True
            elif opcode == 0x7: # bgtz $rs, offset (Branch > 0)
                 # Compare rs as signed value
                 if to_signed_32(self.registers[rs]) > 0:
                     pc_next = self.pc + 4 + (imm_signed * 4)
                     branch_taken = True
            # --- REGIMM Instructions (opcode == 1) ---
            elif opcode == 0x1:
                 # Decode based on rt field
                 if rt == 0x0: # bltz $rs, offset (Branch < 0)
                     if to_signed_32(self.registers[rs]) < 0:
                         pc_next = self.pc + 4 + (imm_signed * 4)
                         branch_taken = True
                 elif rt == 0x1: # bgez $rs, offset (Branch >= 0)
                     if to_signed_32(self.registers[rs]) >= 0:
                         pc_next = self.pc + 4 + (imm_signed * 4)
                         branch_taken = True
                 # Add bltzal, bgezal if needed (rt=0x10, 0x11), remember to set $ra
                 else:
                    self._unimplemented_instruction(instruction, "REGIMM", rt=rt)

            # --- Other I-Type Instructions ---
            elif opcode == 0x9: # addiu $rt, $rs, imm_signed (Add Immediate Unsigned)
                 result = (self.registers[rs] + imm_signed) & 0xFFFFFFFF
                 self._set_register(rt, result)
            elif opcode == 0xd: # ori $rt, $rs, imm_unsigned (OR Immediate)
                 self._set_register(rt, self.registers[rs] | imm) # Immediate is zero-extended
            elif opcode == 0xf: # lui $rt, imm_unsigned (Load Upper Immediate)
                 self._set_register(rt, (imm << 16) & 0xFFFFFFFF)
            elif opcode == 0x23: # lw $rt, offset($rs) (Load Word)
                 mem_addr = (self.registers[rs] + imm_signed) & 0xFFFFFFFF
                 value = self.read_memory(mem_addr, 4) # Read signed word
                 if self.state != 'error': self._set_register(rt, value)
            elif opcode == 0x2b: # sw $rt, offset($rs) (Store Word)
                 mem_addr = (self.registers[rs] + imm_signed) & 0xFFFFFFFF
                 self.write_memory(mem_addr, self.registers[rt], 4)
            # --- Add other I-types here ---
            # Examples: andi, xori, slti, sltiu, lb, lbu, lh, lhu, sb, sh...
            else:
                self._unimplemented_instruction(instruction, "I/J-Type", opcode=opcode)


            # --- Update PC for next instruction ---
            # Ensure $zero register remains zero after any operation
            self.registers[0] = 0

            # Advance PC if execution is proceeding normally
            if self.state not in ["error", "finished", "input_wait"]:
                self.pc = pc_next
                self.state = "paused" # Set state to paused after successful step
            elif self.state == "finished":
                # If syscall caused finish, keep PC where it was
                pass # PC already set by syscall handler or end-of-program logic

            # Log branch/jump decisions
            if branch_taken:
                logger.debug(f"Branch/Jump taken. New PC=0x{self.pc:08x}")
            elif self.state == "paused": # Only log default advance if still running
                logger.debug(f"Instruction executed. New PC=0x{self.pc:08x}")

        except Exception as e:
             # Catch unexpected runtime exceptions during execution
             self.state = "error"
             self.error_message = f"Runtime exception at PC 0x{self.pc:08x}: {e}"
             logger.error(self.error_message, exc_info=True)

        # Return the simulator's current state
        return self.get_state()


    def _set_register(self, reg_index, value):
        """Internal helper to set a register value, ensuring $zero ($0) is ignored."""
        # Check for valid GPR index (1-31)
        if 0 < reg_index < 32:
             # Ensure value fits within 32 bits (Python integers are arbitrary precision)
             # Store as unsigned 32-bit pattern
             unsigned_value = value & 0xFFFFFFFF
             self.registers[reg_index] = unsigned_value
             # Log the signed interpretation for clarity
             logger.debug(f"Set Register ${reg_index} = 0x{unsigned_value:08x} ({to_signed_32(unsigned_value)})")
        elif reg_index == 0:
            pass # Silently ignore writes to the zero register
        else:
             # This case should ideally not be reached if instruction decoding is correct
             logger.error(f"Attempted to write to invalid register index {reg_index}")


    def _execute_syscall(self):
        """Handles MIPS syscalls based on the value in register $v0 ($2). Returns the next PC value."""
        syscall_code = self.registers[2] # Get syscall code from $v0
        pc_next = self.pc + 4 # Default: PC advances after syscall

        logger.debug(f"Syscall triggered: code={syscall_code}")
        # Clear previous step's output buffer for relevant syscalls
        # self.output_buffer = "" # Clear per-step buffer if needed, but not persistent one

        # --- Implement Syscall Behavior ---
        if syscall_code == 1: # print_int: print integer in $a0
            # Interpret $a0 as a signed 32-bit integer for printing
            val_to_print = to_signed_32(self.registers[4])
            output_str = str(val_to_print)
            self.persistent_output += output_str # Append
            self.output_buffer = output_str # Set per-step output too (optional)
            logger.info(f"Syscall print_int: {val_to_print}")

        elif syscall_code == 4: # print_string: print null-terminated string at address in $a0
             address = self.registers[4] # Get base address from $a0
             string_bytes = bytearray()
             max_len = 1024 # Safety limit
             count = 0
             try:
                 while count < max_len:
                     # Read byte by byte from memory
                     byte_val = self.memory[address + count]
                     if byte_val == 0: # Null terminator found
                         break
                     string_bytes.append(byte_val)
                     count += 1
                 else: # Loop finished without break (max_len reached)
                      self.error_message = f"Syscall print_string exceeded max length ({max_len}) or no null terminator found starting at 0x{address:08x}"
                      self.state = "error"
                      logger.error(self.error_message)

                 if self.state != "error":
                      try:
                           # Decode bytes as ASCII (common for simple MIPS simulation)
                           decoded_string = string_bytes.decode('ascii')
                           self.persistent_output += decoded_string # Append
                           self.output_buffer = decoded_string # Set per-step output
                           logger.info(f"Syscall print_string: '{decoded_string}'")
                      except UnicodeDecodeError:
                            self.error_message = f"Syscall print_string found non-ASCII data at address 0x{address:08x}"
                            self.state = "error"
                            logger.error(self.error_message)

             except KeyError: # Should not happen with defaultdict
                  self.error_message = f"Syscall print_string accessed invalid memory address 0x{address + count:08x}"
                  self.state = "error"
                  logger.error(self.error_message)
             except Exception as e: # Catch other potential errors
                  self.error_message = f"Error during print_string memory access near 0x{address + count:08x}: {e}"
                  self.state = "error"
                  logger.error(self.error_message, exc_info=True)

        elif syscall_code == 10: # exit: terminate execution
             self.state = "finished"
             self.exit_code = 0 # Standard MIPS exit code
             self.termination_reason = "Program exited via syscall 10." # Specific reason
             logger.info(self.termination_reason)
             pc_next = self.pc # PC does not advance after exit

        # --- Add other syscalls here ---
        # elif syscall_code == 5: # read_int ... self.input_needed = True ...
        # elif syscall_code == 8: # read_string ... self.input_needed = True ...
        # elif syscall_code == 9: # sbrk ... update self.program_break ...
        # elif syscall_code == 11: # print_char ... handle $a0 lower byte ...
        # elif syscall_code == 17: # exit2 (with exit code in $a0)
        #      self.state = "finished"
        #      self.exit_code = to_signed_32(self.registers[4]) # Get exit code from $a0
        #      self.termination_reason = f"Program exited via syscall 17 with code {self.exit_code}."
        #      logger.info(self.termination_reason)
        #      pc_next = self.pc

        else:
             # Handle unknown syscall code
             logger.warning(f"Encountered unimplemented syscall code: {syscall_code}")
             # Option 1: Treat as error and halt
             self.error_message = f"Unimplemented syscall: {syscall_code}"
             self.state = "error"
             # Option 2: Ignore and continue (might be risky)
             # pass

        return pc_next # Return the calculated next PC value


    def _unimplemented_instruction(self, instruction, type_str, opcode=None, funct=None):
        """Sets error state for an unimplemented instruction."""
        details = f"opcode=0x{opcode:02x}" if opcode is not None else f"funct=0x{funct:02x}"
        self.state = "error"
        self.error_message = f"Execution not implemented for {type_str} instruction at PC 0x{self.pc:08x} (instr=0x{instruction:08x}, {details})"
        logger.error(self.error_message)


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
        # Ensure $sp is within a reasonable range before calculating bottom
        sp_val = self.registers[29]
        if sp_val < 0 or sp_val > STACK_START: # If $sp is invalid, show default stack top
             stack_view_bottom_desired = STACK_START - 128
        else:
             stack_view_bottom_desired = sp_val - 128

        stack_view_bottom = max(0, stack_view_bottom_desired)
        stack_view_bottom = min(stack_view_bottom, stack_view_top) # Prevent bottom > top
        if (stack_view_top - stack_view_bottom) // 4 > (MAX_MEM_WORDS // 2):
             stack_view_bottom = stack_view_top - (MAX_MEM_WORDS // 2) * 4
             stack_view_bottom = max(0, stack_view_bottom)

        logger.debug(f"Memory View Ranges: Data=[0x{data_view_start:08x}-0x{data_view_end:08x}), Stack=[0x{stack_view_bottom:08x}-0x{stack_view_top:08x})")

        # Add data segment view words (aligned)
        word_count = 0
        for addr in range(data_view_start, data_view_end, 4):
             if addr % 4 == 0:
                mem_view[addr] = self.read_memory(addr, 4)
                word_count += 1
                if word_count >= (MAX_MEM_WORDS // 2): break # Enforce limit

        # Add stack view words (aligned)
        stack_word_count = 0
        max_stack_words = MAX_MEM_WORDS - word_count
        addr_range = range(stack_view_bottom, stack_view_top, 4)

        for addr in addr_range:
             if addr % 4 == 0 and addr >= 0 and addr < 0x80000000 and stack_word_count < max_stack_words:
                 if addr not in mem_view: # Avoid duplicates if stack overlaps data view somehow
                      mem_view[addr] = self.read_memory(addr, 4)
                      stack_word_count += 1
             if stack_word_count >= max_stack_words: break # Enforce limit

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
            # FIX: Return the persistent output buffer
            "output": self.persistent_output,
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
    # Ensure value is within unsigned 32-bit range before proceeding
    # Masking helps handle potential Python large integers if needed, though registers should be masked on write
    unsigned_val &= 0xFFFFFFFF
    if unsigned_val >= (1 << 31): # Check if sign bit (bit 31) is set
        # Calculate two's complement negative value
        return unsigned_val - (1 << 32)
    else:
        # Value is positive
        return unsigned_val