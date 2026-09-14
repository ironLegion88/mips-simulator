UI and UX of a web application based MIPS32 Assembler/Dissassembler cum Simulator. I am thinking of something like this, but I want an excellent UI with an intuitive and seamless user experience.

This is a frontend for an interactive web-based MIPS32 ISA Simulator and Visualizer. The frontend should have the following interactive visualization components:

- Editor: A code editor where the user can write and edit MIPS32 assembly code.
- Multi-Format Output: View assembled machine code in Hexadecimal, Binary, or Decimal.
- Disassembler: Convert 32-bit machine code back into human-readable MIPS assembly.
- Real-Time State Display: All registers and relevant memory sections are displayed and updated after each step.
- Change Highlighting: Registers and memory words that were modified by the last instruction are briefly highlighted in green for easy tracking.
- Active Instruction Highlighting: The current line of code about to be executed (based on the PC) is highlighted in the editor.
- Stack Visualization: The memory view automatically displays the region around the stack pointer ($sp), making it easy to visualize stack operations like push (sw) and pop (lw).
- I/O Console: A persistent console displays all program output and provides a prompt for input when required by read_* syscalls.
- Graphical Hardware View: Graphical blocks for the ALU, Register File, and Memory to visually trace the data-path for each instruction.
- A library of pre-loaded code examples (e.g., factorial, array sorting).
- Code export functionality (.s, .hex).
- Tooltips and help modals explaining instructions and concepts.
- Advanced Debugging: Support for setting breakpoints in the code editor.
- Floating-Point Support: The FPU (Coprocessor 1) registers and floating-point instructions.
- UI/UX Focus: The user interface should have polished and modern aesthetic, with seamless mobile responsiveness. The UI should not look cluttered, there can be different modes for different functionalities to avoid that.

The frontend should have the following viewing modes:

- Main view: The main simulator view. It should have a code editor, the I/O console, the memory stack, all the registers (both FP and non-FP), a high level visualization with all the hardware blocks (memory, ALU, PC, FP, etc.) showing the flow of program and data throughout the execution. 
- The converter view: It should have a code editor, and the output block with the option to select the output format (HEX, Binary, etc.), with the screen split between the two blocks.
- Detailed Hardware View: An in-depth view detailing and tracing every step of data-flow, and control-flow of the program through all the different hardware blocks and through the different components of block. This should have the entire MIPS32 processor architecture broken down into pieces showcasing the program running througout.
- Memory View: This should have the same level of detailed views, but focusing on the memory.