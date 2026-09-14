import React, { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  MarkerType,
  BackgroundVariant
} from 'reactflow';
import 'reactflow/dist/style.css';
import { PipelineState, useSignalAnimator } from '../hooks/useSignalAnimator';

const latchStyle = { backgroundColor: '#475569', color: 'white', width: 30, height: 400, border: 'none', borderRadius: 5 };
const componentStyle = { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', display: 'flex', justifyContent: 'center', alignItems: 'center' };
const muxStyle = { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', borderRadius: '15px', width: 40, height: 80, fontSize: '10px', display: 'flex', justifyContent: 'center', alignItems: 'center' };
const adderStyle = { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', borderRadius: '50%', width: 50, height: 50, display: 'flex', justifyContent: 'center', alignItems: 'center' };

const initialNodes: Node[] = [
  // IF Stage
  { id: 'pc', position: { x: 50, y: 250 }, data: { label: 'PC' }, style: { ...componentStyle, width: 50, height: 80 } },
  { id: 'pc_adder', position: { x: 150, y: 100 }, data: { label: '+' }, style: adderStyle },
  { id: 'instr_mem', position: { x: 150, y: 250 }, data: { label: 'Instr Mem' }, style: { ...componentStyle, width: 100, height: 120 } },
  { id: 'mux_branch', position: { x: 50, y: 150 }, data: { label: 'MUX' }, style: muxStyle },
  
  // IF/ID Latch
  { id: 'if_id', position: { x: 300, y: 50 }, data: { label: 'IF/ID' }, style: latchStyle },

  // ID Stage
  { id: 'control_unit', position: { x: 400, y: 50 }, data: { label: 'Control' }, style: { ...componentStyle, borderRadius: '50%', width: 60, height: 60 } },
  { id: 'reg_file', position: { x: 400, y: 250 }, data: { label: 'Registers' }, style: { ...componentStyle, width: 100, height: 140 } },
  { id: 'sign_extend', position: { x: 400, y: 420 }, data: { label: 'Sign Ext' }, style: { ...componentStyle, borderRadius: '20px', width: 60, height: 40, fontSize: '10px' } },

  // ID/EX Latch
  { id: 'id_ex', position: { x: 550, y: 50 }, data: { label: 'ID/EX' }, style: latchStyle },

  // EX Stage
  { id: 'shift_left', position: { x: 620, y: 150 }, data: { label: '<< 2' }, style: { ...componentStyle, width: 40, height: 40, fontSize: '10px' } },
  { id: 'branch_adder', position: { x: 700, y: 100 }, data: { label: '+' }, style: adderStyle },
  { id: 'mux_alusrc', position: { x: 650, y: 350 }, data: { label: 'MUX' }, style: muxStyle },
  { id: 'mux_regdst', position: { x: 650, y: 450 }, data: { label: 'MUX' }, style: muxStyle },
  { id: 'alu', position: { x: 750, y: 250 }, data: { label: 'ALU' }, style: { ...componentStyle, clipPath: 'polygon(0% 0%, 100% 25%, 100% 75%, 0% 100%, 0% 60%, 20% 50%, 0% 40%)', width: 80, height: 120 } },

  // EX/MEM Latch
  { id: 'ex_mem', position: { x: 880, y: 50 }, data: { label: 'EX/MEM' }, style: latchStyle },

  // MEM Stage
  { id: 'data_mem', position: { x: 950, y: 250 }, data: { label: 'Data Mem' }, style: { ...componentStyle, width: 100, height: 120 } },

  // MEM/WB Latch
  { id: 'mem_wb', position: { x: 1100, y: 50 }, data: { label: 'MEM/WB' }, style: latchStyle },

  // WB Stage
  { id: 'mux_memtoreg', position: { x: 1180, y: 250 }, data: { label: 'MUX' }, style: muxStyle },
];

const defaultEdgeOptions = {
  style: { strokeWidth: 2, stroke: '#334155' },
  type: 'smoothstep',
  markerEnd: { type: MarkerType.ArrowClosed, color: '#334155' },
};

const baseEdges: Edge[] = [
  // IF
  { id: 'e-mux_branch-pc', source: 'mux_branch', target: 'pc', ...defaultEdgeOptions },
  { id: 'e-pc-imem', source: 'pc', target: 'instr_mem', ...defaultEdgeOptions },
  { id: 'e-pc-adder', source: 'pc', target: 'pc_adder', ...defaultEdgeOptions },
  { id: 'e-adder-mux', source: 'pc_adder', target: 'mux_branch', ...defaultEdgeOptions },
  { id: 'e-imem-if_id', source: 'instr_mem', target: 'if_id', ...defaultEdgeOptions },
  { id: 'e-adder-if_id', source: 'pc_adder', target: 'if_id', ...defaultEdgeOptions },

  // ID
  { id: 'e-if_id-ctrl', source: 'if_id', target: 'control_unit', ...defaultEdgeOptions },
  { id: 'e-if_id-reg', source: 'if_id', target: 'reg_file', ...defaultEdgeOptions },
  { id: 'e-if_id-sign', source: 'if_id', target: 'sign_extend', ...defaultEdgeOptions },
  { id: 'e-reg-id_ex_1', source: 'reg_file', target: 'id_ex', sourceHandle: 'read1', ...defaultEdgeOptions },
  { id: 'e-reg-id_ex_2', source: 'reg_file', target: 'id_ex', sourceHandle: 'read2', ...defaultEdgeOptions },
  { id: 'e-sign-id_ex', source: 'sign_extend', target: 'id_ex', ...defaultEdgeOptions },
  { id: 'e-ctrl-id_ex', source: 'control_unit', target: 'id_ex', ...defaultEdgeOptions },

  // EX
  { id: 'e-id_ex-adder', source: 'id_ex', target: 'branch_adder', ...defaultEdgeOptions },
  { id: 'e-id_ex-shift', source: 'id_ex', target: 'shift_left', ...defaultEdgeOptions },
  { id: 'e-shift-adder', source: 'shift_left', target: 'branch_adder', ...defaultEdgeOptions },
  { id: 'e-id_ex-alu1', source: 'id_ex', target: 'alu', ...defaultEdgeOptions },
  { id: 'e-id_ex-mux_alusrc', source: 'id_ex', target: 'mux_alusrc', ...defaultEdgeOptions },
  { id: 'e-mux_alusrc-alu', source: 'mux_alusrc', target: 'alu', ...defaultEdgeOptions },
  { id: 'e-id_ex-mux_regdst1', source: 'id_ex', target: 'mux_regdst', ...defaultEdgeOptions },
  { id: 'e-id_ex-mux_regdst2', source: 'id_ex', target: 'mux_regdst', ...defaultEdgeOptions },
  
  { id: 'e-adder-ex_mem', source: 'branch_adder', target: 'ex_mem', ...defaultEdgeOptions },
  { id: 'e-alu-ex_mem', source: 'alu', target: 'ex_mem', ...defaultEdgeOptions },
  { id: 'e-mux_regdst-ex_mem', source: 'mux_regdst', target: 'ex_mem', ...defaultEdgeOptions },
  { id: 'e-id_ex_rd2-ex_mem', source: 'id_ex', target: 'ex_mem', ...defaultEdgeOptions }, // Forwarded Read Data 2

  // MEM
  { id: 'e-ex_mem-dmem_addr', source: 'ex_mem', target: 'data_mem', ...defaultEdgeOptions },
  { id: 'e-ex_mem-dmem_data', source: 'ex_mem', target: 'data_mem', ...defaultEdgeOptions },
  { id: 'e-ex_mem-mux_branch', source: 'ex_mem', target: 'mux_branch', ...defaultEdgeOptions }, // Branch back
  { id: 'e-dmem-mem_wb', source: 'data_mem', target: 'mem_wb', ...defaultEdgeOptions },
  { id: 'e-ex_mem-mem_wb', source: 'ex_mem', target: 'mem_wb', ...defaultEdgeOptions }, // pass ALU result through

  // WB
  { id: 'e-mem_wb-mux_memtoreg1', source: 'mem_wb', target: 'mux_memtoreg', ...defaultEdgeOptions },
  { id: 'e-mem_wb-mux_memtoreg2', source: 'mem_wb', target: 'mux_memtoreg', ...defaultEdgeOptions },
  { id: 'e-mux_memtoreg-reg_write', source: 'mux_memtoreg', target: 'reg_file', ...defaultEdgeOptions }, // Writeback loop
];

export const DatapathCanvas: React.FC<{ pipelineState: PipelineState | null }> = ({ pipelineState }) => {
  const activeSignals = useSignalAnimator(pipelineState);

  const edges = useMemo(() => {
    return baseEdges.map((edge) => {
      let isActive = false;
      let strokeColor = '#334155'; // Default
      
      // Basic highlighting mapping
      if (edge.id.startsWith('e-pc') || edge.id.startsWith('e-adder-if')) {
          if (activeSignals.has('if_active')) { isActive = true; strokeColor = '#06B6D4'; }
      }
      if (edge.id.startsWith('e-if_id')) {
          if (activeSignals.has('id_active')) { isActive = true; strokeColor = '#06B6D4'; }
      }
      if (edge.source === 'control_unit') {
          if (activeSignals.has('id_active')) { isActive = true; strokeColor = '#6366F1'; } // Control Lines
      }
      if (edge.source === 'id_ex' && !edge.id.includes('adder') && !edge.id.includes('shift')) {
          if (activeSignals.has('ex_active')) { isActive = true; strokeColor = '#06B6D4'; }
      }
      if (edge.source === 'ex_mem') {
          if (activeSignals.has('mem_read') || activeSignals.has('mem_write')) { isActive = true; strokeColor = '#06B6D4'; }
      }
      if (edge.id.includes('mux_memtoreg') || edge.id === 'e-mux_memtoreg-reg_write') {
          if (activeSignals.has('reg_write') || activeSignals.has('mem_to_reg')) { isActive = true; strokeColor = '#06B6D4'; }
      }

      return {
        ...edge,
        animated: isActive,
        style: {
          ...edge.style,
          stroke: strokeColor,
          strokeWidth: isActive ? 3 : 2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: strokeColor,
        }
      };
    });
  }, [activeSignals]);

  return (
    <div style={{ width: '100%', height: '100%', background: '#0F172A' }}>
      <ReactFlow
        nodes={initialNodes}
        edges={edges}
        fitView
      >
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} color="#334155" />
        <Controls />
      </ReactFlow>
    </div>
  );
};
