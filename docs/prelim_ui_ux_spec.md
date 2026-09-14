Here is a comprehensive UI/UX design specification for the web-based **MIPS32 Assembler, Disassembler, & Visual Simulator**.

This design minimizes UI clutter by utilizing a **4-Mode Modular Workspace Shell** powered by resizable panes, deep dark-mode aesthetic styling (popular in modern IDEs like VS Code and Figma), and interactive visual micro-animations.

---

# 1. Global Application Shell & Design System

### Visual Language & Aesthetics
* **Theme:** Dark Mode default (Slate `#0F172A` background, Charcoal `#1E293B` panel cards). High contrast creates optimal visibility for animated datapath signals and glowing state changes.
* **Typography:** 
  * **Code & Data:** `JetBrains Mono` or `Fira Code` (with ligature support for registers like `$t0`).
  * **UI & Labels:** `Inter` or `SF Pro Display`.
* **Color Hierarchy:**
  * **Brand / Accent:** Electric Cyan (`#06B6D4`) & Indigo (`#6366F1`)
  * **Modified Registers/Memory:** Emerald Green Glow (`#10B981`)
  * **Active Instruction/PC:** Soft Amber/Yellow highlight (`#F59E0B`)
  * **Breakpoints:** Crimson Red (`#EF4444`)
  * **Data-Path Control Signals:** Glowing Cyan (Data) and Violet (Control Lines)

### Persistent Top Navigation Header
```
+--------------------------------------------------------------------------------------------------------+
| [MIPS Studio]  [ Simulator | Converter | Hardware | Memory ]  [Examples v] | [⏪ ⏸️ ▶️ ⏭️ 🔄] [Speed 🎚️] | [Export v] [⚙️] |
+--------------------------------------------------------------------------------------------------------+
```
1. **Logo & Workspace Mode Switcher:** Segmented pill tabs to instantly toggle between the **4 Viewing Modes**.
2. **Preset Examples Library:** Dropdown menu preloaded with annotated code samples (`Factorial (Recursive)`, `Array BubbleSort`, `String Reverse`, `Floating-Point Matrix Multi`, `Stack Operations`).
3. **Execution Controls (Sticky):** 
   * `Step Back (Undo)` | `Pause` | `Play / Run` | `Step Forward (Clock Cycle)` | `Reset`
   * `Execution Speed Slider` (1 Hz up to Unlimited/Max speed).
4. **Export & Settings Drawer:** Export `.s` assembly, `.hex` raw machine code, `.bin`, or high-res SVG export of the hardware datapath.

---

# 2. Detailed Viewing Modes Architecture

---

## View Mode 1: Main Simulator View

Designed for rapid coding, step-by-step stepping, state inspection, and live execution tracing.

```
+---------------------------------------------------+----------------------------------------------------+
| CODE EDITOR (Monaco)              | Breakpoint    | REGISTERS PANEL                                    |
|---------------------------------------------------| [ GPR ($0-$31) ]  [ FP ($f0-$f31) ]  [ PC / HI / LO ]  |
| 1  | .data                                        |----------------------------------------------------|
| 2  | msg: .asciiz "Result: "                      | $zero: 0x00000000   $t0: 0x0000000A [GREEN FLASH]   |
| 3➔ | .text                                        | $at  : 0x00000000   $t1: 0x00000005                  |
| 4  | main:                                        | $v0  : 0x00000001   $sp: 0x7FFFFFFC                  |
| 5🛑|   addi $t0, $zero, 10                         |----------------------------------------------------|
| 6  |   addi $t1, $zero, 5                         | HIGH-LEVEL HARDWARE DATA FLOW (Mini Visualizer)    |
| 7  |   add  $t2, $t0, $t1                         | [PC] ➔ [Instruction Mem] ➔ [Reg File] ➔ [ALU] ➔ [Mem]
+---------------------------------------------------+----------------------------------------------------+
| I/O CONSOLE                                       | STACK VISUALIZER ($sp Pointer Auto-Focus)          |
| > Program started...                              | Address    | Value       | Variable/Annotation    |
| > Enter number: 10                                | 0x7FFFFFFC | 0x0000000A  | Saved $ra              |
| > Result: 15                                      | 0x7FFFFFF8 | 0x00000005  | Saved $fp              |
+---------------------------------------------------+----------------------------------------------------+
```

### Layout Breakdown & Components
1. **Left Top Pane – Code Editor (Monaco/VS Code Engine):**
   * **Gutter:** Clickable red dot breakpoints.
   * **Active Line Marker:** Highlighted row with a yellow left-arrow (`➔`) indicating the next instruction to execute (linked directly to the Program Counter `$pc`).
   * **Hover Tooltips:** Hovering over any instruction (e.g., `jal`) pops up syntax, bitwise operation format, and execution details.
