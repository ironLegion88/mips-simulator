import math
import random

class CacheLine:
    """Represents a single cache line."""
    def __init__(self):
        self.valid = False
        self.dirty = False
        self.tag = None
        self.data = None
        self.lru_counter = 0
        self.fifo_counter = 0

class CacheSet:
    """Represents a set in the cache containing multiple CacheLines (N-way associativity)."""
    def __init__(self, associativity, replacement_policy):
        self.associativity = associativity
        self.replacement_policy = replacement_policy
        self.lines = [CacheLine() for _ in range(associativity)]
        self.counter = 0  # Monotonically increasing counter for LRU/FIFO
    
    def find_line(self, tag):
        for line in self.lines:
            if line.valid and line.tag == tag:
                self._update_access(line)
                return line
        return None
        
    def _update_access(self, line):
        self.counter += 1
        line.lru_counter = self.counter
        
    def _update_insert(self, line):
        self.counter += 1
        line.lru_counter = self.counter
        line.fifo_counter = self.counter

    def insert(self, tag, data=None, dirty=False):
        """
        Inserts a new block into the set.
        Returns evicted block info if eviction was necessary, else None.
        """
        # 1. Try to find an invalid (empty) line
        for line in self.lines:
            if not line.valid:
                line.valid = True
                line.tag = tag
                line.data = data
                line.dirty = dirty
                self._update_insert(line)
                return None  # No eviction
                
        # 2. Need to evict
        victim_line = self._choose_victim()
        evicted_tag = victim_line.tag
        evicted_dirty = victim_line.dirty
        evicted_data = victim_line.data
        
        # Replace
        victim_line.tag = tag
        victim_line.data = data
        victim_line.dirty = dirty
        self._update_insert(victim_line)
        
        return {
            'tag': evicted_tag,
            'dirty': evicted_dirty,
            'data': evicted_data
        }

    def _choose_victim(self):
        if self.replacement_policy == 'LRU':
            return min(self.lines, key=lambda l: l.lru_counter)
        elif self.replacement_policy == 'FIFO':
            return min(self.lines, key=lambda l: l.fifo_counter)
        elif self.replacement_policy == 'Random':
            return random.choice(self.lines)
        else:
            raise ValueError(f"Unknown replacement policy: {self.replacement_policy}")

class CacheLevel:
    """Represents a single level of cache (e.g., L1, L2)."""
    def __init__(self, size, block_size, associativity, write_policy='Write-Back', replacement_policy='LRU', hit_latency=1, miss_latency=100):
        """
        size: Total cache size in bytes
        block_size: Cache block (line) size in bytes
        associativity: Number of lines per set (N-way)
        write_policy: 'Write-Back' or 'Write-Through'
        replacement_policy: 'LRU', 'FIFO', 'Random'
        hit_latency: Simulated cycles for a hit
        miss_latency: Simulated cycles for a miss
        """
        self.size = size
        self.block_size = block_size
        self.associativity = associativity
        self.write_policy = write_policy
        self.replacement_policy = replacement_policy
        self.hit_latency = hit_latency
        self.miss_latency = miss_latency
        
        self.num_sets = size // (block_size * associativity)
        if self.num_sets <= 0 or (self.num_sets & (self.num_sets - 1)) != 0:
            raise ValueError("Number of sets must be a power of 2 > 0")
        if block_size <= 0 or (block_size & (block_size - 1)) != 0:
            raise ValueError("Block size must be a power of 2 > 0")
            
        self.offset_bits = int(math.log2(block_size))
        self.index_bits = int(math.log2(self.num_sets))
        self.tag_bits = 32 - self.index_bits - self.offset_bits
        
        self.sets = [CacheSet(associativity, replacement_policy) for _ in range(self.num_sets)]
        
        # Metrics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.write_hits = 0
        self.write_misses = 0
        
    def parse_address(self, addr):
        """Splits a 32-bit address into (tag, index, offset)."""
        addr = addr & 0xFFFFFFFF
        offset_mask = (1 << self.offset_bits) - 1
        index_mask = (1 << self.index_bits) - 1
        
        offset = addr & offset_mask
        index = (addr >> self.offset_bits) & index_mask
        tag = addr >> (self.offset_bits + self.index_bits)
        return tag, index, offset

    def build_address(self, tag, index):
        """Reconstructs the base 32-bit address of a cache block."""
        return (tag << (self.offset_bits + self.index_bits)) | (index << self.offset_bits)

    def read(self, addr):
        """
        Simulates a cache read.
        Returns a metadata dictionary containing status and eviction info.
        """
        tag, index, _ = self.parse_address(addr)
        target_set = self.sets[index]
        line = target_set.find_line(tag)
        
        metadata = {
            'status': 'Miss',
            'evicted': False,
            'evicted_address': None,
            'dirty_eviction': False,
            'latency': self.miss_latency
        }
        
        if line is not None:
            self.hits += 1
            metadata['status'] = 'Hit'
            metadata['latency'] = self.hit_latency
        else:
            self.misses += 1
            # Fetch from lower memory and insert
            evict_info = target_set.insert(tag, data=None, dirty=False)
            if evict_info is not None:
                self.evictions += 1
                metadata['evicted'] = True
                metadata['evicted_address'] = self.build_address(evict_info['tag'], index)
                metadata['dirty_eviction'] = evict_info['dirty']
                
        return metadata

    def write(self, addr):
        """
        Simulates a cache write.
        Returns a metadata dictionary containing status, eviction info, and write-through signals.
        """
        tag, index, _ = self.parse_address(addr)
        target_set = self.sets[index]
        line = target_set.find_line(tag)
        
        metadata = {
            'status': 'Miss',
            'evicted': False,
            'evicted_address': None,
            'dirty_eviction': False,
            'write_through_push': False,
            'latency': self.miss_latency
        }
        
        if line is not None:
            self.write_hits += 1
            metadata['status'] = 'Hit'
            metadata['latency'] = self.hit_latency
            if self.write_policy == 'Write-Back':
                line.dirty = True
            elif self.write_policy == 'Write-Through':
                metadata['write_through_push'] = True
        else:
            self.write_misses += 1
            # Write-Allocate policy: load on write miss
            is_dirty = (self.write_policy == 'Write-Back')
            evict_info = target_set.insert(tag, data=None, dirty=is_dirty)
            
            if self.write_policy == 'Write-Through':
                metadata['write_through_push'] = True
                
            if evict_info is not None:
                self.evictions += 1
                metadata['evicted'] = True
                metadata['evicted_address'] = self.build_address(evict_info['tag'], index)
                metadata['dirty_eviction'] = evict_info['dirty']
                
        return metadata
