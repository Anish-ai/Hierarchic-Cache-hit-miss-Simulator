# Cache Hierarchy Simulator

An interactive simulation tool for analyzing L1, L2, and L3 cache behavior with different workloads. This project provides a visual platform to explore how different cache configurations and memory access patterns affect hit/miss rates.

## Features

- Complete simulation of L1, L2, and L3 cache hierarchy
- Configurable cache parameters:
  - Cache size
  - Block/line size
  - Associativity
  - Replacement policy (LRU, FIFO, Random)
- Multiple workload patterns:
  - Sequential access
  - Random access
  - Spatial/temporal locality
  - Matrix traversals (row-major vs. column-major)
  - Loop nest simulation
- Real-time visualization of hit/miss rates
- Detailed statistics reporting

## Requirements

- Python 3.6+
- PyQt5
- matplotlib
- numpy

## Installation

1. Install the required dependencies:

```bash
pip install PyQt5 matplotlib numpy
```

2. Clone or download the project files

## Usage

Run the application with:

```bash
python cache_analyzer.py
```

### Step-by-Step Guide

1. **Configure Cache Parameters**
   - Set the sizes, block sizes, associativity, and replacement policies for each cache level (L1, L2, L3)
   - Typical configurations might be:
     - L1: 32KB, 64B blocks, 8-way associative
     - L2: 256KB, 64B blocks, 8-way associative
     - L3: 8MB, 64B blocks, 16-way associative

2. **Select Workload Type**
   - Choose from different memory access patterns
   - Set the number of memory accesses to simulate
   - Click "Generate Workload" to create the access pattern

3. **Run Simulation**
   - Click "Run Simulation" to process the workload through the cache hierarchy
   - The progress bar indicates simulation progress

4. **Analyze Results**
   - View hit/miss rates in the charts
   - Examine detailed statistics in the table
   - Compare different configurations and workloads to understand cache behavior

## Workload Types

- **Sequential**: Memory accesses with a consistent stride (spatial locality)
- **Random**: Random memory accesses (no locality)
- **Locality**: Memory accesses with both spatial and temporal locality
- **Matrix (Row-Major)**: Row-by-row matrix traversal
- **Matrix (Column-Major)**: Column-by-column matrix traversal
- **Loop Nest**: Simulates nested loops accessing multiple arrays

## Learning Objectives

This simulator helps understand:

- How cache size, block size, and associativity affect hit rates
- Impact of different replacement policies
- Importance of spatial and temporal locality
- How different access patterns interact with the cache hierarchy
- Trade-offs in cache design and optimization

## Project Structure

- `cache_simulator.py`: Core cache simulation logic
- `workload_generator.py`: Different memory access pattern generators
- `cache_analyzer.py`: Main application with GUI and visualization
- `README.md`: Documentation and instructions

## Extending the Project

You can extend this project by:
1. Adding more workload patterns
2. Implementing additional replacement policies
3. Adding support for inclusive/exclusive cache hierarchies
4. Implementing cache coherence protocols for multi-core simulation
5. Adding memory latency simulation 