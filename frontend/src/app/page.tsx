// frontend/src/app/page.tsx
'use client'; // Indicate this is a Client Component (uses hooks, event handlers)

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import axios from 'axios'; // For making API requests to the backend
import Editor, { BitFields } from '../components/Editor';
import Shell from '../components/Shell';
import ExecutionControls from '../components/ExecutionControls';
import { useUIStore } from '../store/useUIStore';

// Define the base URL for the backend API
const API_BASE_URL = 'http://localhost:5001/api'; // Adjust if your backend runs elsewhere

// --- TypeScript Type Definitions ---

// Defines the possible output formats for machine code display
type OutputFormat = 'hex' | 'bin' | 'dec';

// Defines the structure for each assembled machine code line, holding multiple formats
interface MachineCodeOutput {
    hex: string; // Hexadecimal representation (e.g., "0x24020001")
    bin: string; // Binary representation (e.g., "00100100000000100000000000000001")
    dec: string; // Unsigned decimal representation
    bit_fields?: BitFields;
}

// Defines the structure for errors returned from the backend API
interface ApiError {
  line?: number;    // Optional line number where the error occurred in the source code
  message: string; // The error description
  text?: string;    // Optional snippet of the original source text causing the error
}

// Defines the structure for the Simulator State object received from the backend
interface SimulatorState {
    pc: number;                 // Program Counter value
    registers: number[];        // Array of 32 integer register values
    hi: number;                 // HI register value (for multiplication/division)
    lo: number;                 // LO register value (for multiplication/division)
    state: 'idle' | 'loaded' | 'running' | 'paused' | 'finished' | 'error' | 'input_wait'; // Current simulator status
    error: string | null;       // Error message if simulator state is 'error'
    exit_code: number | null;   // Exit code if simulator state is 'finished' (from exit syscall)
    termination_reason?: string;// Added termination reason description
    output: string;             // Accumulated output from print syscalls
    input_needed: boolean;      // Flag indicating if simulator needs input (e.g., read_int syscall)
    memory_view: { [address: number]: number }; // Dictionary mapping memory address to word value for display
}

// --- Helper Functions for Component ---
// Formats a register value (integer) into "0xHEXVAL (DECVAL)" string for display
const formatRegisterValue = (value: number): string => {
    // Ensure value is treated as unsigned 32-bit for hex padding
    const unsignedValue = value >>> 0; // Zero-fill right shift forces unsigned interpretation
    const hex = `0x${unsignedValue.toString(16).padStart(8, '0')}`;
    // Use helper to get signed interpretation for decimal display
    const dec = to_signed_32(unsignedValue).toString();
    return `${hex} (${dec})`;
};
// Formats a memory address (integer) into "0xHEXADDR" string for display
const formatAddress = (addr: number): string => `0x${(addr >>> 0).toString(16).padStart(8, '0')}`;
// Helper to convert unsigned 32-bit number stored as potentially large positive Python/JS number
// back into its signed 32-bit interpretation for display purposes.
const to_signed_32 = (unsigned_val: number): number => {
    // Check if the sign bit (bit 31) is set in the 32-bit pattern
    if (unsigned_val >= 0x80000000) { // 1 << 31
        // Calculate the negative value using two's complement formula
        return unsigned_val - 0x100000000; // Subtract 2^32
    }
    // Otherwise, the value is positive
    return unsigned_val;
};

// Register Map for Display (Number to Name) - Defined at the top level for use in component
const REGISTER_MAP_REV: { [key: number]: string } = {
    0: '$zero', 1: '$at', 2: '$v0', 3: '$v1', 4: '$a0', 5: '$a1', 6: '$a2', 7: '$a3',
    8: '$t0', 9: '$t1', 10: '$t2', 11: '$t3', 12: '$t4', 13: '$t5', 14: '$t6', 15: '$t7',
    16: '$s0', 17: '$s1', 18: '$s2', 19: '$s3', 20: '$s4', 21: '$s5', 22: '$s6', 23: '$s7',
    24: '$t8', 25: '$t9', 26: '$k0', 27: '$k1', 28: '$gp', 29: '$sp', 30: '$fp', 31: '$ra'
};

