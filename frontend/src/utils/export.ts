export function exportStringAsFile(content: string, filename: string, type: string = 'text/plain') {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exportMachineCodeHex(machineCode: { hex: string }[]) {
  const content = machineCode.map(mc => mc.hex).join('\n');
  exportStringAsFile(content, 'program.hex');
}

export function exportMachineCodeBin(machineCode: { bin: string }[]) {
  const content = machineCode.map(mc => mc.bin).join('\n');
  exportStringAsFile(content, 'program.bin');
}

export function exportAssembly(code: string) {
  exportStringAsFile(code, 'program.s');
}
