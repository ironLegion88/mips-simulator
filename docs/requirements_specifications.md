# MIPS32 Interactive Simulator & Visualizer: Product Specification

- **Document type:** Normative product requirements and system specification
- **Status:** Draft for implementation
- **Version:** 2.0.0
- **Last updated:** 2026-09-14
- **Product scope:** Full-stack MIPS32 IDE, Cycle-Accurate Simulator, and Hardware Visualizer
- **Supported frontend:** React/Next.js workspace with Monaco, React Flow, and Cosmos.gl
- **Reasoning target:** MIPS32 Release 1 & 2, Coprocessor 0, Coprocessor 1, MMU, and Cache Hierarchy

The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative. A requirement identified with a stable ID is testable unless it is explicitly marked as a future extension.

## 1. Purpose

This document defines the final intended behavior and architecture of the standalone MIPS32 Interactive Simulator and Visualizer. The application allows users to write, assemble, debug, visualize, and profile MIPS assembly code in a highly educational and architecturally accurate environment. It goes beyond simple ISA execution by providing a transparent window into cycle-accurate microarchitecture, pipeline hazards, branch prediction, and multi-level memory caching.

The product is the complete vertical slice:
```text
Workspace Frontends (Simulator, Hardware, Memory, Profiler)
        |
Public REST / WebSocket API
        |
Debugging and Orchestration Services
        |
Cycle-Accurate CPU Core + MMU + Cache Simulators
        |
Two-Pass Macro Assembler & Disassembler
```

## 2. Product Definition

The Simulator is an educational and architectural exploration application with a unified modular frontend encompassing four core modes:
1. **IDE / Debugger Mode:** Monaco-based editor with breakpoints, live register matrices, and I/O.
2. **Datapath Mode:** React Flow / SVG powered visualization of Single-Cycle and 5-Stage Pipelined datapaths.
3. **Memory / Cache Mode:** Hex editor, stack visualizer, and dynamic set-associative cache mappings.
4. **Profiler Mode:** Metrics dashboard showing CPI, hazard stalls, prediction accuracy, and cache hit rates.

## 3. Goals

### PG-001 Architectural transparency
The application MUST expose internal CPU states (pipeline latches, forwarding paths, TLB entries) rather than just final register mutations.

### PG-002 Cycle-accurate simulation
The execution engine MUST support a cycle-accurate mode that models stalls, flushes, and multi-cycle execution alongside the fast instruction-accurate mode.

### PG-003 Time-travel debugging
Users MUST be able to step backward in time, reversing register, memory, and pipeline state deterministically.

### PG-004 Advanced assembly support
The assembler MUST support macros, multiple files/modules, custom linker scripts, and extensive pseudoinstruction expansion.

### PG-005 Storage and platform independence
No public client contract may depend on the underlying host OS. All memory-mapped I/O and file syscalls MUST be strictly virtualized.

## 4. Non-Goals

### PNG-001 Operating System booting
The simulator is not intended to boot Linux or a full OS. It executes bare-metal MIPS user-space applications with SPIM/MARS compatible syscall emulation.

### PNG-002 Unlimited unbounded execution tracing
While time-travel debugging is supported, maintaining a cycle-by-cycle trace of a 1-billion instruction loop is not a requirement. History buffers MUST be bounded.

## 5. Users And Primary Workflows

### Personas
- **Student:** Writes simple assembly, uses step-by-step debugging to understand instructions and stack frames.
- **Computer Architecture Learner:** Inspects pipeline hazards, cache misses, and forwarding paths.
- **Instructor/Curator:** Creates pre-loaded examples, assignments, and architectural scenarios.

### UW-001 Write and assemble multi-file code
A user MUST be able to author multiple `.s` files, use macros, and assemble them into a single virtual memory space with clear syntax error highlighting.

### UW-002 Step-by-step pipeline inspection
A user MUST be able to execute a single clock cycle and observe data moving through the IF, ID, EX, MEM, WB stages, including hazard unit interventions.

### UW-003 Diagnose a cache miss
A user MUST be able to run a matrix multiplication algorithm and visually observe spatial/temporal locality effects in the Cache Visualizer.

### UW-004 Time-travel debugging
A user MUST be able to hit a breakpoint, realize they overshot the bug, and step backward 10 instructions to inspect the prior state.

### UW-005 Interact with Memory-Mapped I/O
A user MUST be able to type on a simulated keyboard mapped to `0xFFFF0000` and see interrupts trigger exception handlers.

## 6. System Architecture

### AR-101 Client-Server isolation
The frontend MUST communicate via REST (for static assemblies) and WebSockets (for live cycle-by-cycle execution streams and time-travel).

### AR-102 Modular CPU backend
The Python simulation core MUST separate the Instruction Set Architecture (ISA) execution logic from the Microarchitecture (Pipeline/Cache) timing models.

### AR-103 Pluggable memory hierarchy
The MMU MUST support dynamic injection of L1i, L1d, and L2 cache objects that intercept load/store requests before reaching main memory.

