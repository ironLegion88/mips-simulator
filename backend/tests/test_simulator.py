# backend/tests/test_simulator.py
import pytest
from backend.mips_simulator import MipsSimulator, TEXT_START, DATA_START, STACK_START
import struct # Needed for signed conversion helper

# --- Helper Functions for Tests ---

def load_test_code(simulator, code_hex_list, data_hex=""):
    """Loads hex code (list of strings) and data (hex string) into the simulator instance."""
    # Ensure input code is list of hex strings
    code_hex_strings = [item['hex'] if isinstance(item, dict) else item for item in code_hex_list]
    success = simulator.load_program(code_hex_strings, data_hex)
    assert success, f"Simulator failed to load program. Error: {simulator.error_message}"
    return simulator

def to_signed_32(unsigned_val):
    """Converts a 32-bit unsigned value (0 to 0xFFFFFFFF) to its signed equivalent."""
    # Ensure value is within unsigned 32-bit range before proceeding
    unsigned_val &= 0xFFFFFFFF
    if unsigned_val >= (1 << 31): # Check if sign bit is set
        # Calculate two's complement negative value
        return unsigned_val - (1 << 32)
    else:
        return unsigned_val

# --- Test Fixture ---

@pytest.fixture
def simulator():
    """Provides a new MipsSimulator instance for each test."""
    return MipsSimulator()

# --- Test Loading ---

def test_load_program_initial_state(simulator):
    """Tests the initial state after loading a simple program."""
    code = [
        "0x24020005", # addiu $v0, $zero, 5
        "0x0000000c"  # syscall
    ]
    data = "0a000000" # data = 10 (word) at 0x10010000

    load_test_code(simulator, code, data)

    state = simulator.get_state()
    assert state["pc"] == TEXT_START, "PC should start at text base"
    assert state["registers"][0] == 0, "$zero should always be 0"
    assert state["registers"][29] == STACK_START, "$sp should be initialized"
    # Check that other registers are initially zero
    assert all(reg == 0 for i, reg in enumerate(state["registers"]) if i not in [0, 29]), "Other GPRs should be 0 initially"
    assert state["state"] == "loaded", "Simulator state should be 'loaded'"
    assert state["error"] is None, "There should be no initial error"
    # Check if data loaded correctly into memory
    assert simulator.read_memory(DATA_START, 4) == 10, "Data segment value mismatch"

def test_load_program_empty(simulator):
     """Tests loading with no code or data."""
     load_test_code(simulator, [], "")
     state = simulator.get_state()
     assert state["pc"] == TEXT_START, "PC should still initialize"
     assert state["state"] == "loaded", "State should be loaded even if empty"
     assert not simulator.instructions, "Instruction list should be empty"
     assert not simulator.data_segment, "Data segment should be empty"
     assert simulator.program_break == DATA_START, "Program break should be at data start"


# --- Test Memory Access ---

def test_memory_read_write_word(simulator):
    """Tests writing and reading a 32-bit word (signed)."""
    addr = 0x10010020
    value_pos = 0x1234abcd
    value_neg_pattern = 0xdeadbeef # Represents a negative number in 2's complement
    value_neg = to_signed_32(value_neg_pattern) # The actual negative value

    # Test positive value
    assert simulator.write_memory(addr, value_pos, 4) == True, "Write positive word failed"
    read_val = simulator.read_memory(addr, 4)
    assert read_val == value_pos, "Read positive word mismatch"
    # Check internal byte representation (little endian)
    assert simulator.memory[addr] == 0xcd
    assert simulator.memory[addr+1] == 0xab
    assert simulator.memory[addr+2] == 0x34
    assert simulator.memory[addr+3] == 0x12

    # Test negative value
    addr_neg = 0x10010024
    assert simulator.write_memory(addr_neg, value_neg, 4) == True, f"Write negative word ({value_neg}) failed"
    read_val_neg = simulator.read_memory(addr_neg, 4)
    assert read_val_neg == value_neg, f"Read negative word mismatch (expected {value_neg}, got {read_val_neg})"
    # Check internal byte representation (little endian for 0xdeadbeef)
    assert simulator.memory[addr_neg] == 0xef
    assert simulator.memory[addr_neg+1] == 0xbe
    assert simulator.memory[addr_neg+2] == 0xad
    assert simulator.memory[addr_neg+3] == 0xde


