# backend/tests/test_assembler.py
import pytest
# Import relative to the project root, assuming pytest runs from there
from backend.mips_assembler import MipsAssembler

@pytest.fixture
def assembler():
    """Provides a new MipsAssembler instance for each test."""
    return MipsAssembler()

# --- Basic Instruction Tests ---

def test_assemble_addi(assembler):
    code = "addi $t0, $zero, 100"
    result = assembler.assemble(code)
    print(result) # Debugging output
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1
    # addi: opcode=8, rs=0, rt=8, imm=100 (0x64) -> 0x20080064
    assert result["machine_code"][0]["hex"] == "0x20080064"

def test_assemble_add(assembler):
    code = "add $s0, $t1, $t2"
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1
    # add: opcode=0, rs=9, rt=10, rd=16, shamt=0, funct=0x20 -> 0x012a8020
    assert result["machine_code"][0]["hex"] == "0x012a8020"

def test_assemble_sll(assembler):
    code = "sll $t2, $t1, 4"
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1
    # sll: opcode=0, rs=0, rt=9, rd=10, shamt=4, funct=0x00 -> 0x00095100
    assert result["machine_code"][0]["hex"] == "0x00095100"

def test_assemble_mult(assembler):
    code = "mult $t0, $t1"
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1
    # mult: opcode=0, rs=8, rt=9, rd=0, shamt=0, funct=0x18 -> 0x01090018
    assert result["machine_code"][0]["hex"] == "0x01090018"

def test_assemble_lb(assembler):
    code = "lb $s0, -4($sp)"
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1
    # lb: opcode=0x20, rs=29($sp), rt=16($s0), imm=-4 (0xfffc) -> 0x83b0fffc
    assert result["machine_code"][0]["hex"] == "0x83b0fffc"

def test_assemble_sw(assembler):
    code = "sw $a0, 16($gp)"
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1
    # sw: opcode=0x2b, rs=28($gp), rt=4($a0), imm=16 (0x10) -> 0xae040010
    assert result["machine_code"][0]["hex"] == "0xae040010"

def test_assemble_beq(assembler):
    code = """
    loop: beq $t0, $t1, end
          addi $t0, $t0, 1
          j loop
    end:  add $s0, $zero, $zero
    """
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 4
    # beq: pc=0x400000, target='end'=0x40000c. offset = (0xc - (0+4))/4 = 8/4 = 2
    # opcode=4, rs=8, rt=9, imm=2 -> 0x11090002
    assert result["machine_code"][0]["hex"] == "0x11090002"
    # addi: 0x21080001
    assert result["machine_code"][1]["hex"] == "0x21080001"
    # j loop: pc=0x400008, target='loop'=0x400000. addr_part = (0x400000 >> 2) = 0x100000
    # opcode=2 -> 0x08100000
    assert result["machine_code"][2]["hex"] == "0x08100000"
    # add: 0x00008020
    assert result["machine_code"][3]["hex"] == "0x00008020"


def test_assemble_bgez(assembler):
    code = "loop: bgez $a0, loop"
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1
    # bgez: pc=0x400000, target='loop'=0x400000. offset = (0x0 - (0+4))/4 = -1 (0xffff)
    # opcode=1, rs=4($a0), rt(variant)=1, imm=0xffff -> 0x0481ffff
    assert result["machine_code"][0]["hex"] == "0x0481ffff"

def test_assemble_j(assembler):
    code = """
    start: j end
           addiu $t0, $t0, 1 # Some instruction
    end:   addiu $t1, $t1, 1
    """
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 3
    # j: pc=0x400000, target='end'=0x400008. addr_part = (0x400008 >> 2) = 0x100002
    # opcode=2 -> 0x08100002
    assert result["machine_code"][0]["hex"] == "0x08100002"

def test_assemble_jalr_default_rd(assembler):
    code = "jalr $t1" # rd defaults to $ra
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1
    # jalr: opcode=0, rs=9, rt=0, rd=31, shamt=0, funct=9 -> 0x0120f809
    assert result["machine_code"][0]["hex"] == "0x0120f809"

