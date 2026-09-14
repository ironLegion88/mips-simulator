# Sprint 3 Agent Context: The IDE, Time-Travel Debugger, and Global UI

## 1. Project Baseline & Current State
* **Stack**: Python 3 (Flask Backend) + TypeScript (Next.js/React Frontend).
* **Current State**: Sprints 1 and 2 are complete. The backend now supports macros, multi-file assembly, cache simulation, FPU (IEEE-754), and Coproc0 exception routing. The execution loop uses a generator (`yield_state()`). The project is currently on the `develop` branch.
* **Documentation Note**: The `docs/implementation_plan.md` has been updated to mark Sprint 2 as complete, and this new context file has been created. 

## 2. Initial Actions & Branching
* **First Action Required**: Create and switch to a new branch named `feat/sprint-3`.
* **Second Action Required**: You MUST commit these updated documentation files (`docs/implementation_plan.md` and `docs/agent_context_sprint_3.md`) to the `feat/sprint-3` branch before doing anything else. Use a conventional commit like `docs: update sprint 3 context and plan`.

## 3. Sprint 3 Objectives & Targets

### Epic 1: The 4-Mode Shell & Editor
* **Task 1: Global Header & Zustand Router**
  * *File*: `frontend/src/components/Shell.tsx` (New/Update)
  * *Action*: Implement a Tailwind-styled top navigation bar. Use Zustand (or React Context) to implement a global state router that switches the main rendering canvas between 4 modes: `Simulator`, `Datapath`, `Memory`, and `Profiler`.
* **Task 2: Monaco Integration & Tooltips**
  * *File*: `frontend/src/components/Editor.tsx` (New/Update)
  * *Action*: Integrate `@monaco-editor/react`. Register a custom `mips` language for syntax highlighting. Implement a `hoverProvider` that hooks into the backend's metadata payload to display bit-field breakdowns (opcode, rs, rt, immediate) when hovering over instructions.

### Epic 2: Time-Travel & Debugging
* **Task 1: State History Buffer (Backend)**
  * *File*: `backend/mips_simulator.py`
  * *Action*: Implement a fixed-size `collections.deque` (e.g., max length 1000). On each execution cycle, before modifying the state, append a "delta" (the old values of the registers/memory being modified). Implement a `step_backward()` method that pops the last delta and restores those exact values.
* **Task 2: Stepping Controls (Frontend)**
  * *File*: `frontend/src/components/ExecutionControls.tsx` (New/Update)
  * *Action*: Build a playback control bar with `Play`, `Pause`, `Step Forward`, and `Step Backward`. Connect `Step Backward` to the backend's new time-travel functionality.

## 4. Development Rules
* **Frontend Focus**: Sprint 3 heavily shifts focus to the UI/UX. Ensure React components are modular and well-typed (TypeScript).
* **Conventional Commits**: Use `feat:`, `fix:`, `refactor:`, `docs:`, etc.
* **Commit Structure**: Break down your work into atomic commits (e.g., commit the Zustand router separately from the Monaco hover provider). Every commit MUST have a short header (<= 50 chars) and a detailed body.
* **Strict Adherence**: Follow `docs/requirements_specifications.md` and `docs/implementation_plan.md` rigidly. If a requirement is ambiguous, stop and ask the user for clarification.
