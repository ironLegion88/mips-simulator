import React from 'react';

interface ExamplesMenuProps {
  onSelect: (code: string) => void;
}

const EXAMPLES = [
  {
    name: 'Factorial',
    code: `# Factorial (recursive)
.data
prompt: .asciiz "Enter n: "
result: .asciiz "n! = "

.text
.globl main
main:
    li $v0, 4
    la $a0, prompt
    syscall

    li $v0, 5
    syscall
    move $a0, $v0

    jal factorial
    move $t0, $v0

    li $v0, 4
    la $a0, result
    syscall

    li $v0, 1
    move $a0, $t0
    syscall

    li $v0, 10
    syscall

factorial:
    subu $sp, $sp, 8
    sw $ra, 4($sp)
    sw $a0, 0($sp)
    
    bgtz $a0, fact_recurse
    li $v0, 1
    addu $sp, $sp, 8
    jr $ra

fact_recurse:
    subu $a0, $a0, 1
    jal factorial
    lw $a0, 0($sp)
    mul $v0, $a0, $v0
    lw $ra, 4($sp)
    addu $sp, $sp, 8
    jr $ra
`
  },
  {
    name: 'Fibonacci',
    code: `# Fibonacci Sequence
.data
prompt: .asciiz "Enter n: "
newline: .asciiz "\\n"

.text
.globl main
main:
    li $v0, 4
    la $a0, prompt
    syscall

    li $v0, 5
    syscall
    move $t0, $v0
    
    li $t1, 0 # a
    li $t2, 1 # b
    li $t3, 0 # i

loop:
    bge $t3, $t0, end
    
    li $v0, 1
    move $a0, $t1
    syscall
    
    li $v0, 4
    la $a0, newline
    syscall
    
    add $t4, $t1, $t2
    move $t1, $t2
    move $t2, $t4
    
    addi $t3, $t3, 1
    j loop
    
end:
    li $v0, 10
    syscall
`
  },
  {
    name: 'Array Sum',
    code: `# Array Sum
.data
array: .word 10, 20, 30, 40, 50
length: .word 5
result: .asciiz "Sum: "

.text
.globl main
main:
    la $t0, array
    lw $t1, length
    li $t2, 0 # sum = 0
    li $t3, 0 # i = 0

loop:
    bge $t3, $t1, print_sum
    lw $t4, 0($t0)
    add $t2, $t2, $t4
    addi $t0, $t0, 4
    addi $t3, $t3, 1
    j loop

print_sum:
    li $v0, 4
    la $a0, result
    syscall

    li $v0, 1
    move $a0, $t2
    syscall

    li $v0, 10
    syscall
`
  }
];

export default function ExamplesMenu({ onSelect }: ExamplesMenuProps) {
  return (
    <div className="flex gap-2">
      <select 
        className="bg-slate-700 text-white rounded px-2 py-1" 
        onChange={(e) => {
          if (e.target.value !== "") {
            onSelect(EXAMPLES[parseInt(e.target.value)].code);
            e.target.value = "";
          }
        }}
      >
        <option value="">Load Example...</option>
        {EXAMPLES.map((ex, idx) => (
          <option key={idx} value={idx}>{ex.name}</option>
        ))}
      </select>
    </div>
  );
}
