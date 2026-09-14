# backend/tests/test_simulator.py
import pytest
from backend.mips_simulator import MipsSimulator, TEXT_START, DATA_START, STACK_START, MAX_STEPS
import struct # Needed for signed conversion helper
import time # For testing pause potentially

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
    # Ensure value is treated as 32-bit unsigned first
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
    code = ["0x24020005", "0x0000000c"] # addiu $v0, $zero, 5; syscall
    data = "0a000000" # data = 10 (word) at 0x10010000
    load_test_code(simulator, code, data)

    state = simulator.get_state()
    assert state["pc"] == TEXT_START, "PC should start at text base"
    assert state["registers"][0] == 0, "$zero should always be 0"
    assert state["registers"][29] == STACK_START, "$sp should be initialized"
    assert all(reg == 0 for i, reg in enumerate(state["registers"]) if i not in [0, 29]), "Other GPRs should be 0 initially"
    assert state["state"] == "loaded", "Simulator state should be 'loaded'"
    assert state["error"] is None, "There should be no initial error"
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
    value_neg_pattern = 0xdeadbeef
    value_neg = to_signed_32(value_neg_pattern)

    assert simulator.write_memory(addr, value_pos, 4) == True, "Write positive word failed"
    read_val = simulator.read_memory(addr, 4)
    assert read_val == value_pos, "Read positive word mismatch"
    assert simulator.memory[addr] == 0xcd and simulator.memory[addr+3] == 0x12, "Byte check pos failed"

    addr_neg = 0x10010024
    assert simulator.write_memory(addr_neg, value_neg, 4) == True, f"Write negative word ({value_neg}) failed"
    read_val_neg = simulator.read_memory(addr_neg, 4)
    assert read_val_neg == value_neg, f"Read negative word mismatch (expected {value_neg}, got {read_val_neg})"
    assert simulator.memory[addr_neg] == 0xef and simulator.memory[addr_neg+3] == 0xde, "Byte check neg failed"

def test_memory_read_write_byte(simulator):
    """Tests writing and reading signed/unsigned bytes."""
    addr = 0x10010030
    value_neg = -10 # 0xf6
    value_pos = 120 # 0x78

    assert simulator.write_memory(addr, value_neg, 1) == True, "Write negative byte failed"
    read_val_signed = simulator.read_memory(addr, 1)
    assert read_val_signed == -10, "Signed read of negative byte failed"
    read_val_unsigned = simulator.read_memory_unsigned(addr, 1)
    assert read_val_unsigned == 0xf6, "Unsigned read of negative byte failed"
    assert simulator.memory[addr] == 0xf6, "Internal memory value check failed (neg byte)"

    addr_pos = 0x10010031
    assert simulator.write_memory(addr_pos, value_pos, 1) == True, "Write positive byte failed"
    read_val_signed_pos = simulator.read_memory(addr_pos, 1)
    assert read_val_signed_pos == 120, "Signed read of positive byte failed"
    read_val_unsigned_pos = simulator.read_memory_unsigned(addr_pos, 1)
    assert read_val_unsigned_pos == 120, "Unsigned read of positive byte failed"
    assert simulator.memory[addr_pos] == 0x78, "Internal memory value check failed (pos byte)"

    assert simulator.write_memory(addr, 200, 1) == False, "Write out-of-range byte should fail"
    assert simulator.state == "error"
    assert "out of range for 1 byte(s)" in simulator.error_message

def test_memory_read_write_half(simulator):
    """Tests writing and reading signed/unsigned half-words."""
    addr = 0x10010034
    value_neg = -2000 # 0xf830
    value_pos = 15000 # 0x3a98

    assert simulator.write_memory(addr, value_neg, 2) == True, "Write negative half failed"
    read_val_signed = simulator.read_memory(addr, 2)
    assert read_val_signed == -2000, "Signed read of negative half failed"
    read_val_unsigned = simulator.read_memory_unsigned(addr, 2)
    assert read_val_unsigned == 0xf830, "Unsigned read of negative half failed"
    assert simulator.memory[addr] == 0x30 and simulator.memory[addr+1] == 0xf8, "Byte check neg half failed"

    addr_pos = 0x10010036
    assert simulator.write_memory(addr_pos, value_pos, 2) == True, "Write positive half failed"
    read_val_signed_pos = simulator.read_memory(addr_pos, 2)
    assert read_val_signed_pos == 15000, "Signed read of positive half failed"
    read_val_unsigned_pos = simulator.read_memory_unsigned(addr_pos, 2)
    assert read_val_unsigned_pos == 15000, "Unsigned read of positive half failed"
    assert simulator.memory[addr_pos] == 0x98 and simulator.memory[addr_pos+1] == 0x3a, "Byte check pos half failed"

    assert simulator.write_memory(addr, 40000, 2) == False, "Write out-of-range half should fail"
    assert simulator.state == "error"
    assert "out of range for 2 byte(s)" in simulator.error_message

