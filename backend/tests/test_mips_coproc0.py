import unittest
from backend.mips_coproc0 import MipsCoproc0

class TestMipsCoproc0(unittest.TestCase):
    def setUp(self):
        self.cp0 = MipsCoproc0()

    def test_rw_registers(self):
        self.cp0.write_reg(12, 0x12345678)
        self.assertEqual(self.cp0.read_reg(12), 0x12345678)
        
        # Write to non-existent register does nothing
        self.cp0.write_reg(99, 0xFFFFFFFF)
        self.assertEqual(self.cp0.read_reg(99), 0)

    def test_trigger_exception(self):
        epc_val = 0x00400020
        bad_vaddr = 0x10000001
        exc_code = 4 # Address Error (Load)
        
        self.cp0.trigger_exception(exc_code, epc_val, bad_vaddr)
        
        self.assertEqual(self.cp0.read_reg(14), epc_val)
        self.assertEqual(self.cp0.read_reg(8), bad_vaddr)
        
        # Cause register should have ExcCode in bits 2-6
        cause = self.cp0.read_reg(13)
        actual_exc_code = (cause >> 2) & 0x1F
        self.assertEqual(actual_exc_code, exc_code)

if __name__ == '__main__':
    unittest.main()
