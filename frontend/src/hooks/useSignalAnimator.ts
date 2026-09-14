import { useEffect, useState } from 'react';

// Represents the backend pipeline state
export interface PipelineState {
  pc: number;
  cycles: number;
  if_id: any;
  id_ex: any;
  ex_mem: any;
  mem_wb: any;
}

export function useSignalAnimator(pipelineState: PipelineState | null) {
  const [activeSignals, setActiveSignals] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!pipelineState) return;

    const newActiveSignals = new Set<string>();

    // Determine active signals based on current pipeline latches
    // For example, if id_ex.RegDst is 1, signal 'reg_dst' is active.
    if (pipelineState.id_ex?.RegDst) newActiveSignals.add('reg_dst');
    if (pipelineState.id_ex?.ALUSrc) newActiveSignals.add('alu_src');
    
    if (pipelineState.ex_mem?.MemRead) newActiveSignals.add('mem_read');
    if (pipelineState.ex_mem?.MemWrite) newActiveSignals.add('mem_write');
    
    if (pipelineState.mem_wb?.MemtoReg) newActiveSignals.add('mem_to_reg');
    if (pipelineState.mem_wb?.RegWrite) newActiveSignals.add('reg_write');

    // Data paths are generally always active for their respective stages,
    // but we can highlight specific paths based on operations.
    if (pipelineState.if_id?.valid) newActiveSignals.add('if_active');
    if (pipelineState.id_ex?.valid) newActiveSignals.add('id_active');
    if (pipelineState.ex_mem?.valid) newActiveSignals.add('ex_active');
    if (pipelineState.mem_wb?.valid) newActiveSignals.add('wb_active');

    setActiveSignals(newActiveSignals);
  }, [pipelineState]);

  return activeSignals;
}
