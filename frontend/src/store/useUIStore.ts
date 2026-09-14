import { create } from 'zustand';

export type ViewMode = 'Simulator' | 'Datapath' | 'Memory' | 'Profiler';

interface UIState {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
}

export const useUIStore = create<UIState>((set) => ({
  viewMode: 'Simulator',
  setViewMode: (mode) => set({ viewMode: mode }),
}));