2. **Right Top Pane – Register Matrix:**
   * **Tabs:** General Purpose Registers (`$0-$31`), Floating Point Coprocessor 1 (`$f0-$f31`), and Control Registers (`PC`, `HI`, `LO`).
   * **State Highlighting:** Any register modified in the last clock cycle pulses with an **Emerald Green Flash** that slowly fades over 1 second.
   * **Format Toggle:** Toggle display format for values (Hexadecimal, Signed Decimal, Unsigned Decimal, Binary, or IEEE-754 Single/Double Float).
3. **Right Middle Pane – High-Level Data Flow Mini Map:**
   * Live simplified diagram showing data movement across PC ➔ Reg File ➔ ALU ➔ Data Memory for the current instruction.
4. **Bottom Left Pane – Persistent I/O Console:**
   * Handles MIPS `syscall` routines (`print_int`, `print_string`, `read_int`, etc.).
   * Displays prompt inputs inline with custom colored output (Red for system errors, Green for normal input/output).
5. **Bottom Right Pane – Stack Visualizer:**
   * Automatically pins view focus around current `$sp` (Stack Pointer).
   * Visualizes stack frames growing downwards with annotations showing saved registers (`$ra`, `$fp`) or local variables.

---

## View Mode 2: Converter / Assembler View

Focuses on translation between human-readable MIPS assembly and raw 32-bit machine code instructions.

```
+---------------------------------------------------+----------------------------------------------------+
| SOURCE ASSEMBLY EDITOR                            | ASSEMBLED MACHINE CODE OUTPUT                      |
| [ Mode Switch: Assembly ➔ Machine Code ]           | Format: [ HEX | BINARY | DECIMAL ]                 |
|---------------------------------------------------|----------------------------------------------------|
| 1 | addi $t0, $s0, 4                              | Line 1: 0x22080004                                 |
| 2 | lw   $t1, 0($t0)                              | Line 2: 0x8D090000                                 |
| 3 | sub  $s1, $t1, $t2                            | Line 3: 0x012A8822                                 |
|                                                   |----------------------------------------------------|
|                                                   | INSTRUCTION FIELD DECODER (Active Line 1 Selected) |
|                                                   | Type: I-Type | Opcode: 001000 (addi)              |
|                                                   | rs: 10000 ($s0) | rt: 01000 ($t0) | Immediate: 0x0004|
+---------------------------------------------------+----------------------------------------------------+
```

### Key UI/UX Features
* **Two-Way Conversion (Assembler & Disassembler):**
  * **Assemble Mode:** Write Assembly on the left ➔ Output binary/hex on the right.
  * **Disassemble Mode:** Paste hex strings/binary stream on the right ➔ Output readable MIPS assembly on the left.
* **Interactive Instruction Breakdown Grid (Educational Focus):**
  * Clicking any line of machine code expands a colored **Bit-Field Decoding Bar** below it showing the breakdown:
    * **R-Type:** `Opcode [6]` | `rs [5]` | `rt [5]` | `rd [5]` | `shamt [5]` | `funct [6]`
    * **I-Type:** `Opcode [6]` | `rs [5]` | `rt [5]` | `Immediate [16]`
    * **J-Type:** `Opcode [6]` | `Target Address [26]`
  * Hovering over a bit field in the decoder highlights the corresponding assembly operand in the source code!

---

## View Mode 3: Detailed Hardware View

Provides an interactive microarchitectural schematic of the MIPS32 Data-Path and Control-Path (Single-Cycle and 5-Stage Pipelined Architecture option).

```
+--------------------------------------------------------------------------------------------------------+
| DETAILED PROCESSOR DATAPATH SIMULATOR                                 [ View: Single-Cycle | Pipelined ] |
+--------------------------------------------------------------------------------------------------------+
|                                                                                                        |
|  +-------+     +---------------+     +--------------+      +---------+      +-------------+            |
|  |   PC  | ──> | Instruction   | ──> | Register File| ───> |   ALU   | ───> | Data Memory |            |
|  +-------+     |    Memory     |     |  Read / Write|      | (ALUOut)|      | Read / Write|            |
|                +---------------+     +--------------+      +---------+      +-------------+            |
|                        │                    │                   ▲                     │                |
|                        ▼                    ▼                   │                     ▼                |
|               +---------------------------------------------------+                                    |
|               |                   CONTROL UNIT                    |                                    |
|               | RegDst=0 | ALUSrc=1 | MemtoReg=0 | RegWrite=1       |                                    |
|               +---------------------------------------------------+                                    |
+--------------------------------------------------------------------------------------------------------+
| LIVE CONTROL SIGNALS & DATA BUS VALUES                                                                 |
| PC: 0x00400004  |  Instruction: 0x2008000A  |  Read Data 1: 0x00000000  | ALU Result: 0x0000000A            |
+--------------------------------------------------------------------------------------------------------+
```

### Visual & Interactive Features
* **Animated Datapath Lines:**
  * Animated glowing particles flow along active wire paths (e.g., when reading memory, the path from Data Memory to MUX to Register File lights up with moving pulse animations).
