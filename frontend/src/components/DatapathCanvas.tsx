import React, { useCallback, useMemo } from 'react';
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

const initialNodes: Node[] = [
  {
    id: 'pc',
    position: { x: 50, y: 250 },
    data: { label: 'PC' },
    style: { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155' }
  },
  {
    id: 'instr_mem',
    position: { x: 200, y: 250 },
    data: { label: 'Instruction Memory' },
    style: { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', width: 120, height: 100 }
  },
  {
    id: 'mux_regdst',
    position: { x: 380, y: 350 },
    data: { label: 'MUX (RegDst)' },
    style: { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', borderRadius: '20px', width: 60, height: 40, fontSize: '10px' }
  },
  {
    id: 'reg_file',
    position: { x: 480, y: 250 },
    data: { label: 'Registers' },
    style: { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', width: 100, height: 120 }
  },
  {
    id: 'mux_alusrc',
    position: { x: 620, y: 320 },
    data: { label: 'MUX (ALUSrc)' },
    style: { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', borderRadius: '20px', width: 60, height: 40, fontSize: '10px' }
  },
  {
    id: 'alu',
    position: { x: 720, y: 200 },
    data: { label: 'ALU' },
    style: { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', clipPath: 'polygon(0% 0%, 100% 25%, 100% 75%, 0% 100%, 0% 60%, 20% 50%, 0% 40%)', width: 100, height: 140 }
  },
  {
    id: 'data_mem',
    position: { x: 880, y: 250 },
    data: { label: 'Data Memory' },
    style: { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', width: 120, height: 100 }
  },
  {
    id: 'mux_memtoreg',
    position: { x: 1050, y: 250 },
    data: { label: 'MUX (MemtoReg)' },
    style: { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', borderRadius: '20px', width: 60, height: 40, fontSize: '10px' }
  },
  {
    id: 'control_unit',
    position: { x: 480, y: 50 },
    data: { label: 'Control Unit' },
    style: { backgroundColor: '#1E293B', color: 'white', border: '1px solid #334155', borderRadius: '50%' }
  }
];

// Base edge config
const defaultEdgeOptions = {
  style: { strokeWidth: 2, stroke: '#334155' },
  type: 'smoothstep',
  markerEnd: {
    type: MarkerType.ArrowClosed,
    color: '#334155',
  },
};

const baseEdges: Edge[] = [
  { id: 'e-pc-imem', source: 'pc', target: 'instr_mem', ...defaultEdgeOptions },
  { id: 'e-imem-ctrl', source: 'instr_mem', target: 'control_unit', ...defaultEdgeOptions },
  { id: 'e-imem-reg', source: 'instr_mem', target: 'reg_file', ...defaultEdgeOptions },
  { id: 'e-imem-mux_regdst', source: 'instr_mem', target: 'mux_regdst', ...defaultEdgeOptions },
  { id: 'e-mux_regdst-reg', source: 'mux_regdst', target: 'reg_file', ...defaultEdgeOptions },
  { id: 'e-reg-alu', source: 'reg_file', target: 'alu', ...defaultEdgeOptions },
  { id: 'e-reg-mux_alusrc', source: 'reg_file', target: 'mux_alusrc', ...defaultEdgeOptions },
  { id: 'e-mux_alusrc-alu', source: 'mux_alusrc', target: 'alu', ...defaultEdgeOptions },
  { id: 'e-alu-dmem', source: 'alu', target: 'data_mem', ...defaultEdgeOptions },
  { id: 'e-alu-mux_memtoreg', source: 'alu', target: 'mux_memtoreg', ...defaultEdgeOptions },
  { id: 'e-dmem-mux_memtoreg', source: 'data_mem', target: 'mux_memtoreg', ...defaultEdgeOptions },
  { id: 'e-mux_memtoreg-reg', source: 'mux_memtoreg', target: 'reg_file', ...defaultEdgeOptions },
];

export const DatapathCanvas: React.FC<{ pipelineState: PipelineState | null }> = ({ pipelineState }) => {
  const activeSignals = useSignalAnimator(pipelineState);

  const edges = useMemo(() => {
    return baseEdges.map((edge) => {
      let isActive = false;
      let strokeColor = '#334155'; // Default
      
      // Determine if this edge should be animated based on activeSignals
      if (edge.id === 'e-pc-imem' && activeSignals.has('if_active')) {
          isActive = true;
          strokeColor = '#06B6D4'; // Cyan for Data
      }
      if (edge.id === 'e-imem-reg' && activeSignals.has('id_active')) {
          isActive = true;
          strokeColor = '#06B6D4';
      }
      if (edge.id === 'e-imem-ctrl' && activeSignals.has('id_active')) {
          isActive = true;
          strokeColor = '#6366F1'; // Violet for Control
      }
      if (edge.id === 'e-reg-alu' && activeSignals.has('ex_active')) {
          isActive = true;
          strokeColor = '#06B6D4';
      }
      if (edge.id === 'e-alu-dmem' && activeSignals.has('mem_read')) {
          isActive = true;
          strokeColor = '#06B6D4';
      }
      if (edge.id === 'e-alu-dmem' && activeSignals.has('mem_write')) {
          isActive = true;
          strokeColor = '#06B6D4';
      }
      if (edge.id === 'e-dmem-wb' && (activeSignals.has('reg_write') || activeSignals.has('mem_to_reg'))) {
          isActive = true;
          strokeColor = '#06B6D4'; // Green for Writeback
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