def test_memory_alignment_error(simulator):
     """Tests detection of unaligned memory access for word and half-word."""
     assert simulator.write_memory(0x10010040, 123, 4) == True # Aligned OK
     read_val = simulator.read_memory(0x10010041, 4) # Unaligned Read Word
     assert simulator.state == "error" and "Unaligned memory read" in simulator.error_message
     assert read_val == 0

     simulator.reset()
     assert simulator.write_memory(0x10010042, 456, 4) == False # Unaligned Write Word
     assert simulator.state == "error" and "Unaligned memory write" in simulator.error_message

     simulator.reset()
     assert simulator.write_memory(0x10010050, 100, 2) == True # Aligned OK
     assert simulator.read_memory(0x10010051, 2) == 0 # Unaligned Read Half
     assert simulator.state == "error" and "Unaligned memory read" in simulator.error_message

     simulator.reset()
     assert simulator.write_memory(0x10010051, 200, 2) == False # Unaligned Write Half
     assert simulator.state == "error" and "Unaligned memory write" in simulator.error_message

# --- Test Arithmetic/Logical Instruction Execution ---

def test_step_addiu(simulator):
    """Tests ADDIU with positive immediate."""
    load_test_code(simulator, ["0x24080064"]) # addiu $t0, $zero, 100
    state = simulator.step()
    assert state["state"] == "paused" and state["pc"] == TEXT_START + 4
    assert state["registers"][8] == 100 and state["error"] is None

def test_step_addiu_negative(simulator):
    """Tests ADDIU with negative immediate."""
    load_test_code(simulator, ["0x2409fffb"]) # addiu $t1, $zero, -5
    state = simulator.step()
    assert state["state"] == "paused" and state["pc"] == TEXT_START + 4
    assert to_signed_32(state["registers"][9]) == -5 and state["error"] is None

def test_step_addi_no_overflow(simulator):
    """Tests ADDI without overflow."""
    # addi $t1 ($9), $t0 ($8), 1000 (0x3e8) -> 0x210903e8
    sim = load_test_code(simulator, ["0x210903e8"])
    sim.registers[8] = 500 # $t0
    state = sim.step()
    assert state["state"] == "paused" and state["pc"] == TEXT_START + 4
    assert state["registers"][9] == 1500 and state["error"] is None

def test_step_addi_overflow(simulator):
    """Tests ADDI with positive overflow."""
    # addi $t1 ($9), $t0 ($8), 1000
    sim = load_test_code(simulator, ["0x210903e8"])
    sim.registers[8] = 0x7fffffff # Max positive signed int ($t0)
    state = sim.step()
    assert state["state"] == "error" and "Arithmetic overflow" in state["error"]
    assert state["pc"] == TEXT_START # PC should not advance on error

def test_step_addi_negative_overflow(simulator):
    """Tests ADDI with negative overflow."""
    # addi $t1 ($9), $t0 ($8), -1000 (0xfffffc18) -> 0x2109fc18
    sim = load_test_code(simulator, ["0x2109fc18"])
    sim.registers[8] = 0x80000000 # Min negative signed int ($t0)
    state = sim.step()
    assert state["state"] == "error" and "Arithmetic overflow" in state["error"]
    assert state["pc"] == TEXT_START

def test_step_addu(simulator):
    """Tests ADDU."""
    # addu $t2 ($10), $t0 ($8), $t1 ($9) -> 0x01095021
    sim = load_test_code(simulator, ["0x01095021"])
    sim.registers[8] = 0xFFFFFFFF # -1 unsigned
    sim.registers[9] = 5
    state = sim.step()
    assert state["state"] == "paused" and state["pc"] == TEXT_START + 4
    assert state["registers"][10] == 4 # (-1 + 5) & 0xFFFFFFFF
    assert state["error"] is None

def test_step_subu(simulator):
    """Tests SUBU."""
    # subu $t2 ($10), $t0 ($8), $t1 ($9) -> 0x01095023
    sim = load_test_code(simulator, ["0x01095023"])
    sim.registers[8] = 5
    sim.registers[9] = 7
    state = sim.step()
    assert state["state"] == "paused" and state["pc"] == TEXT_START + 4
    assert to_signed_32(state["registers"][10]) == -2 # Result is 0xfffffffe
    assert state["error"] is None

