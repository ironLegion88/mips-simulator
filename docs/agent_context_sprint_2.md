# Sprint 2 Agent Context: Memory Hierarchy, Cache, & Coprocessors

## 1. Project Baseline & Current State
* **Stack**: Python 3 (Flask Backend) + TypeScript (Next.js/React Frontend).
* **Current State**: Sprint 1 is complete. The MIPS assembler supports multi-file linking and a recursive macro engine. The core execution loop in `backend/mips_simulator.py` utilizes a `yield_state()` generator. The project is currently on the `develop` branch with a clean working directory.

## 2. Branching Instruction
* **Action Required**: You MUST create and switch to a new branch named `feat/sprint-2` before writing any code.

## 3. Sprint 2 Objectives & Targets

### Epic 1: Configurable Cache Simulator
* **File to Target**: `backend/cache_simulator.py` (New).
* **Task 1: Cache Data Structures**: Build classes for `CacheLine`, `CacheSet`, and `CacheLevel`. Implement `read(addr)` and `write(addr)` methods. These methods must return metadata about the operation: `Hit`, `Miss`, `Evict`, and simulated latencies.
* **Task 2: Replacement & Write Policies**: Implement eviction algorithms (LRU, FIFO, Random). Implement logic for Write-Through (updating main memory immediately) versus Write-Back (using dirty bit tracking to update memory only upon eviction).

### Epic 2: Coprocessor 0 & 1
* **Task 1: FPU Registers & Arithmetic**: 
  * *File*: `backend/mips_fpu.py` (New).
  * *Action*: Implement 32 single-precision floating-point registers (`$f0-$f31`). Implement standard IEEE-754 arithmetic (e.g., `add.s`, `sub.d`). Use Python's built-in `struct` and `math` libraries to gracefully handle IEEE-754 specifics like NaN, Infinity, and denormals.
* **Task 2: Exception Routing (Coproc 0)**: 
  * *File*: `backend/mips_coproc0.py` (New) and modify `backend/mips_simulator.py` to route exceptions.
  * *Action*: Implement the Coprocessor 0 registers: `Cause`, `Status`, `EPC`. The simulator's execution loop should catch standard exceptions like Python's `ZeroDivisionError` or custom `UnalignedAccessError` from the MMU, populate the `Cause` register appropriately, save the program counter to `EPC`, and set the `PC = 0x80000180` (the MIPS exception vector).

## 4. Development Rules
* **No UI Wiring Yet**: Sprint 2 is heavily focused on the backend architecture. You do not need to build the React components to visualize the cache or FPU yet; focus on making the Python models architecturally sound and testable.
* **Unit Testing**: You MUST write comprehensive unit tests for `cache_simulator.py`, `mips_fpu.py`, and `mips_coproc0.py` to verify their mathematical and logical correctness.
* **Conventional Commits**: Use `feat:`, `fix:`, `refactor:`, `test:`, etc.
* **Commit Structure**: Break down your work. Commit Epic 1 and Epic 2 tasks independently. Every commit MUST have a short header (<= 50 chars) and a detailed body explaining *why* the change was made and *how* it works.
* **Strict Adherence**: Follow `docs/requirements_specifications.md` and `docs/implementation_plan.md` rigidly. If a requirement is ambiguous, stop and ask for clarification.
