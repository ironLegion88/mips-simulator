import struct
import math

class MipsFPU:
    """
    Simulates the MIPS Coprocessor 1 (FPU).
    Handles 32 single-precision registers and IEEE-754 arithmetic.
    """
    def __init__(self):
        # 32 32-bit registers. Stored as unsigned 32-bit integers to exactly preserve bits.
        self.registers = [0] * 32
        self.fcc = False  # Floating Point Condition Code flag
        
    def _read_single(self, reg):
        """Reads a single precision float from a register."""
        val = self.registers[reg] & 0xFFFFFFFF
        return struct.unpack('>f', struct.pack('>I', val))[0]

    def _write_single(self, reg, val):
        """Writes a single precision float to a register."""
        # Pack to float, then to unsigned int
        ival = struct.unpack('>I', struct.pack('>f', val))[0]
        self.registers[reg] = ival

    def _read_double(self, reg):
        """
        Reads a double precision float.
        In MIPS, double precision uses an even-odd register pair.
        Even register holds the lower 32 bits, odd register holds the upper 32 bits.
        """
        if reg % 2 != 0:
            raise ValueError(f"Double precision read requires an even register index, got {reg}")
            
        lower_word = self.registers[reg]
        upper_word = self.registers[reg + 1]
        
        val_64 = (upper_word << 32) | lower_word
        return struct.unpack('>d', struct.pack('>Q', val_64))[0]

    def _write_double(self, reg, val):
        """Writes a double precision float to an even-odd register pair."""
        if reg % 2 != 0:
            raise ValueError(f"Double precision write requires an even register index, got {reg}")
            
        qval = struct.unpack('>Q', struct.pack('>d', val))[0]
        lower_word = qval & 0xFFFFFFFF
        upper_word = (qval >> 32) & 0xFFFFFFFF
        
        self.registers[reg] = lower_word
        self.registers[reg + 1] = upper_word

    # Single Precision Arithmetic
    def add_s(self, fd, fs, ft):
        res = self._read_single(fs) + self._read_single(ft)
        self._write_single(fd, res)
        
    def sub_s(self, fd, fs, ft):
        res = self._read_single(fs) - self._read_single(ft)
        self._write_single(fd, res)
        
    def mul_s(self, fd, fs, ft):
        res = self._read_single(fs) * self._read_single(ft)
        self._write_single(fd, res)
        
    def div_s(self, fd, fs, ft):
        fs_val = self._read_single(fs)
        ft_val = self._read_single(ft)
        self._write_single(fd, self._do_div(fs_val, ft_val))

    # Double Precision Arithmetic
    def add_d(self, fd, fs, ft):
        res = self._read_double(fs) + self._read_double(ft)
        self._write_double(fd, res)
        
    def sub_d(self, fd, fs, ft):
        res = self._read_double(fs) - self._read_double(ft)
        self._write_double(fd, res)
        
    def mul_d(self, fd, fs, ft):
        res = self._read_double(fs) * self._read_double(ft)
        self._write_double(fd, res)
        
    def div_d(self, fd, fs, ft):
        fs_val = self._read_double(fs)
        ft_val = self._read_double(ft)
        self._write_double(fd, self._do_div(fs_val, ft_val))

    def _do_div(self, fs_val, ft_val):
        """Helper to handle IEEE-754 division by zero logic in Python."""
        try:
            return fs_val / ft_val
        except ZeroDivisionError:
            if fs_val == 0.0:
                return float('nan')
            else:
                # Determine sign of infinity
                fs_sign = math.copysign(1, fs_val)
                ft_sign = math.copysign(1, ft_val)
                return float('inf') if fs_sign == ft_sign else float('-inf')

    # Comparisons (Single & Double)
    def c_eq_s(self, fs, ft):
        self.fcc = self._read_single(fs) == self._read_single(ft)

    def c_eq_d(self, fs, ft):
        self.fcc = self._read_double(fs) == self._read_double(ft)

    def c_lt_s(self, fs, ft):
        self.fcc = self._read_single(fs) < self._read_single(ft)

    def c_lt_d(self, fs, ft):
        self.fcc = self._read_double(fs) < self._read_double(ft)

    def c_le_s(self, fs, ft):
        self.fcc = self._read_single(fs) <= self._read_single(ft)

    def c_le_d(self, fs, ft):
        self.fcc = self._read_double(fs) <= self._read_double(ft)