def test_step_and_or_xor_nor(simulator):
    """Tests AND, OR, XOR, NOR."""
    # and $t2, $t0, $t1  -> 0x01095024
    # or  $t3, $t0, $t1  -> 0x01095825
    # xor $t4, $t0, $t1  -> 0x01096026
    # nor $t5, $t0, $t1  -> 0x01096827
    sim = load_test_code(simulator, ["0x01095024", "0x01095825", "0x01096026", "0x01096827"])
    sim.registers[8] = 0x0F0F0F0F # $t0
    sim.registers[9] = 0xF0F0F0F0 # $t1
    # Step 1: and
    state = sim.step()
    assert state["registers"][10] == 0x00000000 # $t2 = $t0 & $t1
    # Step 2: or
    state = sim.step()
    assert state["registers"][11] == 0xFFFFFFFF # $t3 = $t0 | $t1
    # Step 3: xor
    state = sim.step()
    assert state["registers"][12] == 0xFFFFFFFF # $t4 = $t0 ^ $t1
    # Step 4: nor
    state = sim.step()
    assert state["registers"][13] == 0x00000000 # $t5 = ~($t0 | $t1)
    assert state["state"] == "paused" and state["pc"] == TEXT_START + 16

def test_step_slt_sltu(simulator):
    """Tests SLT and SLTU."""
    # slt $t2, $t0, $t1  -> 0x0109502a
    # sltu $t3, $t0, $t1 -> 0x0109582b
    # slt $t4, $t1, $t0  -> 0x0128602a # $t1 < $t0 ?
    # sltu $t5, $t1, $t0 -> 0x0128682b # $t1 < $t0 unsigned ?
    sim = load_test_code(simulator, ["0x0109502a", "0x0109582b", "0x0128602a", "0x0128682b"])
    sim.registers[8] = 0xFFFFFFFF # $t0 = -1 signed, MAX_UINT unsigned
    sim.registers[9] = 5         # $t1 = 5 signed, 5 unsigned
    # Step 1: slt $t2, $t0, $t1 (-1 < 5) -> True
    state = sim.step(); assert state["registers"][10] == 1
    # Step 2: sltu $t3, $t0, $t1 (MAX_UINT < 5) -> False
    state = sim.step(); assert state["registers"][11] == 0
    # Step 3: slt $t4, $t1, $t0 (5 < -1) -> False
    state = sim.step(); assert state["registers"][12] == 0
    # Step 4: sltu $t5, $t1, $t0 (5 < MAX_UINT) -> True
    state = sim.step(); assert state["registers"][13] == 1
    assert state["state"] == "paused" and state["pc"] == TEXT_START + 16

def test_step_shifts_immediate(simulator):
    """Tests SLL, SRL, SRA."""
    # sll $t1, $t0, 4  -> 0x00084900
    # srl $t2, $t0, 8  -> 0x00085202
    # sra $t3, $t0, 12 -> 0x00085b03
    # sra $t4, $t1, 4  -> 0x00096103 # Shift the positive value right
    sim = load_test_code(simulator, ["0x00084900", "0x00085202", "0x00085b03", "0x00096103"])
    sim.registers[8] = 0x87654321 # $t0 (negative number)
    # Step 1: sll $t1, $t0, 4 -> 0x76543210
    state = sim.step(); assert state["registers"][9] == 0x76543210
    # Step 2: srl $t2, $t0, 8 -> 0x00876543 (logical shift)
    state = sim.step(); assert state["registers"][10] == 0x00876543
    # Step 3: sra $t3, $t0, 12 -> 0xfff87654 (arithmetic shift, sign extend)
    state = sim.step(); assert state["registers"][11] == 0xfff87654
    # Step 4: sra $t4, $t1, 4 (positive value 0x76543210) -> 0x07654321
    state = sim.step(); assert state["registers"][12] == 0x07654321
    assert state["state"] == "paused" and state["pc"] == TEXT_START + 16

def test_step_shifts_variable(simulator):
    """Tests SLLV, SRLV, SRAV."""
    # sllv $t2, $t0, $t1 -> 0x01285004
    # srlv $t3, $t0, $t1 -> 0x01285806
    # srav $t4, $t0, $t1 -> 0x01286007
    sim = load_test_code(simulator, ["0x01285004", "0x01285806", "0x01286007"])
    sim.registers[8] = 0x87654321 # $t0 (negative)
    sim.registers[9] = 4         # $t1 (shift amount)
    # Step 1: sllv $t2, $t0, $t1 -> 0x76543210
    state = sim.step(); assert state["registers"][10] == 0x76543210
    # Step 2: srlv $t3, $t0, $t1 -> 0x08765432 (logical)
    state = sim.step(); assert state["registers"][11] == 0x08765432
    # Step 3: srav $t4, $t0, $t1 -> 0xf8765432 (arithmetic)
    state = sim.step(); assert state["registers"][12] == 0xf8765432
    assert state["state"] == "paused" and state["pc"] == TEXT_START + 12

