"use client";

import React from 'react';
import { useUIStore, ViewMode } from '../store/useUIStore';
import { Play, Pause, SkipBack, SkipForward, RotateCcw, Settings, Download } from 'lucide-react';

export default function Shell({ children, controls }: { children: React.ReactNode, controls?: React.ReactNode }) {
  const { viewMode, setViewMode } = useUIStore();
  const modes: ViewMode[] = ['Simulator', 'Datapath', 'Memory', 'Profiler'];

  return (
    <div className="min-h-screen bg-slate-900 text-foreground flex flex-col font-sans">
      {/* Top Navigation Header */}
      <header className="h-14 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-4 sticky top-0 z-50">
        
        {/* Left: Logo and View Mode Switcher */}
        <div className="flex items-center space-x-6">
          <div className="text-accent-cyan font-bold text-lg tracking-wide">
            MIPS Studio
          </div>
          
          <nav className="flex space-x-1 bg-slate-900 rounded-lg p-1">
            {modes.map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  viewMode === mode
                    ? 'bg-slate-700 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {mode}
              </button>
            ))}
          </nav>
        </div>

        {/* Center: Execution Controls */}
        <div className="flex items-center space-x-2">
          {controls}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center space-x-4">
          <select className="bg-slate-900 border border-slate-700 text-sm rounded-md px-2 py-1 text-slate-300 focus:outline-none focus:border-accent-cyan">
            <option>Factorial (Recursive)</option>
            <option>Array BubbleSort</option>
          </select>
          
          <div className="flex items-center space-x-2 border-l border-slate-700 pl-4">
            <button className="text-slate-400 hover:text-white transition-colors">
              <Download size={18} />
            </button>
            <button className="text-slate-400 hover:text-white transition-colors">
              <Settings size={18} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Area */}
      <main className="flex-1 overflow-hidden relative">
        {children}
      </main>
    </div>
  );
}
