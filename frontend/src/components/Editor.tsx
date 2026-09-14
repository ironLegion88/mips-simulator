import React, { useRef, useEffect } from 'react';
import MonacoEditor, { Monaco, OnMount } from '@monaco-editor/react';

// The bit-fields metadata interface
export interface BitFields {
  opcode: number;
  rs: number;
  rt: number;
  rd: number;
  shamt: number;
  funct: number;
  imm: number;
  addr: number;
}

interface EditorProps {
  code: string;
  onChange: (value: string | undefined) => void;
  // Map of line number -> bit_fields
  bitFieldsMap?: Record<number, BitFields>;
  currentLine?: number;
  breakpoints?: number[];
  onBreakpointChange?: (line: number, isAdding: boolean) => void;
}

export default function Editor({ code, onChange, bitFieldsMap = {}, currentLine, breakpoints = [], onBreakpointChange }: EditorProps) {
  const monacoRef = useRef<Monaco | null>(null);
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);
  const editorDecorationsRef = useRef<string[]>([]);
  const bpDecorationsRef = useRef<string[]>([]);
  
  // We need a ref for bitFieldsMap to use inside the hover provider without re-registering
  const bitFieldsRef = useRef(bitFieldsMap);
  useEffect(() => {
    bitFieldsRef.current = bitFieldsMap;
  }, [bitFieldsMap]);

  useEffect(() => {
    if (editorRef.current && monacoRef.current && currentLine !== undefined) {
      const monaco = monacoRef.current;
      const editor = editorRef.current;
      
      const newDecorations: import('monaco-editor').editor.IModelDeltaDecoration[] = [];
      newDecorations.push({
        range: new monaco.Range(currentLine, 1, currentLine, 1),
        options: {
          isWholeLine: true,
          className: 'current-execution-line'
        }
      });
      
      editor.revealLineInCenterIfOutsideViewport(currentLine, monaco.editor.ScrollType.Smooth);
      
      editorDecorationsRef.current = editor.deltaDecorations(
        editorDecorationsRef.current,
        newDecorations
      );
    } else if (editorRef.current) {
      editorDecorationsRef.current = editorRef.current.deltaDecorations(
        editorDecorationsRef.current,
        []
      );
    }
  }, [currentLine]);

  useEffect(() => {
    if (!editorRef.current || !monacoRef.current) return;
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    const decorations = breakpoints.map(line => ({
      range: new monaco.Range(line, 1, line, 1),
      options: {
        isWholeLine: false,
        glyphMarginClassName: 'breakpoint-glyph'
      }
    }));
    bpDecorationsRef.current = editor.deltaDecorations(bpDecorationsRef.current, decorations);
  }, [breakpoints]);

  useEffect(() => {
    if (!editorRef.current || !monacoRef.current) return;
    const editor = editorRef.current;
    const disposable = editor.onMouseDown((e) => {
      if (e.target.type === monacoRef.current?.editor.MouseTargetType.GUTTER_GLYPH_MARGIN) {
        const line = e.target.position?.lineNumber;
        if (line && onBreakpointChange) {
           const hasBreakpoint = breakpoints.includes(line);
           onBreakpointChange(line, !hasBreakpoint);
        }
      }
    });
    return () => disposable.dispose();
  }, [breakpoints, onBreakpointChange]);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    monacoRef.current = monaco;
    editorRef.current = editor;

    // Check if the language is already registered
    const languages = monaco.languages.getLanguages();
    if (!languages.some(lang => lang.id === 'mips')) {
      monaco.languages.register({ id: 'mips' });

      // Monarch syntax highlighting
      monaco.languages.setMonarchTokensProvider('mips', {
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
          'bltzal', 'bgezal', 'move', 'li', 'la', 'blt', 'bgt', 'ble', 'bge', 'nop', 'clear'
        ],
        directives: [
          '.data', '.text', '.globl', '.extern', '.word', '.byte', '.half', '.space', '.asciiz', '.ascii', '.align'
        ],
        tokenizer: {
          root: [
            [/#.*$/, 'comment'],
            [/^\s*\.[a-zA-Z]+/, { token: 'keyword.directive' }],
            [/^([a-zA-Z_]\w*)\s*:/, 'type.identifier'],
            [/[$.a-zA-Z_]\w*/, {
              cases: {
                '@keywords': 'keyword',
                '@registers': 'variable.predefined',
                '@default': 'identifier'
              }
            }],
            [/0[xX][0-9a-fA-F]+/, 'number.hex'],
            [/-?\d+/, 'number'],
            [/"([^"\\]|\\.)*$/, 'string.invalid'],
            [/"/, { token: 'string.quote', bracket: '@open', next: '@string' }],
            [/[(),]/, 'delimiter'],
          ],
          string: [
            [/[^\\"]+/, 'string'],
            [/\\./, 'string.escape.invalid'],
            [/"/, { token: 'string.quote', bracket: '@close', next: '@pop' }]
          ],
        }
      });

      monaco.editor.defineTheme('mips-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [
          { token: 'keyword', foreground: 'C586C0' },
          { token: 'keyword.directive', foreground: '4FD0FF' },
          { token: 'variable.predefined', foreground: '9CDCFE' },
          { token: 'number', foreground: 'B5CEA8'},
          { token: 'comment', foreground: '6A9955', fontStyle: 'italic' },
          { token: 'string', foreground: 'CE9178' },
          { token: 'type.identifier', foreground: 'DCDCAA' },
          { token: 'identifier', foreground: 'D4D4D4'},
          { token: 'delimiter', foreground: 'D4D4D4'},
        ],
        colors: {
          'editor.background': '#1E293B', // Tailwind slate-800
        }
      });
      
      // Register Hover Provider
      monaco.languages.registerHoverProvider('mips', {
        provideHover: (model, position) => {
          const lineMap = bitFieldsRef.current;
          const fields = lineMap[position.lineNumber];
          
          if (!fields) return null;
          
          // Determine instruction type from opcode
          let formatStr = '';
          if (fields.opcode === 0) {
            // R-Type
            formatStr = `**R-Type**\n- Opcode: ${fields.opcode}\n- rs: ${fields.rs}\n- rt: ${fields.rt}\n- rd: ${fields.rd}\n- shamt: ${fields.shamt}\n- funct: 0x${fields.funct.toString(16)}`;
          } else if (fields.opcode === 2 || fields.opcode === 3) {
            // J-Type
            formatStr = `**J-Type**\n- Opcode: ${fields.opcode}\n- Target Address: 0x${fields.addr.toString(16)}`;
          } else {
            // I-Type
            formatStr = `**I-Type**\n- Opcode: ${fields.opcode}\n- rs: ${fields.rs}\n- rt: ${fields.rt}\n- Immediate: 0x${fields.imm.toString(16)}`;
          }
          
          return {
            range: new monaco.Range(position.lineNumber, 1, position.lineNumber, model.getLineMaxColumn(position.lineNumber)),
            contents: [
              { value: `### Instruction Bit-Fields\n${formatStr}` }
            ]
          };
        }
      });
    }
  };

  return (
    <MonacoEditor
      height="100%"
      language="mips"
      theme="mips-dark"
      value={code}
      onChange={onChange}
      onMount={handleEditorDidMount}
      options={{
        minimap: { enabled: false },
        wordWrap: 'on',
        fontSize: 14,
        fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
        glyphMargin: true,
        padding: { top: 16 },
      }}
    />
  );
}