def test_step_mult_div_mflo_mfhi(simulator):
    """Tests MULT, DIVU, MFLO, MFHI."""
    # mult $t0, $t1 -> 0x01090018
    # divu $t2, $t3 -> 0x014b001b
    # mflo $s0      -> 0x00008012
    # mfhi $s1      -> 0x00008810
    sim = load_test_code(simulator, ["0x01090018", "0x014b001b", "0x00008012", "0x00008810"])
    sim.registers[8] = -5      # $t0
    sim.registers[9] = 3       # $t1
    sim.registers[10] = 100    # $t2
    sim.registers[11] = 7      # $t3

    # Step 1: mult $t0, $t1 (-5 * 3 = -15 = 0xfffffffffffffff1)
    state = sim.step()
    assert state["lo"] == 0xfffffff1 # Lower 32 bits
    assert state["hi"] == 0xffffffff # Upper 32 bits (sign extension)
    assert state["pc"] == TEXT_START + 4

    # Step 2: divu $t2, $t3 (100 / 7 = 14 rem 2)
    state = sim.step()
    assert state["lo"] == 14 # Quotient
    assert state["hi"] == 2  # Remainder
    assert state["pc"] == TEXT_START + 8

    # Step 3: mflo $s0
    state = sim.step()
    assert state["registers"][16] == 14 # $s0 gets LO
    assert state["pc"] == TEXT_START + 12

    # Step 4: mfhi $s1
    state = sim.step()
    assert state["registers"][17] == 2 # $s1 gets HI
    assert state["pc"] == TEXT_START + 16
    assert state["state"] == "paused"

def test_step_div_by_zero(simulator):
    """Tests division by zero error."""
    # div $t0, $t1 -> 0x0109001a
    sim = load_test_code(simulator, ["0x0109001a"])
    sim.registers[8] = 10
    sim.registers[9] = 0 # Divide by zero
    state = sim.step()
    assert state["state"] == "error"
    assert "Division by zero" in state["error"]
    assert state["pc"] == TEXT_START # PC does not advance

def test_step_mtlo_mthi(simulator):
    """Tests MTLO, MTHI."""
    # mtlo $t0 -> 0x01000013
    # mthi $t1 -> 0x01200011
    sim = load_test_code(simulator, ["0x01000013", "0x01200011"])
    sim.registers[8] = 0x12345678 # $t0
    sim.registers[9] = 0xabcdef01 # $t1
    # Step 1: mtlo
    state = sim.step()
    assert state["lo"] == 0x12345678
    assert state["pc"] == TEXT_START + 4
    # Step 2: mthi
    state = sim.step()
    assert state["hi"] == 0xabcdef01
    assert state["pc"] == TEXT_START + 8
    assert state["state"] == "paused"

def test_step_lui_ori(simulator):
    """Tests LUI and ORI combination."""
    # lui $t0, 0x1234 -> 0x3c081234
    # ori $t0, $t0, 0x5678 -> 0x35085678
    load_test_code(simulator, ["0x3c081234", "0x35085678"])
    state = simulator.step() # lui
    assert state["registers"][8] == 0x12340000
    assert state["pc"] == TEXT_START + 4
    state = simulator.step() # ori
    assert state["registers"][8] == 0x12345678
    assert state["pc"] == TEXT_START + 8
    assert state["state"] == "paused"

def test_step_lw_sw(simulator):
    """Tests LW and SW."""
    # sw $t0, 8($zero) -> 0xac080008
    # lw $t1, 8($zero) -> 0x8c090008
    sim = load_test_code(simulator, ["0xac080008", "0x8c090008"])
    sim.registers[8] = 999 # $t0
    sim.step() # sw
    assert sim.read_memory(8, 4) == 999
    assert sim.pc == TEXT_START + 4
    state = sim.step() # lw
    assert state["registers"][9] == 999 # $t1
    assert state["pc"] == TEXT_START + 8
    assert state["state"] == "paused"


# --- Test Branch and Jump Instructions ---

def test_step_beq_taken(simulator):
    """Tests BEQ when the branch should be taken."""
    # Target: PC+4 + 2*4 = PC + 12 (0x0040000c)
    # beq $t0, $t1, offset=2 -> 0x11090002
    sim = load_test_code(simulator, ["0x11090002", "0x00000000", "0x00000000", "0x00000000"])
    sim.registers[8] = 5; sim.registers[9] = 5 # $t0 = $t1
    state = sim.step()
    assert state["pc"] == TEXT_START + 12 and state["state"] == "paused"

def test_step_beq_not_taken(simulator):
    """Tests BEQ when the branch should NOT be taken."""
    # beq $t0, $t1, offset=2 -> 0x11090002
    sim = load_test_code(simulator, ["0x11090002", "0x00000000"])
    sim.registers[8] = 5; sim.registers[9] = 6 # $t0 != $t1
    state = sim.step()
    assert state["pc"] == TEXT_START + 4 and state["state"] == "paused" # PC advances normally

