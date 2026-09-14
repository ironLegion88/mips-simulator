import React from 'react';

interface StackViewProps {
  registers: number[];
  memoryView: { [address: number]: number };
  prevMemoryView?: { [address: number]: number };
}

export default function StackView({ registers, memoryView, prevMemoryView }: StackViewProps) {
  const sp = registers[29];
  const fp = registers[30];
  
  // If fp is 0 or less than sp, it's probably not being used as a frame pointer in this context,
  // or it's uninitialized. We'll show a reasonable range around sp.
  let startAddr = sp;
  let endAddr = (fp > 0 && fp >= sp && fp - sp <= 1024) ? fp : sp + 64; 
  
  // Align to words
  startAddr = Math.floor(startAddr / 4) * 4;
  endAddr = Math.floor(endAddr / 4) * 4;

  const stackAddresses = [];
  // Stack grows downwards, so display from top (higher address) to bottom (lower address)
  for (let addr = endAddr; addr >= startAddr; addr -= 4) {
      stackAddresses.push(addr);
  }

  const formatHex = (val: number | undefined) => {
      if (val === undefined) return '0x00000000';
      return `0x${(val >>> 0).toString(16).padStart(8, '0')}`;
  };

  return (
    <div className="section">
      <h3>Stack Frame Viewer</h3>
      <div className="outputPre memoryTableWrapper">
        <table>
          <thead>
            <tr>
              <th>Address</th>
              <th>Value (Hex)</th>
              <th>Pointers</th>
            </tr>
          </thead>
          <tbody>
            {stackAddresses.map((addr) => {
              const val = memoryView[addr];
              const changed = prevMemoryView && prevMemoryView[addr] !== val;
              const isSp = addr === sp;
              const isFp = addr === fp;
              
              let pointerLabel = '';
              if (isSp && isFp) pointerLabel = '<-- sp, fp';
              else if (isSp) pointerLabel = '<-- sp';
              else if (isFp) pointerLabel = '<-- fp';

              return (
                <tr key={addr} className={changed ? 'highlight-change' : ''}>
                  <td>0x{addr.toString(16).padStart(8, '0')}</td>
                  <td>{formatHex(val)}</td>
                  <td className="text-slate-400 font-bold">{pointerLabel}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