def test_memory_read_write_byte(simulator):
    """Tests writing and reading signed/unsigned bytes."""
    addr = 0x10010030
    value_neg = -10 # Signed byte requires -128 to 127. Represents 0xf6.
    value_pos = 120 # Signed byte 0x78

    # Test negative byte write/read
    assert simulator.write_memory(addr, value_neg, 1) == True, "Write negative byte failed"
    read_val_signed = simulator.read_memory(addr, 1) # Reads as signed byte ('lb')
    assert read_val_signed == -10, "Signed read of negative byte failed"
    read_val_unsigned = simulator.read_memory_unsigned(addr, 1) # Reads as unsigned byte ('lbu')
    assert read_val_unsigned == 0xf6, "Unsigned read of negative byte failed"
    assert simulator.memory[addr] == 0xf6, "Internal memory value check failed (neg byte)"

    # Test positive byte write/read
    addr_pos = 0x10010031
    assert simulator.write_memory(addr_pos, value_pos, 1) == True, "Write positive byte failed"
    read_val_signed_pos = simulator.read_memory(addr_pos, 1)
    assert read_val_signed_pos == 120, "Signed read of positive byte failed"
    read_val_unsigned_pos = simulator.read_memory_unsigned(addr_pos, 1)
    assert read_val_unsigned_pos == 120, "Unsigned read of positive byte failed"
    assert simulator.memory[addr_pos] == 0x78, "Internal memory value check failed (pos byte)"

    # Test byte write out of range
    assert simulator.write_memory(addr, 200, 1) == False, "Write out-of-range byte should fail"
    assert simulator.state == "error"
    assert "out of range for 1 byte(s)" in simulator.error_message


def test_memory_read_write_half(simulator):
    """Tests writing and reading signed/unsigned half-words."""
    addr = 0x10010034
    value_neg = -2000 # Signed half requires -32768 to 32767. Represents 0xf830.
    value_pos = 15000 # Signed half 0x3a98

    # Test negative half write/read
    assert simulator.write_memory(addr, value_neg, 2) == True, "Write negative half failed"
    read_val_signed = simulator.read_memory(addr, 2) # Reads as signed half ('lh')
    assert read_val_signed == -2000, "Signed read of negative half failed"
    read_val_unsigned = simulator.read_memory_unsigned(addr, 2) # Reads as unsigned half ('lhu')
    assert read_val_unsigned == 0xf830, "Unsigned read of negative half failed"
    assert simulator.memory[addr] == 0x30, "Internal memory low byte check failed (neg half)" # Little Endian
    assert simulator.memory[addr+1] == 0xf8, "Internal memory high byte check failed (neg half)"

    # Test positive half write/read
    addr_pos = 0x10010036
    assert simulator.write_memory(addr_pos, value_pos, 2) == True, "Write positive half failed"
    read_val_signed_pos = simulator.read_memory(addr_pos, 2)
    assert read_val_signed_pos == 15000, "Signed read of positive half failed"
    read_val_unsigned_pos = simulator.read_memory_unsigned(addr_pos, 2)
    assert read_val_unsigned_pos == 15000, "Unsigned read of positive half failed"
    assert simulator.memory[addr_pos] == 0x98, "Internal memory low byte check failed (pos half)" # Little Endian
    assert simulator.memory[addr_pos+1] == 0x3a, "Internal memory high byte check failed (pos half)"

    # Test half write out of range
    assert simulator.write_memory(addr, 40000, 2) == False, "Write out-of-range half should fail"
    assert simulator.state == "error"
    assert "out of range for 2 byte(s)" in simulator.error_message


def test_memory_alignment_error(simulator):
     """Tests detection of unaligned memory access for word and half-word."""
     # Write word aligned - should succeed
     assert simulator.write_memory(0x10010040, 123, 4) == True, "Aligned word write failed"

     # Read word unaligned - should fail
     read_val = simulator.read_memory(0x10010041, 4)
     assert simulator.state == "error", "Simulator state should be 'error' after unaligned read"
     assert "Unaligned memory read" in simulator.error_message, "Incorrect error message for unaligned read"
     assert read_val == 0, "Should return 0 on read error"

     simulator.reset() # Reset error state for next test

     # Write word unaligned - should fail
     assert simulator.write_memory(0x10010042, 456, 4) == False, "Unaligned write should return False"
     assert simulator.state == "error", "Simulator state should be 'error' after unaligned write"
     assert "Unaligned memory write" in simulator.error_message, "Incorrect error message for unaligned write"

     simulator.reset() # Reset error state for next test

     # Test half-word alignment
     assert simulator.write_memory(0x10010050, 100, 2) == True, "Aligned half write failed"
     assert simulator.read_memory(0x10010051, 2) == 0, "Unaligned half read should return 0"
     assert simulator.state == "error", "State not set to error after unaligned half read"
     assert "Unaligned memory read" in simulator.error_message, "Incorrect error message for unaligned half read"

     simulator.reset()
     assert simulator.write_memory(0x10010051, 200, 2) == False, "Unaligned half write should return False"
     assert simulator.state == "error", "State not set to error after unaligned half write"
     assert "Unaligned memory write" in simulator.error_message, "Incorrect error message for unaligned half write"