def test_step_bne_taken(simulator):
    """Tests BNE when the branch should be taken."""
     # Target: PC+4 + 2*4 = PC + 12 (0x0040000c)
     # bne $t0, $t1, offset=2 -> 0x15090002
    sim = load_test_code(simulator, ["0x15090002", "0x00000000", "0x00000000", "0x00000000"])
    sim.registers[8] = 5; sim.registers[9] = 6 # $t0 != $t1
    state = sim.step()
    assert state["pc"] == TEXT_START + 12 and state["state"] == "paused"

def test_step_bne_not_taken(simulator):
    """Tests BNE when the branch should NOT be taken."""
    # bne $t0, $t1, offset=2 -> 0x15090002
    sim = load_test_code(simulator, ["0x15090002", "0x00000000"])
    sim.registers[8] = 5; sim.registers[9] = 5 # $t0 == $t1
    state = sim.step()
    assert state["pc"] == TEXT_START + 4 and state["state"] == "paused"

def test_step_blez_taken(simulator):
    """Tests BLEZ when branch should be taken (rs <= 0)."""
    # Target: PC+4 + 3*4 = PC + 16 (0x10)
    # blez $t0, offset=3 -> opcode=6, rs=8 -> 0x19000003
    sim = load_test_code(simulator, ["0x19000003"] + ["0"]*4)
    sim.registers[8] = to_signed_32(0xffffffff) # $t0 = -1
    state = sim.step()
    assert state["pc"] == TEXT_START + 16 and state["state"] == "paused"
    sim.reset()
    sim = load_test_code(simulator, ["0x19000003"] + ["0"]*4)
    sim.registers[8] = 0 # $t0 = 0
    state = sim.step()
    assert state["pc"] == TEXT_START + 16 and state["state"] == "paused"

def test_step_blez_not_taken(simulator):
    """Tests BLEZ when branch should NOT be taken (rs > 0)."""
    # blez $t0, offset=3 -> 0x19000003
    sim = load_test_code(simulator, ["0x19000003", "0"])
    sim.registers[8] = 1 # $t0 = 1
    state = sim.step()
    assert state["pc"] == TEXT_START + 4 and state["state"] == "paused"

# Add similar tests for bgtz, bltz, bgez, bltzal, bgezal...

def test_step_j(simulator):
    """Tests the J (Jump) instruction."""
    # Target address: 0x0040000c
    # j target -> 0x08100003
    sim = load_test_code(simulator, ["0x08100003", "0", "0", "0"]) # Code + padding
    state = sim.step()
    assert state["pc"] == TEXT_START + 12 and state["state"] == "paused"

def test_step_jal(simulator):
    """Tests the JAL (Jump And Link) instruction."""
    # Target address: 0x0040000c
    # jal target -> 0x0c100003
    sim = load_test_code(simulator, ["0x0c100003", "0", "0", "0"])
    state = sim.step()
    assert state["pc"] == TEXT_START + 12 and state["state"] == "paused"
    assert state["registers"][31] == TEXT_START + 8, "$ra check failed" # PC + 8

def test_step_jr(simulator):
    """Tests the JR (Jump Register) instruction."""
    # jr $t0 -> 0x01000008
    sim = load_test_code(simulator, ["0x01000008", "0", "0"])
    target_pc = TEXT_START + 8 # Aligned target
    sim.registers[8] = target_pc # $t0
    state = sim.step()
    assert state["pc"] == target_pc and state["state"] == "paused"

def test_step_jr_unaligned(simulator):
    """Tests JR with an unaligned target address."""
    # jr $t0 -> 0x01000008
    sim = load_test_code(simulator, ["0x01000008"])
    target_pc = TEXT_START + 9 # Unaligned target
    sim.registers[8] = target_pc
    state = sim.step()
    assert state["state"] == "error" and "unaligned" in state["error"].lower()
    assert state["pc"] == TEXT_START # PC should not advance

def test_step_jalr(simulator):
    """Tests the JALR (Jump And Link Register) instruction."""
    # jalr $t1, $t0 (rd=t1=9, rs=t0=8) -> 0x01004809
    sim = load_test_code(simulator, ["0x01004809", "0", "0"])
    target_pc = TEXT_START + 8 # Aligned target
    sim.registers[8] = target_pc # $t0 (target address)
    state = sim.step()
    assert state["pc"] == target_pc and state["state"] == "paused"
    assert state["registers"][9] == TEXT_START + 8, "$t1 (rd) should be PC+8"

