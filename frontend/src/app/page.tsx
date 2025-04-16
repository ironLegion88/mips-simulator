// frontend/src/app/page.tsx
'use client';

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import Editor, { Monaco } from '@monaco-editor/react';

const API_BASE_URL = 'http://localhost:5001/api'; // Backend URL

// --- Types ---
type OutputFormat = 'hex' | 'bin' | 'dec';

interface MachineCodeOutput {
    hex: string;
    bin: string;
    dec: string;
}

interface ApiError {
  line?: number;
  message: string;
  text?: string; // Optionally include original text causing error
}

// MIPS Language Definition for Monaco
function setupMipsLanguage(monaco: Monaco) {
  // Prevent duplicate registration
  if (monaco.languages.getLanguages().some(lang => lang.id === 'mips')) {
     return;
  }
  monaco.languages.register({ id: 'mips' });

  monaco.languages.setMonarchTokensProvider('mips', {
    // Basic MIPS Keywords and Registers
    registers: [
      '$zero', '$at', '$v0', '$v1', '$a0', '$a1', '$a2', '$a3',
      '$t0', '$t1', '$t2', '$t3', '$t4', '$t5', '$t6', '$t7',
      '$s0', '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
      '$t8', '$t9', '$k0', '$k1', '$gp', '$sp', '$fp', '$ra',
      '$0', '$1', '$2', '$3', '$4', '$5', '$6', '$7', '$8', '$9', '$10',
      '$11', '$12', '$13', '$14', '$15', '$16', '$17', '$18', '$19', '$20',
      '$21', '$22', '$23', '$24', '$25', '$26', '$27', '$28', '$29', '$30', '$31'
    ],
    keywords: [
      'add', 'addu', 'addi', 'addiu', 'sub', 'subu', 'and', 'andi', 'or', 'ori',
      'xor', 'xori', 'nor', 'slt', 'sltu', 'slti', 'sltiu', 'sll', 'srl', 'sra',
      'sllv', 'srlv', 'srav', 'lw', 'sw', 'lb', 'sb', 'lh', 'sh', 'lui', 'lbu', 'lhu',
      'beq', 'bne', 'blez', 'bgtz', 'bltz', 'bgez', 'j', 'jal', 'jr', 'jalr',
      'syscall', 'break', 'mfhi', 'mflo', 'mthi', 'mtlo', 'mult', 'multu', 'div', 'divu',
      'bltzal', 'bgezal',
      // Common Pseudo Instructions (highlight as keywords too)
      'move', 'li', 'la', 'blt', 'bgt', 'ble', 'bge', 'nop', 'clear'
    ],
    directives: [
        '.data', '.text', '.globl', '.extern', '.word', '.byte', '.half', '.space', '.asciiz', '.ascii', '.align'
    ],
    tokenizer: {
      root: [
        // Comments
        [/#.*$/, 'comment'],

        // Directives
        [/^\s*\.[a-zA-Z]+/, { token: 'keyword.directive', next: '@directive_args'}],

        // Labels ending with :
        [/^([a-zA-Z_]\w*)\s*:/, 'type.identifier'], // Label definition at start of line

        // Keywords and Registers first
        [/[$.a-zA-Z_]\w*/, {
          cases: {
            '@keywords': 'keyword',
            '@registers': 'variable.predefined', // Registers
            '@default': 'identifier' // Could be labels used as operands or identifiers
          }
        }],

        // Numbers (hex, decimal)
        [/0[xX][0-9a-fA-F]+/, 'number.hex'],
        [/-?\d+/, 'number'],

        // Strings for directives (basic)
        [/"([^"\\]|\\.)*$/, 'string.invalid'], // Unterminated string
        [/"/, { token: 'string.quote', bracket: '@open', next: '@string' }],

        // Delimiters and Operators (commas, parentheses for memory access)
        [/[(),]/, 'delimiter'],
      ],
      // State for handling directive arguments (mainly to allow strings)
      directive_args: [
          [/#.*$/, 'comment', '@pop'], // Comment ends directive args state
          [/"([^"\\]|\\.)*$/, 'string.invalid', '@pop'],
          [/"/, { token: 'string.quote', bracket: '@open', next: '@string_in_directive' }],
          [/[^#"]+/, ''], // Consume other args
          [/$/, '', '@pop'] // End of line pops the state
      ],
      string_in_directive: [
          [/[^\\"]+/, 'string'],
          [/\\./, 'string.escape'], // Allow basic escapes like \"
          [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }] // Pop back to directive_args
      ],
      // State for handling regular strings (e.g., if needed in future for specific instructions)
      string: [
          [/[^\\"]+/, 'string'],
          [/\\./, 'string.escape.invalid'],
          [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }]
      ],
    }
  });

  // Custom theme (adjust colors as desired)
  monaco.editor.defineTheme('mips-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
          { token: 'keyword', foreground: 'C586C0' }, // Instructions etc.
          { token: 'keyword.directive', foreground: '4FD0FF' }, // Directives like .data
          { token: 'variable.predefined', foreground: '9CDCFE' }, // Registers $..
          { token: 'number', foreground: 'B5CEA8'}, // Numbers
          { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
          { token: 'string', foreground: 'CE9178' }, // Strings
          { token: 'type.identifier', foreground: 'DCDCAA' }, // Labels defined with :
          { token: 'identifier', foreground: 'D4D4D4'}, // Other identifiers (label usage)
          { token: 'delimiter', foreground: 'D4D4D4'}, // Commas, parentheses
      ],
      colors: { 'editor.foreground': '#D4D4D4' }
  });
}


export default function Home() {
  const [pingResponse, setPingResponse] = useState<string>('Pinging backend...');
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
  const [machineCode, setMachineCode] = useState<MachineCodeOutput[]>([]); // Store structured output
  const [outputFormat, setOutputFormat] = useState<OutputFormat>('hex'); // State for format selection
  const [disassemblyInput, setDisassemblyInput] = useState<string>("0x24020001\n0x3c011001\n0x34240000\n0x8c840000\n0x0000000c");
  const [disassemblyOutput, setDisassemblyOutput] = useState<string>("");
  const [errorMessages, setErrorMessages] = useState<ApiError[]>([]);
  const monacoRef = useRef<Monaco | null>(null); // Ref to store Monaco instance

  // Setup Monaco language on mount
  const handleEditorWillMount = (monacoInstance: Monaco) => {
    monacoRef.current = monacoInstance; // Store instance
    setupMipsLanguage(monacoInstance);
  };

  // Ping backend on component mount
  useEffect(() => {
    axios.get(`${API_BASE_URL}/ping`)
      .then(response => {
        setPingResponse(`Backend status: ${response.data.message}`);
      })
      .catch(error => {
        console.error("Error pinging backend:", error);
        setPingResponse('Backend status: Error - Could not connect');
      });
  }, []); // Empty dependency array means run once on mount

  const handleAssemblyChange = (value: string | undefined) => {
    setAssemblyCode(value || "");
  };

  const handleAssemble = () => {
    setErrorMessages([]); // Clear previous errors
    setMachineCode([]); // Clear previous output
    axios.post(`${API_BASE_URL}/assemble`, { assembly: assemblyCode })
      .then(response => {
        // Expect response.data to have { machine_code: MachineCodeOutput[], errors: ApiError[], data_segment: string }
        if (response.data.errors && response.data.errors.length > 0) {
          setErrorMessages(response.data.errors);
        } else {
          setErrorMessages([]); // Clear errors on success
        }
        // Always set machine code, even if partial results on error
        setMachineCode(response.data.machine_code || []);
        // TODO: Handle display of data_segment if needed
      })
      .catch(error => {
        console.error("Assembly Error:", error);
        const backendMessage = error?.response?.data?.errors?.[0]?.message;
        const fallbackMessage = error instanceof Error ? error.message : "Failed to assemble code.";
        setErrorMessages([{ message: `Network or Server Error: ${backendMessage || fallbackMessage}` }]);
        setMachineCode([]);
      });
  };

  const handleDisassemble = () => {
    setErrorMessages([]); // Clear previous errors
    setDisassemblyOutput(""); // Clear previous output
    try {
      // Split input, trim, filter empty, basic validation
      const lines = disassemblyInput.split('\n')
        .map(line => line.trim().toLowerCase().replace(/^0x/, '')) // Remove prefix, lower case
        .filter(line => line.length > 0);

      const validLines = lines.map(line => {
         if (!/^[0-9a-f]+$/.test(line)) throw new Error(`Invalid hex character in '${line.substring(0,20)}...'`);
         if (line.length > 8) throw new Error(`Hex value too long in '${line.substring(0,20)}...'`);
         // Pad and add prefix for consistency before sending to backend
         return '0x' + line.padStart(8, '0');
      });

      axios.post(`${API_BASE_URL}/disassemble`, { machine_code: validLines })
        .then(response => {
           // Expect response.data to have { assembly_code: string, errors: ApiError[] }
          if (response.data.errors && response.data.errors.length > 0) {
            setErrorMessages(response.data.errors);
            setDisassemblyOutput(''); // Clear output on error
          } else {
            setDisassemblyOutput(response.data.assembly_code || "");
            setErrorMessages([]); // Clear errors on success
          }
        })
        .catch(error => {
          console.error("Disassembly Error:", error);
          const backendMessage = error?.response?.data?.errors?.[0]?.message;
          const fallbackMessage = error instanceof Error ? error.message : "Failed to disassemble code.";
           setErrorMessages([{ message: `Network or Server Error: ${backendMessage || fallbackMessage}` }]);
           setDisassemblyOutput('');
        });
    } catch (e) { // Catch input validation errors
       const message = (e instanceof Error) ? e.message : String(e);
       setErrorMessages([{ message: `Input Error: ${message}` }]);
       setDisassemblyOutput('');
    }
  };

  return (
    <main className="container">
      <h1>MIPS Assembler & Disassembler</h1>
      <p>{pingResponse}</p>

      {/* Error Display Area */}
      {errorMessages.length > 0 && (
        <div className="errorBox">
          <strong>Errors:</strong>
          <ul>
            {errorMessages.map((err, index) => (
              <li key={index}>
                 {err.line ? `Line ${err.line}: ` : ''}{err.message}
                 {/* Optionally display err.text if available */}
                 {err.text ? <span style={{ color: '#a83232', marginLeft: '5px', fontStyle: 'italic' }}> (near '{err.text.substring(0, 30)}{err.text.length > 30 ? '...' : ''}')</span> : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="sectionContainer">
        {/* Assembly Section */}
        <div className="section">
          <h2>Assembly Input</h2>
          <div className="editorWrapper">
            <Editor
              // height prop is now handled by CSS className
              language="mips"
              theme="mips-dark" // Use the custom theme
              value={assemblyCode}
              onChange={handleAssemblyChange}
              beforeMount={handleEditorWillMount} // Setup language before mount
              options={{ minimap: { enabled: false }, wordWrap: 'on', fontSize: 13 }} // Example options
            />
          </div>
          <button onClick={handleAssemble} className="button">Assemble</button>
          <div>
            <h3>Machine Code Output</h3>
            {/* --- Output Format Selector --- */}
            <div style={{ marginBottom: '10px', marginTop:'5px' }}>
                <label style={{ marginRight: '15px', cursor:'pointer' }}>
                    <input style={{marginRight:'3px', cursor:'pointer'}} type="radio" name="format" value="hex" checked={outputFormat === 'hex'} onChange={() => setOutputFormat('hex')} /> Hex
                </label>
                <label style={{ marginRight: '15px', cursor:'pointer' }}>
                    <input style={{marginRight:'3px', cursor:'pointer'}} type="radio" name="format" value="bin" checked={outputFormat === 'bin'} onChange={() => setOutputFormat('bin')} /> Binary
                </label>
                <label style={{ cursor:'pointer' }}>
                    <input style={{marginRight:'3px', cursor:'pointer'}} type="radio" name="format" value="dec" checked={outputFormat === 'dec'} onChange={() => setOutputFormat('dec')} /> Decimal
                </label>
            </div>
            {/* --- Machine Code Display --- */}
            <pre className="outputPre">
              {/* Display based on selected format */}
              {machineCode.map((code, index) => code[outputFormat]).join('\n')}
            </pre>
          </div>
        </div>

        {/* Disassembly Section */}
        <div className="section">
          <h2>Machine Code Input (Hex)</h2>
          <textarea
             className="textArea" // Apply className for styling
             rows={10} // Still useful for initial height guess
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
      </div>
    </main>
  );
}