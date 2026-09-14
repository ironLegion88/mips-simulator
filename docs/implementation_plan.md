# MIPS32 Interactive Simulator: Complete Implementation Plan

- **Document type:** Delivery and implementation plan
- **Status:** Draft for execution
- **Version:** 2.0.0
- **Last updated:** 2026-09-14
- **Requirements baseline:** [MIPS32 Interactive Simulator Specification](requirements_specifications.md)

## 1. Purpose

This document translates the massive product specification into five dependency-gated development sprints. Each sprint delivers a testable, vertical slice of the application.

1. **Sprint 1:** Advanced Execution Architecture & Multi-file Assembler.
2. **Sprint 2:** Memory Hierarchy, Caching, and Coprocessors (FPU, System).
3. **Sprint 3:** The IDE, Time-Travel Debugger, and Global UI Shell.
4. **Sprint 4:** Microarchitecture, Pipeline, and React Flow Hardware Visualization.
5. **Sprint 5:** Profiler, Metrics, MMIO, and Polish.

## 2. Planning Principles

### IP-001 Requirement-driven delivery
Every task MUST reference requirement IDs from the product specification. 

### IP-002 Vertical validation
Each sprint MUST end with an executable validation.

### IP-003 Bounded-by-default behavior
No sprint may introduce unbounded history buffers, unlimited execution times, or unbounded memory allocations.

## 3. Shared Definition Of Done
A story is complete only when:
- Backend and Frontend unit tests pass.
- Public errors contain no sensitive implementation details.
- Performance behavior (CPI, caching algorithms) matches verified architectural models.
- UI components are accessible and responsive.

---

## 4. Sprint 1: Advanced Execution Architecture & Assembler

### 4.1 Epic: The Macro Assembler [Req: AD-001 to AD-004]
* **[x] Task S1-E1-T1: Multi-file & Linker Support**
  * *File:* `backend/mips_assembler.py`
  * *Action:* Refactor `assemble` to accept a list of file payloads. Implement a global symbol table resolving `.globl` and `.extern` across files.
* **[x] Task S1-E1-T2: Macro Engine Implementation**
  * *File:* `backend/mips_preprocessor.py` (New)
  * *Action:* Implement a pre-pass that parses `%macro name(args)` and `%end_macro`, performing text substitution before Pass 1.

### 4.2 Epic: The Instruction-Accurate Core [Req: EX-001, EX-002]
* **[x] Task S1-E2-T1: Refactoring the Execution Loop**
  * *File:* `backend/mips_simulator.py`
  * *Action:* Decouple fetch, decode, and execute logic into modular methods to prepare for pipelining. Implement an execution generator `yield_state()` for WebSocket streaming.

---

## 5. Sprint 2: Memory Hierarchy, Cache, & Coprocessors

### 5.1 Epic: Configurable Cache Simulator [Req: MC-001 to MC-004]
* **Task S2-E1-T1: Cache Data Structures**
  * *File:* `backend/cache_simulator.py` (New)
  * *Action:* Build classes `CacheLine`, `CacheSet`, `CacheLevel`. Implement `read(addr)` and `write(addr)` returning `Hit/Miss/Evict` and the latencies.
* **Task S2-E1-T2: Replacement & Write Policies**
  * *File:* `backend/cache_simulator.py`
  * *Action:* Implement LRU, FIFO, and Random eviction algorithms. Implement Write-Through vs Write-Back logic (dirty bit tracking).

### 5.2 Epic: Coprocessor 0 & 1 [Req: EX-003, EX-004]
* **Task S2-E2-T1: FPU Registers & Arithmetic**
  * *File:* `backend/mips_fpu.py` (New)
  * *Action:* Implement `$f0-$f31`. Implement IEEE-754 arithmetic (`add.s`, `sub.d`) handling NaN, Infinity, and denormals gracefully via Python's `struct` and `math` libraries.
* **Task S2-E2-T2: Exception Routing**
  * *File:* `backend/mips_coproc0.py` (New)
  * *Action:* Implement `Cause`, `Status`, `EPC`. Catch Python `ZeroDivisionError` or MMU `UnalignedAccessError`, populate `Cause`, and set `PC = 0x80000180`.

