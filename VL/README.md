# Virtual Loss (VL) Parallel MCTS

This directory implements the **Virtual Loss** approach for parallel Monte Carlo Tree Search, applied to the Orienteering Problem.

## Overview

Virtual Loss (VL) is a simple yet effective mechanism for coordinating parallel MCTS workers. Unlike WU-UCT which modifies the UCT formula with pending simulation counts, VL uses **fixed penalty values** that are temporarily applied to nodes being explored.

## Key Concept

When a thread selects a path for exploration:
1. Apply a **fixed virtual loss** (penalty) to all nodes in the path
2. Other threads see reduced node values and avoid these nodes
3. After simulation completes, remove the virtual loss
4. Add the real simulation result

This is simpler than WU-UCT because:
- No modification to UCT formula needed
- Uses standard UCT selection
- Fixed penalty is intuitive to tune
- Direct impact on node attractiveness

## Virtual Loss vs WU-UCT

| Aspect | Virtual Loss (VL) | WU-UCT |
|--------|------------------|---------|
| **Mechanism** | Fixed penalty value | Pending simulation counter |
| **UCT Formula** | Standard (unchanged) | Modified to include O_n, O_c |
| **Node Tracking** | Virtual loss per thread | Total pending count |
| **Parameter** | Loss value (e.g., 1.0) | Implicit in formula |
| **Complexity** | Simpler | More complex |
| **Tuning** | Direct (penalty magnitude) | Indirect (affects UCT) |

### Mathematical Difference

**Virtual Loss:**
```
UCT = (Q - VL) / N + c * sqrt(ln(N_parent) / N)
```
- VL directly reduces Q (quality/reward)
- Standard UCT formula otherwise

**WU-UCT:**
```
UCT = Q / N + c * sqrt(ln(N_parent + O_parent) / (N + O))
```
- O (pending simulations) affects both exploration terms
- Formula modification needed

## Implementation Structure

```
VL/
├── __init__.py              # Package initialization
├── vl_node.py              # VLNode class with virtual loss tracking
├── vl_worker.py            # Worker thread with VL coordination
├── vl_coordinator.py       # VirtualLossMCTS coordinator
├── main.py                 # Command-line interface
└── README.md               # This file
```

## Usage

### Basic Usage

```bash
python VL/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt
```

### Advanced Options

```bash
python VL/main.py \
    --problem-file path/to/problem.txt \
    --workers 4 \
    --iterations 10000 \
    --vl-value 1.5 \
    --exploration 1.414 \
    --verbose
```

### Parameters

#### Required
- `--problem-file`, `-p`: Path to orienteering problem file

#### Algorithm Configuration
- `--workers`, `-w`: Number of parallel workers (default: 4)
- `--iterations`, `-i`: Total iterations (default: 10000)
- `--time-limit`, `-t`: Time limit in seconds (overrides iterations)

#### Virtual Loss Parameters
- `--vl-value`, `-v`: Virtual loss penalty value (default: 1.0)
  - 0.5-1.0: Light coordination (more exploitation)
  - 1.0-2.0: Standard coordination (balanced)
  - 2.0-3.0: Strong coordination (more exploration diversity)
  
- `--exploration`, `-e`: UCT exploration constant (default: √2 ≈ 1.414)

#### Problem Settings
- `--normalize`: Enable reward normalization (default)
- `--no-normalize`: Disable reward normalization

#### Output
- `--verbose`: Detailed progress and statistics
- `--quiet`, `-q`: Minimal output

## Python API

### Example 1: Basic Usage

```python
from orienteering.orienteering_traditional import OrienteeringProblem
from VL.vl_coordinator import VirtualLossMCTS

# Load problem
problem = OrienteeringProblem("problem.txt", normalize_rewards=True)

# Initialize VL-MCTS
vl_mcts = VirtualLossMCTS(
    problem=problem,
    num_workers=4,
    virtual_loss_value=1.0
)

# Run search
solution = vl_mcts.run(
    max_iterations=10000,
    verbose=True
)

print(f"Best path: {solution.path}")
print(f"Reward: {solution.reward_so_far}")
```

### Example 2: Parameter Tuning

```python
# More aggressive thread separation
vl_mcts = VirtualLossMCTS(
    problem=problem,
    num_workers=8,
    virtual_loss_value=2.0,      # Higher penalty
    exploration_constant=1.0      # Less exploration
)

solution = vl_mcts.run(max_iterations=50000)
```

### Example 3: Time-Limited Search

```python
# Run for fixed time period
solution = vl_mcts.run(
    max_iterations=1000000,  # Large number
    max_time=60.0,           # But stop after 60 seconds
    verbose=True
)
```

