# Sprint 1 Agent Context: Advanced Execution Architecture & Assembler

## 1. Project Baseline
* **Stack**: Python 3 (Flask Backend) + TypeScript (Next.js/React Frontend).
* **Core Goal of Sprint 1**: 
  1. Upgrade the Assembler to support multi-file linking and a Macro engine.
  2. Decouple the execution loop in the Simulator core to use a generator (`yield_state()`) pattern, preparing the architecture for cycle-accurate pipelining and WebSocket streaming.

## 2. Current Repository State & Branching
* The project is currently on the `develop` branch.
* **CRITICAL**: There are existing uncommitted modifications in the working directory (specifically in `backend/app.py`, `backend/mips_simulator.py`, `frontend/src/app/page.tsx`, etc.) that implement basic step-by-step UI, I/O handling, and Stack Pointer tracking.
* **First Action Required**: You MUST review these uncommitted changes and commit them to the `develop` branch before starting Sprint 1 work.
* **Second Action Required**: After cleaning the working directory, you MUST create and switch to a new branch named `feature/sprint-1`.

## 3. Sprint 1 Objectives & Targets

### Epic 1: The Macro Assembler
* **Files to Target**: `backend/mips_assembler.py`, `backend/mips_preprocessor.py` (New).
* **Task 1: Multi-file & Linker Support**: Refactor the assembler to accept a list of file payloads instead of a single string. Implement a global symbol table to resolve `.globl` and `.extern` labels across different files.
* **Task 2: Macro Engine**: Create a preprocessor that scans for `%macro name(args)` and `%end_macro`. It should perform text substitution for these macros before the standard Pass 1 assembler logic begins. **Requirement**: The macro engine MUST support complex scenarios, including nested macros and recursive macro expansion.

### Epic 2: The Instruction-Accurate Core
* **Files to Target**: `backend/mips_simulator.py`.
* **Task 1: Refactoring the Execution Loop**: Decouple the monolithic `run()` loop. Split the logic into clean `fetch()`, `decode()`, and `execute()` methods. 
* **Task 2: Generator Pattern**: Implement a `yield_state()` execution generator that yields the CPU state (registers, memory diffs, pc) after every cycle, replacing the blocking while-loop. **Note**: Do NOT implement the actual WebSocket networking (e.g., Flask-SocketIO) in this sprint. Focus purely on the Python generator architecture.

## 4. Development Rules
* **No Bulk Commits**: Break down your work. Commit the existing changes logically, and then commit Sprint 1 tasks individually.
* **Conventional Commits**: Use `feat:`, `fix:`, `refactor:`, `test:`, etc.
* **Commit Structure**: Every commit MUST have a short header (<= 50 chars) and a detailed body explaining *why* the change was made and *how* it works.
* **Strict Adherence**: Follow `docs/requirements_specifications.md` and `docs/implementation_plan.md` rigidly. If a requirement is ambiguous, stop and ask the user for clarification.