// --- React Component Definition ---
export default function Home() {
    // --- State Variables ---
    const [pingResponse, setPingResponse] = useState<string>('Pinging backend...');
    const [assemblyCode, setAssemblyCode] = useState<string>(
      "# Sample MIPS Code\n" +
      ".data\n" +
      "my_label: .word 10       # A word variable\n" +
      "prompt: .asciiz \"Enter an integer: \"\n"+ // Input prompt string
      "msg: .asciiz \"\\nYou entered: \"\n"+    // Output message string
      ".align 2                 # Align next data\n" +
      "input_val: .space 4      # Reserve space for integer input\n" +
      "\n" +
      ".text\n" +
      ".globl main\n" +
      "main:\n" +
      "  # Prompt user\n"+
      "  li $v0, 4              # syscall: print_string\n" +
      "  la $a0, prompt         # address of string to print\n" +
      "  syscall\n" +
      "\n"+
      "  # Read integer\n"+
      "  li $v0, 5              # syscall: read_int\n"+
      "  syscall                # $v0 now contains the integer read\n"+
      "\n"+
      "  # Store the read integer (optional)\n"+
      "  la $t0, input_val      # Load address of input_val\n"+
      "  sw $v0, 0($t0)         # Store the integer from $v0\n"+
      "\n"+
      "  # Print message\n"+
      "  li $v0, 4\n"+
      "  la $a0, msg\n"+
      "  syscall\n"+
      "\n"+
      "  # Print the integer read\n"+
      "  li $v0, 1              # syscall: print_int\n"+
      "  lw $a0, 0($t0)         # Load the stored integer into $a0\n"+
      "  syscall\n"+
      "\n" +
      "  # Exit program\n" +
      "  li $v0, 10             # syscall: exit\n" +
      "  syscall\n"
    ); // Editor content (updated example)
    const [machineCode, setMachineCode] = useState<MachineCodeOutput[]>([]);
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [dataSegmentHex, setDataSegmentHex] = useState<string>(""); // Unused for now
    const [outputFormat, setOutputFormat] = useState<OutputFormat>('hex');
    const [disassemblyInput, setDisassemblyInput] = useState<string>("0x24020001\n0x3c041001\n0x8c840000\n0x0000000c");
    const [disassemblyOutput, setDisassemblyOutput] = useState<string>("");
    const [errorMessages, setErrorMessages] = useState<ApiError[]>([]);
    const monacoRef = useRef<Monaco | null>(null);
    const editorRef = useRef<Parameters<OnMount>[0] | null>(null); // Ref to editor instance

    // --- Simulator State ---
    const [simState, setSimState] = useState<SimulatorState | null>(null);
    const [prevSimState, setPrevSimState] = useState<SimulatorState | null>(null); // Store previous state for highlighting
    const [lastAssembleResult, setLastAssembleResult] = useState<{ machine_code: MachineCodeOutput[], data_segment: string, address_map: { [key: number]: number } } | null>(null);
    const [addressMap, setAddressMap] = useState<{ [address: number]: number }>({});
    const editorDecorationsRef = useRef<string[]>([]); // Store Monaco decoration IDs
    const [userInput, setUserInput] = useState<string>(""); // Input field for syscalls
    const runIntervalRef = useRef<NodeJS.Timeout | null>(null); // Ref to store interval timer ID

    // --- Effects and Callback Handlers ---

    // Setup Monaco editor language provider when the editor component mounts
    const handleEditorDidMount: OnMount = (editor, monaco) => {
        editorRef.current = editor; // Store editor instance for API calls
        monacoRef.current = monaco; // Store monaco API instance
        if (monaco) {
            setupMipsLanguage(monaco); // Register MIPS language rules and theme
        } else {
            console.error("Monaco instance not available on mount.");
        }
    };

    // Ping backend on initial component load to check connectivity
    useEffect(() => {
        axios.get(`${API_BASE_URL}/ping`)
            .then(response => { setPingResponse(`Backend status: ${response.data.message}`); })
            .catch(error => { console.error("Error pinging backend:", error); setPingResponse('Backend status: Error - Could not connect'); });
    }, []); // Empty dependency array ensures this runs only once on mount

    // Update assemblyCode state when the Monaco editor content changes
    const handleAssemblyChange = (value: string | undefined) => {
        setAssemblyCode(value || "");
    };

    // Handler for the "Assemble" button click
    const handleAssemble = useCallback(() => {
        // Clear previous results and errors
        setErrorMessages([]); setMachineCode([]); setAddressMap({});
        setLastAssembleResult(null); setSimState(null); setPrevSimState(null);

        // Send assembly code string to the backend '/api/assemble' endpoint
        axios.post<{ machine_code: MachineCodeOutput[], errors: ApiError[], data_segment: string, address_map: { [key: string]: number } }>(`${API_BASE_URL}/assemble`, { assembly: assemblyCode })
            .then(response => {
                const errors = response.data.errors || [];
                const assembledCode = response.data.machine_code || [];
                const dataSeg = response.data.data_segment || "";
                // Convert string keys from JSON map back to numbers for address map
                const addrMap: { [address: number]: number } = {};
                if (response.data.address_map) {
                    for (const [addrStr, lineNum] of Object.entries(response.data.address_map)) {
                        addrMap[parseInt(addrStr)] = lineNum;
                    }
                }
                setAddressMap(addrMap); // Store the address map
                setErrorMessages(errors);
                setMachineCode(assembledCode);
                setDataSegmentHex(dataSeg); // Store data segment hex if needed later

                // If assembly was fully successful, store results for loading simulator
                if (errors.length === 0) {
                    setLastAssembleResult({ machine_code: assembledCode, data_segment: dataSeg, address_map: addrMap });
                }
            })
            .catch(error => {
                // Handle network errors or unexpected server errors
                console.error("Assembly Error:", error);
                const backendMessage = error?.response?.data?.errors?.[0]?.message;
                const fallbackMessage = error instanceof Error ? error.message : "Failed to assemble code.";
                setErrorMessages([{ message: `Network or Server Error: ${backendMessage || fallbackMessage}` }]);
                setMachineCode([]); // Clear output on error
            });
    }, [assemblyCode]); // Recalculate only if assemblyCode changes

    // Handler for the "Disassemble" button click
    const handleDisassemble = () => {
        setErrorMessages([]); setDisassemblyOutput("");
        try {
            // Prepare and validate input hex lines
            const lines = disassemblyInput.split('\n')
                .map(line => line.trim().toLowerCase().replace(/^0x/, ''))
                .filter(line => line.length > 0);
            const validLines = lines.map(line => {
                if (!/^[0-9a-f]+$/.test(line)) throw new Error(`Invalid hex character in '${line.substring(0,20)}...'`);
                if (line.length > 8) throw new Error(`Hex value too long in '${line.substring(0,20)}...'`);
                return '0x' + line.padStart(8, '0');
            });
            // Send validated lines to backend
            axios.post(`${API_BASE_URL}/disassemble`, { machine_code: validLines })
                .then(response => { // Process response
                    if (response.data.errors && response.data.errors.length > 0) {
                        setErrorMessages(response.data.errors); setDisassemblyOutput('');
                    } else {
                        setDisassemblyOutput(response.data.assembly_code || ""); setErrorMessages([]);
                    }
                })
                .catch(error => { // Handle API errors
                    console.error("Disassembly Error:", error);
                    const backendMessage = error?.response?.data?.errors?.[0]?.message;
                    const fallbackMessage = error instanceof Error ? error.message : "Failed to disassemble code.";
                    setErrorMessages([{ message: `Network or Server Error: ${backendMessage || fallbackMessage}` }]);
                    setDisassemblyOutput('');
                });
        } catch (e) { // Catch client-side validation errors
            const message = (e instanceof Error) ? e.message : String(e);
            setErrorMessages([{ message: `Input Error: ${message}` }]);
            setDisassemblyOutput('');
        }
    };

    // --- Simulation Handlers ---

    // Handler for the "Load Simulation" button
    const handleLoadSimulation = useCallback(() => {
        if (!lastAssembleResult) { // Check if assembly results are available
            setErrorMessages([{ message: "Assemble the code successfully before loading simulation." }]);
            return;
        }
        setErrorMessages([]); setPrevSimState(null); // Reset previous state
        setSimState(null); // Indicate loading

        // Send assembled code/data to backend '/api/simulate/load' endpoint
        axios.post<SimulatorState>(`${API_BASE_URL}/simulate/load`, {
            machine_code: lastAssembleResult.machine_code,
            data_segment: lastAssembleResult.data_segment
        })
        .then(response => { setSimState(response.data); }) // Set initial simulator state
        .catch(error => { // Handle loading errors
            console.error("Sim Load Error:", error);
            const backendMessage = error?.response?.data?.error || error?.response?.data?.message;
            const fallbackMessage = error instanceof Error ? error.message : "Failed to load simulation.";
            setErrorMessages([{ message: `Sim Load Error: ${backendMessage || fallbackMessage}` }]);
            setSimState(null);
        });
    }, [lastAssembleResult]); // Re-create only if lastAssembleResult changes

    // Handler for the "Reset Sim" button
    const handleResetSimulation = useCallback(() => {
        setErrorMessages([]); setPrevSimState(null); // Reset previous state
        // Call backend '/api/simulate/reset' endpoint
        axios.post<SimulatorState>(`${API_BASE_URL}/simulate/reset`)
             .then(response => { setSimState(response.data); }) // Update frontend with reset state
             .catch(error => { // Handle reset errors
                 console.error("Sim Reset Error:", error);
                 const backendMessage = error?.response?.data?.error || error?.response?.data?.message;
                 const fallbackMessage = error instanceof Error ? error.message : "Failed to reset simulation.";
                 setErrorMessages([{ message: `Sim Reset Error: ${backendMessage || fallbackMessage}` }]);
             });
    }, []); // No dependencies

    // Handler for the "Step" button
    const handleStepSimulation = useCallback(() => {
        if (!simState || !["loaded", "paused", "input_wait"].includes(simState.state)) { return; } // Check valid state
        setErrorMessages([]);
        setPrevSimState(simState); // Store current state before stepping

        // Call backend '/api/simulate/step' endpoint
        axios.post<SimulatorState>(`${API_BASE_URL}/simulate/step`)
            .then(response => {
                setSimState(response.data); // Update state with result of step
                 if (response.data.state === 'error') { // Check for runtime errors
                     setErrorMessages([{ message: `Runtime Error: ${response.data.error || 'Unknown error'}` }]);
                 }
            })
            .catch(error => { // Handle step errors
                console.error("Sim Step Error:", error);
                const backendMessage = error?.response?.data?.error || error?.response?.data?.message;
                const fallbackMessage = error instanceof Error ? error.message : "Failed to step simulation.";
                setErrorMessages([{ message: `Sim Step Error: ${backendMessage || fallbackMessage}` }]);
                // Attempt to refetch state if step fails
                axios.get<SimulatorState>(`${API_BASE_URL}/simulate/state`).then(res => setSimState(res.data));
            });
    }, [simState]); // Dependency on current simulator state

    // Handler for the "Run" button
    const handleRunSimulation = useCallback(() => {
        // Check if simulation can start running
        if (!simState || !["loaded", "paused"].includes(simState.state)) {
            console.warn("Cannot run, invalid sim state:", simState?.state);
            return;
        }
        setErrorMessages([]);
        setPrevSimState(simState); // Store current state before starting run

        // Set state to running immediately for UI feedback
        setSimState(prev => prev ? { ...prev, state: "running" } : null);

        // Clear any existing interval timer from previous runs/pauses
        if (runIntervalRef.current) {
            clearInterval(runIntervalRef.current);
        }

        // Function to perform a single step and check if we should continue
        const performStep = () => {
            // Check state before making API call inside interval
            // Need to use functional update with setSimState or access state via ref if closure becomes stale
            setSimState(currentSimState => {
                // If state changed externally (e.g., pause clicked, finished, error), stop interval
                if (!currentSimState || currentSimState.state !== "running") {
                    if (runIntervalRef.current) clearInterval(runIntervalRef.current);
                    runIntervalRef.current = null;
                    return currentSimState; // Return current state without stepping
                }

                // Store previous state for highlighting *before* the step call
                setPrevSimState(currentSimState);

                // Call the backend step endpoint
                axios.post<SimulatorState>(`${API_BASE_URL}/simulate/step`)
                    .then(response => {
                        // Update state with the result of the step
                        setSimState(response.data);

                        // Check if the new state means we should stop running
                        const nextState = response.data.state;
                        if (nextState !== 'paused' && nextState !== 'running') { // Includes finished, error, input_wait
                            if (runIntervalRef.current) clearInterval(runIntervalRef.current);
                            runIntervalRef.current = null;
                            console.log("Run interval stopped due to simulator state:", nextState);
                            if (nextState === 'error') {
                                setErrorMessages([{ message: `Runtime Error: ${response.data.error || 'Unknown error'}` }]);
                            }
                        }
                    })
                    .catch(error => {
                        // Handle step errors during run
                        console.error("Sim Step Error during run:", error);
                        const backendMessage = error?.response?.data?.error || error?.response?.data?.message;
                        const fallbackMessage = error instanceof Error ? error.message : "Failed to step simulation.";
                        setErrorMessages([{ message: `Sim Step Error: ${backendMessage || fallbackMessage}` }]);
                        if (runIntervalRef.current) clearInterval(runIntervalRef.current); // Stop interval on error
                        runIntervalRef.current = null;
                        // Try to update state to reflect the error
                        axios.get<SimulatorState>(`${API_BASE_URL}/simulate/state`).then(res => setSimState(res.data));
                    });

                // Return the *current* state for the functional update (it will be updated async by axios)
                // It's important to keep state as 'running' here unless axios call fails/completes
                return currentSimState ? { ...currentSimState, state: "running" } : null;
            });
        };

        // Start the interval timer to call performStep repeatedly
        runIntervalRef.current = setInterval(performStep, 300); // Adjust delay (ms) as needed

    }, [simState]); // Re-create only if simState changes (needed to get initial state check right)

    // Handler for the "Pause" button
    const handlePauseSimulation = useCallback(() => {
        // Clear the interval timer to stop automatic stepping
        if (runIntervalRef.current) {
            clearInterval(runIntervalRef.current);
            runIntervalRef.current = null;
        }
        // Update the state to paused if it was running
        // (Backend state might already be paused if step finished)
        if (simState && simState.state === "running") {
            setSimState(prev => prev ? { ...prev, state: "paused" } : null);
        }
        console.log("Simulation paused by user.");
    }, [simState]); // Dependency on simState

    // This useEffect handles clearing the interval timer if the component unmounts
    // or if the simulator state changes to a non-running state externally (e.g., error, finished)
    useEffect(() => {
        // Check if the interval is running but the state is no longer 'running'
        if (runIntervalRef.current && simState?.state !== 'running') {
            console.log("Clearing run interval because simulator state is no longer 'running':", simState?.state);
            clearInterval(runIntervalRef.current);
            runIntervalRef.current = null;
        }

        // Cleanup function: clear interval when the component unmounts or dependencies change
        return () => {
            if (runIntervalRef.current) {
                console.log("Clearing run interval on cleanup.");
                clearInterval(runIntervalRef.current);
                runIntervalRef.current = null;
            }
        };
    }, [simState?.state]); // Dependency: only the simulator's state string

    // Handler for submitting user input for read syscalls
    const handleSubmitInput = useCallback(() => {
        if (!simState || simState.state !== "input_wait") { return; } // Check if waiting for input
        setErrorMessages([]);
        setPrevSimState(simState); // Store state before submitting input

        // Call backend '/api/simulate/provide_input' endpoint
        axios.post<SimulatorState>(`${API_BASE_URL}/simulate/provide_input`, { input_data: userInput })
            .then(response => {
                setUserInput(""); // Clear input field after submission
                setSimState(response.data); // Update state (should be 'paused' or still 'input_wait' on error)
                if (response.data.state === 'input_wait') { // Check if backend reported invalid input
                     setErrorMessages([{ message: `Invalid Input: ${response.data.error || 'Format error'}` }]);
                 }
            })
            .catch(error => { // Handle input submission errors
                 console.error("Sim Input Error:", error);
                 const backendMessage = error?.response?.data?.error || error?.response?.data?.message;
                 const fallbackMessage = error instanceof Error ? error.message : "Failed to submit input.";
                 setErrorMessages([{ message: `Sim Input Error: ${backendMessage || fallbackMessage}` }]);
            });

    }, [simState, userInput]); // Dependencies on state and the user input value

    const { viewMode } = useUIStore();
    
    // --- Render ---
    // Determine button enable/disable states based on current application/simulator status
    const canLoadSim = !!lastAssembleResult; // Can load if assembly succeeded
    const canStepSim = simState && ["loaded", "paused"].includes(simState.state); // Can step if loaded/paused
    const canRunSim = simState && ["loaded", "paused"].includes(simState.state); // Can run if loaded/paused
    const canPauseSim = simState && simState.state === "running"; // Can pause only if currently running
    const canResetSim = !!simState; // Can reset if simulator has been loaded at least once
    const isWaitingForInput = simState?.state === 'input_wait'; // Check if waiting for user input
    
    const bitFieldsMap = useMemo(() => {
        const map: Record<number, BitFields> = {};
        if (lastAssembleResult) {
            Object.entries(addressMap).forEach(([addr, lineNum]) => {
                const instrIdx = (parseInt(addr) - 0x00400000) / 4;
                if (instrIdx >= 0 && instrIdx < lastAssembleResult.machine_code.length) {
                    const bf = lastAssembleResult.machine_code[instrIdx].bit_fields;
                    if (bf) map[lineNum] = bf;
                }
            });
        }
        return map;
    }, [lastAssembleResult, addressMap]);

    let currentLine: number | undefined = undefined;
    if (simState?.pc !== undefined && addressMap && simState.state !== 'finished' && simState.state !== 'error') {
        currentLine = addressMap[simState.pc];
    }
    
    const handleStepBackwardSimulation = useCallback(() => {
        if (!simState || !["loaded", "paused", "input_wait"].includes(simState.state)) { return; }
        setErrorMessages([]);
        setPrevSimState(simState);
        
        axios.post<SimulatorState>(`${API_BASE_URL}/simulate/step_backward`)
            .then(response => {
                setSimState(response.data);
                if (response.data.state === 'error') {
                    setErrorMessages([{ message: `Runtime Error: ${response.data.error || 'Unknown error'}` }]);
                }
            })
            .catch(error => {
                console.error("Sim Step Backward Error:", error);
                const backendMessage = error?.response?.data?.error || error?.response?.data?.message;
                const fallbackMessage = error instanceof Error ? error.message : "Failed to step backward simulation.";
                setErrorMessages([{ message: `Sim Step Backward Error: ${backendMessage || fallbackMessage}` }]);
            });
    }, [simState]);


    return (
        <Shell controls={
            <ExecutionControls
                onStepBack={handleStepBackwardSimulation}
                onPause={handlePauseSimulation}
                onRun={handleRunSimulation}
                onStepForward={handleStepSimulation}
                onReset={handleResetSimulation}
                canStepBack={canStepSim && simState !== null} // Simple condition for now
                canPause={canPauseSim}
                canRun={canRunSim && !isWaitingForInput}
                canStepForward={canStepSim && !isWaitingForInput}
                canReset={canResetSim}
            />
        }>
            {viewMode === 'Simulator' && (
            <div className="container overflow-y-auto h-full p-4">
                <h1>MIPS Assembler & Simulator</h1>
                <p>{pingResponse}</p>

                {/* Error Display Area */}
                {errorMessages.length > 0 && (
                     <div className="errorBox">
                        <strong>Errors:</strong>
                        <ul>
                            {errorMessages.map((err, index) => (
                            <li key={`err-${index}`}>
                                {err.line ? `Line ${err.line}: ` : ''}{err.message}
                                {err.text ? <span className="errorTextSpan">{`(near '`} {err.text.substring(0, 30)}{err.text.length > 30 ? '...' : ''} {`')`}</span> : ''}
                            </li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* Top Row: Assembly and Disassembly */}
                <div className="sectionContainer">
                    {/* Assembly Section */}
                    <div className="section">
                        <h2>Assembly Input</h2>
                        <div className="editorWrapper" style={{ height: '400px' }}>
                            <Editor
                                code={assemblyCode}
                                onChange={handleAssemblyChange}
                                bitFieldsMap={bitFieldsMap}
                                currentLine={currentLine}
                             />
                        </div>
                        <div className="simControls">
                             <button onClick={handleAssemble} className="button">Assemble</button>
                             <button onClick={handleLoadSimulation} className="button" disabled={!canLoadSim}>Load Sim</button>
                        </div>
                        <div>
                            <h3>Machine Code Output</h3>
                            <div className="formatSelector">
                                <label><input type="radio" name="format" value="hex" checked={outputFormat === 'hex'} onChange={() => setOutputFormat('hex')} /> Hex</label>
                                <label><input type="radio" name="format" value="bin" checked={outputFormat === 'bin'} onChange={() => setOutputFormat('bin')} /> Binary</label>
                                <label><input type="radio" name="format" value="dec" checked={outputFormat === 'dec'} onChange={() => setOutputFormat('dec')} /> Decimal</label>
                            </div>
                            <pre className="outputPre">
                                {machineCode.map((code) => code[outputFormat]).join('\n')}
                            </pre>
                        </div>
                    </div>

                {/* Disassembly Section */}
                <div className="section">
                    <h2>Machine Code Input (Hex)</h2>
                    <textarea
                        className="textArea"
                        rows={10}
                        value={disassemblyInput}
                        onChange={(e) => setDisassemblyInput(e.target.value)}
                        placeholder="Enter 32-bit hex machine code (e.g., 24020001 or 0x24020001), one per line."
                    />
                    <button onClick={handleDisassemble} className="button">Disassemble</button>
                    <div>
                        <h3>Assembly Output</h3>
                        <pre className="outputPre">
                            {disassemblyOutput}
                        </pre>
                    </div>
                </div>
            </div> {/* End Top Row */}

            <hr className="horizontalRule" />

            {/* Simulation Section */}
            <h2>Simulator State</h2>

            {/* Conditional rendering for simulator state display */}
            {simState ? (
                 <div className="sectionContainer">
                    {/* Registers Display Column */}
                    <div className="section">
                         <h3>Registers</h3>
                         <div className="outputPre registerTableWrapper">
                             <table>
                                 <thead>
                                     {/* Ensure no extra whitespace within table structure */}
                                     <tr><th>Name</th><th>Num</th><th>Value (Hex / Dec)</th></tr>
                                 </thead>
                                 <tbody>
                                    {simState.registers.map((value, regIndex) => {
                                        // Check if register changed from previous state for highlighting
                                        const changed = prevSimState && prevSimState.registers[regIndex] !== value;
                                        const isSP = regIndex === 29; // Flag if it's the Stack Pointer
                                        return (
                                            // Apply 'highlight-change' class if changed
                                            <tr key={`reg-${regIndex}`} className={changed ? 'highlight-change' : ''}>
                                                <td>{REGISTER_MAP_REV[regIndex] || `$${regIndex}`}{isSP ? ' (sp)' : ''}</td>
                                                <td>{regIndex}</td>
                                                <td>{formatRegisterValue(value)}</td>
                                            </tr>
                                        );
                                    })}
                                    {/* Display special registers, check for changes */}
                                    <tr className={prevSimState && prevSimState.pc !== simState.pc ? 'highlight-change' : ''}><td>pc</td><td>-</td><td>{formatAddress(simState.pc)}</td></tr>
                                    <tr className={prevSimState && prevSimState.hi !== simState.hi ? 'highlight-change' : ''}><td>hi</td><td>-</td><td>{formatRegisterValue(simState.hi)}</td></tr>
                                    <tr className={prevSimState && prevSimState.lo !== simState.lo ? 'highlight-change' : ''}><td>lo</td><td>-</td><td>{formatRegisterValue(simState.lo)}</td></tr>
                                 </tbody>
                             </table>
                         </div>
                         {/* Simulator Status Display */}
                         <div className="simStatus">Status: <strong>{simState.state}</strong></div>
                         {simState.state === 'finished' && (
                             <div className="simStatus">
                                 Exit Code: {simState.exit_code ?? 'N/A'}<br />
                                 Reason: {simState.termination_reason || 'Finished'} {/* Display termination reason */}
                             </div>
                         )}
                         {simState.state === 'error' && <div className="simStatus error">Error: {simState.error || 'Unknown Error'}</div>}
                    </div>

                    {/* Memory & I/O Column */}
                    <div className="section">
                        {/* Memory View */}
                        <div>
                             <h3>Memory View (Stack & Data)</h3>
                             <div className="outputPre memoryTableWrapper">
                                 <table>
                                     <thead>
                                         <tr><th>Address</th><th>Value (Hex Word)</th></tr>
                                     </thead>
                                     <tbody>
                                        {/* Sort memory addresses and check for changes */}
                                        {Object.entries(simState.memory_view)
                                            .map(([addrStr, val]) => ({ address: parseInt(addrStr), value: val }))
                                            .sort((a, b) => a.address - b.address)
                                            .map(({ address, value }) => {
                                                // Check if memory value changed from previous state
                                                const changed = prevSimState && prevSimState.memory_view[address] !== value;
                                                // Check if this memory address is the current stack pointer
                                                const isSPLocation = address === simState.registers[29];
                                                return (
                                                    // Apply 'highlight-change' class if changed
                                                    <tr key={`mem-${address}`} className={changed ? 'highlight-change' : ''}>
                                                        <td>{formatAddress(address)}{isSPLocation ? ' <-- sp' : ''}</td>
                                                        <td>{formatRegisterValue(value)}</td>
                                                    </tr>
                                                );
                                            })}
                                     </tbody>
                                 </table>
                             </div>
                        </div>
                        {/* I/O Console View */}
                        <div>
                            <h3>I/O Console</h3>
                             <pre className="outputPre ioConsole">
                                 {/* Display accumulated output */}
                                 {simState.output}
                             </pre>
                             {/* Input Area (shown only when needed) */}
                             {isWaitingForInput && ( // Conditionally render based on simState.input_needed
                                 <div className='input-area'>
                                     <label htmlFor='syscall-input'>Input Required:</label>
                                     <input
                                         type="text"
                                         id='syscall-input'
                                         value={userInput}
                                         onChange={(e) => setUserInput(e.target.value)}
                                         // Allow submission on Enter key
                                         onKeyDown={(e) => { if (e.key === 'Enter') handleSubmitInput(); }}
                                         className='input-field' // Apply CSS class
                                         autoFocus // Focus the input field automatically
                                     />
                                     <button onClick={handleSubmitInput} className='button input-submit'>Submit</button>
                                 </div>
                             )}
                        </div>
                    </div>
                </div>
            ) : (
                // Message shown if simulation hasn't been loaded yet
                <p>Assemble code and click &quot;Load Simulation&quot; to begin.</p> // Escaped quotes
            )}
            )}
        </Shell>
    );
}