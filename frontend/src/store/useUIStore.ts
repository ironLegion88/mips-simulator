import { create } from 'zustand';
import { io, Socket } from 'socket.io-client';

export type ViewMode = 'Simulator' | 'Datapath' | 'Memory' | 'Profiler';

export interface SimulatorState {
    pc: number;                 
    registers: number[];        
    hi: number;                 
    lo: number;                 
    state: 'idle' | 'loaded' | 'running' | 'paused' | 'finished' | 'error' | 'input_wait'; 
    error: string | null;       
    exit_code: number | null;   
    termination_reason?: string;
    output: string;             
    input_needed: boolean;      
    memory_view: { [address: number]: number }; 
}

interface UIState {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  socket: Socket | null;
  simState: SimulatorState | null;
  setSimState: (state: SimulatorState | null) => void;
  connectSocket: () => void;
}

export const useUIStore = create<UIState>((set, get) => ({
  viewMode: 'Simulator',
  setViewMode: (mode) => set({ viewMode: mode }),
  socket: null,
  simState: null,
  setSimState: (state) => set({ simState: state }),
  connectSocket: () => {
    if (get().socket) return;
    const socket = io('http://localhost:5001');
    socket.on('connect', () => console.log('WebSocket connected'));
    socket.on('state_update', (state: SimulatorState) => {
        set({ simState: state });
    });
    set({ socket });
  }
}));