---

## 6. Sprint 3: The IDE, Time-Travel Debugger, and Global UI

### 6.1 Epic: The 4-Mode Shell & Editor [Req: UI-1, ID-001]
* **Task S3-E1-T1: Global Header & Zustand Router**
  * *File:* `frontend/src/components/Shell.tsx`
  * *Action:* Implement Tailwind-styled top navigation. Use Zustand to switch rendering between Simulator, Datapath, Memory, and Profiler modes.
* **Task S3-E1-T2: Monaco Integration & Tooltips**
  * *File:* `frontend/src/components/Editor.tsx`
  * *Action:* Register the `mips` language. Feed the Disassembler's bit-field metadata into Monaco's `hoverProvider` to show instruction breakdowns on hover.

### 6.2 Epic: Time-Travel & Debugging [Req: PG-003, ID-003]
* **Task S3-E2-T1: State History Buffer**
  * *File:* `backend/mips_simulator.py`
  * *Action:* Create a fixed-size `collections.deque`. On each cycle, append a delta of changed registers and memory addresses.
* **Task S3-E2-T2: Stepping Controls**
  * *File:* `frontend/src/components/ExecutionControls.tsx`
  * *Action:* Implement `Play`, `Pause`, `Step Over`, `Step Into`, and `Step Back`. Bind WebSockets to trigger history popping on `Step Back`.

---

## 7. Sprint 4: Microarchitecture & React Flow Visualizer

### 7.1 Epic: The Cycle-Accurate Engine [Req: MV-002, MV-003]
* **Task S4-E1-T1: 5-Stage Pipeline Modeling**
  * *File:* `backend/mips_pipeline.py` (New)
  * *Action:* Implement latches `IF_ID`, `ID_EX`, `EX_MEM`, `MEM_WB`. Simulate one clock tick moving instructions across latches.
* **Task S4-E1-T2: Hazard Unit & Branch Predictor**
  * *File:* `backend/mips_pipeline.py`
  * *Action:* Detect `ID_EX.MemRead` matching `IF_ID.rs/rt` for stalls. Implement static/dynamic branch prediction tables and flush logic on mispredict.

### 7.2 Epic: Datapath React Flow Canvas [Req: MV-001]
* **Task S4-E2-T1: Blueprint Nodes & Edges**
  * *File:* `frontend/src/components/DatapathCanvas.tsx`
  * *Action:* Use React Flow to layout ALU, Registers, MUXes, and Memory. Define explicit SVG edges for Data and Control signals.
* **Task S4-E2-T2: Live Signal Animation**
  * *File:* `frontend/src/hooks/useSignalAnimator.ts`
  * *Action:* Subscribe to WebSocket pipeline state. If `RegWrite` is 1, apply CSS marching-ants animation to the Writeback wire path.

---

## 8. Sprint 5: Profiler, MMIO, and Polish

### 8.1 Epic: Performance Profiler Mode [Req: PM-001 to PM-003]
* **Task S5-E1-T1: Chart.js Metrics Dashboard**
  * *File:* `frontend/src/components/Profiler.tsx`
  * *Action:* Render pie charts for Hazard breakdowns (Data vs Control), Line charts for Cache Hit Rates over time, and a KPI block for overall CPI.

### 8.2 Epic: Virtual File System & MMIO [Req: EX-005, EX-006]
* **Task S5-E2-T1: Keyboard & Terminal MMIO**
  * *File:* `backend/mips_mmu.py`, `frontend/src/components/Terminal.tsx`
  * *Action:* Map frontend terminal keystrokes to WebSocket events, writing to `0xFFFF0000`. Trigger hardware interrupt in Coprocessor 0.
* **Task S5-E2-T2: Virtual File System Sandbox**
  * *File:* `backend/vfs.py`
  * *Action:* Intercept syscalls 13-16. Route read/write requests to a Python dictionary representing virtual file descriptors.
