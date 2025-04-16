# Sample MIPS Code
.data
my_label: .word 10       # A word variable
my_string: .asciiz "Hello\n" # A null-terminated string
.align 2                 # Align next data to 4-byte boundary
other_val: .byte -1

.text
.globl main              # Declare main as global
main:                    # Label for main program entry
  # Print the integer value
  li $v0, 1              # syscall code for print_int
  la $a0, my_label       # Load address of my_label into $a0
  lw $a0, 0($a0)         # Load word from address in $a0
  syscall                # Make the syscall

  # Print the string
  li $v0, 4              # syscall code for print_string
  la $a0, my_string      # Load address of my_string
  syscall

  # Exit program
  li $v0, 10             # syscall code for exit
  syscall
