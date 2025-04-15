// frontend/src/app/page.tsx
'use client';

import React, { useState, useEffect, useRef } from 'react'; // Added useRef
import axios from 'axios';
import Editor, { Monaco } from '@monaco-editor/react'; // Import Monaco type

const API_BASE_URL = 'http://localhost:5001/api';

interface ApiError {
  line?: number; // Optional line number
  message: string;
}

// MIPS Language Definition for Monaco
function setupMipsLanguage(monaco: Monaco) {
  // Check if language already exists
  if (monaco.languages.getLanguages().some(lang => lang.id === 'mips')) {
     console.log("MIPS language already registered.");
     return;
  }
  console.log("Registering MIPS language.");

  monaco.languages.register({ id: 'mips' });

  monaco.languages.setMonarchTokensProvider('mips', {
    // Basic MIPS Keywords and Registers
    registers: [
      '$zero', '$at', '$v0', '$v1', '$a0', '$a1', '$a2', '$a3',
      '$t0', '$t1', '$t2', '$t3', '$t4', '$t5', '$t6', '$t7',
      '$s0', '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
      '$t8', '$t9', '$k0', '$k1', '$gp', '$sp', '$fp', '$ra',
      // Also allow numbers $0 through $31
      '$0', '$1', '$2', '$3', '$4', '$5', '$6', '$7', '$8', '$9', '$10',
      '$11', '$12', '$13', '$14', '$15', '$16', '$17', '$18', '$19', '$20',
      '$21', '$22', '$23', '$24', '$25', '$26', '$27', '$28', '$29', '$30', '$31'
    ],
    keywords: [
      'add', 'addu', 'addi', 'addiu', 'sub', 'subu', 'and', 'andi', 'or', 'ori',
      'xor', 'xori', 'nor', 'slt', 'sltu', 'slti', 'sltiu', 'sll', 'srl', 'sra',
      'sllv', 'srlv', 'srav', 'lw', 'sw', 'lb', 'sb', 'lh', 'sh', 'lui',
      'beq', 'bne', 'blez', 'bgtz', 'bltz', 'bgez', 'j', 'jal', 'jr', 'jalr',
      'syscall', 'mfhi', 'mflo', 'mthi', 'mtlo', 'mult', 'multu', 'div', 'divu',
      // Pseudo Instructions (optional to highlight differently)
      'move', 'li', 'la', 'blt', 'bgt', 'ble', 'bge', 'nop', 'clear'
    ],
    directives: [
        '.data', '.text', '.globl', '.word', '.byte', '.half', '.space', '.asciiz', '.align'
    ],
    tokenizer: {
      root: [
        // Identifiers and Keywords
        [/[a-zA-Z_]\w*/, {
          cases: {
            '@keywords': 'keyword', // MIPS instructions
            '@registers': 'variable.predefined', // Registers
            '@directives': 'keyword.directive', // Assembler directives
            '@default': 'identifier' // Labels potentially
          }
        }],
        // Labels ending with :
        [/([a-zA-Z_]\w*)\s*:/, 'type.identifier'], // Label definition

        // Numbers (hex, decimal)
        [/0[xX][0-9a-fA-F]+/, 'number.hex'],
        [/-?\d+/, 'number'],

        // Comments
        [/#.*$/, 'comment'],

        // Strings for .asciiz (basic)
        [/"([^"\\]|\\.)*$/, 'string.invalid'], // Unterminated string
        [/"/, { token: 'string.quote', bracket: '@open', next: '@string' }],

        // Delimiters and Operators (commas, parentheses for memory access)
        [/[(),]/, 'delimiter'],
      ],
      string: [
          [/[^\\"]+/, 'string'],
          [/\\./, 'string.escape.invalid'],
          [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }]
      ],
    }
  });

  // Optional: Define a custom theme or use existing ones ('vs-dark', 'light')
  monaco.editor.defineTheme('mips-dark', {
      base: 'vs-dark',
      inherit: true,
      rules: [
          { token: 'keyword', foreground: 'C586C0' }, // Pink/Purple for keywords
          { token: 'variable.predefined', foreground: '4FC1FF' }, // Blue for registers
          { token: 'number', foreground: 'B5CEA8'}, // Green for numbers
          { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
          { token: 'string', foreground: 'CE9178' }, // Orange for strings
          { token: 'type.identifier', foreground: 'DCDCAA' }, // Yellow for labels
          { token: 'keyword.directive', foreground: '9CDCFE'} // Light blue for directives
      ],
      colors: {
          'editor.foreground': '#D4D4D4',
      }
  });
    console.log("MIPS language and theme defined.");
}


export default function Home() {
  const [pingResponse, setPingResponse] = useState<string>('Pinging backend...');
  const [assemblyCode, setAssemblyCode] = useState<string>(
    "# Sample MIPS Code\n" +
    ".data\n" +
    "my_label: .word 10\n" +
    ".text\n" +
    "main:\n" +
    "  li $v0, 1      # syscall code for print integer\n" +
    "  la $a0, my_label # load address of my_label\n" +
    "  lw $a0, 0($a0) # load value from address\n" +
    "  syscall        # print the integer (should be 10)\n" +
    "\n" +
    "  # Exit syscall\n" +
    "  li $v0, 10\n" +
    "  syscall\n"
  );
  const [machineCode, setMachineCode] = useState<string[]>([]);
  const [disassemblyInput, setDisassemblyInput] = useState<string>("0x24020001\n0x3c041001\n0x8c840000\n0x0000000c"); // Example li, la -> lui/ori, lw, syscall
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
  }, []);

  const handleAssemblyChange = (value: string | undefined) => {
    setAssemblyCode(value || "");
  };

  const handleAssemble = () => {
    setErrorMessages([]);
    setMachineCode([]);
    axios.post(`${API_BASE_URL}/assemble`, { assembly: assemblyCode })
      .then(response => {
        if (response.data.errors && response.data.errors.length > 0) {
          setErrorMessages(response.data.errors);
          setMachineCode([]); // Clear machine code output on error
        } else {
          setMachineCode(response.data.machine_code || []);
          setErrorMessages([]); // Clear errors on success
        }
      })
      .catch(error => {
        console.error("Assembly Error:", error);
        // Use safe access for nested properties
        const backendMessage = error?.response?.data?.errors?.[0]?.message;
        const fallbackMessage = error instanceof Error ? error.message : "Failed to assemble code.";
        setErrorMessages([{ message: `Network or Server Error: ${backendMessage || fallbackMessage}` }]);
        setMachineCode([]);
      });
  };

  const handleDisassemble = () => {
    setErrorMessages([]);
    setDisassemblyOutput("");
    try {
      const lines = disassemblyInput.split('\n').map(line => line.trim()).filter(line => line.length > 0);
      // Add 0x prefix if missing, basic validation
      const validLines = lines.map(line => {
         if (!line.startsWith('0x')) line = `0x${line}`;
         if (!/^0x[0-9a-fA-F]{1,8}$/.test(line)) throw new Error(`Invalid hex format: ${line}`);
         // Pad to 8 hex digits (excluding 0x)
         return '0x' + line.substring(2).padStart(8, '0');
      });


      axios.post(`${API_BASE_URL}/disassemble`, { machine_code: validLines })
        .then(response => {
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
    } catch (e) {
       // Safely extract error message
       const message = (e instanceof Error) ? e.message : String(e);
       setErrorMessages([{ message: `Input Error: ${message}` }]);
       setDisassemblyOutput('');
    }
  };

  return (
    // Use className for main container
    <main className="container">
      <h1>MIPS Assembler & Disassembler</h1>
      <p>{pingResponse}</p>

      {/* Error Display Area */}
      {errorMessages.length > 0 && (
        // Use className for error box
        <div className="errorBox">
          <strong>Errors:</strong>
          <ul>
            {errorMessages.map((err, index) => (
              <li key={index}>
                 {err.line ? `Line ${err.line}: ` : ''}{err.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Use className for section container */}
      <div className="sectionContainer">
        {/* Assembly Section */}
        {/* Use className for section */}
        <div className="section">
          <h2>Assembly Input</h2>
          {/* Use className for editor wrapper */}
          <div className="editorWrapper">
            <Editor
              // Height is now controlled by editorWrapper CSS
              language="mips"
              theme="mips-dark"
              value={assemblyCode}
              onChange={handleAssemblyChange}
              beforeMount={handleEditorWillMount}
              options={{ minimap: { enabled: false }, wordWrap: 'on' }}
            />
          </div>
          {/* Use className for button */}
          <button onClick={handleAssemble} className="button">Assemble</button>
          <div>
            <h3>Machine Code Output (Hex)</h3>
            {/* Use className for output pre */}
            <pre className="outputPre">
              {machineCode.join('\n')}
            </pre>
          </div>
        </div>

        {/* Disassembly Section */}
         {/* Use className for section */}
        <div className="section">
          <h2>Machine Code Input (Hex)</h2>
          {/* Use className for text area */}
          <textarea
             className="textArea" // Apply className
             rows={10} // rows might not be needed if height is set via CSS
             value={disassemblyInput}
             onChange={(e) => setDisassemblyInput(e.target.value)}
             placeholder="Enter 32-bit hex machine code (e.g., 0x212800ff), one per line. '0x' prefix is optional."
          />
           {/* Use className for button */}
          <button onClick={handleDisassemble} className="button">Disassemble</button>
           <div>
            <h3>Assembly Output</h3>
             {/* Use className for output pre */}
            <pre className="outputPre">
              {disassemblyOutput}
            </pre>
          </div>
        </div>
      </div>
    </main>
  );
}