# --- Test Basic Instruction Execution ---

def test_step_addiu(simulator):
    """Tests the ADDIU instruction with a positive immediate."""
    # addiu $t0 ($8), $zero ($0), 100 (0x64) -> 0x24080064
    load_test_code(simulator, ["0x24080064"])
    state = simulator.step()
    assert state["state"] == "paused", "State should be paused after step"
    assert state["pc"] == TEXT_START + 4, "PC should advance by 4"
    assert state["registers"][8] == 100, "$t0 should be 100"
    assert state["error"] is None, "No error should occur"

def test_step_addiu_negative(simulator):
    """Tests ADDIU with a negative immediate."""
    # addiu $t1 ($9), $zero ($0), -5 (imm = 0xfffb) -> 0x2409fffb
    load_test_code(simulator, ["0x2409fffb"])
    state = simulator.step()
    assert state["state"] == "paused", "State should be paused after step"
    assert state["pc"] == TEXT_START + 4, "PC should advance by 4"
    # Check the signed interpretation of the result in the register
    assert to_signed_32(state["registers"][9]) == -5, "$t1 should represent -5"
    assert state["error"] is None, "No error should occur"

def test_step_addu(simulator):
    """Tests the ADDU instruction."""
    # addu $t2 ($10), $t0 ($8), $t1 ($9) -> 0x01095021
    sim = load_test_code(simulator, ["0x01095021"])
    # Pre-load registers
    sim.registers[8] = 5 # $t0
    sim.registers[9] = 7 # $t1
    state = sim.step()
    assert state["state"] == "paused", "State should be paused after step"
    assert state["pc"] == TEXT_START + 4, "PC should advance by 4"
    assert state["registers"][10] == 12, "$t2 should be 5 + 7 = 12"
    assert state["error"] is None, "No error should occur"

def test_step_lui_ori(simulator):
    """Tests a LUI followed by ORI to load a 32-bit immediate."""
    # lui $t0 ($8), 0x1234 -> 0x3c081234
    # ori $t0 ($8), $t0 ($8), 0x5678 -> 0x35085678
    load_test_code(simulator, ["0x3c081234", "0x35085678"])

    # Step 1: Execute lui
    state = simulator.step()
    assert state["state"] == "paused", "State should be paused after LUI"
    assert state["pc"] == TEXT_START + 4, "PC should advance after LUI"
    assert state["registers"][8] == 0x12340000, "$t0 should hold upper bits after LUI"
    assert state["error"] is None, "No error after LUI"

    # Step 2: Execute ori
    state = simulator.step()
    assert state["state"] == "paused", "State should be paused after ORI"
    assert state["pc"] == TEXT_START + 8, "PC should advance after ORI"
    assert state["registers"][8] == 0x12345678, "$t0 should hold full value after ORI"
    assert state["error"] is None, "No error after ORI"


def test_step_lw_sw(simulator):
    """Tests basic load word (LW) and store word (SW)."""
    # sw $t0 ($8), 8($zero) -> 0xac080008
    # lw $t1 ($9), 8($zero) -> 0x8c090008
    sim = load_test_code(simulator, ["0xac080008", "0x8c090008"])
    sim.registers[8] = 999 # $t0 = 999
    sim.registers[9] = 0   # $t1 = 0 initially

    # Step 1: Execute sw
    state = sim.step()
    assert state["state"] == "paused", "State should be paused after SW"
    assert state["pc"] == TEXT_START + 4, "PC should advance after SW"
    assert state["registers"][9] == 0, "$t1 unchanged after SW"
    assert state["error"] is None, "No error after SW"
    assert sim.read_memory(8, 4) == 999, "Memory content incorrect after SW"

    # Step 2: Execute lw
    state = sim.step()
    assert state["state"] == "paused", "State should be paused after LW"
    assert state["pc"] == TEXT_START + 8, "PC should advance after LW"
    assert state["registers"][9] == 999, "$t1 should hold loaded value after LW"
    assert state["error"] is None, "No error after LW"


# --- Test Basic Syscalls ---

