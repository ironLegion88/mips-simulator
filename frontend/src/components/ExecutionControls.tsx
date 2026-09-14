import React from 'react';
import { Play, Pause, SkipBack, SkipForward, RotateCcw } from 'lucide-react';

export interface ExecutionControlsProps {
  onStepBack: () => void;
  onPause: () => void;
  onRun: () => void;
  onStepForward: () => void;
  onReset: () => void;
  canStepBack?: boolean;
  canPause?: boolean;
  canRun?: boolean;
  canStepForward?: boolean;
  canReset?: boolean;
}

export default function ExecutionControls({
  onStepBack, onPause, onRun, onStepForward, onReset,
  canStepBack = false, canPause = false, canRun = false, canStepForward = false, canReset = false
}: ExecutionControlsProps) {
  return (
    <div className="flex items-center space-x-2 bg-slate-900 rounded-lg p-1 px-2 border border-slate-700">
      <button 
        className={`p-1.5 rounded transition-colors ${canStepBack ? 'text-slate-200 hover:text-accent-cyan' : 'text-slate-600 cursor-not-allowed'}`} 
        title="Step Back"
        onClick={onStepBack}
        disabled={!canStepBack}
      >
        <SkipBack size={18} />
      </button>
      <button 
        className={`p-1.5 rounded transition-colors ${canPause ? 'text-slate-200 hover:text-status-active' : 'text-slate-600 cursor-not-allowed'}`} 
        title="Pause"
        onClick={onPause}
        disabled={!canPause}
      >
        <Pause size={18} />
      </button>
      <button 
        className={`p-1.5 rounded transition-colors ${canRun ? 'text-slate-200 hover:text-status-modified' : 'text-slate-600 cursor-not-allowed'}`} 
        title="Run"
        onClick={onRun}
        disabled={!canRun}
      >
        <Play size={18} />
      </button>
      <button 
        className={`p-1.5 rounded transition-colors ${canStepForward ? 'text-slate-200 hover:text-accent-cyan' : 'text-slate-600 cursor-not-allowed'}`} 
        title="Step Forward"
        onClick={onStepForward}
        disabled={!canStepForward}
      >
        <SkipForward size={18} />
      </button>
      <button 
        className={`p-1.5 rounded transition-colors ${canReset ? 'text-slate-200 hover:text-status-breakpoint' : 'text-slate-600 cursor-not-allowed'}`} 
        title="Reset"
        onClick={onReset}
        disabled={!canReset}
      >
        <RotateCcw size={18} />
      </button>
    </div>
  );
}