def test_step_jalr_default_ra(simulator):
    """Tests JALR using default $ra for return address."""
    # jalr $t0 (rd=implicit $ra=31, rs=t0=8) -> 0x0100f809
    sim = load_test_code(simulator, ["0x0100f809", "0", "0"])
    target_pc = TEXT_START + 8
    sim.registers[8] = target_pc
    state = sim.step()
    assert state["pc"] == target_pc and state["state"] == "paused"
    assert state["registers"][31] == TEXT_START + 8, "$ra should be PC+8"


# --- Test Syscalls (Including Input/Output) ---

def test_step_syscall_exit(simulator):
    """Tests the exit syscall (code 10)."""
    load_test_code(simulator, ["0x2402000a", "0x0000000c"]) # li $v0, 10; syscall
    simulator.step() # li
    state = simulator.step() # syscall
    assert state["state"] == "finished" and state["exit_code"] == 0
    assert "syscall 10" in state.get("termination_reason", "")
    assert state["pc"] == TEXT_START + 4 # PC stops at syscall

def test_step_syscall_exit2(simulator):
    """Tests the exit2 syscall (code 17) with exit code."""
    # li $v0, 17 -> 0x24020011
    # li $a0, -1 -> 0x2404ffff (-1 imm)
    # syscall -> 0x0000000c
    sim = load_test_code(simulator, ["0x24020011", "0x2404ffff", "0x0000000c"])
    sim.step() # li v0
    sim.step() # li a0
    state = sim.step() # syscall
    assert state["state"] == "finished"
    assert state["exit_code"] == -1
    assert "syscall 17" in state.get("termination_reason", "")
    assert state["pc"] == TEXT_START + 8 # PC stops at syscall

def test_step_syscall_print_int(simulator):
    """Tests the print_int syscall (code 1)."""
    # li $v0, 1 -> 0x24020001
    # li $a0, -123 (imm=0xffffff85 -> ori/lui or just addiu?) -> Use addiu 0x2404ff85
    # syscall -> 0x0000000c
    sim = load_test_code(simulator, ["0x24020001", "0x2404ff85", "0x0000000c"])
    sim.step(); sim.step() # li v0, li a0
    state = sim.step()
    assert state["state"] == "paused" and state["output"] == "-123"
    assert state["pc"] == TEXT_START + 12

def test_step_syscall_print_char(simulator):
    """Tests the print_char syscall (code 11)."""
    # li $v0, 11 -> 0x2402000b
    # li $a0, 65 # ASCII 'A' -> 0x24040041
    # syscall -> 0x0000000c
    sim = load_test_code(simulator, ["0x2402000b", "0x24040041", "0x0000000c"])
    sim.step(); sim.step() # li v0, li a0
    state = sim.step()
    assert state["state"] == "paused" and state["output"] == "A"
    assert state["pc"] == TEXT_START + 12

def test_step_syscall_print_string(simulator):
    """Tests the print_string syscall (code 4)."""
    # li $v0, 4 -> 0x24020004
    # lui $a0, 0x1001 -> 0x3c041001 (address 0x10010000)
    # syscall -> 0x0000000c
    code = ["0x24020004", "0x3c041001", "0x0000000c"]
    data = "48656c6c6f00" # "Hello\0"
    sim = load_test_code(simulator, code, data)
    sim.step(); sim.step() # li v0, lui a0
    state = sim.step()
    assert state["state"] == "paused" and state["output"] == "Hello"
    assert state["pc"] == TEXT_START + 12

def test_step_syscall_read_int(simulator):
    """Tests the read_int syscall (code 5) interaction."""
    # li $v0, 5 -> 0x24020005
    # syscall -> 0x0000000c
    sim = load_test_code(simulator, ["0x24020005", "0x0000000c"])
    sim.step() # li v0
    state = sim.step() # syscall read_int
    # Should pause, waiting for input
    assert state["state"] == "input_wait"
    assert state["input_needed"] == True
    assert state["pc"] == TEXT_START + 4 # PC hasn't advanced past syscall yet
    assert state["error"] is None

    # Provide valid input
    assert simulator.provide_input(" 987 ") == True
    state = simulator.get_state() # Get state AFTER input provided
    assert state["state"] == "paused" # State changes to paused after input
    assert state["input_needed"] == False
    assert state["registers"][2] == 987 # $v0 should contain the read integer
    assert state["pc"] == TEXT_START + 8 # PC should have advanced past syscall

    # Test invalid input
    sim.pc = TEXT_START + 4 # Reset PC to syscall instruction
    sim.state = "loaded"    # Reset state to allow step
    sim.input_needed = False # Reset flag
    sim.error_message = None # Clear previous error
    # --- FIX: Reset $v0 before executing the syscall again ---
    sim.registers[2] = 5 # Reset $v0 to 5 for read_int syscall
    # --- END FIX ---
    state_before_step = sim.get_state()
    assert state_before_step["state"] == "loaded"
    state_after_syscall = sim.step() # Execute syscall again
    assert state_after_syscall["state"] == "input_wait" # Should be waiting again

    # Provide invalid input
    assert simulator.provide_input("abc") == False # Invalid input causes provide_input to return False
    state_after_invalid_input = simulator.get_state() # Check state immediately after invalid input
    assert state_after_invalid_input["state"] == "input_wait" # State remains input_wait
    assert state_after_invalid_input["input_needed"] == True # Still needs input
    assert "Invalid input format" in state_after_invalid_input["error"] # Error message set
    assert state_after_invalid_input["pc"] == TEXT_START + 4 # PC still at syscall