def test_step_syscall_exit(simulator):
    """Tests the exit syscall (code 10)."""
    # li $v0 ($2), 10 -> 0x2402000a
    # syscall -> 0x0000000c
    load_test_code(simulator, ["0x2402000a", "0x0000000c"])

    # Step 1: Execute li
    state = simulator.step()
    assert state["state"] == "paused"
    assert state["pc"] == TEXT_START + 4
    assert state["registers"][2] == 10, "$v0 should be 10 for exit syscall"

    # Step 2: Execute syscall
    state = simulator.step()
    assert state["state"] == "finished", "Simulator state should be 'finished' after exit"
    assert state["exit_code"] == 0, "Default exit code should be 0"
    # Check termination reason distinguishing syscall exit
    assert "syscall 10" in state.get("termination_reason", ""), "Termination reason mismatch"
    assert state["pc"] == TEXT_START + 4, "PC should not advance after exit syscall"
    assert state["error"] is None, "No error on exit"


def test_step_syscall_print_int(simulator):
    """Tests the print_int syscall (code 1)."""
    # li $v0 ($2), 1 -> 0x24020001
    # li $a0 ($4), 123 -> 0x2404007b
    # syscall -> 0x0000000c
    sim = load_test_code(simulator, ["0x24020001", "0x2404007b", "0x0000000c"])

    sim.step() # li $v0
    sim.step() # li $a0
    assert sim.registers[2] == 1, "$v0 setup failed"
    assert sim.registers[4] == 123, "$a0 setup failed"

    # Step 3: Execute syscall
    state = sim.step()
    assert state["state"] == "paused", "State should be paused after print syscall"
    assert state["output"] == "123", "Syscall output buffer should contain '123'"
    assert state["pc"] == TEXT_START + 12, "PC should advance after print syscall"
    assert state["error"] is None, "No error on print_int"

def test_step_syscall_print_string(simulator):
    """Tests the print_string syscall (code 4)."""
    # Code to load address of string "Test" into $a0 and print it
    code = ["0x24020004", "0x3c041001", "0x0000000c"] # li $v0,4; lui $a0,0x1001; syscall
    data = "5465737400" # "Test\0" hex encoded at 0x10010000
    sim = load_test_code(simulator, code, data)

    sim.step() # li $v0
    sim.step() # lui $a0
    assert sim.registers[2] == 4, "$v0 setup failed"
    assert sim.registers[4] == 0x10010000, "$a0 setup failed (address)"

    # Step 3: Execute syscall
    state = sim.step()
    assert state["state"] == "paused", "State should be paused after print syscall"
    assert state["output"] == "Test", "Syscall output buffer should contain 'Test'"
    assert state["pc"] == TEXT_START + 12, "PC should advance after print syscall"
    assert state["error"] is None, "No error on print_string"

# --- Test Branch and Jump Instructions ---

def test_step_beq_taken(simulator):
    """Tests BEQ when the branch should be taken."""
    # beq $t0, $t1, +8 (offset=2) -> 0x11090002 (@ 0x00400000)
    # nop                       -> 0x00000000 (@ 0x00400004) delay slot
    # nop                       -> 0x00000000 (@ 0x00400008) should be skipped
    # nop                       -> 0x00000000 (@ 0x0040000c) target
    sim = load_test_code(simulator, ["0x11090002", "0x00000000", "0x00000000", "0x00000000"])
    # Set registers equal
    sim.registers[8] = 5 # $t0
    sim.registers[9] = 5 # $t1
    state = sim.step() # Execute beq
    assert state["state"] == "paused"
    # MIPS branch delay slot: PC goes to target AFTER executing the next instruction
    # Our simplified simulator jumps immediately. Target = PC + 4 + offset*4 = 0 + 4 + 2*4 = 12 (0xc)
    # Effective target address for PC after this step is 0x0040000c
    assert state["pc"] == TEXT_START + 12, "PC should jump to target address"
    assert state["error"] is None

def test_step_beq_not_taken(simulator):
    """Tests BEQ when the branch should NOT be taken."""
    # beq $t0, $t1, +8 (offset=2) -> 0x11090002 (@ 0x00400000)
    # nop                       -> 0x00000000 (@ 0x00400004) should execute next
    sim = load_test_code(simulator, ["0x11090002", "0x00000000"])
    # Set registers not equal
    sim.registers[8] = 5 # $t0
    sim.registers[9] = 6 # $t1
    state = sim.step() # Execute beq
    assert state["state"] == "paused"
    # Branch not taken, PC advances normally
    assert state["pc"] == TEXT_START + 4, "PC should advance normally"
    assert state["error"] is None

