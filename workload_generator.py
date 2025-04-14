import random
import numpy as np

class WorkloadGenerator:
    def __init__(self, memory_size_kb=1024, seed=None):
        """
        Initialize the workload generator
        
        Args:
            memory_size_kb: Size of simulated memory in KB
            seed: Random seed for reproducibility
        """
        self.memory_size = memory_size_kb * 1024  # Convert to bytes
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
    
    def generate_sequential(self, num_accesses, start_address=0, stride=4):
        """
        Generate sequential memory accesses
        
        Args:
            num_accesses: Number of memory accesses to generate
            start_address: Starting address
            stride: Bytes between each access
        
        Returns:
            List of memory addresses
        """
        addresses = []
        current = start_address
        for _ in range(num_accesses):
            addresses.append(current)
            current = (current + stride) % self.memory_size
        return addresses
    
    def generate_random(self, num_accesses):
        """
        Generate random memory accesses
        
        Args:
            num_accesses: Number of memory accesses to generate
        
        Returns:
            List of memory addresses
        """
        return [random.randrange(0, self.memory_size) for _ in range(num_accesses)]
    
    def generate_locality(self, num_accesses, num_regions=5, region_size_kb=4, locality_prob=0.9):
        """
        Generate memory accesses with spatial and temporal locality
        
        Args:
            num_accesses: Number of memory accesses to generate
            num_regions: Number of "hot" memory regions
            region_size_kb: Size of each region in KB
            locality_prob: Probability of accessing a hot region (vs random)
        
        Returns:
            List of memory addresses
        """
        region_size = region_size_kb * 1024
        
        # Create hot regions (randomly distributed throughout memory)
        region_starts = []
        for _ in range(num_regions):
            region_start = random.randrange(0, self.memory_size - region_size)
            region_starts.append(region_start)
        
        addresses = []
        for _ in range(num_accesses):
            if random.random() < locality_prob:
                # Access a hot region
                region_idx = random.randrange(0, num_regions)
                region_start = region_starts[region_idx]
                offset = random.randrange(0, region_size)
                addresses.append(region_start + offset)
            else:
                # Random access
                addresses.append(random.randrange(0, self.memory_size))
        
        return addresses
    
    def generate_matrix_traversal(self, matrix_size=1024, row_major=True):
        """
        Generate memory accesses for matrix traversal
        
        Args:
            matrix_size: Size of the square matrix (N x N)
            row_major: If True, traverse in row-major order, else column-major
        
        Returns:
            List of memory addresses
        """
        addresses = []
        element_size = 4  # Assume 4 bytes per element (e.g., float or int)
        base_address = 0
        
        if row_major:
            # Row-major traversal (i,j)
            for i in range(matrix_size):
                for j in range(matrix_size):
                    addr = base_address + (i * matrix_size + j) * element_size
                    addresses.append(addr)
        else:
            # Column-major traversal (j,i)
            for j in range(matrix_size):
                for i in range(matrix_size):
                    addr = base_address + (i * matrix_size + j) * element_size
                    addresses.append(addr)
        
        return addresses
    
    def generate_loop_nest(self, iterations=1000, stride=16, num_arrays=3):
        """
        Generate memory accesses for a typical loop nest accessing multiple arrays
        
        Args:
            iterations: Number of loop iterations
            stride: Access stride
            num_arrays: Number of arrays accessed
        
        Returns:
            List of memory addresses
        """
        addresses = []
        array_bases = [random.randrange(0, self.memory_size - iterations*stride) 
                       for _ in range(num_arrays)]
        
        for i in range(iterations):
            for array_base in array_bases:
                addr = array_base + i * stride
                addresses.append(addr)
        
        return addresses 