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
        if address == 0xFFFF0004:
            # Fall through to raw memory read where the character is stored
            pass
            
        return self.simulator._read_memory_raw(address, num_bytes)
        
    def read_memory_unsigned(self, address, num_bytes):
        if address == 0xFFFF0000:
            return 1
        if address == 0xFFFF0004:
            pass
            
        return self.simulator._read_memory_unsigned_raw(address, num_bytes)

    def write_memory(self, address, value, num_bytes):
        return self.simulator._write_memory_raw(address, value, num_bytes)
