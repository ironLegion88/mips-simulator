import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import axios from 'axios';
import { Terminal as TerminalIcon } from 'lucide-react';

const API_BASE_URL = 'http://localhost:5001/api';

export default function Terminal() {
  const [output, setOutput] = useState<string>('');
  const terminalRef = useRef<HTMLDivElement>(null);

  // Focus terminal automatically
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.focus();
    }
  }, []);

  const handleKeyDown = async (e: KeyboardEvent<HTMLDivElement>) => {
    // Only capture printable characters and Enter
    if (e.key.length === 1 || e.key === 'Enter') {
      const asciiVal = e.key === 'Enter' ? 10 : e.key.charCodeAt(0);
      
      // Update local output for visual feedback
      setOutput(prev => prev + (e.key === 'Enter' ? '\n' : e.key));
      
      try {
        await axios.post(`${API_BASE_URL}/simulate/mmio_write`, {
          address: 0xFFFF0004, // Receiver Data
          value: asciiVal
        });
      } catch (err) {
        console.error("Failed to send keystroke to MMIO", err);
      }
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg flex flex-col h-full font-mono">
      <div className="bg-slate-800 px-4 py-2 border-b border-slate-700 flex items-center gap-2 text-slate-300 text-sm">
        <TerminalIcon size={16} />
        MMIO Terminal (0xFFFF0000)
      </div>
      <div 
        ref={terminalRef}
        className="flex-1 p-4 overflow-y-auto text-emerald-400 focus:outline-none focus:ring-1 focus:ring-accent-cyan whitespace-pre-wrap"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {output}
        <span className="animate-pulse bg-emerald-400 w-2 h-4 inline-block ml-1 align-middle"></span>
      </div>
    </div>
  );
}
