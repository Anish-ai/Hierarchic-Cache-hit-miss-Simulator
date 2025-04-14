import math
from collections import OrderedDict

class Cache:
    def __init__(self, size_kb, block_size_bytes, associativity, replacement_policy='LRU', name="Cache"):
        """Initialize cache parameters

        Args:
            size_kb: Cache size in KB
            block_size_bytes: Block/line size in bytes
            associativity: Number of ways (1 for direct-mapped)
            replacement_policy: 'LRU', 'FIFO', or 'Random'
            name: Cache name (L1, L2, etc.)
        """
        self.name = name
        self.size = size_kb * 1024  # Convert to bytes
        self.block_size = block_size_bytes
        self.associativity = associativity
        self.replacement_policy = replacement_policy
        
        # Calculate cache organization
        self.num_blocks = self.size // self.block_size
        self.num_sets = self.num_blocks // self.associativity
        self.offset_bits = int(math.log2(self.block_size))
        self.index_bits = int(math.log2(self.num_sets))
        self.tag_bits = 32 - self.index_bits - self.offset_bits  # Assuming 32-bit addresses
        
        # Initialize cache sets
        self.sets = [OrderedDict() for _ in range(self.num_sets)]
        
        # Statistics
        self.accesses = 0
        self.hits = 0
        self.misses = 0
    
    def get_cache_address_parts(self, address):
        """Split address into tag, index, and offset"""
        offset = address & ((1 << self.offset_bits) - 1)
        index = (address >> self.offset_bits) & ((1 << self.index_bits) - 1)
        tag = address >> (self.offset_bits + self.index_bits)
        return tag, index, offset
    
    def access(self, address):
        """
        Access the cache at the given address
        Returns True for hit, False for miss
        """
        self.accesses += 1
        tag, index, _ = self.get_cache_address_parts(address)
        cache_set = self.sets[index]
        
        # Check if the tag is in the set (cache hit)
        if tag in cache_set:
            self.hits += 1
            # Update access order for LRU
            if self.replacement_policy == 'LRU':
                cache_set.move_to_end(tag)
            return True
        
        # Cache miss
        self.misses += 1
        
        # Add the new block to the cache
        if len(cache_set) >= self.associativity:
            # Remove the least recently used entry
            cache_set.popitem(last=False)
        
        # Add the new entry
        cache_set[tag] = True
        if self.replacement_policy == 'LRU':
            cache_set.move_to_end(tag)
        
        return False
    
    def get_hit_rate(self):
        """Return the hit rate as a percentage"""
        if self.accesses == 0:
            return 0
        return (self.hits / self.accesses) * 100
    
    def get_miss_rate(self):
        """Return the miss rate as a percentage"""
        if self.accesses == 0:
            return 0
        return (self.misses / self.accesses) * 100
    
    def reset_stats(self):
        """Reset hit/miss statistics"""
        self.accesses = 0
        self.hits = 0
        self.misses = 0

class CacheHierarchy:
    def __init__(self, l1_params, l2_params, l3_params):
        """
        Initialize a three-level cache hierarchy
        
        Args:
            l1_params: Dict with L1 cache parameters
            l2_params: Dict with L2 cache parameters
            l3_params: Dict with L3 cache parameters
        """
        self.l1_cache = Cache(**l1_params, name="L1")
        self.l2_cache = Cache(**l2_params, name="L2")
        self.l3_cache = Cache(**l3_params, name="L3")
        
        # Statistics
        self.memory_accesses = 0
    
    def access(self, address):
        """
        Access the cache hierarchy with the given address
        Returns tuple of (l1_hit, l2_hit, l3_hit)
        """
        self.memory_accesses += 1
        
        # Try L1 cache first
        if self.l1_cache.access(address):
            return True, False, False
        
        # L1 miss, try L2
        if self.l2_cache.access(address):
            return False, True, False
        
        # L2 miss, try L3
        if self.l3_cache.access(address):
            return False, False, True
        
        # L3 miss, access memory
        return False, False, False
    
    def get_stats(self):
        """Return statistics for the entire cache hierarchy"""
        return {
            "L1": {
                "hit_rate": self.l1_cache.get_hit_rate(),
                "miss_rate": self.l1_cache.get_miss_rate(),
                "accesses": self.l1_cache.accesses,
                "hits": self.l1_cache.hits,
                "misses": self.l1_cache.misses
            },
            "L2": {
                "hit_rate": self.l2_cache.get_hit_rate(),
                "miss_rate": self.l2_cache.get_miss_rate(),
                "accesses": self.l2_cache.accesses,
                "hits": self.l2_cache.hits,
                "misses": self.l2_cache.misses
            },
            "L3": {
                "hit_rate": self.l3_cache.get_hit_rate(),
                "miss_rate": self.l3_cache.get_miss_rate(),
                "accesses": self.l3_cache.accesses,
                "hits": self.l3_cache.hits,
                "misses": self.l3_cache.misses
            },
            "total_accesses": self.memory_accesses
        }
    
    def reset_stats(self):
        """Reset statistics for all cache levels"""
        self.memory_accesses = 0
        self.l1_cache.reset_stats()
        self.l2_cache.reset_stats()
        self.l3_cache.reset_stats() 