def test_assemble_jalr_explicit_rd(assembler):
    code = "jalr $t0, $t1" # rd=$t0 (8)
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1
    # jalr: opcode=0, rs=9, rt=0, rd=8, shamt=0, funct=9 -> 0x01204009
    assert result["machine_code"][0]["hex"] == "0x01204009"

# --- Pseudo-Instruction Tests ---

def test_assemble_li(assembler):
     code = "li $t0, 65537" # Requires lui/ori expansion (0x10001)
     result = assembler.assemble(code)
     assert not result["errors"], f"Expected no errors, got: {result['errors']}"
     assert len(result["machine_code"]) == 2
     # Expected:
     # lui $at, 1      (0x3c010001)
     # ori $t0, $at, 1 (0x34280001)
     assert result["machine_code"][0]["hex"] == "0x3c010001"
     assert result["machine_code"][1]["hex"] == "0x34280001"

def test_assemble_li_small_immediate(assembler):
     code = "li $t0, 100" # Should use addiu
     result = assembler.assemble(code)
     assert not result["errors"], f"Expected no errors, got: {result['errors']}"
     assert len(result["machine_code"]) == 1
     # Expected: addiu $t0, $zero, 100 (0x24080064)
     assert result["machine_code"][0]["hex"] == "0x24080064"

def test_assemble_la(assembler):
    code = """
    .data
    myvar: .word 5
    .text
    la $t1, myvar
    """
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1 # Optimized la for address 0x10010000
    # Expected: lui $t1, 0x1001 (0x3c091001) because lower 16 bits are 0
    assert result["machine_code"][0]["hex"] == "0x3c091001"

def test_assemble_la_nonzero_lower(assembler):
    code = """
    .data
           .space 4 # Force next address to 0x10010004
    myvar: .word 5
    .text
    la $t1, myvar
    """
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 2 # Requires lui/ori
    # Expected:
    # lui $at, 0x1001 (0x3c011001)
    # ori $t1, $at, 4 (0x34290004)
    assert result["machine_code"][0]["hex"] == "0x3c011001"
    assert result["machine_code"][1]["hex"] == "0x34290004"


def test_assemble_nop(assembler):
    code = "nop"
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == 1
    # nop -> sll $zero, $zero, 0 -> 0x00000000
    assert result["machine_code"][0]["hex"] == "0x00000000"


def test_assemble_branch_pseudo(assembler):
    code = """
    start: blt $t0, $t1, target
           bgt $t0, $t1, target
           ble $t0, $t1, target
           bge $t0, $t1, target
    target: nop
    """
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert len(result["machine_code"]) == (2 * 4) + 1 # 4 pseudo-branches expand to 2 instr each, plus nop

    # blt $t0, $t1, target -> slt $at, $t0, $t1; bne $at, $zero, target
    # pc=0, target=0x10. offset = (0x10 - (4+4))/4 = 8/4 = 2
    assert result["machine_code"][0]["hex"] == "0x0109082a" # slt $at, $t0, $t1
    assert result["machine_code"][1]["hex"] == "0x14200002" # bne $at, $zero, offset=2

    # bgt $t0, $t1, target -> slt $at, $t1, $t0; bne $at, $zero, target
    # pc=8, target=0x10. offset = (0x10 - (8+4))/4 = 4/4 = 1
    assert result["machine_code"][2]["hex"] == "0x0128082a" # slt $at, $t1, $t0
    assert result["machine_code"][3]["hex"] == "0x14200001" # bne $at, $zero, offset=1

    # ble $t0, $t1, target -> slt $at, $t1, $t0; beq $at, $zero, target
    # pc=0xc, target=0x10. offset = (0x10 - (c+4))/4 = 0/4 = 0
    assert result["machine_code"][4]["hex"] == "0x0128082a" # slt $at, $t1, $t0
    assert result["machine_code"][5]["hex"] == "0x10200000" # beq $at, $zero, offset=0

    # bge $t0, $t1, target -> slt $at, $t0, $t1; beq $at, $zero, target
    # pc=0x10, target=0x10. offset = (0x10 - (10+4))/4 = -4/4 = -1 (0xffff)
    assert result["machine_code"][6]["hex"] == "0x0109082a" # slt $at, $t0, $t1
    assert result["machine_code"][7]["hex"] == "0x1020ffff" # beq $at, $zero, offset=-1

    # nop
    assert result["machine_code"][8]["hex"] == "0x00000000"


