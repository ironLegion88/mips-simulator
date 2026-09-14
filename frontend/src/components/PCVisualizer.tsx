import React from 'react';

interface BitFields {
  opcode: number;
  rs: number;
  rt: number;
  rd: number;
  shamt: number;
  funct: number;
  imm: number;
  addr: number;
}

interface PCVisualizerProps {
  pc: number;
  machineCode: any[];
}

export default function PCVisualizer({ pc, machineCode }: PCVisualizerProps) {
  let nextPc = pc + 4;
  let branchTarget: number | undefined;

  const instrIdx = (pc - 0x00400000) / 4;
  if (instrIdx >= 0 && instrIdx < machineCode.length) {
      const bf = machineCode[instrIdx]?.bit_fields as BitFields | undefined;
      if (bf) {
          if (bf.opcode === 2 || bf.opcode === 3) {
              branchTarget = (bf.addr << 2) | ((pc + 4) & 0xF0000000);
          } else if (bf.opcode === 4 || bf.opcode === 5 || bf.opcode === 6 || bf.opcode === 7 || bf.opcode === 1) {
              let imm_signed = bf.imm;
              if (imm_signed >= 0x8000) imm_signed -= 0x10000;
              branchTarget = pc + 4 + (imm_signed * 4);
          }
      }
  }

  return (
    <div className="flex gap-4 items-center bg-slate-800 px-3 py-1.5 rounded border border-slate-700 text-sm font-mono mt-2 mb-2">
      <div className="text-accent-cyan">
        <span className="opacity-75">PC:</span> 0x{pc.toString(16).padStart(8, '0')}
      </div>
      {branchTarget !== undefined ? (
        <>
          <span className="text-slate-500">➔</span>
          <div className="text-status-active font-bold">
            <span className="opacity-75 animate-pulse">Target:</span> 0x{branchTarget.toString(16).padStart(8, '0')}
          </div>
        </>
      ) : (
        <>
          <span className="text-slate-500">➔</span>
          <div className="text-slate-400">
            <span className="opacity-75">Next:</span> 0x{nextPc.toString(16).padStart(8, '0')}
          </div>
        </>
      )}
    </div>
  );
}
