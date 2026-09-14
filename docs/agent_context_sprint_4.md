# Sprint 4 Agent Context: Microarchitecture, Pipeline, and Hardware Visualization

## 1. Project Baseline & Current State
* **Stack**: Python 3 (Flask Backend) + TypeScript (Next.js/React Frontend).
* **Current State**: Sprints 1, 2, and 3 are complete. The backend simulator now supports multi-file assembly, IEEE-754 FPU, CP0 exception routing, cache simulation, and time-travel debugging. The frontend features a Zustand-based 4-mode shell and a Monaco editor with custom hover tooltips. The project is currently on the `develop` branch.
* **Documentation Note**: The `docs/implementation_plan.md` has been updated to mark Sprint 3 as complete, and this new context file has been generated.

## 2. Initial Actions & Branching
* **First Action Required**: You MUST create and switch to a new branch named `feat/sprint-4`.
* **Second Action Required**: Once on `feat/sprint-4`, commit these updated documentation files (`docs/implementation_plan.md` and `docs/agent_context_sprint_4.md`). Use a conventional commit like `docs: update sprint 4 context and plan`.

## 3. Sprint 4 Objectives & Targets

### Epic 1: The Cycle-Accurate Engine
* **Task 1: 5-Stage Pipeline Modeling**
  * *File*: `backend/mips_pipeline.py` (New)
  * *Action*: Build a cycle-accurate backend model. Implement classes or data structures for the inter-stage latches: `IF_ID`, `ID_EX`, `EX_MEM`, `MEM_WB`. Simulate clock ticks that advance instruction states through these stages.
* **Task 2: Hazard Unit & Branch Predictor**
  * *File*: `backend/mips_pipeline.py`
  * *Action*: Implement data hazard detection (e.g., stalls when `ID_EX.MemRead` matches `IF_ID.rs/rt`). Implement data forwarding (bypassing) logic. Implement a branch predictor (start with static or 1-bit dynamic) that handles control hazards and triggers pipeline flushes (zeroing out latches) on mispredictions.

### Epic 2: Datapath React Flow Canvas
* **Task 1: Blueprint Nodes & Edges**
  * *File*: `frontend/src/components/DatapathCanvas.tsx` (New)
  * *Action*: Utilize React Flow (or a similar SVG/canvas approach) to visually lay out the MIPS 5-stage datapath. Create custom nodes for components like the ALU, Register File, Instruction Memory, Data Memory, and MUXes. Define the explicit edges (wires) connecting them.
* **Task 2: Live Signal Animation**
  * *File*: `frontend/src/hooks/useSignalAnimator.ts` (New)
  * *Action*: Create a hook that can accept pipeline state updates. It should output CSS or state changes to apply "marching-ants" or color-fill animations to the edges (wires) when specific control signals are active (e.g., if `RegWrite=1`, the wire from `MEM_WB` to the Register File turns bright blue).

## 4. Development Rules
* **Frontend Packages**: If you need to install React Flow (`npm install reactflow` or `@xyflow/react`), do so on this branch.
* **Conventional Commits**: Use `feat:`, `fix:`, `refactor:`, `docs:`, etc.
* **Commit Structure**: Break down your work atomically. Keep the React visualization commits separate from the Python backend engine commits. Every commit MUST have a short header (<= 50 chars) and a detailed body.
* **Strict Adherence**: Follow `docs/requirements_specifications.md` and `docs/implementation_plan.md` rigidly. Do not make assumptions about datapath layouts; use standard MIPS32 textbook layouts (e.g., Patterson & Hennessy).