# --- Directive Tests ---

def test_assemble_data_directives(assembler):
    code = """
    .data
    valB: .byte 10, -2, 0xa # Multiple byte values
    valH: .half 0x100, -1   # Half words
    valA: .asciiz "Hi!"     # Null-terminated string
    valS: .ascii "OK"       # Non-null-terminated
    .align 2                # Align to 4-byte boundary
    valW: .word 0xdeadbeef   # Word
    bigS: .space 5          # Reserve 5 bytes
    cont: .word 0x12345678
    """
    result = assembler.assemble(code)
    assert not result["errors"], f"Expected no errors, got: {result['errors']}"
    assert not result["machine_code"] # No instructions generated

    # Expected data segment content (little-endian):
    # valB: byte 10=0a, byte -2=fe, byte 0xa=0a
    # valH: half 0x100=00 01, half -1=ff ff
    # valA: asciiz "Hi!" = 48 69 21 00
    # valS: ascii "OK" = 4f 4b
    # align 2: current offset = 3+4+2 = 9 bytes. Need 3 bytes padding (9 -> c) = 00 00 00
    # valW: word 0xdeadbeef = ef be ad de
    # bigS: space 5 = 00 00 00 00 00
    # cont: word 0x12345678 = 78 56 34 12
    expected_data_hex = "0afe0a0001ffff486921004f4b000000efbeadde000000000078563412"
    assert result["data_segment"] == expected_data_hex


# --- Error Condition Tests ---

def test_invalid_register(assembler):
    code = "addi $t10, $zero, 1" # $t10 is invalid
    result = assembler.assemble(code)
    assert len(result["errors"]) >= 1 # Expect at least one error
    # Check if the specific error message is present
    assert any("Invalid register name: '$t10'" in e["message"] for e in result["errors"])


def test_undefined_label_branch(assembler):
    code = "beq $zero, $zero, missing_label"
    result = assembler.assemble(code)
    assert len(result["errors"]) >= 1
    assert any("Undefined label: 'missing_label'" in e["message"] for e in result["errors"])


def test_operand_count_error(assembler):
    code = "add $t0, $t1" # Missing one operand
    result = assembler.assemble(code)
    assert len(result["errors"]) >= 1
    assert any("Incorrect operand count for 'add'" in e["message"] for e in result["errors"])


def test_immediate_out_of_range(assembler):
    code = "addi $t0, $zero, 32768" # Max signed 16-bit is 32767
    result = assembler.assemble(code)
    assert len(result["errors"]) >= 1
    assert any("out of range for 16-bit signed" in e["message"] for e in result["errors"])


def test_branch_too_far(assembler):
    # Create a branch that exceeds the 16-bit signed offset range
    # Need approx 2^15 instructions = 32768 instructions apart
    # This is hard to test directly without huge code, focus on offset calculation logic if needed
    # For now, test a case that should work fine
    code = "beq $zero, $zero, target\n" + ".space 0x10000\n" + "target: nop" # ~64k space
    result = assembler.assemble(code)
    # This specific setup might actually work depending on address wrapping etc.
    # A better test might involve calculating the offset directly.
    # Let's test a known *failing* case if offset calculation is correct
    code_fail = "beq $zero, $zero, target\n" + ".space 0x40000\n" + "target: nop" # 256k space -> offset > 2^15 words
    result_fail = assembler.assemble(code_fail)
    assert len(result_fail["errors"]) >= 1
    assert any("Branch target 'target' (offset 65535) too far" in e["message"] for e in result_fail["errors"])


def test_duplicate_label(assembler):
    code = """
    label1: nop
    label1: addi $t0, $t0, 1
    """
    result = assembler.assemble(code)
    assert len(result["errors"]) >= 1
    assert any("Duplicate label definition: label1" in e["message"] for e in result["errors"])