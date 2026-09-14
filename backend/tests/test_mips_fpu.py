import unittest
import math
from backend.mips_fpu import MipsFPU

class TestMipsFPU(unittest.TestCase):
    def setUp(self):
        self.fpu = MipsFPU()

    def test_single_precision_rw(self):
        self.fpu._write_single(0, 3.14159)
        val = self.fpu._read_single(0)
        self.assertAlmostEqual(val, 3.14159, places=5)

    def test_double_precision_rw(self):
        self.fpu._write_double(2, 3.141592653589793)
        val = self.fpu._read_double(2)
        self.assertAlmostEqual(val, 3.141592653589793, places=15)
        
        # Verify it throws when using odd register
        with self.assertRaises(ValueError):
            self.fpu._write_double(3, 1.0)
            
        with self.assertRaises(ValueError):
            self.fpu._read_double(3)

    def test_add_sub_mul_s(self):
        self.fpu._write_single(2, 2.5)
        self.fpu._write_single(4, 4.0)
        
        self.fpu.add_s(6, 2, 4)
        self.assertEqual(self.fpu._read_single(6), 6.5)
        
        self.fpu.sub_s(8, 2, 4)
        self.assertEqual(self.fpu._read_single(8), -1.5)
        
        self.fpu.mul_s(10, 2, 4)
        self.assertEqual(self.fpu._read_single(10), 10.0)

    def test_div_s(self):
        self.fpu._write_single(2, 5.0)
        self.fpu._write_single(4, 2.0)
        self.fpu.div_s(6, 2, 4)
        self.assertEqual(self.fpu._read_single(6), 2.5)

    def test_div_by_zero_ieee754(self):
        self.fpu._write_single(2, 5.0)
        self.fpu._write_single(4, 0.0)
        
        self.fpu.div_s(6, 2, 4)
        res = self.fpu._read_single(6)
        self.assertTrue(math.isinf(res))
        self.assertTrue(res > 0)
        
        # -5.0 / 0.0 = -inf
        self.fpu._write_single(2, -5.0)
        self.fpu.div_s(8, 2, 4)
        res2 = self.fpu._read_single(8)
        self.assertTrue(math.isinf(res2))
        self.assertTrue(res2 < 0)
        
        # 0.0 / 0.0 = NaN
        self.fpu._write_single(2, 0.0)
        self.fpu.div_s(10, 2, 4)
        res3 = self.fpu._read_single(10)
        self.assertTrue(math.isnan(res3))

    def test_comparisons(self):
        self.fpu._write_single(0, 1.0)
        self.fpu._write_single(2, 2.0)
        
        self.fpu.c_eq_s(0, 2)
        self.assertFalse(self.fpu.fcc)
        
        self.fpu.c_lt_s(0, 2)
        self.assertTrue(self.fpu.fcc)
        
        self.fpu.c_le_s(2, 0)
        self.assertFalse(self.fpu.fcc)

if __name__ == '__main__':
    unittest.main()
