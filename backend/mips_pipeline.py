from typing import Dict, Any

class PipelineLatch:
    def __init__(self):
        self.valid = False
        self.instr = 0
        self.pc = 0

    def flush(self):
        self.__init__()

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

class IF_ID(PipelineLatch):
    def __init__(self):
        super().__init__()
        self.pc_plus_4 = 0

class ID_EX(PipelineLatch):
    def __init__(self):
        super().__init__()
        self.pc_plus_4 = 0
        self.rs_val = 0
        self.rt_val = 0
        self.rs = 0
        self.rt = 0
        self.rd = 0
        self.shamt = 0
        self.sign_ext_imm = 0
        
        # Control Signals
        self.RegDst = 0
        self.ALUSrc = 0
        self.MemtoReg = 0
        self.RegWrite = 0
        self.MemRead = 0
        self.MemWrite = 0
        self.Branch = 0
        self.ALUOp = 0
        
        # Branch prediction state
        self.predicted_taken = False
        self.predicted_target = 0

class EX_MEM(PipelineLatch):
    def __init__(self):
        super().__init__()
        self.branch_target = 0
        self.branch_taken = False
        self.alu_result = 0
        self.rt_val = 0
        self.dest_reg = 0
        
        # Control Signals
        self.MemtoReg = 0
        self.RegWrite = 0
        self.MemRead = 0
        self.MemWrite = 0
        self.Branch = 0

class MEM_WB(PipelineLatch):
    def __init__(self):
        super().__init__()
        self.mem_data = 0
        self.alu_result = 0
        self.dest_reg = 0
        
        # Control Signals
        self.MemtoReg = 0
        self.RegWrite = 0

