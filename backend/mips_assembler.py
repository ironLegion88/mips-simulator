# backend/mips_assembler.py
import re
import logging
# Use absolute imports relative to backend package
from backend.mips_consts import (
    REGISTER_MAP, REGISTER_MAP_REV, R_TYPE_FUNCT, I_TYPE_OPCODE, J_TYPE_OPCODE,
    PSEUDO_INSTRUCTIONS, R_TYPE_FORMATS, I_TYPE_FORMATS, J_TYPE_FORMATS,
    PSEUDO_HANDLERS, DIRECTIVES # Assuming PSEUDO_HANDLERS dict is added to mips_consts for expansion logic functions
)

logger = logging.getLogger(__name__)
# Basic configuration if running standalone for debugging
# logging.basicConfig(level=logging.DEBUG)

class MipsAssembler:
    def __init__(self):
        self.symbol_table = {}
        self.data_segment = bytearray() # Store data segment contents
        self.current_address = 0
        self.base_text_address = 0x00400000
        self.base_data_address = 0x10010000
        self.parsed_lines = [] # Store detailed parsed info from first pass
        self.machine_code = [] # Stores generated integer machine code words
        self.errors = []
        self.in_data_segment = False

    def _add_error(self, line_num, message, instruction_text=""):
        """Adds an error, preventing duplicates for the same line/message."""
        if not any(err['line'] == line_num and err['message'] == message for err in self.errors):
             logger.debug(f"Adding error: Line {line_num}, Msg: {message}, Text: '{instruction_text}'")
             self.errors.append({"line": line_num, "message": message, "text": instruction_text})

    def _parse_register(self, reg_str, line_num, instruction_text):
        """Converts register name ($t0, $3, etc.) to its number."""
        if not reg_str:
             self._add_error(line_num, "Empty register operand.", instruction_text)
             return None
        reg_str_lower = reg_str.lower()
        if reg_str_lower not in REGISTER_MAP:
            self._add_error(line_num, f"Invalid register name: '{reg_str}'", instruction_text)
            return None
        return REGISTER_MAP[reg_str_lower]

    def _parse_immediate(self, imm_str, line_num, instruction_text, bits=16, signed=True):
        """Converts immediate string (dec/hex) to int, checks range."""
        if not imm_str:
             self._add_error(line_num, "Empty immediate value.", instruction_text)
             return None
        try:
            val = int(imm_str, 0) # Automatically handles '0x' prefix
        except ValueError:
            self._add_error(line_num, f"Invalid immediate value: '{imm_str}'", instruction_text)
            return None

        # Range checking
        if signed:
            min_val, max_val = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
            if not (min_val <= val <= max_val):
                self._add_error(line_num, f"Immediate '{imm_str}' out of range for {bits}-bit signed value ({min_val} to {max_val})", instruction_text)
                return None
            # Return the value masked to 'bits' width for encoding (handles 2's complement)
            return val & ((1 << bits) - 1)
        else: # Unsigned
            min_val, max_val = 0, (1 << bits) - 1
            if not (min_val <= val <= max_val):
                 self._add_error(line_num, f"Immediate '{imm_str}' out of range for {bits}-bit unsigned value ({min_val} to {max_val})", instruction_text)
                 return None
            return val # Already positive and within range

    def _parse_memory_operand(self, operand_str, line_num, instruction_text):
        """ Parses 'offset($register)' or '($register)'. Returns (offset_int, reg_name_str) or None, None on error. """
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
            line = label_match.group(2).strip()

        if not line: # Line could just be a label
            return {"type": "label_only", "label": label, "line_num": line_num, "original_text": original_line}

        # --- Check for Directive ---
        if line.startswith('.'):
            parts = re.split(r'\s+', line, maxsplit=1) # Use maxsplit keyword
            directive = parts[0].lower()
            args_str = parts[1] if len(parts) > 1 else ""
            args = []
            # Special handling for string arguments
            if directive in ['.asciiz', '.ascii']:
                 match_str = re.match(r'"(.*)"', args_str) # Basic quoted string
                 if match_str:
                     # Handle basic escape sequences if needed, e.g., \\, \"
                     # For simplicity now, just take the content
                     args = [match_str.group(1)]
                 else:
                     self._add_error(line_num, f"Invalid string format for {directive}: {args_str}", original_line)
            elif args_str: # For other directives like .word, .byte, .space, .globl
                args = [a.strip() for a in args_str.split(',')]
                args = [a for a in args if a] # Remove empty strings

            # Validate directive name
            if directive not in DIRECTIVES:
                 self._add_error(line_num, f"Unknown directive: '{directive}'", original_line)
                 # Still return a structure so parsing continues, but mark as invalid?
                 # Or return None here to fully ignore? Let's return structure.

            return {"type": "directive", "label": label, "directive": directive, "args": args, "line_num": line_num, "original_text": original_line}

        # --- Assume Instruction ---
        parts = re.split(r'\s+', line, maxsplit=1) # Use maxsplit keyword
        instruction = parts[0].lower()
        operands_str = parts[1] if len(parts) > 1 else ""

        # Split operands by comma, trim whitespace
        operands = [op.strip() for op in operands_str.split(',')]
        operands = [op for op in operands if op] # Remove empty strings

        # Check for instructions that use memory format 'offset($reg)' and pre-parse if applicable
        is_memory_op = instruction in ['lw', 'sw', 'lb', 'sb', 'lh', 'sh', 'lbu', 'lhu', 'lwl', 'lwr', 'swl', 'swr'] # Add others like lwl, lwr etc.
        parsed_operands = []

        if is_memory_op and len(operands) == 2:
             # Expects rt, offset($rs) format potentially
             reg_op = operands[0]
             mem_op_str = operands[1]
             offset, base_reg = self._parse_memory_operand(mem_op_str, line_num, original_line)
             if base_reg is not None: # Successfully parsed memory format
                 # Standardize order: rt, imm, rs (imm is the offset)
                 parsed_operands = [reg_op, str(offset), base_reg]
             else:
                 # Error added by _parse_memory_operand. Treat as format error below.
                 parsed_operands = operands # Use original for operand count check
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
        """ Pass 1: Build symbol table, parse lines, handle basic directives for address calculation. """
        self.symbol_table = {}
        self.parsed_lines = []
        self.errors = []
        self.current_address = self.base_text_address # Start in .text
        self.in_data_segment = False
        lines = assembly_code.splitlines()
        current_segment_base = self.base_text_address

        logger.debug("--- Starting First Pass ---")
        for i, line in enumerate(lines):
            line_num = i + 1
            parsed = self._parse_line(line, line_num)
            if not parsed: continue

            # Assign current address *before* potentially modifying it for the current item
            parsed["address"] = self.current_address
            original_text = parsed["original_text"] # Cache for logging/errors

            if parsed.get("label"):
                label = parsed["label"]
                if label in self.symbol_table:
                    self._add_error(line_num, f"Duplicate label definition: {label}", original_text)
                else:
                    # Ensure label doesn't conflict with instruction names etc. (optional check)
                    self.symbol_table[label] = self.current_address
                    logger.debug(f"Pass 1: Label '{label}' defined at address 0x{self.current_address:08x}")

            # Handle segment switching first
            if parsed["type"] == "directive":
                directive = parsed["directive"]
                if directive == ".data":
                    if not self.in_data_segment:
                        self.in_data_segment = True
                        # Align data segment start? Often defaults to 0x10010000
                        self.current_address = self.base_data_address
                        current_segment_base = self.base_data_address
                        logger.debug(f"Pass 1: Switched to .data segment at 0x{self.current_address:08x}")
                    # Store the parsed line even if it's just the directive
                    self.parsed_lines.append(parsed)
                    continue # Directive itself takes no space

                elif directive == ".text":
                     if self.in_data_segment:
                        self.in_data_segment = False
                        # Align text segment start? Often defaults to 0x00400000
                        self.current_address = self.base_text_address
                        current_segment_base = self.base_text_address
                        logger.debug(f"Pass 1: Switched to .text segment at 0x{self.current_address:08x}")
                     # Store the parsed line even if it's just the directive
                     self.parsed_lines.append(parsed)
                     continue # Directive itself takes no space

            # Handle directives that allocate space/data OR declare symbols
            if parsed["type"] == "directive":
                 directive = parsed["directive"]
                 args = parsed["args"]
                 increment = 0

                 # --- Handle Symbol Declaration Directives ---
                 if directive in [".globl", ".extern"]:
                     if not args:
                         self._add_error(line_num, f"Directive '{directive}' requires at least one symbol argument", original_text)
                     else:
                         logger.debug(f"Pass 1: Parsed '{directive}' for symbols: {', '.join(args)}")
                     # These directives do not take space or change the current address
                     self.parsed_lines.append(parsed) # Store parsed line
                     continue # Move to next line

                 # --- Handle Data Allocation/Alignment Directives ---
                 if not self.in_data_segment:
                      # Only allow these directives in .data segment
                      self._add_error(line_num, f"Directive '{directive}' only allowed in .data segment", original_text)
                      self.parsed_lines.append(parsed) # Store parsed line anyway
                      continue

                 elif directive == ".word":
                     increment = len(args) * 4
                 elif directive == ".byte":
                     increment = len(args) * 1
                 elif directive == ".half":
                     increment = len(args) * 2
                 elif directive == ".space":
                     if len(args) == 1:
                         try: increment = int(args[0])
                         except ValueError: self._add_error(line_num, f"Invalid size for .space: {args[0]}", original_text)
                     else: self._add_error(line_num, ".space expects one argument (size in bytes)", original_text)
                 elif directive == ".asciiz":
                     if len(args) == 1: increment = len(args[0].encode('ascii', 'ignore')) + 1 # String length + null terminator
                     else: self._add_error(line_num, ".asciiz expects one string argument", original_text)
                 elif directive == ".ascii": # Not null-terminated
                     if len(args) == 1: increment = len(args[0].encode('ascii', 'ignore'))
                     else: self._add_error(line_num, ".ascii expects one string argument", original_text)
                 elif directive == ".align":
                     if len(args) == 1:
                         try:
                             n = int(args[0])
                             if n < 0 or (1 << n) > 16384: raise ValueError("Alignment must be power of 2 (0-14)")
                             alignment = 1 << n
                             offset = self.current_address % alignment
                             if offset != 0: increment = alignment - offset
                         except ValueError: self._add_error(line_num, f"Invalid alignment value for .align: {args[0]} (must be 0-14)", original_text)
                     else: self._add_error(line_num, ".align expects one argument (power of 2 exponent)", original_text)
                 elif directive not in DIRECTIVES:
                     # Error for unknown directive added during parsing, just skip here
                     pass
                 # Add other directives (.float, .double) if needed

                 self.current_address += increment
                 logger.debug(f"Pass 1: Directive '{directive}' at 0x{parsed['address']:08x}, incremented address by {increment} to 0x{self.current_address:08x}")


            # Handle instructions (only estimate size for now, expansion happens later)
            elif parsed["type"] == "instruction":
                 if self.in_data_segment:
                     self._add_error(line_num, "Instructions not allowed in .data segment", original_text)
                 else:
                     # Estimate size - assume 4 bytes unless known pseudo-op expands
                     instr_name = parsed["instruction"]
                     estimated_increment = 4
                     if instr_name in PSEUDO_INSTRUCTIONS:
                         handler_key = PSEUDO_INSTRUCTIONS[instr_name]
                         # Refine estimate based on known expansions
                         if handler_key in ['_expand_li', '_expand_la', '_expand_blt', '_expand_bgt', '_expand_ble', '_expand_bge']:
                             estimated_increment = 8 # These often expand to 2 instructions
                         elif handler_key == '_expand_nop':
                              estimated_increment = 4 # Nop is 1 instruction
                         # Add estimates for other complex pseudo-ops if necessary
                     self.current_address += estimated_increment
                     logger.debug(f"Pass 1: Instruction '{instr_name}' at 0x{parsed['address']:08x}, estimated increment {estimated_increment}, next addr 0x{self.current_address:08x}")


            # Store the parsed line info after processing (ensure this is done for all valid parsed types)
            self.parsed_lines.append(parsed)
        logger.debug("--- First Pass Complete ---")


    def second_pass(self):
        """ Pass 2: Expand pseudo instructions, resolve labels, generate machine code and data segment. """
        final_instructions = [] # List to hold only *base* instructions after expansion
        self.machine_code = [] # Reset machine code list (stores integers)
        self.data_segment = bytearray() # Reset data segment
        self.current_address = self.base_text_address # Reset address for accurate calculation
        self.in_data_segment = False

        logger.debug("--- Starting Second Pass ---")

        # --- Pass 2a: Expand Pseudo Instructions, Calculate Final Addresses, Build Data Segment ---
        logger.debug("--- Pass 2a: Expanding Pseudo-instructions, Calculating Addresses, Building Data ---")
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
                        self.current_address = self.base_text_address # Or last known text address? Use base for simplicity.
                        logger.debug(f"Pass 2a: Switched to .text at 0x{self.current_address:08x}")
                     continue # Directive itself takes no space

            # Process instructions (expand if pseudo) in .text segment
            if parsed_line["type"] == "instruction" and not self.in_data_segment:
                instruction_name = parsed_line["instruction"]
                expanded_base_instructions = []

                # Check if it's a pseudo-instruction first
                if instruction_name in PSEUDO_INSTRUCTIONS:
                    handler_key = PSEUDO_INSTRUCTIONS[instruction_name]
                    handler_func = PSEUDO_HANDLERS.get(handler_key)

                    if handler_func:
                        try:
                            parsed_line_with_context = {**parsed_line, "original_text": original_text, "line_num": line_num}
                            expanded = handler_func(parsed_line_with_context, self.symbol_table, self.current_address)

                            if expanded is None:
                                # Assume handler already added error if needed
                                logger.warning(f"Pass 2a: Expansion failed for '{instruction_name}' on line {line_num}")
                                expanded_base_instructions = []
                            else:
                                expanded_base_instructions = expanded if isinstance(expanded, list) else [expanded]
                        except Exception as e:
                            logger.error(f"Exception during expansion of '{instruction_name}' on line {line_num}: {e}", exc_info=True)
                            self._add_error(line_num, f"Internal error expanding pseudo-instruction '{instruction_name}': {e}", original_text)
                            expanded_base_instructions = []
                    else:
                        self._add_error(line_num, f"Internal Error: No handler found for pseudo-instruction key '{handler_key}'", original_text)
                        expanded_base_instructions = []

                # Check if it's a known base instruction or syscall
                elif instruction_name in R_TYPE_FUNCT or instruction_name in I_TYPE_OPCODE or instruction_name in J_TYPE_OPCODE:
                    expanded_base_instructions = [parsed_line]
                # Check unknown instructions (error added in Pass 1 or here if missed)
                else:
                    if not any(e['line'] == line_num and e['message'].startswith("Unknown instruction") for e in self.errors):
                         self._add_error(line_num, f"Unknown instruction: '{instruction_name}'", original_text)
                    expanded_base_instructions = []

                # Add expanded instructions to final list and assign addresses
                for i, base_instr in enumerate(expanded_base_instructions):
                    if not base_instr or self.errors: continue

                    base_instr['type'] = 'instruction' # Ensure type is correct
                    base_instr['address'] = self.current_address
                    base_instr['original_line_num'] = line_num # Keep track for errors
                    base_instr['original_text'] = original_text # Keep track for errors
                    if i > 0: base_instr['label'] = None # Label only applies to first expanded instruction

                    final_instructions.append(base_instr)
                    self.current_address += 4 # Each base instruction is 4 bytes
                    logger.debug(f"Pass 2a: Added base instruction '{base_instr['instruction']}' at 0x{base_instr['address']:08x}, next addr 0x{self.current_address:08x} (from line {line_num})")

            # Process data directives (fill data_segment) in .data segment
            elif parsed_line["type"] == "directive" and self.in_data_segment:
                 directive = parsed_line["directive"]
                 args = parsed_line["args"]
                 directive_addr = parsed_line["address"] # Address assigned in Pass 1

                 # Ensure data segment aligns with current address (handle potential gaps from .align in pass 1)
                 current_data_offset = len(self.data_segment)
                 expected_data_offset = directive_addr - self.base_data_address
                 if current_data_offset < expected_data_offset:
                      padding = expected_data_offset - current_data_offset
                      self.data_segment.extend(bytearray(padding))
                      logger.debug(f"Pass 2a: Padded data segment by {padding} bytes to reach 0x{directive_addr:08x}")
                 elif current_data_offset > expected_data_offset:
                      # This indicates an overlap or error in Pass 1 address calculation
                      self._add_error(line_num, f"Internal Error: Data address mismatch. Expected 0x{expected_data_offset:08x}, current offset is {current_data_offset}", original_text)
                      continue # Skip processing this directive

                 # Append data based on directive type
                 if directive == ".word":
                     for val_str in args:
                         try:
                             val = int(val_str, 0)
                             # Store as 4 bytes, handle endianness (e.g., little)
                             self.data_segment.extend(val.to_bytes(4, byteorder='little', signed=True)) # Use signed=True? Depends on MIPS spec/target
                         except ValueError: self._add_error(line_num, f"Invalid value for .word: '{val_str}'", original_text)
                 elif directive == ".byte":
                      for val_str in args:
                         try:
                             val = int(val_str, 0)
                             # MIPS bytes are often treated signed range (-128 to 127)
                             self.data_segment.extend(val.to_bytes(1, byteorder='little', signed=True))
                         except ValueError: self._add_error(line_num, f"Invalid value for .byte: '{val_str}'", original_text)
                         except OverflowError: self._add_error(line_num, f"Value '{val_str}' out of range for .byte", original_text)
                 elif directive == ".half":
                      for val_str in args:
                         try:
                             val = int(val_str, 0)
                             self.data_segment.extend(val.to_bytes(2, byteorder='little', signed=True))
                         except ValueError: self._add_error(line_num, f"Invalid value for .half: '{val_str}'", original_text)
                         except OverflowError: self._add_error(line_num, f"Value '{val_str}' out of range for .half", original_text)

                 elif directive == ".asciiz":
                     if args:
                         try:
                             encoded_string = args[0].encode('ascii') # Basic ASCII encoding
                             self.data_segment.extend(encoded_string)
                             self.data_segment.append(0) # Null terminator
                         except UnicodeEncodeError: self._add_error(line_num, f"Non-ASCII character in .asciiz string: {args[0]}", original_text)
                 elif directive == ".ascii":
                      if args:
                         try:
                             encoded_string = args[0].encode('ascii')
                             self.data_segment.extend(encoded_string)
                         except UnicodeEncodeError: self._add_error(line_num, f"Non-ASCII character in .ascii string: {args[0]}", original_text)

                 elif directive == ".space": # Already handled by address increment in Pass 1, just ensure padding
                      try:
                          size = int(args[0]) if args else 0
                          if size < 0: raise ValueError
                          # Padding added above based on address difference
                          logger.debug(f"Pass 2a: .space directive reserved {size} bytes implicitly.")
                      except ValueError: pass # Error handled in Pass 1

                 elif directive == ".align": # Also handled by address increment, ensure padding
                      # Padding added above based on address difference
                      logger.debug(f"Pass 2a: .align directive handled by address calculation.")

                 # Update current_address based on actual data appended (redundant if padding logic is correct)
                 # self.current_address = self.base_data_address + len(self.data_segment)
                 # logger.debug(f"Pass 2a: Processed directive '{directive}' at 0x{directive_addr:08x}. Data segment size: {len(self.data_segment)}, next data addr 0x{self.current_address:08x}")


        if self.errors:
            logger.warning("Errors detected after Pass 2a (Expansion/Addressing/Data Gen). Stopping assembly.")
            return # Stop if errors occurred

        # --- Pass 2b: Assemble Base Instructions ---
        logger.debug("--- Pass 2b: Assembling Base Instructions ---")
        self.machine_code = [] # Ensure it's clear before starting
        for instr_details in final_instructions:
            if self.errors: break # Stop if errors detected

            line_num = instr_details["original_line_num"]
            original_text = instr_details["original_text"]
            instr = instr_details["instruction"]
            operands = instr_details["operands"]
            address = instr_details["address"]

            machine_word = None
            encode_func = None

            # Determine encoding function based on type
            if instr in R_TYPE_FUNCT:
                encode_func = self._encode_r_type
            elif instr in I_TYPE_OPCODE:
                encode_func = self._encode_i_type
            elif instr in J_TYPE_OPCODE:
                encode_func = self._encode_j_type
            else:
                 self._add_error(line_num, f"Internal Error: Unknown instruction '{instr}' reached Pass 2b.", original_text)
                 continue

            # Call the appropriate encoding function
            try:
                machine_word = encode_func(instr_details) # Pass the whole dict
                if machine_word is None:
                     logger.warning(f"Encoding failed for instruction on line {line_num}: '{original_text}'")
                     # Error should have been added by the encode function
                     # Append placeholder only if we want partial output despite errors
                     # self.machine_code.append(0x00000000)
                     # For now, let's stop adding code if an error occurs in encoding
                     break # Stop processing further instructions on encoding error
                else:
                     self.machine_code.append(machine_word) # Add integer code
                     logger.debug(f"Pass 2b: Assembled 0x{machine_word:08x} for '{instr} {' '.join(operands)}' at 0x{address:08x} (from line {line_num})")
            except Exception as e:
                logger.error(f"Exception during encoding of '{instr}' on line {line_num}: {e}", exc_info=True)
                self._add_error(line_num, f"Internal error encoding instruction '{instr}': {e}", original_text)
                # self.machine_code.append(0x00000000) # Placeholder on exception
                break # Stop processing further instructions on exception


    def _resolve_label(self, label_name, current_pc, line_num, instruction_text):
        """Looks up label address, returns address integer or None on error."""
        if label_name not in self.symbol_table:
            self._add_error(line_num, f"Undefined label: '{label_name}'", instruction_text)
            return None
        return self.symbol_table[label_name]

    def _encode_r_type(self, instr_details):
        """Encodes R-type instruction, returning integer machine code or None on error."""
        instr = instr_details["instruction"]
        operands = instr_details["operands"]
        line_num = instr_details["original_line_num"]
        original_text = instr_details["original_text"]

        # Handle syscall/break which have fixed funct codes
        if instr == 'syscall': funct = 0x0c
        elif instr == 'break': funct = 0x0d
        else: funct = R_TYPE_FUNCT.get(instr)

        if funct is None:
            self._add_error(line_num, f"Internal Error: Unknown R-type '{instr}' in _encode_r_type", original_text)
            return None

        expected_ops = R_TYPE_FORMATS.get(instr, [])
        actual_ops_count = len(operands)
        rd_val, rs_val, rt_val, shamt_val = 0, 0, 0, 0

        # --- Special handling for jalr optional rd ---
        if instr == 'jalr':
            if actual_ops_count == 1: # Only rs provided, rd defaults to $ra (31)
                rs_op = operands[0]
                rd_val = 31 # Default $ra
                rs_val = self._parse_register(rs_op, line_num, original_text)
                if rs_val is None: return None
            elif actual_ops_count == 2: # Both rd, rs provided
                rd_op, rs_op = operands
                rd_val = self._parse_register(rd_op, line_num, original_text)
                rs_val = self._parse_register(rs_op, line_num, original_text)
                if rd_val is None or rs_val is None: return None
            else:
                self._add_error(line_num, f"Incorrect operand count for '{instr}'. Expected 1 or 2, got {actual_ops_count}.", original_text)
                return None
            # jalr uses rt=0, shamt=0 implicitly
        # --- Standard R-type operand parsing ---
        else:
            if actual_ops_count != len(expected_ops):
                # Handle instructions with no operands like syscall, break
                if not expected_ops and actual_ops_count == 0:
                    pass # Correct, no operands needed or parsed
                else:
                    self._add_error(line_num, f"Incorrect operand count for '{instr}'. Expected {len(expected_ops)}, got {actual_ops_count}.", original_text)
                    return None

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
        """Encodes I-type instruction, returning integer machine code or None on error."""
        instr = instr_details["instruction"]
        operands = instr_details["operands"]
        line_num = instr_details["original_line_num"]
        original_text = instr_details["original_text"]
        address = instr_details["address"]

        opcode = I_TYPE_OPCODE.get(instr)
        if opcode is None:
            self._add_error(line_num, f"Internal Error: Unknown I-type '{instr}' in _encode_i_type", original_text)
            return None

        expected_ops = I_TYPE_FORMATS.get(instr, [])
        actual_ops_count = len(operands)

        # Simple operand count check first
        if actual_ops_count != len(expected_ops):
            # Check for memory ops parsed into rt, imm, rs format already
            if instr in ['lw', 'sw', 'lb', 'sb', 'lh', 'sh', 'lbu', 'lhu'] and len(expected_ops) == 3 and actual_ops_count > 0:
                 # Assume parsing put rt, imm, rs into operands correctly earlier
                 pass # Allow processing
            else:
                 self._add_error(line_num, f"Incorrect operand count for '{instr}'. Expected {len(expected_ops)}, got {actual_ops_count}.", original_text)
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
                 # lui, andi, ori, xori, sltiu are unsigned
                 signed_imm = instr not in ['andi', 'ori', 'xori', 'lui', 'sltiu']
                 imm = self._parse_immediate(op_str, line_num, original_text, bits=16, signed=signed_imm)
                 if imm is None: has_error = True; break
                 vals[op_type] = imm
            elif op_type == "label": # Branch/REGIMM instructions
                 target_addr = self._resolve_label(op_str, address, line_num, original_text)
                 if target_addr is None: has_error = True; break
                 pc_plus_4 = address + 4
                 byte_offset = target_addr - pc_plus_4
                 if byte_offset % 4 != 0:
                     self._add_error(line_num, f"Branch target address 0x{target_addr:08x} for label '{op_str}' is not word-aligned relative to PC+4 (0x{pc_plus_4:08x})", original_text)
                     has_error = True; break
                 word_offset = byte_offset >> 2
                 if not (-(1 << 15) <= word_offset <= (1 << 15) - 1):
                     self._add_error(line_num, f"Branch target '{op_str}' (offset {word_offset}) too far for 16-bit signed relative offset.", original_text)
                     has_error = True; break
                 vals["imm"] = word_offset & 0xFFFF # Get 16-bit representation
                 logger.debug(f"Branch '{instr}' to '{op_str}' (0x{target_addr:08x}) from 0x{address:08x}. Offset = ({target_addr} - {pc_plus_4}) / 4 = {word_offset}. Encoded imm = 0x{vals['imm']:04x}")

        if has_error: return None

        # Assign parsed values, handling defaults
        rs_val = vals.get("rs", 0)
        rt_val = vals.get("rt", 0) # Default rt for non-REGIMM
        imm_val = vals.get("imm", 0)

        # --- Special handling for REGIMM (opcode 0x1) ---
        # These use the 'rt' field to differentiate the instruction variant
        if opcode == 0x1:
            if instr == 'bltz': rt_val = 0x00
            elif instr == 'bgez': rt_val = 0x01
            elif instr == 'bltzal': rt_val = 0x10
            elif instr == 'bgezal': rt_val = 0x11
            else:
                 self._add_error(line_num, f"Internal Error: Unknown REGIMM instruction '{instr}'", original_text)
                 return None
            logger.debug(f"REGIMM instruction '{instr}' setting rt field to 0x{rt_val:02x}")
        # --- End REGIMM handling ---

        # --- Special handling for branch instructions using rt=0 but not REGIMM ---
        elif instr in ['blez', 'bgtz']:
             rt_val = 0 # These instructions require rt field to be 0
             logger.debug(f"Branch instruction '{instr}' setting rt field to 0")


        # Format: opcode(6) rs(5) rt(5) immediate(16)
        return (opcode << 26) | (rs_val << 21) | (rt_val << 16) | imm_val


    def _encode_j_type(self, instr_details):
        """Encodes J-type instruction, returning integer machine code or None on error."""
        instr = instr_details["instruction"]
        operands = instr_details["operands"]
        line_num = instr_details["original_line_num"]
        original_text = instr_details["original_text"]
        address = instr_details["address"]

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
                 self._add_error(line_num, f"Invalid jump target: '{target_str}' is not a defined label or a valid address.", original_text)
                 return None

        # Jump target encoding: uses lower 28 bits of target address, shifted right by 2
        # Check alignment
        if target_addr % 4 != 0:
            self._add_error(line_num, f"Jump target address 0x{target_addr:08x} is not word-aligned.", original_text)
            return None

        # Check if target is in the same 256MB segment (optional, but good practice)
        if (address & 0xF0000000) != (target_addr & 0xF0000000):
            logger.warning(f"Warning line {line_num}: Jump target 0x{target_addr:08x} crosses 256MB boundary from 0x{address:08x}.")
            # Some assemblers might error here, we'll allow it with a warning

        encoded_addr_part = (target_addr >> 2) & 0x03FFFFFF # Mask to 26 bits
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
        self.machine_code = [] # Stores integer words
        self.errors = []
        self.in_data_segment = False

        # Run Passes
        try:
            self.first_pass(assembly_code)
            # Don't stop completely on first pass errors, Pass 2 might find more useful context
            # if self.errors: return {"machine_code": [], "errors": self.errors, "data_segment": ""}

            self.second_pass()
            # Errors might have occurred in Pass 1 or Pass 2

        except Exception as e:
            logger.error(f"Unexpected exception during assembly: {e}", exc_info=True)
            self._add_error(0, f"An unexpected internal error occurred during assembly: {e}", "")
            # Fall through to return errors

        # Format output regardless of errors (might have partial results)
        formatted_output = []
        for code in self.machine_code: # Iterate over generated integer codes
             formatted_output.append({
                 "hex": f"0x{code:08x}",
                 "bin": f"{code:032b}",
                 "dec": str(code) # Unsigned decimal representation
             })

        hex_data = self.data_segment.hex()

        if self.errors:
             logger.warning(f"Assembly completed with {len(self.errors)} errors.")
        else:
             logger.info("Assembly successful.")

        return {"machine_code": formatted_output, "errors": self.errors, "data_segment": hex_data}