def test_step_bne_taken(simulator):
    """Tests BNE when the branch should be taken."""
    # bne $t0, $t1, +8 (offset=2) -> 0x15090002 (@ 0x00400000)
    sim = load_test_code(simulator, ["0x15090002", "0x00000000", "0x00000000", "0x00000000"])
    # Set registers not equal
    sim.registers[8] = 5 # $t0
    sim.registers[9] = 6 # $t1
    state = sim.step() # Execute bne
    assert state["state"] == "paused"
    # Target = PC + 4 + offset*4 = 0 + 4 + 2*4 = 12 (0xc)
    assert state["pc"] == TEXT_START + 12, "PC should jump to target address"
    assert state["error"] is None

def test_step_j(simulator):
    """Tests the J (Jump) instruction."""
    # Target address: 0x0040000c (Index 3 in instruction list if starting at 0)
    # Encoded addr part = (0x0040000c >> 2) = 0x00100003
    # j target -> opcode=2 -> 000010 00000100000000000000000011 -> 0x08100003
    sim = load_test_code(simulator, ["0x08100003", "0x00000000", "0x00000000", "0x00000000"])
    state = sim.step() # Execute j
    assert state["state"] == "paused"
    # Jumps immediately in this simulator model
    assert state["pc"] == TEXT_START + 12, "PC should jump to target address 0x0040000c"
    assert state["error"] is None

def test_step_jal(simulator):
    """Tests the JAL (Jump And Link) instruction."""
    # Target address: 0x0040000c
    # Encoded addr part = 0x00100003
    # jal target -> opcode=3 -> 000011 00000100000000000000000011 -> 0x0c100003
    sim = load_test_code(simulator, ["0x0c100003", "0x00000000", "0x00000000", "0x00000000"])
    initial_ra = sim.registers[31]
    state = sim.step() # Execute jal
    assert state["state"] == "paused"
    # Jumps immediately
    assert state["pc"] == TEXT_START + 12, "PC should jump to target address 0x0040000c"
    # Return address is PC + 8 (instruction after delay slot)
    assert state["registers"][31] == TEXT_START + 8, "$ra should store return address 0x00400008"
    assert state["error"] is None

def test_step_jr(simulator):
    """Tests the JR (Jump Register) instruction."""
    # jr $t0 -> funct=8 -> 000000 01000 00000 00000 00000 001000 -> 0x01000008
    sim = load_test_code(simulator, ["0x01000008"])
    # Set $t0 to the target address (must be word-aligned)
    target_pc = TEXT_START + 0x20 # Example target
    sim.registers[8] = target_pc # $t0
    state = sim.step()
    assert state["state"] == "paused"
    assert state["pc"] == target_pc, "PC should jump to address in $t0"
    assert state["error"] is None

def test_step_jr_unaligned(simulator):
    """Tests JR with an unaligned target address."""
    # jr $t0 -> funct=8 -> 000000 01000 00000 00000 00000 001000 -> 0x01000008
    sim = load_test_code(simulator, ["0x01000008"])
    # Set $t0 to an unaligned target address
    target_pc = TEXT_START + 0x21 # Unaligned target (ends in 1)
    sim.registers[8] = target_pc # $t0

    state = sim.step() # Execute jr

    assert state["state"] == "error", "State should be 'error' for unaligned JR"
    assert state["error"] is not None, "Error message should not be None"
    # --- FIX: Make check case-insensitive or check for specific substring ---
    assert "unaligned" in state["error"].lower(), f"Error message should mention alignment, got: {state['error']}"
    # Alternative exact check:
    # assert "target address unaligned" in state["error"], f"Error message should mention alignment, got: {state['error']}"
    # --- END FIX ---
    assert state["pc"] == TEXT_START, "PC should not advance on JR error"

# --- Test Termination Conditions ---

def test_finish_run_off_end(simulator):
    """Tests program finishing by running off the end."""
    sim = load_test_code(simulator, ["0x00000000"]) # Single NOP
    state = sim.step() # Execute NOP
    assert state["pc"] == TEXT_START + 4
    assert state["state"] == "paused"
    state = sim.step() # Step when PC is past the end
    assert state["state"] == "finished"
    assert state["exit_code"] == 0
    assert "ran off the end" in state.get("termination_reason", "")
    assert state["pc"] == TEXT_START + 4 # PC stays where it was when finished

# Add tests for other branches (blez, bgtz, bltz, bgez) and jalr