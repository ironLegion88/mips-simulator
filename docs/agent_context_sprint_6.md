# Sprint 6 Agent Context: WebSockets, Debugging, and Visualizations

## 1. Project Baseline & Current State
* **Stack**: Python 3 (Flask Backend) + TypeScript (Next.js/React Frontend).
* **Current State**: Sprints 1 through 5 are successfully completed. The project has a 5-stage pipeline, cache simulator, terminal MMIO, and a VFS. The `docs/implementation_plan.md` has been updated with Sprint 6 tasks.
* **Documentation Note**: This context file outlines the final sprint to achieve full feature completeness.

## 2. Initial Actions & Branching
* **First Action Required**: You MUST create and switch to a new branch named `feat/sprint-6`.
* **Second Action Required**: ON the new `feat/sprint-6` branch, commit these updated documentation files (`docs/implementation_plan.md` and `docs/agent_context_sprint_6.md`). Use a conventional commit like `docs: add sprint 6 context and plan` with a body that lists all the changes.

## 3. Sprint 6 Objectives & Targets

### Epic 1: Real-Time Networking [Req: NW-001]
* **Task 1: WebSocket Backend Stream**
  * *File*: `backend/app.py`, `backend/requirements.txt`
  * *Action*: Install and integrate `Flask-SocketIO`. Convert or wrap the existing `yield_state()` generator logic so that it streams simulator state payloads over WebSockets instead of requiring REST polling.
* **Task 2: Zustand WebSocket Client**
  * *File*: `frontend/src/store/useUIStore.ts`
  * *Action*: Install `socket.io-client`. Establish a persistent connection to the backend. Listen for `state_update` events and patch the Zustand global state automatically.

### Epic 2: Advanced Debugging [Req: DB-001, DB-002]
* **Task 1: Breakpoints & Watchpoints Backend**
  * *File*: `backend/mips_simulator.py`
  * *Action*: Add `breakpoints: set[int]` and `watchpoints: set[int]`. Modify the execution loop to pause execution if `self.pc` hits a breakpoint, or if memory/registers specified in a watchpoint are altered.
* **Task 2: Editor Gutter Integration**
  * *File*: `frontend/src/components/Editor.tsx`
  * *Action*: Hook into the Monaco Editor glyph margin API. Let users click the line number margin to drop a red breakpoint dot. Map these lines to instruction addresses and sync them with the backend over REST or WebSockets.

### Epic 3: Advanced Visualizations & Content [Req: UI-002, ED-001]
* **Task 1: Program Counter (PC) Visualizer**
  * *File*: `frontend/src/components/PCVisualizer.tsx` (New)
  * *Action*: Build a widget near the Execution Controls that visualizes the PC's journey. Display the current PC, the next predicted PC, and highlight jump/branch targets.
* **Task 2: Stack Frame Visualizer**
  * *File*: `frontend/src/components/StackView.tsx` (New)
  * *Action*: Build a specialized memory view that exclusively visualizes the region between `$sp` and `$fp`. Highlight newly pushed/popped words.
* **Task 3: Examples Library & Code Export**
  * *Files*: `frontend/src/components/ExamplesMenu.tsx`, `frontend/src/utils/export.ts`
  * *Action*: Hardcode 3 classic MIPS algorithms (e.g., Factorial, Bubble Sort). Implement Blob URL exports for `.s`, `.bin`, and `.hex` files.

## 4. Development Rules
* **Dependencies**: You are responsible for properly installing `flask-socketio` (backend) and `socket.io-client` (frontend).
* **Conventional Commits**: Keep backend networking, frontend networking, debugging, and visualization commits strictly separated into atomic commits.
* **Strict Adherence**: Follow `docs/implementation_plan.md` rigidly. For all UI design and layout decisions (like the PC visualizer and Stack View), you MUST reference and adhere to `docs/prelim_ui_ux_spec.md`. If a layout or WebSocket payload structure is ambiguous, stop and ask the user for clarification.