def test_step_syscall_read_string(simulator):
    """Tests the read_string syscall (code 8)."""
    # li $v0, 8 -> 0x24020008
    # lui $a0, 0x1001 # buffer @ 0x10010000 -> 0x3c041001
    # li $a1, 10 # max length 10 -> 0x2405000a
    # syscall -> 0x0000000c
    code = ["0x24020008", "0x3c041001", "0x2405000a", "0x0000000c"]
    sim = load_test_code(simulator, code)
    sim.step(); sim.step(); sim.step() # Setup v0, a0, a1
    state = sim.step() # syscall read_string
    assert state["state"] == "input_wait" and state["input_needed"] == True
    assert state["pc"] == TEXT_START + 12

    # Provide input (less than max length)
    input_str = "world"
    assert simulator.provide_input(input_str) == True
    state = simulator.get_state()
    assert state["state"] == "paused" and state["input_needed"] == False
    assert state["pc"] == TEXT_START + 16 # PC advanced past syscall

    # Verify memory content
    mem_bytes = bytearray(simulator.memory[0x10010000 + i] for i in range(len(input_str) + 1))
    assert mem_bytes == b"world\0"

    # Test input longer than buffer
    sim.pc = TEXT_START + 12 # Reset PC
    state = sim.step()
    assert state["state"] == "input_wait"
    long_input = "this is too long"
    assert simulator.provide_input(long_input) == True # Should truncate
    state = simulator.get_state()
    assert state["state"] == "paused"
    # Buffer size is 10 ($a1), so stores 9 chars + null
    mem_bytes_long = bytearray(simulator.memory[0x10010000 + i] for i in range(10))
    assert mem_bytes_long == b"this is t\0"

def test_step_syscall_sbrk(simulator):
    """Tests the sbrk syscall (code 9)."""
    # li $v0, 9 -> 0x24020009
    # li $a0, 16 # Allocate 16 bytes -> 0x24040010
    # syscall -> 0x0000000c
    # Store result in $s0
    # add $s0, $v0, $zero -> 0x00408021
    sim = load_test_code(simulator, ["0x24020009", "0x24040010", "0x0000000c", "0x00408021"])
    initial_break = sim.program_break
    sim.step(); sim.step() # li v0, li a0
    state = sim.step() # syscall sbrk
    assert state["state"] == "paused"
    assert state["pc"] == TEXT_START + 12
    assert state["registers"][2] == initial_break # $v0 holds *start* of allocated block
    assert sim.program_break == initial_break + 16 # Program break pointer moved
    state = sim.step() # add $s0, $v0, $zero
    assert state["registers"][16] == initial_break # $s0 gets start address


# --- Test Run Functionality ---

def test_run_to_finish(simulator):
    """Tests running a program until it finishes normally."""
    # Simple program that runs off the end
    # addiu $t0, $t0, 1 -> 0x21080001
    # addiu $t1, $t1, 1 -> 0x21290001
    sim = load_test_code(simulator, ["0x21080001", "0x21290001"])
    state = sim.run() # Run until end
    assert state["state"] == "finished"
    assert "ran off the end" in state.get("termination_reason", "")
    assert state["registers"][8] == 1 # $t0 incremented
    assert state["registers"][9] == 1 # $t1 incremented
    assert state["pc"] == TEXT_START + 8 # PC is past the last instruction

def test_run_to_exit_syscall(simulator):
    """Tests running until an exit syscall."""
    # li $v0, 10 -> 0x2402000a
    # syscall -> 0x0000000c
    sim = load_test_code(simulator, ["0x2402000a", "0x0000000c"])
    state = sim.run()
    assert state["state"] == "finished"
    assert state["exit_code"] == 0
    assert "syscall 10" in state.get("termination_reason", "")
    assert state["pc"] == TEXT_START + 4 # PC stops at syscall

def test_run_step_limit(simulator):
    """Tests if the run loop stops at the step limit."""
    sim = load_test_code(simulator, ["0x08100000"]) # Infinite loop
    state = sim.run(step_limit=100)
    assert state["state"] == "paused"
    assert "Maximum simulation steps" in state["error"]
    # --- FIX: Assert exact number of steps executed ---
    assert sim.steps_executed == 100, "Should execute exactly step_limit steps"
    # --- END FIX ---

