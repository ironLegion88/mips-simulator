# backend/tests/test_assembler.py
import pytest
# Import relative to the project root, assuming pytest runs from there
from backend.mips_assembler import MipsAssembler

@pytest.fixture
def assembler():
    return MipsAssembler()

def test_assemble_addi(assembler):
    code = "addi $t0, $zero, 100"
    result = assembler.assemble(code)
    assert not result["errors"]
    assert result["machine_code"] == ["0x20080064"] # opcode=8, rs=0, rt=8, imm=100

def test_assemble_add(assembler):
    code = "add $s0, $t1, $t2"
    result = assembler.assemble(code)
    assert not result["errors"]
    assert result["machine_code"] == ["0x012a8020"] # opcode=0, rs=9, rt=10, rd=16, shamt=0, funct=0x20

def test_assemble_j(assembler):
    # Requires label resolution
    code = """
    start: j end
           nop
    end:   nop
    """
    result = assembler.assemble(code)
    assert not result["errors"]
    # Assuming start is 0x00400000, first nop is 0x00400004, end is 0x00400008
    # j end -> opcode=2, target=(0x00400008 >> 2) & 0x3FFFFFF = 0x00100002
    # Expected: j instruction (0x08000000 | target) -> 0x08100002
    # nop (sll $0,$0,0) -> 0x00000000
    assert result["machine_code"] == ["0x08100002", "0x00000000", "0x00000000"]

def test_assemble_li(assembler):
     code = "li $t0, 65537" # Requires lui/ori expansion (0x10001)
     result = assembler.assemble(code)
     assert not result["errors"]
     # Expected:
     # lui $at, 1   (0x3c010001)
     # ori $t0, $at, 1 (0x34280001)
     assert result["machine_code"] == ["0x3c010001", "0x34280001"]

def test_invalid_register(assembler):
    code = "addi $t10, $zero, 1" # $t10 is invalid
    result = assembler.assemble(code)
    assert len(result["errors"]) == 1
    assert "Invalid register name: $t10" in result["errors"][0]["message"]

# Add many more tests for R/I/J types, pseudo-ops, labels, directives, errors...