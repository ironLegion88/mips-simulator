# Sprint 5 Agent Context: Profiler, MMIO, and Polish

## 1. Project Baseline & Current State
* **Stack**: Python 3 (Flask Backend) + TypeScript (Next.js/React Frontend).
* **Current State**: Sprints 1 through 4 are successfully completed. The system now boasts a cycle-accurate pipeline engine, cache simulation, FPU, Coprocessor 0, time-travel debugging, a Monaco-powered IDE, and a React Flow datapath visualizer. The project is currently on the `develop` branch.
* **Documentation Note**: The `docs/implementation_plan.md` has been updated to mark Sprint 4 as complete, and this new context file has been generated.

## 2. Initial Actions & Branching
* **First Action Required**: You MUST create and switch to a new branch named `feat/sprint-5`.
* **Second Action Required**: ON the new `feat/sprint-5` branch, commit these updated documentation files (`docs/implementation_plan.md` and `docs/agent_context_sprint_5.md`). Use a conventional commit like `docs: update sprint 5 context and plan`.

## 3. Sprint 5 Objectives & Targets

### Epic 1: Performance Profiler Mode
* **Task 1: Metrics Dashboard**
  * *File*: `frontend/src/components/Profiler.tsx` (New)
  * *Action*: Implement a professional dashboard interface for the Profiler tab. You may install a charting library like `recharts` or `chart.js` (`react-chartjs-2`). Render:
    - **KPI Blocks**: Overall CPI (Cycles Per Instruction), total cycles, total instructions.
    - **Pie/Doughnut Charts**: Hazard breakdown (Data Hazards vs. Control Hazards).
    - **Line Charts**: Cache Hit vs Miss rates over time.

### Epic 2: Virtual File System & MMIO
* **Task 1: Keyboard & Terminal MMIO**
  * *Files*: `backend/mips_mmu.py` (New/Update), `frontend/src/components/Terminal.tsx` (New/Update)
  * *Action*: Reserve memory address `0xFFFF0000` for the Receiver Control register and `0xFFFF0004` for Receiver Data. Build a frontend Terminal component that captures keystrokes. When a keystroke is registered, write the ASCII value to the MMIO address and trigger a hardware interrupt via Coprocessor 0 (using the exception routing built in Sprint 2).
* **Task 2: Virtual File System Sandbox**
  * *File*: `backend/vfs.py` (New)
  * *Action*: Intercept SPIM/MARS file I/O syscalls (13=open, 14=read, 15=write, 16=close). Route these to a sandboxed Python dictionary representing virtual file descriptors, preventing the simulator from actually accessing the host OS file system.

## 4. Development Rules
* **Frontend Packages**: If you need to install charting libraries (e.g., `npm install recharts`), do so on this branch.
* **Conventional Commits**: Use `feat:`, `fix:`, `refactor:`, `docs:`, etc.
* **Commit Structure**: Break down your work atomically. Keep frontend dashboard commits separate from backend VFS/MMIO commits. Every commit MUST have a short header (<= 50 chars) and a detailed body.
* **Strict Adherence**: Follow `docs/requirements_specifications.md` and `docs/implementation_plan.md` rigidly. If a requirement is ambiguous, stop and ask the user for clarification.