## 7. Assembler & Disassembler (The Compiler Frontend)

### AD-001 ISA Coverage
The assembler MUST support all MIPS32 Release 1 & 2 user-mode instructions, Coprocessor 0 (System) instructions, and Coprocessor 1 (FPU) instructions.

### AD-002 Macro system
The assembler MUST support defining macros with `%macro` and `%end_macro`, supporting parameterized arguments.

### AD-003 Multi-file linking
The assembler MUST resolve `.extern` and `.globl` symbols across multiple uploaded files.

### AD-004 Directives
MUST support `.data`, `.text`, `.kdata`, `.ktext`, `.word`, `.half`, `.byte`, `.float`, `.double`, `.ascii`, `.asciiz`, `.space`, `.align`.

### AD-005 Two-way bit-field decoding
The disassembler MUST generate a metadata payload mapping every 32-bit word to its visual bit-fields (opcode, rs, rt, rd, shamt, funct, imm) for UI tooltips.

## 8. CPU Simulation Core (The Execution Backend)

### EX-001 Execution Modes
MUST support Fast (Instruction-accurate, max IPC), Pipelined (Cycle-accurate), and Reverse (Time-travel) modes.

### EX-002 General & Special Registers
MUST simulate `$0-$31`, `HI`, `LO`, and `PC`. `$0` MUST remain hardwired to zero.

### EX-003 Coprocessor 0 (Exceptions & Interrupts)
MUST implement `Status`, `Cause`, `EPC`, `BadVAddr`. MUST route division by zero, unaligned access, and syscalls to `0x80000180`.

### EX-004 Coprocessor 1 (FPU)
MUST implement 32 single-precision registers (`$f0-$f31`). MUST support IEEE-754 arithmetic, conversions, and FCC branching (`bc1t`, `bc1f`).

### EX-005 Memory-Mapped I/O (MMIO)
MUST reserve `0xFFFF0000` for virtual devices (Terminal Receiver/Transmitter control and data registers).

### EX-006 Virtual File System (Syscalls)
MUST support SPIM/MARS syscalls (1-17). File I/O (13,14,15,16) MUST interact with a sandboxed in-memory VFS, not the host OS.

## 9. Microarchitecture & Pipeline Visualization

### MV-001 Single-Cycle Datapath
MUST provide a structural representation where one instruction completes per cycle, highlighting active paths in Blue (Data) and Red (Control).

### MV-002 5-Stage Pipelined Datapath
MUST model IF, ID, EX, MEM, WB. MUST expose inter-stage latch contents (e.g., `ID/EX.IR`, `EX/MEM.ALUOut`).

### MV-003 Data Hazards & Forwarding
MUST detect RAW hazards. MUST visually animate data forwarding from EX/MEM to ALU input, or MEM/WB to ALU input.

### MV-004 Control Hazards & Branch Prediction
MUST model pipeline flushes on mispredict. MUST support configurable predictors (Always Taken, Always Not Taken, 1-bit BHT, 2-bit BHT).

## 10. Memory Hierarchy & Cache Simulation

### MC-001 Configuration
Users MUST be able to configure L1 Data and Instruction cache size, block size, and associativity (Direct, N-Way, Fully).

### MC-002 Cache Metrics
MUST track Read Hits, Read Misses, Write Hits, Write Misses, and Evictions.

### MC-003 Write Policies
MUST support configuring Write-Through (with write buffer) vs. Write-Back (with dirty bits) policies.

### MC-004 Visual Cache Explorer
The frontend MUST render the cache as a grid of sets and ways, highlighting valid, dirty, tag, and data blocks. Green highlights MUST denote hits; Red MUST denote misses/evictions.

## 11. Debugging & IDE Experience

### ID-001 Monaco Editor Integration
MUST provide syntax highlighting, error squiggles, and hover documentation for all MIPS mnemonics.

### ID-002 Breakpoints & Watchpoints
MUST support standard PC line breakpoints and data watchpoints (halt when memory address `X` is written/read).

### ID-003 Time-Travel Buffer
The backend MUST retain a sliding window of the last N=1000 state diffs, enabling the `Step Backward` UI button.

### ID-004 Dynamic Stack Visualizer
MUST pin the memory view to `$sp` and dynamically grow/shrink, annotating stack frames based on `jal` and `$fp` usage.

## 12. Performance & Metrics (Profiler Mode)

### PM-001 Execution Dashboard
MUST display real-time CPI (Cycles Per Instruction), total cycles, total instructions, and frequency.

### PM-002 Hazard Breakdown
MUST chart stall cycles categorized by Data Hazard (Load-Use) and Control Hazard (Mispredict).

### PM-003 Cache Efficacy
MUST chart spatial and temporal locality hit rates over time.

## 13. Security and Abuse Protection

### SC-001 Bounded Execution
Continuous run MUST have a configurable timeout and max-instruction limit to prevent infinite loops from hanging the backend worker.

### SC-002 Payload Limits
API requests MUST enforce strict payload size limits for assembly uploads to prevent memory exhaustion.