* **Control Unit Signal Table:**
  * Displays real-time binary/boolean state of control signals (`RegDst`, `ALUSrc`, `MemtoReg`, `RegWrite`, `MemRead`, `MemWrite`, `Branch`, `ALUOp`).
* **Zoom & Pan Canvas:**
  * Powered by SVG/HTML5 Canvas with infinite pan/zoom controls, allowing users to zoom into specific components (e.g., internal architecture of the ALU or MUXes).
* **FPU Extension Toggle:**
  * Toggle view switch to include Coprocessor 1 (Floating Point Unit) hardware layout connected via the MIPS coprocessor bus.

---

## View Mode 4: Memory View

A deep-dive spatial representation of the full MIPS32 4GB Virtual Address Space.

```
+----------------------------------------------------+---------------------------------------------------+
| MEMORY SEGMENT MAP                                 | LIVE HEX & ASCII MEMORY EDITOR                    |
|----------------------------------------------------| Search Address / Label: [ 0x10010000          🔍 ]|
| [ Stack Segment ]  0x7FFFFFFF down                 |---------------------------------------------------|
|   ▲ (Dynamic Growth)                               | Address    | +0 +1 +2 +3 | +4 +5 +6 +7 | ASCII      |
| [ Heap Segment  ]  0x10040000 up                   |---------------------------------------------------|
|   ▼ (Dynamic Growth)                               | 0x10010000 | 48 65 6C 6C | 6F 20 57 6F | Hello Wo   |
| [ Static Data   ]  0x10010000 (.data)              | 0x10010008 | 72 6C 64 00 | 00 00 00 00 | rld.       |
| [ Text Segment  ]  0x00400000 (.text)              | 0x10010010 | 00 00 00 0A | 00 00 00 05 | ........   |
| [ Reserved      ]  0x00000000                      +---------------------------------------------------+
|                                                    | CACHE & ALIGNMENT ANALYZER (Optional View)        |
| Selected Region: .data (0x10010000 - 0x1001FFFF)   | Direct Mapping | Block Size: 4 Words | Hits: 12   |
+----------------------------------------------------+---------------------------------------------------+
```

### Key UI/UX Features
* **Segment Selector Bar:** Quick-jump buttons for standard MIPS regions: `.text` (Code), `.data` (Variables), `.heap` (Dynamic `sbrk`), `.stack` (Stack pointer region).
* **Modified Memory Glow:** Memory cells updated by `sw`, `sb`, or `s.s` instructions turn **Emerald Green** and fade back to neutral gray over execution steps.
* **Inline Word Editing:** Double-clicking any memory cell opens an inline editor to manually modify memory bytes during debugging.
* **Alignment Guidance:** Highlights 4-byte word boundary alignment issues in red if unaligned access occurs (`lw`/`sw`).

---

# 3. Micro-Interactions & UX Details

1. **Contextual Help & Instruction Tooltips:**
   * Hovering over any instruction mnemonic anywhere in the UI displays a floating card:
     * *Example:* `lw $t0, 4($s0)`
     * *Popover:* **Load Word (I-Type)**: `$t0 = Memory[$s0 + 4]`. Loads a 32-bit word from memory address into register `$t0`.
2. **Keyboard Shortcuts for Power Users:**
   * `F5`: Run / Pause execution.
   * `F10`: Step forward (1 Instruction).
   * `F9`: Toggle Breakpoint on current line.
   * `Ctrl + Shift + A`: Quick-switch to Assembler Converter mode.
   * `Ctrl + K`: Open Command Palette for quick search of instructions, documentation, or settings.
3. **Responsive Mobile & Tablet View Strategy:**
   * On smaller screens (Tablets/Mobile Devices), split-pane grids collapse into a **Tabbed Mobile Layout**:
     * Tabs: `[ Editor ]` | `[ Registers ]` | `[ Console/Stack ]` | `[ Hardware ]`.
     * Control Bar collapses into a sticky floating bottom drawer for easy thumb execution during mobile testing.

---

# 4. Recommended Frontend Tech Stack

| Component | Recommended Technology / Library | Purpose |
| :--- | :--- | :--- |
| **UI Framework** | React.js / Next.js or SvelteKit | Component architecture and fast reactive state management. |
| **Code Editor** | `@monaco-editor/react` | VS Code-grade code editor with custom MIPS syntax highlighting & breakpoints. |
| **Hardware Visualizer** | React Flow / Canvas API / SVG | Drag/zoom canvas with animated edges for hardware datapath tracing. |
| **Styling & Icons** | Tailwind CSS + Lucide Icons | Clean modern dark-mode utility classes with sleek visual icons. |
| **State Management** | Zustand or Redux Toolkit | Fast global state sync between registers, memory, line highlights, and CPU clock cycles. |
| **MIPS Core Engine** | WebAssembly (C/C++ core) or TypeScript Engine | Executes MIPS instructions, syscalls, and disassembles machine code in real time. |