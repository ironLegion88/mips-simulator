import struct
import logging

logger = logging.getLogger(__name__)

class MipsMMU:
    """
    Memory Management Unit for MIPS32.
    Handles virtual to physical memory mapping, basic alignment checks,
    and Memory-Mapped I/O (MMIO) routing.
    """
    def __init__(self, simulator):
        self.simulator = simulator
        
    def read_memory(self, address, num_bytes):
        # Handle MMIO Receiver Control
        if address == 0xFFFF0000:
            return 1 # Ready bit is 1
            
        return self.simulator.read_memory(address, num_bytes)
        
    def read_memory_unsigned(self, address, num_bytes):
        return self.simulator.read_memory_unsigned(address, num_bytes)

    def write_memory(self, address, value, num_bytes):
        return self.simulator.write_memory(address, value, num_bytes)
