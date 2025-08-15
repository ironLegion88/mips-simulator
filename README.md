# Interactive MIPS Assembly Simulator & Visualizer

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)

A full-stack, web-based educational tool designed to make learning the MIPS instruction set architecture intuitive and interactive. Convert MIPS assembly to machine code, simulate program execution step-by-step, and visualize the internal state of a MIPS processor in real-time.

---

## Core Features

This simulator provides a rich feature set to bridge the gap between theoretical MIPS concepts and practical execution.

###  Assembler & Disassembler
- **Two-Pass Assembler**: Correctly handles forward label references for branches and jumps.
- **Comprehensive Instruction Support**: Assembles a wide range of MIPS I integer instructions (R/I/J types).
- **Pseudo-Instruction Expansion**: Automatically expands common pseudo-instructions (`li`, `la`, `move`, `blt`, etc.) into base instructions.
- **Assembler Directives**: Full support for `.data`, `.text`, `.word`, `.byte`, `.half`, `.asciiz`, `.ascii`, `.space`, and `.align`.
- **Multi-Format Output**: View assembled machine code in Hexadecimal, Binary, or Decimal.
- **Disassembler**: Convert 32-bit machine code back into human-readable MIPS assembly.

### Execution Simulator
- **Step-by-Step Execution**: Execute code one instruction at a time, observing the impact on the system.
- **Continuous Run & Pause**: Run the program with an adjustable animation delay to see the flow, and pause at any time.
- **Register & Memory Simulation**: Manages the state of all 32 GPRs, plus PC, HI, and LO registers, and a byte-addressable memory space.
- **Syscall Handling**: Simulates common SPIM/MARS syscalls for I/O (`print_int`, `print_string`, `read_int`, etc.) and program control (`exit`, `sbrk`).

### Interactive Visualization
- **Real-Time State Display**: All registers and relevant memory sections are displayed and updated after each step.
- **Change Highlighting**: Registers and memory words that were modified by the last instruction are briefly highlighted in green for easy tracking.
- **Active Instruction Highlighting**: The current line of code about to be executed (based on the PC) is highlighted in the editor.
- **Stack Visualization**: The memory view automatically displays the region around the stack pointer (`$sp`), making it easy to visualize stack operations like push (`sw`) and pop (`lw`).
- **I/O Console**: A persistent console displays all program output and provides a prompt for input when required by `read_*` syscalls.

---

## Technical Architecture

The application is built on a modern client-server model to separate the UI from the core simulation logic.

- **Frontend (Client)**: A **React** single-page application built with **Next.js** and **TypeScript**. It provides a rich, responsive user interface, manages all visual components, and communicates with the backend via a REST API. The powerful **Monaco Editor** is used for the code editing experience.
- **Backend (Server)**: A **Python** and **Flask** based REST API that exposes endpoints for assembling, disassembling, and simulating code. The core logic is implemented from scratch:
    - `MipsAssembler`: A two-pass assembler class.
    - `MipsDisassembler`: A class for converting machine code to assembly.
    - `MipsSimulator`: A state machine class that manages the CPU state and executes instructions.
- **API Communication**: The frontend sends requests (e.g., assembly code, step commands) to the backend. The backend processes the request and returns the result or updated state as a JSON object, which the frontend then uses to render the UI.

---

## Getting Started

### Prerequisites

- **Git**
- **Python** (3.8+) and **pip**
- **Node.js** (LTS version) and **npm** (or `yarn`)

### Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-username/mips-simulator.git
    cd mips-simulator
    ```

2.  **Backend Setup (Python/Flask):**
    ```bash
    # Navigate to the backend directory
    cd backend

    # Create and activate a Python virtual environment
    python -m venv venv
    # Windows:
    .\venv\Scripts\activate
    # Linux/macOS:
    # source venv/bin/activate

    # Install required Python packages
    pip install -r requirements.txt
    ```

3.  **Frontend Setup (Node.js/Next.js):**
    ```bash
    # Navigate to the frontend directory from the root
    cd ../frontend

    # Install Node.js dependencies
    npm install
    ```

### Running the Application

You must run both servers concurrently in separate terminals.

1.  **Start the Backend Server:**
    - Open a terminal in the **project root** (`mips-simulator/`).
    - Activate the virtual environment: `.\backend\venv\Scripts\activate` (Windows) or `source backend/venv/bin/activate` (Linux/macOS).
    - Set the `FLASK_APP` environment variable:
        ```bash
        # Windows CMD: set FLASK_APP=backend.app
        # Windows PowerShell: $env:FLASK_APP = "backend.app"
        # Linux/macOS: export FLASK_APP=backend.app
        ```
    - Run the Flask server:
        ```bash
        flask run --port 5001
        ```

2.  **Start the Frontend Server:**
    - Open a **separate** terminal in the **frontend directory** (`mips-simulator/frontend/`).
    - Run the Next.js development server:
        ```bash
        npm run dev
        ```

3.  **Access the Application:**
    - Open your web browser and navigate to **`http://localhost:3000`**.

---

## Running Tests

The backend includes a suite of unit tests to ensure the correctness of the assembler and simulator.

-   To run the tests:
    1.  Open a terminal in the **project root** (`mips-simulator/`).
    2.  Activate the Python virtual environment.
    3.  Run `pytest`:
        ```bash
        pytest
        ```

---

## Future Work

This project has a solid foundation with many opportunities for expansion:

-   **Graphical Hardware View**: Implement graphical blocks for the ALU, Register File, and Memory to visually trace the datapath for each instruction.
-   **Enhanced Educational Features**:
    -   Add a library of pre-loaded code examples (e.g., factorial, array sorting).
    -   Implement code export functionality (.s, .hex).
    -   Add tooltips and help modals explaining instructions and concepts.
-   **Advanced Debugging**: Introduce support for setting breakpoints in the code editor.
-   **Floating-Point Support**: Add the FPU (Coprocessor 1) registers and floating-point instructions.
-   **UI/UX Polish**: Refine the user interface for a more polished and modern aesthetic, and improve mobile responsiveness.
