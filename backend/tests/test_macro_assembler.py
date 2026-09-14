import pytest
from backend.mips_assembler import MipsAssembler
from backend.mips_preprocessor import MipsPreprocessor

def test_macro_preprocessor():
    files = [{
        'filename': 'test.s',
        'content': '''
        %macro add_three(dst, src1, src2, src3)
            add dst, src1, src2
            add dst, dst, src3
        %end_macro
        
        main:
            add_three($t0, $t1, $t2, $t3)
        '''
    }]
    preprocessor = MipsPreprocessor()
    lines = preprocessor.preprocess(files)
    assert not preprocessor.errors
    texts = [l['text'].strip() for l in lines if l['text'].strip()]
    assert texts == ['main:', 'add $t0, $t1, $t2', 'add $t0, $t0, $t3']

def test_macro_assembler():
    assembler = MipsAssembler()
    files = [{
        'filename': 'main.s',
        'content': '''
        %macro push(reg)
            addi $sp, $sp, -4
            sw reg, 0($sp)
        %end_macro
        
        %macro pop(reg)
            lw reg, 0($sp)
            addi $sp, $sp, 4
        %end_macro
        
        main:
            li $t0, 5
            push($t0)
            pop($t1)
        '''
    }]
    res = assembler.assemble(files)
    assert not res['errors']
    assert len(res['machine_code']) == 5 # li expands to 1 (5 fits in 16-bit), push to 2, pop to 2.
    
    # Check that multi file extern/globl resolves fine.
    # main.s calls a function in lib.s
    multi_files = [
        {
            'filename': 'main.s',
            'content': '''
            .extern my_var
            .text
            .globl main
            main:
                la $t0, my_var
                lw $t1, 0($t0)
                jal my_func
            '''
        },
        {
            'filename': 'lib.s',
            'content': '''
            .data
            .globl my_var
            my_var: .word 42
            
            .text
            .globl my_func
            my_func:
                add $v0, $t1, $t1
                jr $ra
            '''
        }
    ]
    res_multi = assembler.assemble(multi_files)
    assert not res_multi['errors']
    assert len(res_multi['data_segment']) == 8 # 42 in a word, padded due to base addresses? wait, base is 0x10010000, 42 is one word, length=4 (wait, hex string is 8 chars).