class MIPSPipeline:
    """
    A structural model of a 5-stage MIPS pipeline with Data Forwarding, 
    Hazard Detection, and Branch Prediction.
    """
    def __init__(self, memory_accessor, register_accessor):
        # Functions to read/write memory and registers without full simulator integration
        # memory_accessor(addr) -> int, memory_writer(addr, val)
        # register_accessor(reg) -> int, register_writer(reg, val)
        self.read_mem = memory_accessor
        self.read_reg = register_accessor
        
        self.pc = 0x00400000
        
        self.if_id = IF_ID()
        self.id_ex = ID_EX()
        self.ex_mem = EX_MEM()
        self.mem_wb = MEM_WB()
        
        # Statistics
        self.cycles = 0
        self.stalls = 0
        self.flushes = 0
        self.instructions_completed = 0
        
        # Branch Prediction (1-bit BHT)
        self.bht: Dict[int, bool] = {} # pc -> predicted taken

    def get_state(self):
        return {
            'pc': self.pc,
            'cycles': self.cycles,
            'stalls': self.stalls,
            'flushes': self.flushes,
            'if_id': self.if_id.to_dict(),
            'id_ex': self.id_ex.to_dict(),
            'ex_mem': self.ex_mem.to_dict(),
            'mem_wb': self.mem_wb.to_dict(),
        }

    def decode_instruction(self, instr: int) -> Dict[str, Any]:
        """Minimal decoder to extract fields needed for pipeline."""
        opcode = (instr >> 26) & 0x3F
        rs = (instr >> 21) & 0x1F
        rt = (instr >> 16) & 0x1F
        rd = (instr >> 11) & 0x1F
        shamt = (instr >> 6) & 0x1F
        funct = instr & 0x3F
        imm = instr & 0xFFFF
        sign_ext_imm = imm if (imm & 0x8000) == 0 else (imm | 0xFFFF0000)
        
        # Very simplified control logic for structural modeling
        # Assumes basic MIPS instructions: R-type, lw, sw, beq
        ctrl = {
            'RegDst': 1 if opcode == 0 else 0,
            'ALUSrc': 0 if opcode == 0 or opcode == 4 else 1,
            'MemtoReg': 1 if opcode == 35 else 0, # lw
            'RegWrite': 1 if opcode == 0 or opcode == 35 or opcode == 8 else 0, # R-type, lw, addi
            'MemRead': 1 if opcode == 35 else 0,
            'MemWrite': 1 if opcode == 43 else 0, # sw
            'Branch': 1 if opcode == 4 else 0, # beq
            'ALUOp': 2 if opcode == 0 else (1 if opcode == 4 else 0)
        }
        
        return {
            'opcode': opcode, 'rs': rs, 'rt': rt, 'rd': rd, 
            'shamt': shamt, 'funct': funct, 'imm': imm, 
            'sign_ext_imm': sign_ext_imm, 'ctrl': ctrl
        }

    def tick(self):
        """Simulate one clock cycle."""
        # 1. Write Back (WB) Stage
        if self.mem_wb.valid:
            if self.mem_wb.RegWrite and self.mem_wb.dest_reg != 0:
                write_data = self.mem_wb.mem_data if self.mem_wb.MemtoReg else self.mem_wb.alu_result
                # self.write_reg(self.mem_wb.dest_reg, write_data) # Actually doing it might diverge state
            self.instructions_completed += 1

        # 2. Memory (MEM) Stage
        next_mem_wb = MEM_WB()
        if self.ex_mem.valid:
            next_mem_wb.valid = True
            next_mem_wb.pc = self.ex_mem.pc
            next_mem_wb.instr = self.ex_mem.instr
            next_mem_wb.MemtoReg = self.ex_mem.MemtoReg
            next_mem_wb.RegWrite = self.ex_mem.RegWrite
            next_mem_wb.dest_reg = self.ex_mem.dest_reg
            next_mem_wb.alu_result = self.ex_mem.alu_result
            
            if self.ex_mem.MemRead:
                # read data (mocked)
                next_mem_wb.mem_data = 0 # self.read_mem(self.ex_mem.alu_result)
            elif self.ex_mem.MemWrite:
                pass # self.write_mem(self.ex_mem.alu_result, self.ex_mem.rt_val)

        # 3. Execute (EX) Stage
        next_ex_mem = EX_MEM()
        if self.id_ex.valid:
            next_ex_mem.valid = True
            next_ex_mem.pc = self.id_ex.pc
            next_ex_mem.instr = self.id_ex.instr
            
            # Forwarding Unit
            forward_a = 00
            forward_b = 00
            
            # EX hazard
            if self.ex_mem.valid and self.ex_mem.RegWrite and self.ex_mem.dest_reg != 0:
                if self.ex_mem.dest_reg == self.id_ex.rs: forward_a = 10 # 2
                if self.ex_mem.dest_reg == self.id_ex.rt: forward_b = 10 # 2
            
            # MEM hazard
            if self.mem_wb.valid and self.mem_wb.RegWrite and self.mem_wb.dest_reg != 0:
                if not (self.ex_mem.valid and self.ex_mem.RegWrite and self.ex_mem.dest_reg != 0 and self.ex_mem.dest_reg == self.id_ex.rs):
                    if self.mem_wb.dest_reg == self.id_ex.rs: forward_a = 1 # 1
                if not (self.ex_mem.valid and self.ex_mem.RegWrite and self.ex_mem.dest_reg != 0 and self.ex_mem.dest_reg == self.id_ex.rt):
                    if self.mem_wb.dest_reg == self.id_ex.rt: forward_b = 1 # 1
            
            # ALU Inputs
            alu_in_a = self.id_ex.rs_val
            if forward_a == 10: alu_in_a = self.ex_mem.alu_result
            elif forward_a == 1: alu_in_a = self.mem_wb.alu_result if not self.mem_wb.MemtoReg else self.mem_wb.mem_data
            
            alu_in_b_orig = self.id_ex.rt_val
            if forward_b == 10: alu_in_b_orig = self.ex_mem.alu_result
            elif forward_b == 1: alu_in_b_orig = self.mem_wb.alu_result if not self.mem_wb.MemtoReg else self.mem_wb.mem_data
            
            alu_in_b = self.id_ex.sign_ext_imm if self.id_ex.ALUSrc else alu_in_b_orig
            
            # Simple ALU execution
            next_ex_mem.alu_result = (alu_in_a + alu_in_b) & 0xFFFFFFFF # simplified
            
            # Destination register
            next_ex_mem.dest_reg = self.id_ex.rd if self.id_ex.RegDst else self.id_ex.rt
            next_ex_mem.rt_val = alu_in_b_orig
            
            # Control lines
            next_ex_mem.MemtoReg = self.id_ex.MemtoReg
            next_ex_mem.RegWrite = self.id_ex.RegWrite
            next_ex_mem.MemRead = self.id_ex.MemRead
            next_ex_mem.MemWrite = self.id_ex.MemWrite
            next_ex_mem.Branch = self.id_ex.Branch
            
            # Branch calculation
            next_ex_mem.branch_target = (self.id_ex.pc_plus_4 + (self.id_ex.sign_ext_imm << 2)) & 0xFFFFFFFF
            next_ex_mem.branch_taken = (self.id_ex.Branch and (alu_in_a == alu_in_b_orig))
            
            # Branch Misprediction Recovery
            actual_taken = next_ex_mem.branch_taken
            actual_target = next_ex_mem.branch_target if actual_taken else self.id_ex.pc_plus_4
            
            mispredicted = False
            if actual_taken != self.id_ex.predicted_taken:
                mispredicted = True
            elif actual_taken and actual_target != self.id_ex.predicted_target:
                mispredicted = True
                
            if self.id_ex.Branch:
                self.bht[self.id_ex.pc] = actual_taken # Update predictor
                
            if mispredicted:
                self.flushes += 1
                self.if_id.flush()
                # We need to signal ID to flush too, handled below.
                # Update PC
                self.pc = actual_target

        # Hazard Detection Unit (Load-Use)
        stall = False
        if self.id_ex.valid and self.id_ex.MemRead:
            # Current instruction in ID
            if self.if_id.valid:
                dec = self.decode_instruction(self.if_id.instr)
                if self.id_ex.rt == dec['rs'] or self.id_ex.rt == dec['rt']:
                    stall = True
                    self.stalls += 1

        # 4. Instruction Decode (ID) Stage
        next_id_ex = ID_EX()
        flush_id = False
        if self.id_ex.valid and self.id_ex.Branch:
            # Check if we mispredicted (calculated in EX)
            # We already handled PC update in EX.
            # alu_in_a and alu_in_b_orig might not be defined if not valid, but we checked valid.
            actual_taken = (self.id_ex.Branch and (alu_in_a == alu_in_b_orig))
            mispredicted = actual_taken != self.id_ex.predicted_taken
            if mispredicted:
                flush_id = True
                
        if stall:
            # ID stays same, insert bubble into EX
            next_id_ex.flush()
        elif self.if_id.valid and not flush_id:
            next_id_ex.valid = True
            next_id_ex.pc = self.if_id.pc
            next_id_ex.instr = self.if_id.instr
            next_id_ex.pc_plus_4 = self.if_id.pc_plus_4
            
            dec = self.decode_instruction(self.if_id.instr)
            next_id_ex.rs = dec['rs']
            next_id_ex.rt = dec['rt']
            next_id_ex.rd = dec['rd']
            next_id_ex.shamt = dec['shamt']
            next_id_ex.sign_ext_imm = dec['sign_ext_imm']
            
            # Read registers
            next_id_ex.rs_val = self.read_reg(next_id_ex.rs) if next_id_ex.rs != 0 else 0
            next_id_ex.rt_val = self.read_reg(next_id_ex.rt) if next_id_ex.rt != 0 else 0
            
            # Control lines
            ctrl = dec['ctrl']
            next_id_ex.RegDst = ctrl['RegDst']
            next_id_ex.ALUSrc = ctrl['ALUSrc']
            next_id_ex.MemtoReg = ctrl['MemtoReg']
            next_id_ex.RegWrite = ctrl['RegWrite']
            next_id_ex.MemRead = ctrl['MemRead']
            next_id_ex.MemWrite = ctrl['MemWrite']
            next_id_ex.Branch = ctrl['Branch']
            next_id_ex.ALUOp = ctrl['ALUOp']
            
            # Branch Predictor (in ID)
            if next_id_ex.Branch:
                next_id_ex.predicted_taken = self.bht.get(next_id_ex.pc, False) # default not taken
                next_id_ex.predicted_target = (next_id_ex.pc_plus_4 + (next_id_ex.sign_ext_imm << 2)) & 0xFFFFFFFF
                if next_id_ex.predicted_taken:
                    self.pc = next_id_ex.predicted_target

        # 5. Instruction Fetch (IF) Stage
        next_if_id = self.if_id
        if not stall and not flush_id:
            next_if_id = IF_ID()
            # Try to fetch
            try:
                instr = self.read_mem(self.pc)
                if instr is not None:
                    next_if_id.valid = True
                    next_if_id.pc = self.pc
                    next_if_id.instr = instr
                    next_if_id.pc_plus_4 = self.pc + 4
                    self.pc += 4
            except Exception:
                # E.g., End of memory
                pass
                
        # Update Latches
        self.mem_wb = next_mem_wb
        self.ex_mem = next_ex_mem
        if not stall:
            self.id_ex = next_id_ex
            self.if_id = next_if_id
            
        if flush_id:
            self.id_ex = ID_EX()
            
        self.cycles += 1
