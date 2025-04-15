# backend/mips_assembler.py
import re
# Use absolute imports relative to backend package
from backend.mips_consts import (
    REGISTER_MAP, REGISTER_MAP_REV, R_TYPE_FUNCT, I_TYPE_OPCODE, J_TYPE_OPCODE,
    PSEUDO_INSTRUCTIONS, R_TYPE_FORMATS, I_TYPE_FORMATS, J_TYPE_FORMATS,
    PSEUDO_HANDLERS # Assuming PSEUDO_HANDLERS dict is added to mips_consts for expansion logic functions
)
import logging # Add logging

logger = logging.getLogger(__name__)

class MipsAssembler:
    def __init__(self):
        self.symbol_table = {}
        self.data_segment = bytearray() # Store data segment contents
        self.current_address = 0
        self.base_text_address = 0x00400000
        self.base_data_address = 0x10010000
        self.parsed_lines = [] # Store detailed parsed info from first pass
        self.machine_code = []
        self.errors = []
        self.in_data_segment = False

    def _add_error(self, line_num, message, instruction_text=""):
        # Avoid duplicate errors for the same line/message
        if not any(err['line'] == line_num and err['message'] == message for err in self.errors):
             logger.debug(f"Adding error: Line {line_num}, Msg: {message}, Text: '{instruction_text}'")
             self.errors.append({"line": line_num, "message": message, "text": instruction_text})

    def _parse_register(self, reg_str, line_num, instruction_text):
        # Simplified register parsing
        reg_str_lower = reg_str.lower()
        if reg_str_lower not in REGISTER_MAP:
            self._add_error(line_num, f"Invalid register name: '{reg_str}'", instruction_text)
            return None
        return REGISTER_MAP[reg_str_lower]

    def _parse_immediate(self, imm_str, line_num, instruction_text, bits=16, signed=True):
        if not imm_str:
             self._add_error(line_num, "Empty immediate value.", instruction_text)
             return None
        try:
            val = int(imm_str, 0) # Handles '0x' hex and decimal
        except ValueError:
            self._add_error(line_num, f"Invalid immediate value: '{imm_str}'", instruction_text)
            return None

        # Range checking
        if signed:
            min_val, max_val = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
            if not (min_val <= val <= max_val):
                self._add_error(line_num, f"Immediate '{imm_str}' out of range for {bits}-bit signed value ({min_val} to {max_val})", instruction_text)
                return None
            # Return the value, ensuring it fits within 'bits' for encoding (2's complement for negatives)
            return val & ((1 << bits) - 1)
        else: # Unsigned
            min_val, max_val = 0, (1 << bits) - 1
            if not (min_val <= val <= max_val):
                self._add_error(line_num, f"Immediate '{imm_str}' out of range for {bits}-bit unsigned value ({min_val} to {max_val})", instruction_text)
                return None
            return val # Already positive and within range

    def _parse_memory_operand(self, operand_str, line_num, instruction_text):
        """ Parses 'offset($register)' or '($register)' format. Returns (offset, reg_name) or None on error. """
        match = re.match(r'^\s*(-?\d+)?\s*\(\s*(\$[a-zA-Z0-9]+)\s*\)\s*$', operand_str)
        if match:
            offset_str = match.group(1)
            reg_name = match.group(2)
            offset = int(offset_str) if offset_str else 0 # Default offset is 0 if omitted
            return offset, reg_name
        else:
            # Check for just a bare register e.g. '($sp)' which implies 0 offset
             match_bare = re.match(r'^\s*\(\s*(\$[a-zA-Z0-9]+)\s*\)\s*$', operand_str)
             if match_bare:
                 reg_name = match_bare.group(1)
                 return 0, reg_name

             self._add_error(line_num, f"Invalid memory operand format: '{operand_str}'. Expected 'offset($reg)' or '($reg)'.", instruction_text)
             return None, None

    def _parse_line(self, line, line_num):
        """ Parses a raw line into its components (label, directive, instruction, operands). """
        original_line = line
        line = line.split('#')[0].strip()
        if not line:
            return None # Skip empty/comment lines

        # --- Check for Label ---
        label_match = re.match(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)', line)
        label = None
        if label_match:
            label = label_match.group(1)
            line = label_match.group(2).strip() # Remainder of the line

        if not line: # Line could just be a label
            return {"type": "label_only", "label": label, "line_num": line_num, "original_text": original_line}

        # --- Check for Directive ---
        if line.startswith('.'):
            parts = re.split(r'\s+', line, 1)
            directive = parts[0].lower()
            args_str = parts[1] if len(parts) > 1 else ""
            # Split args carefully, handling strings
            args = []
            if directive == '.asciiz':
                 # Find the first quote, take everything after it until the last quote
                 first_quote = args_str.find('"')
                 last_quote = args_str.rfind('"')
                 if first_quote != -1 and last_quote > first_quote:
                     args = [args_str[first_quote + 1 : last_quote]]
                 else:
                     self._add_error(line_num, f"Invalid string format for {directive}: {args_str}", original_line)
            elif args_str: # For other directives like .word, .byte, .space
                args = [a.strip() for a in args_str.split(',')]
                args = [a for a in args if a] # Remove empty strings resulting from extra commas

            return {"type": "directive", "label": label, "directive": directive, "args": args, "line_num": line_num, "original_text": original_line}

        # --- Assume Instruction ---
        parts = re.split(r'\s+', line, 1)
        instruction = parts[0].lower()
        operands_str = parts[1] if len(parts) > 1 else ""

        # Simple operand splitting by comma - handle memory format later if needed
        operands = [op.strip() for op in operands_str.split(',')]
        operands = [op for op in operands if op] # Remove empty strings

        # Check for instructions that REQUIRE memory format and parse specifically
        # CRITICAL FIX: Handle instructions like 'lw $a0, 0' by NOT trying to parse as memory unless format matches
        is_memory_op = instruction in ['lw', 'sw', 'lb', 'sb', 'lh', 'sh', 'lbu', 'lhu'] # Add others like lwl, lwr etc.
        parsed_operands = []
        expected_format = I_TYPE_FORMATS.get(instruction, []) # Get expected format

        if is_memory_op and len(operands) == 2:
             # Expects rt, offset($rs) format
             reg_op = operands[0]
             mem_op_str = operands[1]
             offset, base_reg = self._parse_memory_operand(mem_op_str, line_num, original_line)
             if base_reg is not None: # Successfully parsed memory format
                 parsed_operands = [reg_op, str(offset), base_reg] # Standardize order: rt, imm, rs
             else:
                 # Error already added by _parse_memory_operand if format was wrong
                 # If it didn't parse as memory, treat as potentially wrong operand count below
                 parsed_operands = operands # Keep original operands for error checking later
        else:
            # For non-memory ops or memory ops with wrong number of comma-separated parts
            parsed_operands = operands


        return {
            "type": "instruction",
            "label": label,
            "instruction": instruction,
            "operands": parsed_operands, # Use the potentially restructured list
            "line_num": line_num,
            "original_text": original_line
        }

    def first_pass(self, assembly_code):
        """ Build symbol table, parse lines, handle basic directives for address calculation. """
        self.symbol_table = {}
        self.parsed_lines = []
        self.errors = []
        self.current_address = self.base_text_address # Start in .text
        self.in_data_segment = False
        lines = assembly_code.splitlines()
        current_segment_base = self.base_text_address

        for i, line in enumerate(lines):
            line_num = i + 1
            parsed = self._parse_line(line, line_num)
            if not parsed: continue

            # Assign current address *before* potentially modifying it for the current item
            parsed["address"] = self.current_address

            if parsed.get("label"):
                label = parsed["label"]
                if label in self.symbol_table:
                    self._add_error(line_num, f"Duplicate label definition: {label}", parsed["original_text"])
                else:
                    self.symbol_table[label] = self.current_address
                    logger.debug(f"Label '{label}' defined at address 0x{self.current_address:08x}")

            # Handle segment switching first
            if parsed["type"] == "directive":
                directive = parsed["directive"]
                if directive == ".data":
                    if not self.in_data_segment:
                        self.in_data_segment = True
                        self.current_address = self.base_data_address # Switch to data segment start
                        current_segment_base = self.base_data_address
                        logger.debug(f"Switched to .data segment at 0x{self.current_address:08x}")
                    # Store the parsed line even if it's just the directive
                    self.parsed_lines.append(parsed)
                    continue # Directive itself takes no space

                elif directive == ".text":
                    if self.in_data_segment:
                        self.in_data_segment = False
                        self.current_address = self.base_text_address # Switch to text segment start
                        current_segment_base = self.base_text_address
                        logger.debug(f"Switched to .text segment at 0x{self.current_address:08x}")
                    # Store the parsed line even if it's just the directive
                    self.parsed_lines.append(parsed)
                    continue # Directive itself takes no space

            # Handle directives that allocate space/data
            if parsed["type"] == "directive":
                 directive = parsed["directive"]
                 args = parsed["args"]
                 increment = 0
                 if not self.in_data_segment and directive not in ['.globl', '.extern']: # Only allow data directives in .data
                     self._add_error(line_num, f"Directive '{directive}' only allowed in .data segment", parsed["original_text"])
                 elif directive == ".word":
                     increment = len(args) * 4
                 elif directive == ".byte":
                     increment = len(args) * 1
                 elif directive == ".half":
                     increment = len(args) * 2
                 elif directive == ".space":
                     if len(args) == 1:
                         try: increment = int(args[0])
                         except ValueError: self._add_error(line_num, f"Invalid size for .space: {args[0]}", parsed["original_text"])
                     else: self._add_error(line_num, ".space expects one argument (size in bytes)", parsed["original_text"])
                 elif directive == ".asciiz":
                     if len(args) == 1:
                         increment = len(args[0]) + 1 # String length + null terminator
                     else: self._add_error(line_num, ".asciiz expects one string argument", parsed["original_text"])
                 elif directive == ".align":
                     if len(args) == 1:
                         try:
                             n = int(args[0])
                             if n < 0 or (1 << n) > 16384: # Basic sanity check
                                 raise ValueError("Alignment must be power of 2")
                             alignment = 1 << n
                             offset = self.current_address % alignment
                             if offset != 0:
                                 increment = alignment - offset
                         except ValueError: self._add_error(line_num, f"Invalid alignment value for .align: {args[0]}", parsed["original_text"])
                     else: self._add_error(line_num, ".align expects one argument (power of 2)", parsed["original_text"])

                 self.current_address += increment
                 logger.debug(f"Directive '{directive}' at 0x{parsed['address']:08x}, incremented address by {increment} to 0x{self.current_address:08x}")


            # Handle instructions (only estimate size for now, expansion happens later)
            elif parsed["type"] == "instruction":
                 if self.in_data_segment:
                     self._add_error(line_num, "Instructions not allowed in .data segment", parsed["original_text"])
                 else:
                     # Estimate size - assume 4 bytes unless known pseudo-op expands
                     # This estimation is less critical now, as Pass 2a recalculates accurately
                     instr_name = parsed["instruction"]
                     estimated_increment = 4
                     if instr_name in PSEUDO_INSTRUCTIONS:
                         # Rough estimate (can be refined if needed, but Pass 2a fixes it)
                         if instr_name in ['li', 'la', 'blt', 'bgt', 'ble', 'bge']:
                             estimated_increment = 8 # These often expand to 2 instructions
                         # Add estimates for other complex pseudo-ops if necessary
                     self.current_address += estimated_increment
                     logger.debug(f"Instruction '{instr_name}' at 0x{parsed['address']:08x}, estimated increment {estimated_increment}, next addr 0x{self.current_address:08x}")


            # Store the parsed line info after processing
            self.parsed_lines.append(parsed)


    def second_pass(self):
        """ Expand pseudo instructions, resolve labels, generate machine code. """
        self.machine_code = []
        final_instructions = [] # List to hold only *base* instructions after expansion
        self.current_address = self.base_text_address # Reset address for accurate calculation
        self.in_data_segment = False
        self.data_segment = bytearray() # Reset data segment

        logger.debug("Starting Second Pass...")

        # --- Pass 2a: Expand Pseudo Instructions & Calculate Final Addresses ---
        logger.debug("--- Pass 2a: Expanding Pseudo-instructions and Calculating Addresses ---")
        for parsed_line in self.parsed_lines:
            line_num = parsed_line["line_num"]
            original_text = parsed_line["original_text"]

            # Handle segment switching
            if parsed_line["type"] == "directive":
                directive = parsed_line["directive"]
                if directive == ".data":
                    if not self.in_data_segment:
                        self.in_data_segment = True
                        self.current_address = self.base_data_address
                        logger.debug(f"Pass 2a: Switched to .data at 0x{self.current_address:08x}")
                    continue # Directive itself takes no space
                elif directive == ".text":
                     if self.in_data_segment:
                        self.in_data_segment = False
                        self.current_address = self.base_text_address
                        logger.debug(f"Pass 2a: Switched to .text at 0x{self.current_address:08x}")
                     continue # Directive itself takes no space


            # Process instructions (expand if pseudo)
            if parsed_line["type"] == "instruction":
                if self.in_data_segment: continue # Skip instructions in data segment (error already logged)

                instruction_name = parsed_line["instruction"]
                expanded_base_instructions = []

                if instruction_name in PSEUDO_HANDLERS:
                    handler_func = PSEUDO_HANDLERS[instruction_name]
                    try:
                        # Pass necessary context like symbol table, current address
                        expanded = handler_func(parsed_line, self.symbol_table, self.current_address)
                        if expanded is None: # Expansion function indicated an error
                             self._add_error(line_num, f"Error expanding pseudo-instruction '{instruction_name}'", original_text)
                             expanded_base_instructions = [] # Ensure no instructions added on error
                        else:
                             expanded_base_instructions = expanded
                    except Exception as e:
                        logger.error(f"Exception during expansion of '{instruction_name}' on line {line_num}: {e}", exc_info=True)
                        self._add_error(line_num, f"Internal error expanding pseudo-instruction '{instruction_name}': {e}", original_text)
                        expanded_base_instructions = []

                elif instruction_name in R_TYPE_FUNCT or instruction_name in I_TYPE_OPCODE or instruction_name in J_TYPE_OPCODE or instruction_name == 'syscall':
                    # It's a base instruction
                    expanded_base_instructions = [parsed_line]
                else:
                    self._add_error(line_num, f"Unknown instruction: '{instruction_name}'", original_text)
                    expanded_base_instructions = []

                # Add expanded instructions to final list and assign addresses
                for i, base_instr in enumerate(expanded_base_instructions):
                    if not base_instr or self.errors: continue # Skip if expansion failed or prior errors exist for line

                    # Ensure it's marked as a base instruction type if not already
                    base_instr['type'] = 'instruction'
                    base_instr['address'] = self.current_address
                    # Propagate original line number and text for error reporting
                    base_instr['original_line_num'] = line_num
                    base_instr['original_text'] = original_text
                     # Assign original label only to the *first* expanded instruction
                    if i > 0: base_instr['label'] = None

                    final_instructions.append(base_instr)
                    self.current_address += 4 # Each base instruction is 4 bytes
                    logger.debug(f"Pass 2a: Added base instruction '{base_instr['instruction']}' at 0x{base_instr['address']:08x}, next addr 0x{self.current_address:08x} (from line {line_num})")


            # Process data directives (fill data_segment)
            elif parsed_line["type"] == "directive" and self.in_data_segment:
                 directive = parsed_line["directive"]
                 args = parsed_line["args"]
                 directive_addr = parsed_line["address"] # Address assigned in Pass 1

                 # Ensure data segment aligns with current address (handle potential gaps)
                 if directive_addr > len(self.data_segment) + self.base_data_address:
                      padding = directive_addr - (len(self.data_segment) + self.base_data_address)
                      self.data_segment.extend(bytearray(padding))
                      logger.debug(f"Pass 2a: Padded data segment by {padding} bytes to reach 0x{directive_addr:08x}")

                 if directive == ".word":
                     for val_str in args:
                         try:
                             val = int(val_str, 0)
                             # Store as 4 bytes, little-endian common for MIPS simulators
                             self.data_segment.extend(val.to_bytes(4, byteorder='little', signed=True))
                         except ValueError: self._add_error(line_num, f"Invalid value for .word: '{val_str}'", original_text)
                 elif directive == ".byte":
                      for val_str in args:
                         try:
                             val = int(val_str, 0)
                             self.data_segment.extend(val.to_bytes(1, byteorder='little', signed=True)) # Signed byte
                         except ValueError: self._add_error(line_num, f"Invalid value for .byte: '{val_str}'", original_text)
                 elif directive == ".half":
                      for val_str in args:
                         try:
                             val = int(val_str, 0)
                             self.data_segment.extend(val.to_bytes(2, byteorder='little', signed=True))
                         except ValueError: self._add_error(line_num, f"Invalid value for .half: '{val_str}'", original_text)

                 elif directive == ".asciiz":
                     if args:
                         encoded_string = args[0].encode('ascii') # Basic ASCII encoding
                         self.data_segment.extend(encoded_string)
                         self.data_segment.append(0) # Null terminator
                 elif directive == ".space":
                     if args:
                         try:
                             size = int(args[0])
                             self.data_segment.extend(bytearray(size))
                         except ValueError: pass # Error handled in Pass 1
                 elif directive == ".align":
                      if args:
                           try:
                               n = int(args[0])
                               alignment = 1 << n
                               current_offset_in_data = len(self.data_segment)
                               padding_needed = (alignment - (current_offset_in_data % alignment)) % alignment
                               self.data_segment.extend(bytearray(padding_needed))
                           except ValueError: pass # Error handled in Pass 1

                 # Update current_address based on data added
                 self.current_address = self.base_data_address + len(self.data_segment)
                 logger.debug(f"Pass 2a: Processed directive '{directive}' at 0x{directive_addr:08x}. Data segment size: {len(self.data_segment)}, next addr 0x{self.current_address:08x}")


        if self.errors:
            logger.warning("Errors detected after Pass 2a (Expansion/Addressing). Stopping assembly.")
            return # Stop if errors occurred during expansion/addressing

        # --- Pass 2b: Assemble Base Instructions ---
        logger.debug("--- Pass 2b: Assembling Base Instructions ---")
        self.machine_code = []
        for instr_details in final_instructions:
            if self.errors: break # Stop if errors detected

            line_num = instr_details["original_line_num"] # Use original line number for errors
            original_text = instr_details["original_text"]
            instr = instr_details["instruction"]
            operands = instr_details["operands"]
            address = instr_details["address"]

            machine_word = None
            encode_func = None

            # Determine encoding function based on type
            if instr in R_TYPE_FUNCT or instr == 'syscall': # Syscall is R-type format
                encode_func = self._encode_r_type
            elif instr in I_TYPE_OPCODE:
                encode_func = self._encode_i_type
            elif instr in J_TYPE_OPCODE:
                encode_func = self._encode_j_type
            else:
                 # Should not happen if Pass 2a worked correctly
                 self._add_error(line_num, f"Internal Error: Unknown instruction '{instr}' reached Pass 2b.", original_text)
                 continue

            # Call the appropriate encoding function
            try:
                machine_word = encode_func(instr_details) # Pass the whole dict
                if machine_word is None:
                     # Error should have been added by the encode function
                     logger.warning(f"Encoding failed for instruction on line {line_num}: '{original_text}'")
                     self.machine_code.append(0x00000000) # Append placeholder on error
                else:
                     self.machine_code.append(machine_word)
                     logger.debug(f"Pass 2b: Assembled 0x{machine_word:08x} for '{instr} {' '.join(operands)}' at 0x{address:08x} (from line {line_num})")
            except Exception as e:
                logger.error(f"Exception during encoding of '{instr}' on line {line_num}: {e}", exc_info=True)
                self._add_error(line_num, f"Internal error encoding instruction '{instr}': {e}", original_text)
                self.machine_code.append(0x00000000) # Placeholder on exception


    # --- Encoding Functions (Called from Pass 2b) ---

    def _resolve_label(self, label_name, current_pc, line_num, instruction_text):
        """Looks up label address, returns None on error."""
        if label_name not in self.symbol_table:
            self._add_error(line_num, f"Undefined label: '{label_name}'", instruction_text)
            return None
        return self.symbol_table[label_name]

    def _encode_r_type(self, instr_details):
        instr = instr_details["instruction"]
        operands = instr_details["operands"]
        line_num = instr_details["original_line_num"]
        original_text = instr_details["original_text"]

        funct = R_TYPE_FUNCT.get(instr)
        # Handle syscall separately as it has a fixed funct code (0x0c) but isn't usually in R_TYPE_FUNCT map
        if instr == 'syscall':
            funct = 0x0c
        elif funct is None:
            # Should not happen if called correctly
            self._add_error(line_num, f"Internal Error: Unknown R-type '{instr}' in _encode_r_type", original_text)
            return None

        expected_ops = R_TYPE_FORMATS.get(instr, [])
        if len(operands) != len(expected_ops):
            self._add_error(line_num, f"Incorrect operand count for '{instr}'. Expected {len(expected_ops)}, got {len(operands)}.", original_text)
            return None

        rd_val, rs_val, rt_val, shamt_val = 0, 0, 0, 0
        vals = {}
        has_error = False

        for i, op_type in enumerate(expected_ops):
            op_str = operands[i]
            if op_type in ["rd", "rs", "rt"]:
                reg_num = self._parse_register(op_str, line_num, original_text)
                if reg_num is None: has_error = True; break
                vals[op_type] = reg_num
            elif op_type == "shamt":
                 shamt = self._parse_immediate(op_str, line_num, original_text, bits=5, signed=False)
                 if shamt is None: has_error = True; break
                 vals[op_type] = shamt

        if has_error: return None

        rd_val = vals.get("rd", 0)
        rs_val = vals.get("rs", 0)
        rt_val = vals.get("rt", 0)
        shamt_val = vals.get("shamt", 0)

        # Format: opcode(6)=0 rs(5) rt(5) rd(5) shamt(5) funct(6)
        return (0 << 26) | (rs_val << 21) | (rt_val << 16) | (rd_val << 11) | (shamt_val << 6) | funct


    def _encode_i_type(self, instr_details):
        instr = instr_details["instruction"]
        operands = instr_details["operands"]
        line_num = instr_details["original_line_num"]
        original_text = instr_details["original_text"]
        address = instr_details["address"] # PC for this instruction

        opcode = I_TYPE_OPCODE.get(instr)
        if opcode is None:
            self._add_error(line_num, f"Internal Error: Unknown I-type '{instr}' in _encode_i_type", original_text)
            return None

        expected_ops = I_TYPE_FORMATS.get(instr, [])
        if len(operands) != len(expected_ops):
            # Special check for lw/sw missing offset: lw $t0, ($sp) is valid after parsing
            if instr in ['lw', 'sw'] and len(operands) == 2 and len(expected_ops) == 3:
                # Likely parsed as rt, rs (missing immediate offset) -> assume offset 0
                operands.insert(1, '0') # Insert offset '0'
            else:
                self._add_error(line_num, f"Incorrect operand count for '{instr}'. Expected {len(expected_ops)}, got {len(operands)}.", original_text)
                return None

        rs_val, rt_val, imm_val = 0, 0, 0
        vals = {}
        has_error = False

        for i, op_type in enumerate(expected_ops):
            op_str = operands[i]
            if op_type in ["rt", "rs"]:
                 reg_num = self._parse_register(op_str, line_num, original_text)
                 if reg_num is None: has_error = True; break
                 vals[op_type] = reg_num
            elif op_type == "imm":
                 # Determine if immediate should be signed based on instruction
                 signed_imm = instr not in ['andi', 'ori', 'xori', 'lui', 'sltiu'] # lui/logical are unsigned, addiu/slti signed
                 imm = self._parse_immediate(op_str, line_num, original_text, bits=16, signed=signed_imm)
                 if imm is None: has_error = True; break
                 vals[op_type] = imm
            elif op_type == "label": # Branch instructions
                 target_addr = self._resolve_label(op_str, address, line_num, original_text)
                 if target_addr is None: has_error = True; break
                 pc_plus_4 = address + 4
                 # Offset is relative to PC+4, measured in words (bytes/4)
                 byte_offset = target_addr - pc_plus_4
                 if byte_offset % 4 != 0:
                     self._add_error(line_num, f"Branch target address 0x{target_addr:08x} for label '{op_str}' is not word-aligned relative to PC+4 (0x{pc_plus_4:08x})", original_text)
                     has_error = True; break
                 word_offset = byte_offset >> 2

                 # Check range for 16-bit signed offset
                 if not (-(1 << 15) <= word_offset <= (1 << 15) - 1):
                     self._add_error(line_num, f"Branch target '{op_str}' (offset {word_offset}) too far for 16-bit signed relative offset.", original_text)
                     has_error = True; break
                 # Store 16-bit representation (handles negative via 2's complement)
                 vals["imm"] = word_offset & 0xFFFF
                 logger.debug(f"Branch '{instr}' to '{op_str}' (0x{target_addr:08x}) from 0x{address:08x}. Offset = ({target_addr} - {pc_plus_4}) / 4 = {word_offset}. Encoded imm = 0x{vals['imm']:04x}")


        if has_error: return None

        rs_val = vals.get("rs", 0)
        rt_val = vals.get("rt", 0)
        imm_val = vals.get("imm", 0)

        # Format: opcode(6) rs(5) rt(5) immediate(16)
        return (opcode << 26) | (rs_val << 21) | (rt_val << 16) | imm_val


    def _encode_j_type(self, instr_details):
        instr = instr_details["instruction"]
        operands = instr_details["operands"]
        line_num = instr_details["original_line_num"]
        original_text = instr_details["original_text"]
        address = instr_details["address"] # PC for this instruction

        opcode = J_TYPE_OPCODE.get(instr)
        if opcode is None:
            self._add_error(line_num, f"Internal Error: Unknown J-type '{instr}' in _encode_j_type", original_text)
            return None

        expected_ops = J_TYPE_FORMATS.get(instr, [])
        if len(operands) != len(expected_ops):
            self._add_error(line_num, f"Incorrect operand count for '{instr}'. Expected {len(expected_ops)}, got {len(operands)}.", original_text)
            return None

        target_str = operands[0]
        target_addr = None

        # Check if target is a label or an absolute address
        if target_str in self.symbol_table:
            target_addr = self.symbol_table[target_str]
        else:
            try: # Try parsing as an absolute address
                target_addr = int(target_str, 0)
            except ValueError:
                 self._add_error(line_num, f"Invalid jump target: '{target_str}' is not a label or address.", original_text)
                 return None

        # Jump target encoding: takes 26 bits of the address
        # The target address must be in the same 256MB region as the jump instruction itself.
        # The encoded address is (target_addr / 4) & 0x3FFFFFF
        if (address & 0xF0000000) != (target_addr & 0xF0000000):
            self._add_error(line_num, f"Jump target 0x{target_addr:08x} is not in the same 256MB segment as the jump instruction at 0x{address:08x}", original_text)
            # Some assemblers might allow this, but MARS/SPIM usually don't jump across segments like this
            # return None # Strict check
            logger.warning(f"Warning line {line_num}: Jump target 0x{target_addr:08x} crosses 256MB boundary from 0x{address:08x}.")

        if target_addr % 4 != 0:
            self._add_error(line_num, f"Jump target address 0x{target_addr:08x} is not word-aligned.", original_text)
            return None

        encoded_addr_part = (target_addr >> 2) & 0x03FFFFFF
        logger.debug(f"Jump '{instr}' to '{target_str}' (0x{target_addr:08x}) from 0x{address:08x}. Encoded addr part = 0x{encoded_addr_part:07x}")


        # Format: opcode(6) address(26)
        return (opcode << 26) | encoded_addr_part


    def assemble(self, assembly_code):
        """ Main method to assemble MIPS code. """
        logger.info("Starting assembly process...")
        # Clear previous state
        self.symbol_table = {}
        self.data_segment = bytearray()
        self.current_address = 0
        self.parsed_lines = []
        self.machine_code = []
        self.errors = []
        self.in_data_segment = False

        # Run Passes
        try:
            self.first_pass(assembly_code)
            if self.errors:
                logger.warning("Errors detected after first pass.")
                return {"machine_code": [], "errors": self.errors, "data_segment": ""}

            self.second_pass()
            if self.errors:
                 logger.warning("Errors detected after second pass.")
                 # Still return partial machine code if any was generated before error
                 hex_code = [f"0x{code:08x}" for code in self.machine_code]
                 hex_data = self.data_segment.hex() # Get data segment as hex string
                 return {"machine_code": hex_code, "errors": self.errors, "data_segment": hex_data}

            # Format output
            hex_code = [f"0x{code:08x}" for code in self.machine_code]
            hex_data = self.data_segment.hex()
            logger.info("Assembly successful.")
            return {"machine_code": hex_code, "errors": [], "data_segment": hex_data}

        except Exception as e:
            logger.error(f"Unexpected exception during assembly: {e}", exc_info=True)
            # Add a general error if something unexpected happened
            self._add_error(0, f"An unexpected internal error occurred during assembly: {e}", "")
            return {"machine_code": [], "errors": self.errors, "data_segment": ""}