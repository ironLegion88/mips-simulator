import unittest
from backend.cache_simulator import CacheLevel

class TestCacheSimulator(unittest.TestCase):
    def test_address_parsing(self):
        # Cache size = 1024 bytes
        # Block size = 16 bytes (offset_bits = 4)
        # Associativity = 4
        # Num sets = 1024 / (16 * 4) = 16 (index_bits = 4)
        # Tag bits = 32 - 4 - 4 = 24
        cache = CacheLevel(size=1024, block_size=16, associativity=4)
        self.assertEqual(cache.offset_bits, 4)
        self.assertEqual(cache.index_bits, 4)
        self.assertEqual(cache.tag_bits, 24)
        self.assertEqual(cache.num_sets, 16)
        
        addr = 0xABCD1234
        tag, index, offset = cache.parse_address(addr)
        # offset = lower 4 bits of 4 = 4
        # index = next 4 bits of 0x34 -> 3
        # tag = remaining 24 bits -> 0xABCD12
        self.assertEqual(offset, 0x4)
        self.assertEqual(index, 0x3)
        self.assertEqual(tag, 0xABCD12)
        
        rebuilt = cache.build_address(tag, index)
        # 0xABCD1230 (offset is zeroed)
        self.assertEqual(rebuilt, 0xABCD1230)

    def test_read_hit_miss(self):
        # Direct mapped cache, 4 sets, 16 bytes per block = 64 bytes
        cache = CacheLevel(size=64, block_size=16, associativity=1)
        
        addr1 = 0x100 # tag=0x10, index=0, offset=0
        meta = cache.read(addr1)
        self.assertEqual(meta['status'], 'Miss')
        
        meta = cache.read(addr1)
        self.assertEqual(meta['status'], 'Hit')

    def test_lru_eviction(self):
        # 2-way associative, 1 set, 16 bytes block = 32 bytes
        cache = CacheLevel(size=32, block_size=16, associativity=2, replacement_policy='LRU')
        
        cache.read(0x00) # Miss, loads Tag 0 into Line 0
        cache.read(0x10) # Miss, loads Tag 1 into Line 1 (Wait, index is still 0 if index bits=0? But 1 set means index is always 0. Tag is address >> 4)
        # Yes, addr 0x00 -> tag 0, index 0
        # addr 0x10 -> tag 1, index 0
        
        # Access 0x00 to make 0x10 the LRU victim
        cache.read(0x00)
        
        # addr 0x20 -> tag 2, index 0. Should evict 0x10
        meta = cache.read(0x20)
        self.assertEqual(meta['status'], 'Miss')
        self.assertTrue(meta['evicted'])
        self.assertEqual(meta['evicted_address'], 0x10)
        
    def test_fifo_eviction(self):
        # 2-way associative, 1 set
        cache = CacheLevel(size=32, block_size=16, associativity=2, replacement_policy='FIFO')
        cache.read(0x00) # loads Tag 0, fifo_counter=1
        cache.read(0x10) # loads Tag 1, fifo_counter=2
        
        cache.read(0x00) # Access Tag 0, but this shouldn't change FIFO order
        
        # addr 0x20 -> tag 2. Should evict Tag 0 because it was loaded first
        meta = cache.read(0x20)
        self.assertEqual(meta['status'], 'Miss')
        self.assertTrue(meta['evicted'])
        self.assertEqual(meta['evicted_address'], 0x00)
        
    def test_write_back(self):
        cache = CacheLevel(size=32, block_size=16, associativity=1, write_policy='Write-Back')
        
        meta = cache.write(0x00)
        self.assertEqual(meta['status'], 'Miss')
        self.assertFalse(meta['write_through_push'])
        
        # Block 0 is now dirty
        meta = cache.write(0x20) # Conflict miss, index 0, tag 1
        self.assertEqual(meta['status'], 'Miss')
        self.assertTrue(meta['evicted'])
        self.assertTrue(meta['dirty_eviction']) # Victim (0x00) was dirty
        
    def test_write_through(self):
        cache = CacheLevel(size=32, block_size=16, associativity=1, write_policy='Write-Through')
        
        meta = cache.write(0x00)
        self.assertEqual(meta['status'], 'Miss')
        self.assertTrue(meta['write_through_push'])
        
        meta = cache.write(0x20) # Evicts 0x00
        self.assertEqual(meta['status'], 'Miss')
        self.assertTrue(meta['evicted'])
        self.assertFalse(meta['dirty_eviction']) # Nothing should be marked dirty in write-through

if __name__ == '__main__':
    unittest.main()