def test_run_and_pause(simulator):
    """Tests pausing a running simulation."""
    # Loop that increments $t0
    # loop: addiu $t0, $t0, 1 -> 0x21080001
    #       j loop -> 0x08100000
    sim = load_test_code(simulator, ["0x21080001", "0x08100000"]) # Inc $t0, loop

    # Simulate a few steps running - call step directly, which leaves state as paused
    sim.step(); current_t0_1 = sim.registers[8]; assert sim.state == "paused"
    sim.step(); current_t0_2 = sim.registers[8]; assert sim.state == "paused"
    sim.step(); current_t0_3 = sim.registers[8]; assert sim.state == "paused"
    assert current_t0_3 == 2, f"Expected $t0 to be 2 after 3 steps, got {current_t0_3}"

    # Start the generator
    state_gen = sim.yield_state(step_limit=10)
    
    # Step 1: Execute one instruction via generator
    state = next(state_gen)
    assert state["state"] == "running"
    
    # Request pause while running
    sim.request_pause()
    assert sim.pause_requested == True, "Pause request flag should be set"
    
    # Step 2: The generator should catch the pause and yield paused state
    state = next(state_gen)
    assert state["state"] == "paused", "Run should have paused on request"
    assert sim.pause_requested == False, "Pause request flag should be cleared"
    
    # Since we took one step in the generator before pausing, total steps is 3 + 1 = 4
    assert sim.steps_executed == 4, f"$t0 value ({state['registers'][8]}) or step count ({sim.steps_executed}) changed unexpectedly after pause request"
    # --- END FIX ---

# --- Test Termination Conditions ---

def test_finish_run_off_end(simulator):
    """Tests program finishing by running off the end."""
    sim = load_test_code(simulator, ["0x00000000"]) # Single NOP
    state = sim.step()
    assert state["pc"] == TEXT_START + 4 and state["state"] == "paused"
    state = sim.step() # Step when PC is past the end
    assert state["state"] == "finished" and state["exit_code"] == 0
    assert "ran off the end" in state.get("termination_reason", "")
    assert state["pc"] == TEXT_START + 4 # PC stays where it was when finished

# --- Test Stack Simulation (using instructions) ---

def test_stack_push_pop(simulator):
    """Simulates pushing and popping from the stack."""
    # 1. addiu $sp, $sp, -8  # Make space for 2 words (0x23bdfff8)
    # 2. sw $ra, 4($sp)       # Save $ra (0xafbf0004)
    # 3. sw $s0, 0($sp)       # Save $s0 (0xafb00000)
    # ... (do something) ...
    # 4. lw $s0, 0($sp)       # Restore $s0 (0x8fb00000)
    # 5. lw $ra, 4($sp)       # Restore $ra (0x8fbf0004)
    # 6. addiu $sp, $sp, 8   # Restore stack pointer (0x23bd0008)
    code = ["0x23bdfff8", "0xafbf0004", "0xafb00000", "0x8fb00000", "0x8fbf0004", "0x23bd0008"]
    sim = load_test_code(simulator, code)

    # Set initial values
    initial_sp = sim.registers[29] # Should be STACK_START (0x7ffffffc)
    sim.registers[31] = 0x1111AAAA # $ra = dummy return address
    sim.registers[16] = 0x2222BBBB # $s0 = dummy saved register value

    # Step 1: addiu $sp, $sp, -8
    state = sim.step()
    expected_sp1 = initial_sp - 8
    assert state["registers"][29] == expected_sp1
    assert state["pc"] == TEXT_START + 4

    # Step 2: sw $ra, 4($sp)
    state = sim.step()
    assert sim.read_memory(expected_sp1 + 4, 4) == 0x1111AAAA # Check $ra saved
    assert state["pc"] == TEXT_START + 8

    # Step 3: sw $s0, 0($sp)
    state = sim.step()
    assert sim.read_memory(expected_sp1 + 0, 4) == 0x2222BBBB # Check $s0 saved
    assert state["pc"] == TEXT_START + 12
    # Clear registers to ensure restore works
    sim.registers[16] = 0
    sim.registers[31] = 0

    # Step 4: lw $s0, 0($sp)
    state = sim.step()
    assert state["registers"][16] == 0x2222BBBB # $s0 restored
    assert state["pc"] == TEXT_START + 16

    # Step 5: lw $ra, 4($sp)
    state = sim.step()
    assert state["registers"][31] == 0x1111AAAA # $ra restored
    assert state["pc"] == TEXT_START + 20

    # Step 6: addiu $sp, $sp, 8
    state = sim.step()
    assert state["registers"][29] == initial_sp # $sp restored to original value
    assert state["pc"] == TEXT_START + 24
    assert state["state"] == "paused"