// frontend/src/app/page.tsx
'use client'; // Indicate this is a Client Component (uses hooks, event handlers)

import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios'; // For making API requests to the backend
import Editor, { Monaco, OnMount } from '@monaco-editor/react'; // Monaco code editor component and types

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
    output: string;             // Accumulated output from print syscalls in the last step/run
    input_needed: boolean;      // Flag indicating if simulator is waiting for input (e.g., read_int syscall)
    memory_view: { [address: number]: number }; // Dictionary mapping memory address to word value for display
}

// --- MIPS Language Definition for Monaco Editor ---
// This function registers the 'mips' language with Monaco and defines its syntax highlighting rules and theme.
function setupMipsLanguage(monaco: Monaco) {
  // Check if the language is already registered to prevent errors, especially during development hot reloads
  const languages = monaco.languages.getLanguages();
  if (languages.some(lang => lang.id === 'mips')) {
     console.log("MIPS language already registered.");
     return; // Exit if already registered
  }
  console.log("Registering MIPS language.");

  // Register the language identifier
  monaco.languages.register({ id: 'mips' });

  // Define the tokenization rules using Monarch syntax (a state-based tokenizer)
  monaco.languages.setMonarchTokensProvider('mips', {
    // Define lists of known keywords and registers for easier reference in rules
    registers: [ // All common MIPS register names (including numeric)
      '$zero', '$at', '$v0', '$v1', '$a0', '$a1', '$a2', '$a3',
      '$t0', '$t1', '$t2', '$t3', '$t4', '$t5', '$t6', '$t7',
      '$s0', '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
      '$t8', '$t9', '$k0', '$k1', '$gp', '$sp', '$fp', '$ra',
      '$0', '$1', '$2', '$3', '$4', '$5', '$6', '$7', '$8', '$9', '$10',
      '$11', '$12', '$13', '$14', '$15', '$16', '$17', '$18', '$19', '$20',
      '$21', '$22', '$23', '$24', '$25', '$26', '$27', '$28', '$29', '$30', '$31'
    ],
    keywords: [ // MIPS instruction mnemonics
      'add', 'addu', 'addi', 'addiu', 'sub', 'subu', 'and', 'andi', 'or', 'ori',
      'xor', 'xori', 'nor', 'slt', 'sltu', 'slti', 'sltiu', 'sll', 'srl', 'sra',
      'sllv', 'srlv', 'srav', 'lw', 'sw', 'lb', 'sb', 'lh', 'sh', 'lui', 'lbu', 'lhu',
      'beq', 'bne', 'blez', 'bgtz', 'bltz', 'bgez', 'j', 'jal', 'jr', 'jalr',
      'syscall', 'break', 'mfhi', 'mflo', 'mthi', 'mtlo', 'mult', 'multu', 'div', 'divu',
      'bltzal', 'bgezal',
      // Common Pseudo Instructions (highlight as keywords for visibility)
      'move', 'li', 'la', 'blt', 'bgt', 'ble', 'bge', 'nop', 'clear'
    ],
    directives: [ // Assembler directives (start with '.')
        '.data', '.text', '.globl', '.extern', '.word', '.byte', '.half', '.space', '.asciiz', '.ascii', '.align'
    ],
    tokenizer: { // Define states and rules for tokenizing the code
      root: [ // Default state
        // Comments (start with # until end of line) -> 'comment' token type
        [/#.*$/, 'comment'],

        // Directives (start with . at beginning of line) -> 'keyword.directive', switch to directive_args state
        [/^\s*\.[a-zA-Z]+/, { token: 'keyword.directive', next: '@directive_args'}],

        // Labels (identifier followed by : at beginning of line) -> 'type.identifier' token type
        [/^([a-zA-Z_]\w*)\s*:/, 'type.identifier'],

        // Keywords, Registers, Identifiers (order matters for precedence)
        [/[$.a-zA-Z_]\w*/, { // Match potential keywords, registers, or identifiers
          cases: { // Check against predefined lists
            '@keywords': 'keyword', // If it's in the keywords list
            '@registers': 'variable.predefined', // If it's in the registers list
            '@default': 'identifier' // Otherwise, it's a general identifier (like a label usage)
          }
        }],

        // Numbers (hexadecimal starting with 0x, or decimal)
        [/0[xX][0-9a-fA-F]+/, 'number.hex'],
        [/-?\d+/, 'number'],

        // Strings (double-quoted)
        [/"([^"\\]|\\.)*$/, 'string.invalid'], // Handle unterminated strings -> 'string.invalid'
        [/"/, { token: 'string.quote', bracket: '@open', next: '@string' }], // Start of string -> 'string.quote', switch to string state

        // Delimiters (commas, parentheses) -> 'delimiter' token type
        [/[(),]/, 'delimiter'],
      ],
      // State for handling arguments after a directive (allows strings)
      directive_args: [
          [/#.*$/, 'comment', '@pop'], // Comment ends args state, pop back to root
          [/"([^"\\]|\\.)*$/, 'string.invalid', '@pop'], // Unterminated string ends state, pop back
          [/"/, { token: 'string.quote', bracket: '@open', next: '@string_in_directive' }], // Enter specific string state
          [/[^#"]+/, ''], // Consume other non-string, non-comment arguments (no specific token type)
          [/$/, '', '@pop'] // End of line ends args state, pop back
      ],
      // State specifically for strings within directive arguments
      string_in_directive: [
          [/[^\\"]+/, 'string'], // String content -> 'string'
          [/\\./, 'string.escape'], // Handle simple escapes like \" or \\ -> 'string.escape'
          [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }] // End quote -> 'string.quote', pop back to directive_args
      ],
      // General string state (if needed for future language features)
      string: [
          [/[^\\"]+/, 'string'],
          [/\\./, 'string.escape.invalid'], // Mark escapes as invalid here by default if not handled
          [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }] // End quote, pop back to root
      ],
    }
  });

  // Define a custom theme for the editor (optional, provides specific colors)
  monaco.editor.defineTheme('mips-dark', {
      base: 'vs-dark', // Inherit from the built-in VS Dark theme
      inherit: true,   // Apply inherited rules
      rules: [ // Define specific colors for token types identified by the tokenizer
          { token: 'keyword', foreground: 'C586C0' },           // Instructions etc.: Pink/Purple
          { token: 'keyword.directive', foreground: '4FD0FF' },  // Directives (.data, .text): Light Blue
          { token: 'variable.predefined', foreground: '9CDCFE' },// Registers ($t0, $sp): Blue
          { token: 'number', foreground: 'B5CEA8'},            // Numbers: Green
          { token: 'comment', foreground: '6A9955', fontStyle: 'italic' }, // Comments: Green Italic
          { token: 'string', foreground: 'CE9178' },           // Strings: Orange
          { token: 'type.identifier', foreground: 'DCDCAA' },   // Label definitions (label:): Yellow
          { token: 'identifier', foreground: 'D4D4D4'},        // Label usages/other identifiers: Default Grey
          { token: 'delimiter', foreground: 'D4D4D4'},         // Commas, parentheses: Default Grey
      ],
      colors: { // Define general editor colors (optional overrides)
          'editor.foreground': '#D4D4D4', // Default text color
          // Add other color overrides if needed (e.g., 'editor.background')
      }
  });
    console.log("MIPS language and theme defined.");
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

// Register Map for Display (Number to Name) - Moved to top
const REGISTER_MAP_REV: { [key: number]: string } = {
    0: '$zero', 1: '$at', 2: '$v0', 3: '$v1', 4: '$a0', 5: '$a1', 6: '$a2', 7: '$a3',
    8: '$t0', 9: '$t1', 10: '$t2', 11: '$t3', 12: '$t4', 13: '$t5', 14: '$t6', 15: '$t7',
    16: '$s0', 17: '$s1', 18: '$s2', 19: '$s3', 20: '$s4', 21: '$s5', 22: '$s6', 23: '$s7',
    24: '$t8', 25: '$t9', 26: '$k0', 27: '$k1', 28: '$gp', 29: '$sp', 30: '$fp', 31: '$ra'
};

// --- React Component Definition ---
export default function Home() {
    // --- State Variables ---
    // Holds the response from the backend ping check
    const [pingResponse, setPingResponse] = useState<string>('Pinging backend...');
    // Holds the MIPS assembly code currently in the editor
    const [assemblyCode, setAssemblyCode] = useState<string>(
      "# Sample MIPS Code\n" +
      ".data\n" +
      "my_label: .word 10       # A word variable\n" +
      "my_string: .asciiz \"Hello\\n\" # A null-terminated string\n" +
      ".align 2                 # Align next data to 4-byte boundary\n" +
      "other_val: .byte -1\n" +
      "\n" +
      ".text\n" +
      ".globl main              # Declare main as global\n" +
      "main:                    # Label for main program entry\n" +
      "  # Print the integer value\n" +
      "  li $v0, 1              # syscall code for print_int\n" +
      "  la $a0, my_label       # Load address of my_label into $a0\n" +
      "  lw $a0, 0($a0)         # Load word from address in $a0\n" +
      "  syscall                # Make the syscall\n" +
      "\n" +
      "  # Print the string\n" +
      "  li $v0, 4              # syscall code for print_string\n" +
      "  la $a0, my_string      # Load address of my_string\n" +
      "  syscall\n" +
      "\n" +
      "  # Exit program\n" +
      "  li $v0, 10             # syscall code for exit\n" +
      "  syscall\n"
    );
    // Holds the assembled machine code (array of objects with hex/bin/dec)
    const [machineCode, setMachineCode] = useState<MachineCodeOutput[]>([]);
    // Holds the assembled data segment as a hex string (Currently unused, but available)
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [dataSegmentHex, setDataSegmentHex] = useState<string>("");
    // Holds the selected format for displaying machine code
    const [outputFormat, setOutputFormat] = useState<OutputFormat>('hex');
    // Holds the machine code input for the disassembler
    const [disassemblyInput, setDisassemblyInput] = useState<string>("0x24020001\n0x3c041001\n0x8c840000\n0x0000000c");
    // Holds the assembly output from the disassembler
    const [disassemblyOutput, setDisassemblyOutput] = useState<string>("");
    // Holds any errors reported by the backend (assembly, disassembly, simulation)
    const [errorMessages, setErrorMessages] = useState<ApiError[]>([]);
    // Ref to the Monaco editor instance (not currently used but available)
    const monacoRef = useRef<Monaco | null>(null);
    // Store address -> source line map from assembler
    const [addressMap, setAddressMap] = useState<{ [address: number]: number }>({});
    // Store decoration IDs for Monaco highlighting
    const editorDecorationsRef = useRef<string[]>([]);
    // Ref to the actual editor instance
    const editorRef = useRef<Parameters<OnMount>[0] | null>(null); // Store editor instance

    // --- Simulator State ---
    // Holds the complete state of the MIPS simulator received from the backend
    const [simState, setSimState] = useState<SimulatorState | null>(null);
    // Stores the result of the last successful assembly (code + data) to feed into the simulator load
    const [lastAssembleResult, setLastAssembleResult] = useState<{ machine_code: MachineCodeOutput[], data_segment: string } | null>(null);

    // --- Effects and Callback Handlers ---

    // Setup Monaco editor language provider when the editor component mounts
    // FIX: Use onMount prop which provides both editor and monaco instances
    const handleEditorDidMount: OnMount = (editor, monaco) => {
      editorRef.current = editor; // Store editor instance
      monacoRef.current = monaco;
      if (monaco) {
          setupMipsLanguage(monaco);
      } else {
          console.error("Monaco instance not available on mount.");
      }
    };

    // Ping backend on initial component load
    useEffect(() => {
        axios.get(`${API_BASE_URL}/ping`)
            .then(response => { setPingResponse(`Backend status: ${response.data.message}`); })
            .catch(error => { console.error("Error pinging backend:", error); setPingResponse('Backend status: Error - Could not connect'); });
    }, []); // Empty dependency array means run only once on mount

    // Update assemblyCode state when the Monaco editor content changes
    const handleAssemblyChange = (value: string | undefined) => {
        setAssemblyCode(value || "");
    };

    // Handler for the "Assemble" button click, using useCallback for potential performance optimization
    const handleAssemble = useCallback(() => {
        // Clear previous results and errors
        setErrorMessages([]);
        setMachineCode([]);
        setDataSegmentHex("");
        setLastAssembleResult(null); // Clear previous assembly result used by simulator
        setSimState(null);     // Reset simulator state whenever new code is assembled
        setAddressMap({}); // Clear address map

        // Send assembly code string to the backend '/api/assemble' endpoint
        axios.post(`${API_BASE_URL}/assemble`, { assembly: assemblyCode })
            .then(response => {
                // Handle the response from the backend
                if (response.data.errors && response.data.errors.length > 0) {
                    // Set errors if the backend reported any
                    setErrorMessages(response.data.errors);
                } else {
                    // Clear errors if assembly was successful
                    setErrorMessages([]);
                }
                // Update state with the machine code and data segment from the response
                // This will display results even if there were errors (e.g., partial assembly)
                setMachineCode(response.data.machine_code || []);
                setDataSegmentHex(response.data.data_segment || "");
                setAddressMap(response.data.address_map || {}); // Store the map

                // If assembly was fully successful (no errors), store the result
                // so it can be used to load the simulator later
                if (!response.data.errors || response.data.errors.length === 0) {
                    setLastAssembleResult({
                        machine_code: response.data.machine_code || [],
                        data_segment: response.data.data_segment || ""
                    });
                }
            })
            .catch(error => {
                // Handle network errors or unexpected server errors
                console.error("Assembly Error:", error);
                const backendMessage = error?.response?.data?.errors?.[0]?.message; // Try to get specific error
                const fallbackMessage = error instanceof Error ? error.message : "Failed to assemble code."; // Generic fallback
                setErrorMessages([{ message: `Network or Server Error: ${backendMessage || fallbackMessage}` }]);
                setMachineCode([]); // Clear output on error
            });
    }, [assemblyCode]); // Recalculate this function only if 'assemblyCode' state changes

    // Handler for the "Disassemble" button click
    const handleDisassemble = () => {
        setErrorMessages([]); // Clear previous errors
        setDisassemblyOutput(""); // Clear previous output

        try {
            // Prepare machine code input lines for the backend
            const lines = disassemblyInput.split('\n') // Split by newline
                .map(line => line.trim().toLowerCase().replace(/^0x/, '')) // Trim, lowercase, remove 0x prefix
                .filter(line => line.length > 0); // Remove empty lines

            // Client-side validation for each line
            const validLines = lines.map(line => {
                if (!/^[0-9a-f]+$/.test(line)) throw new Error(`Invalid hex character in '${line.substring(0,20)}...'`);
                if (line.length > 8) throw new Error(`Hex value too long in '${line.substring(0,20)}...'`);
                // Ensure 8 hex digits and add '0x' prefix for consistency before sending
                return '0x' + line.padStart(8, '0');
            });

            // Send validated machine code lines to the backend '/api/disassemble' endpoint
            axios.post(`${API_BASE_URL}/disassemble`, { machine_code: validLines })
                .then(response => {
                    // Process the response
                    if (response.data.errors && response.data.errors.length > 0) {
                        setErrorMessages(response.data.errors);
                        setDisassemblyOutput(''); // Clear output on backend error
                    } else {
                        setDisassemblyOutput(response.data.assembly_code || "");
                        setErrorMessages([]); // Clear errors on success
                    }
                })
                .catch(error => {
                     // Handle network or server errors during disassembly
                    console.error("Disassembly Error:", error);
                    const backendMessage = error?.response?.data?.errors?.[0]?.message;
                    const fallbackMessage = error instanceof Error ? error.message : "Failed to disassemble code.";
                    setErrorMessages([{ message: `Network or Server Error: ${backendMessage || fallbackMessage}` }]);
                    setDisassemblyOutput('');
                });
        } catch (e) { // Catch client-side validation errors from the try block
            const message = (e instanceof Error) ? e.message : String(e); // Get error message safely
            setErrorMessages([{ message: `Input Error: ${message}` }]);
            setDisassemblyOutput(''); // Clear output on input error
        }
    };

    // --- Simulation Handlers ---

    // Handler for the "Load Simulation" button
    const handleLoadSimulation = useCallback(() => {
        // Check if assembly was successful and results are available
        if (!lastAssembleResult) {
            setErrorMessages([{ message: "Assemble the code successfully before loading simulation." }]);
            return;
        }
        setErrorMessages([]); // Clear previous errors
        setSimState(null); // Set state to null to indicate loading process

        // Send assembled code and data to the backend '/api/simulate/load' endpoint
        axios.post(`${API_BASE_URL}/simulate/load`, {
            machine_code: lastAssembleResult.machine_code, // Pass the structured machine code output
            data_segment: lastAssembleResult.data_segment
        })
        .then(response => {
            // Update frontend state with the initial simulator state received from backend
            setSimState(response.data);
        })
        .catch(error => {
            // Handle errors during the simulation loading process
            console.error("Sim Load Error:", error);
            const backendMessage = error?.response?.data?.error || error?.response?.data?.message; // Try getting error message
            const fallbackMessage = error instanceof Error ? error.message : "Failed to load simulation.";
            setErrorMessages([{ message: `Sim Load Error: ${backendMessage || fallbackMessage}` }]);
            setSimState(null); // Ensure simulator state is cleared if loading fails
        });
    }, [lastAssembleResult]); // Re-create only if 'lastAssembleResult' changes

    // Handler for the "Reset Sim" button
    const handleResetSimulation = useCallback(() => {
        setErrorMessages([]); // Clear errors
        // Send request to backend '/api/simulate/reset' endpoint
        axios.post(`${API_BASE_URL}/simulate/reset`)
             .then(response => {
                 // Update frontend state with the reset ('idle') state from backend
                 setSimState(response.data);
                 console.log("Simulator reset via backend.");
                 // Note: Code is not automatically reloaded; user must click "Load Simulation" again.
             })
             .catch(error => {
                  // Handle errors during reset
                 console.error("Sim Reset Error:", error);
                 const backendMessage = error?.response?.data?.error || error?.response?.data?.message;
                 const fallbackMessage = error instanceof Error ? error.message : "Failed to reset simulation.";
                 setErrorMessages([{ message: `Sim Reset Error: ${backendMessage || fallbackMessage}` }]);
             });
    }, []); // No dependencies, this handler always performs the same action

    // --- Highlight Line Logic ---
    // Use useEffect to update decorations when PC changes
    useEffect(() => {
        if (editorRef.current && monacoRef.current && simState?.pc !== undefined && addressMap) {
            const currentPc = simState.pc;
            const currentLine = addressMap[currentPc]; // Find line number from map

            // Remove previous decorations
            editorDecorationsRef.current = editorRef.current.deltaDecorations(
                editorDecorationsRef.current, // Old decoration IDs to remove
                [] // No new decorations initially
            );

            let newDecorations = [];
            if (currentLine !== undefined) {
                // Add new decoration for the current line
                newDecorations.push({
                    range: new monacoRef.current.Range(currentLine, 1, currentLine, 1), // Range for the whole line
                    options: {
                        isWholeLine: true,
                        // Define CSS class for highlighting (add this class to globals.css)
                        className: 'current-execution-line',
                        // Optional: Customize gutter icon/tooltip
                        // glyphMarginClassName: 'current-execution-gutter',
                    }
                });
                // Store the IDs of the new decorations
                editorDecorationsRef.current = editorRef.current.deltaDecorations(
                    [], // No old decorations to remove this time
                    newDecorations
                );
                // Optionally reveal the line if it's off-screen
                editorRef.current.revealLineInCenterIfOutsideViewport(currentLine);

            } else {
                // PC doesn't map to a known source line (e.g., finished, error state, or jump to invalid area)
                // Clear decorations if needed, handled above by resetting deltaDecorations
            }
        } else {
            // Clear decorations if simulator is not running or PC is unknown
            if(editorRef.current) {
                editorDecorationsRef.current = editorRef.current.deltaDecorations(
                    editorDecorationsRef.current,
                    []
                );
            }
        }
    // Depend on PC, simulator state, and the address map
    }, [simState?.pc, simState?.state, addressMap]);
    
    // Handler for the "Step" button
    const handleStepSimulation = useCallback(() => {
        // Check if the simulator is in a state that allows stepping forward
        if (!simState || !["loaded", "paused", "input_wait"].includes(simState.state)) {
            console.warn("Cannot step, invalid sim state:", simState?.state);
            return; // Do nothing if not in a valid state
        }
        setErrorMessages([]); // Clear errors from the previous step

        // Send request to backend '/api/simulate/step' endpoint
        axios.post(`${API_BASE_URL}/simulate/step`)
            .then(response => {
                // Update frontend state with the new simulator state after the step
                setSimState(response.data);
                 // Check if the backend reported a runtime error during the step execution
                 if (response.data.state === 'error') {
                     setErrorMessages([{ message: `Runtime Error: ${response.data.error || 'Unknown error'}` }]);
                 }
            })
            .catch(error => {
                // Handle errors during the step execution
                console.error("Sim Step Error:", error);
                const backendMessage = error?.response?.data?.error || error?.response?.data?.message;
                const fallbackMessage = error instanceof Error ? error.message : "Failed to step simulation.";
                setErrorMessages([{ message: `Sim Step Error: ${backendMessage || fallbackMessage}` }]);
                // If a step fails, the simulator state might be inconsistent.
                // Consider fetching the state again or displaying a specific error.
            });
    }, [simState]); // Re-create this handler only if 'simState' changes

    // --- Render Logic ---
    // Determine button enable/disable states based on current application/simulator status
    const canLoadSim = !!lastAssembleResult; // Can load if assembly succeeded
    const canStepSim = simState && ["loaded", "paused", "input_wait"].includes(simState.state); // Can step if loaded/paused/waiting for input
    const canResetSim = !!simState; // Can reset if simulator has been loaded at least once

    return (
        // Main container for the page
        <main className="container">
            <h1>MIPS Assembler & Simulator</h1>
            <p>{pingResponse}</p>

            {/* Error Display Area - only shown if there are errors */}
            {errorMessages.length > 0 && (
                 <div className="errorBox">
                    <strong>Errors:</strong>
                    <ul>
                        {/* Map through errors and display each one */}
                        {errorMessages.map((err, index) => ( // FIX: Use _ or remove index if not used
                        <li key={`err-${index}`}> {/* Use unique key */}
                            {err.line ? `Line ${err.line}: ` : ''}{err.message}
                            {/* Display code snippet if available */}
                            {err.text ? <span className="errorTextSpan">{`(near '`} {err.text.substring(0, 30)}{err.text.length > 30 ? '...' : ''} {`')`}</span> : ''}
                        </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Top Row: Assembly and Disassembly Sections */}
            <div className="sectionContainer">
                {/* Assembly Section */}
                <div className="section">
                    <h2>Assembly Input</h2>
                    {/* Monaco Editor component */}
                    <div className="editorWrapper">
                        <Editor
                            language="mips"
                            theme="mips-dark"
                            value={assemblyCode}
                            onChange={handleAssemblyChange}
                            onMount={handleEditorDidMount} // FIX: Use onMount instead of beforeMount
                            options={{ minimap: { enabled: false }, wordWrap: 'on', fontSize: 13, glyphMargin: true }} // Enable glyph margin if using gutter decorations
                         />
                    </div>
                    {/* Buttons related to assembly */}
                    <div className="simControls">
                         <button onClick={handleAssemble} className="button">Assemble</button>
                         {/* TODO: Add Export Assembly Button here */}
                    </div>
                    {/* Machine Code Output Area */}
                    <div>
                        <h3>Machine Code Output</h3>
                        {/* Radio buttons to select output format */}
                        <div className="formatSelector">
                            <label>
                                <input type="radio" name="format" value="hex" checked={outputFormat === 'hex'} onChange={() => setOutputFormat('hex')} /> Hex
                            </label>
                            <label>
                                <input type="radio" name="format" value="bin" checked={outputFormat === 'bin'} onChange={() => setOutputFormat('bin')} /> Binary
                            </label>
                            <label>
                                <input type="radio" name="format" value="dec" checked={outputFormat === 'dec'} onChange={() => setOutputFormat('dec')} /> Decimal
                            </label>
                        </div>
                        {/* Display machine code in the selected format */}
                        <pre className="outputPre">
                            {machineCode.map((code) => code[outputFormat]).join('\n')}
                        </pre>
                         {/* TODO: Add Export Binary Button here */}
                    </div>
                </div>

                {/* Disassembly Section */}
                <div className="section">
                    <h2>Machine Code Input (Hex)</h2>
                    <textarea
                        className="textArea"
                        rows={10} // Provides initial size hint
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
            </div> {/* End Assembly/Disassembly Row */}

            <hr className="horizontalRule" /> {/* Visual separator */}

            {/* Simulation Section */}
            <h2>Simulation Controls & State</h2>
            {/* Buttons for controlling the simulation */}
            <div className="simControls">
                 <button onClick={handleLoadSimulation} className="button" disabled={!canLoadSim}>Load Simulation</button>
                 <button onClick={handleStepSimulation} className="button" disabled={!canStepSim}>Step</button>
                 {/* TODO: Add Run/Pause buttons here */}
                 <button onClick={handleResetSimulation} className="button" disabled={!canResetSim}>Reset Sim</button>
            </div>

            {/* Conditional rendering: Only display simulator state if it exists */}
            {simState ? (
                 // Use columns for Register/Memory/IO display
                 <div className="sectionContainer">
                    {/* Registers Display Column */}
                    <div className="section">
                         <h3>Registers</h3>
                         {/* Scrollable table for registers */}
                         <div className="outputPre registerTableWrapper">
                             <table>
                             <thead>
                                     {/* FIX: Remove whitespace between tr/th */}
                                     <tr><th>Name</th><th>Num</th><th>Value (Hex / Dec)</th></tr>
                                 </thead>
                                 <tbody>
                                    {/* FIX: Remove whitespace between map/tr and tr/td */}
                                    {/* Map through the registers array */}
                                    {simState.registers.map((value, regIndex) => ( // FIX: Use regIndex instead of index
                                        <tr key={`reg-${regIndex}`}><td>{REGISTER_MAP_REV[regIndex] || `$${regIndex}`}</td><td>{regIndex}</td><td>{formatRegisterValue(value)}</td></tr>
                                    ))}
                                    {/* Display special registers */}
                                     <tr><td>pc</td><td>-</td><td>{formatAddress(simState.pc)}</td></tr>
                                     <tr><td>hi</td><td>-</td><td>{formatRegisterValue(simState.hi)}</td></tr>
                                     <tr><td>lo</td><td>-</td><td>{formatRegisterValue(simState.lo)}</td></tr>
                                 </tbody>
                             </table>
                         </div>
                         {/* Display current simulator status */}
                         <div className="simStatus">
                            Status: <strong>{simState.state}</strong>
                         </div>
                         {/* Display exit code AND termination reason if finished */}
                         {simState.state === 'finished' && (
                             <div className="simStatus">
                                 Exit Code: {simState.exit_code ?? 'N/A'}
                                 {/* --- FIX: Display Termination Reason --- */}
                                 <br /> {/* Add line break */}
                                 Reason: {simState.termination_reason || 'Finished'} {/* Display reason */}
                                 {/* --- END FIX --- */}
                             </div>
                         )}
                         {/* Display error message if in error state */}
                         {simState.state === 'error' && <div className="simStatus error">Error: {simState.error || 'Unknown Error'}</div>}
                    </div>

                    {/* Memory & I/O Column */}
                    <div className="section">
                        {/* Memory View */}
                        <div>
                             <h3>Memory View (Partial)</h3>
                             {/* Scrollable table for memory view */}
                             <div className="outputPre memoryTableWrapper">
                                 <table>
                                 <thead>
                                      {/* FIX: Remove whitespace between tr/th */}
                                      <tr><th>Address</th><th>Value (Hex Word)</th></tr>
                                  </thead>
                                     <tbody>
                                        {/* FIX: Remove whitespace between map/tr and tr/td */}
                                        {/* Sort memory addresses from the view before displaying */}
                                        {Object.entries(simState.memory_view)
                                            .map(([addrStr, val]) => ({ address: parseInt(addrStr), value: val }))
                                            .sort((a, b) => a.address - b.address)
                                            .map(({ address, value }) => (
                                                <tr key={`mem-${address}`}><td>{formatAddress(address)}</td><td>{formatRegisterValue(value)}</td></tr>
                                        ))}
                                     </tbody>
                                 </table>
                             </div>
                        </div>
                        {/* I/O Console View */}
                        <div>
                            <h3>I/O Console Output</h3>
                            {/* Display output generated by syscalls */}
                             <pre className="outputPre ioConsole">
                                 {simState.output}
                             </pre>
                             {/* Indicate if the simulator is waiting for input */}
                             {simState.input_needed && <div className="simStatus">Waiting for input...</div>}
                             {/* TODO: Add Input field here later for read syscalls */}
                        </div>
                    </div>
                </div>
            ) : (
                // Message shown if simulation hasn't been loaded yet
                // FIX: Escape apostrophes
                <p>Assemble code and click &quot;Load Simulation&quot; to begin.</p>
            )}
        </main>
    );
}