## Virtual Loss Value Guidelines

The `virtual_loss_value` parameter controls how strongly threads avoid each other:

### Low Values (0.5 - 1.0)
- **Effect**: Light coordination
- **Behavior**: Threads may select similar paths
- **Best for**: Exploitation-heavy problems, small search spaces
- **Collision rate**: Higher (10-30%)

### Medium Values (1.0 - 2.0)
- **Effect**: Balanced coordination
- **Behavior**: Good separation with some overlap
- **Best for**: General problems, balanced exploration/exploitation
- **Collision rate**: Moderate (5-15%)

### High Values (2.0 - 3.0+)
- **Effect**: Strong coordination
- **Behavior**: Threads strongly avoid each other
- **Best for**: Large search spaces, exploration-heavy problems
- **Collision rate**: Low (1-5%)

## Performance Metrics

The algorithm tracks several metrics:

1. **Collision Rate**: How often threads select paths with existing virtual loss
   - Lower is better (indicates good thread separation)
   - Target: < 10% for most problems

2. **Iterations/Second**: Overall throughput
   - Higher is better
   - Should scale with number of workers

3. **Tree Statistics**: 
   - Total nodes created
   - Maximum depth reached
   - Root node visits

## Understanding Output

### Verbose Output Example

```
Virtual Loss MCTS Statistics
============================================================

Overall Performance:
  Total Time: 5.23s
  Total Iterations: 10000
  Total Simulations: 10000
  Iterations/sec: 1912.35

Root Node:
  Visits: 9876
  Total Reward: 4532.15
  Avg Reward: 0.4589
  Children: 15

Virtual Loss Coordination:
  VL Value: 1.0
  Total Collisions: 523
  Avg Collision Rate: 5.23%
    (Lower is better - indicates good thread separation)

Per-Worker Performance:
  Worker   Iters    Sims     Avg Sim(ms)  Collisions   Coll Rate
  ----------------------------------------------------------------------
  0        2500     2500     0.452        131          5.24%
  1        2500     2500     0.448        127          5.08%
  2        2500     2500     0.455        134          5.36%
  3        2500     2500     0.450        131          5.24%

Best Solution Found:
  Path: [0, 5, 12, 18, 25, 30, 1]
  Reward: 2.3456
  Cost: 29.87 / 30.00
  Path Length: 7 nodes
```

## Comparison with Other Approaches

### vs Sequential MCTS
- **Advantage**: Near-linear speedup with multiple cores
- **Trade-off**: Slightly more memory overhead

### vs Root Parallelization
- **Advantage**: Better tree quality, shared knowledge
- **Trade-off**: More complex coordination

### vs WU-UCT
- **Advantage**: Simpler implementation, easier tuning
- **Trade-off**: May have slightly different convergence behavior

## Tips for Best Results

1. **Start with default values**: vl_value=1.0 works well for most problems

2. **Adjust based on collision rate**:
   - High collisions (>15%)? Increase vl_value
   - Low collisions (<3%)? Decrease vl_value

3. **Scale workers with problem size**:
   - Small problems (< 50 nodes): 2-4 workers
   - Medium problems (50-200 nodes): 4-8 workers
   - Large problems (> 200 nodes): 8-16 workers

4. **Use reward normalization**: Almost always beneficial

5. **Monitor collision rate**: It's the key indicator of coordination quality

## Technical Details

### Thread Safety

- Each node has its own lock (`_vl_lock`)
- Virtual loss operations are atomic
- Updates don't interfere with selection

### Memory Usage

- Similar to standard MCTS
- Extra: Dictionary of virtual losses per node (small overhead)
- Scales linearly with tree size

### Computational Overhead

- Virtual loss application: O(path_length)
- Virtual loss removal: O(path_length)
- Overhead per iteration: < 1% typically

## References

The Virtual Loss approach is commonly used in parallel MCTS implementations, particularly in computer Go programs. While less theoretically grounded than WU-UCT, it's proven effective in practice.

Key papers discussing Virtual Loss:
- Chaslot et al. "Parallel Monte-Carlo Tree Search" (2008)
- Enzenberger & Müller "A Lock-Free Multithreaded Monte-Carlo Tree Search Algorithm" (2010)

## Troubleshooting

### High collision rates
- Increase `--vl-value`
- Reduce number of workers
- Check if problem is too small for parallelization

### Low collision rates but poor performance
- Decrease `--vl-value` (threads too separated)
- Adjust exploration constant
- Try more iterations

### Memory issues
- Reduce number of workers
- Reduce iteration count
- Use time limit instead

## License

Same license as the parent project.
