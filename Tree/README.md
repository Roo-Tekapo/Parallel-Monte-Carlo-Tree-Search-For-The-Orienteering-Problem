# Tree-Parallel MCTS

Basic parallel MCTS implementation using one shared tree structure with **standard UCT formula** (no WU-UCT modifications).

## Overview

This implementation provides tree parallelism for MCTS where multiple workers share a single search tree. Unlike the WU-UCT implementation in `Simple_WU/`, this uses the **standard UCT formula** without virtual loss or the "Watch the Unobservable" mechanism.

### Key Differences from WU-UCT

| Feature | Tree-Parallel MCTS (this) | WU-UCT (Simple_WU) |
|---------|---------------------------|---------------------|
| **UCT Formula** | Standard: `V + c*sqrt(ln(N_parent)/N_child)` | Modified: Uses pending simulations (O) |
| **Virtual Loss** | ❌ Not implemented | ✅ Tracks pending simulations |
| **Coordination** | Basic locking only | Advanced via virtual loss |
| **Formula** | `V_i + c * sqrt(ln(N_p) / N_i)` | `V_c + β * sqrt(2*ln(N_n+O_n)/(N_c+O_c))` |

## Architecture

### Components

1. **`TreeParallelNode`** (`tree_parallel_node.py`)
   - Node class for the shared tree
   - Uses standard MCTS statistics (visits, total_reward)
   - Thread-safe operations via per-node locks
   - Standard UCT selection formula

2. **`TreeParallelWorker`** (`tree_parallel_worker.py`)
   - Worker thread performing MCTS iterations
   - Each iteration: Selection → Expansion → Simulation → Backpropagation
   - Uses standard UCT for tree traversal
   - No virtual loss mechanism

3. **`TreeParallelMCTS`** (`tree_parallel_coordinator.py`)
   - Coordinator managing multiple workers
   - Initializes shared tree
   - Distributes iterations across workers
   - Extracts best solution

## Usage

### Basic Example

```python
from orienteering.orienteering_traditional import OrienteeringProblem
from Tree.tree_parallel_coordinator import TreeParallelMCTS
import math

# Load problem
nodes, budget = OrienteeringProblem.load_problem("path/to/problem.txt")
problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)

# Create coordinator with 4 workers
coordinator = TreeParallelMCTS(
    problem=problem,
    num_workers=4,
    exploration_constant=math.sqrt(2)
)

# Run the algorithm
best_solution = coordinator.run(
    max_iterations=10000,
    verbose=True
)

print(f"Best path: {best_solution.path}")
print(f"Reward: {best_solution.reward_so_far}")
print(f"Cost: {best_solution.cost_so_far}")
```

### Parameters

#### TreeParallelMCTS Constructor

- `problem`: OrienteeringProblem instance
- `num_workers`: Number of parallel workers (default: 4)
- `exploration_constant`: UCT exploration parameter c (default: √2)

#### run() Method

- `max_iterations`: Total number of MCTS iterations to perform
- `max_time`: Optional time limit in seconds
- `verbose`: Whether to print progress information (default: False)

## Standard UCT Formula

This implementation uses the **standard UCT formula**:

```
UCT(node) = V_i + c * sqrt(ln(N_parent) / N_i)
```

Where:
- `V_i` = Average reward of node i = `Q_i / N_i`
- `N_parent` = Visit count of parent node
- `N_i` = Visit count of node i
- `c` = Exploration constant (typically √2)

**Key Point**: This formula does NOT account for pending simulations (unlike WU-UCT).

## Thread Safety

Thread safety is achieved through:

1. **Per-node locks**: Each node has its own `_node_lock` for atomic updates
2. **Global tree lock**: Used during expansion to prevent race conditions
3. **No virtual loss**: Simpler synchronization compared to WU-UCT

### Lock Usage

- **Selection**: Read-only traversal, minimal locking
- **Expansion**: Requires tree lock to add new nodes
- **Backpropagation**: Updates nodes with per-node locks

## Performance Characteristics

### Advantages

- ✅ Simple implementation
- ✅ Standard UCT behavior
- ✅ Easy to understand and modify
- ✅ Lower overhead than WU-UCT

### Limitations

- ⚠️ Workers may select same promising paths
- ⚠️ No coordination via virtual loss
- ⚠️ May have more lock contention than WU-UCT
- ⚠️ Efficiency drops with many workers

## Comparison with Other Approaches

### vs Single-Threaded MCTS

- **Pro**: Faster convergence with multiple cores
- **Con**: Lock overhead reduces per-iteration speed

### vs WU-UCT (Simple_WU)

- **Pro**: Simpler, more faithful to standard MCTS
- **Con**: Less efficient parallelization
- **Con**: No virtual loss coordination

### vs Root Parallelism

- **Pro**: Shares tree structure (better information sharing)
- **Con**: More complex synchronization

## Testing

Run the test script:

```bash
python -m Tree.test_tree_parallel
```

The test includes:
1. Small problem verification
2. Scalability test with different worker counts
3. Comparison with single-threaded MCTS

## File Structure

```
Tree/
├── __init__.py                      # Package initialization
├── orienteering_adapter.py          # Flexible orienteering variant selector
├── tree_parallel_node.py            # Node with standard UCT
├── tree_parallel_worker.py          # Worker thread implementation
├── tree_parallel_coordinator.py     # Main coordinator
├── test_tree_parallel.py            # Test and examples
├── README.md                        # This file
└── IMPLEMENTATION_SUMMARY.md        # Implementation details
```

## Implementation Notes

### Design Decisions

1. **Standard UCT**: Uses classical UCT formula without modifications
2. **Simplified Structure**: Inspired by Simple_WU but removes WU-UCT complexity
3. **Thread Safety**: Uses locks for correctness, not optimized for throughput
4. **Expansion Lock**: Global lock prevents duplicate expansions

### When to Use This Implementation

Use Tree-Parallel MCTS when:
- You want standard MCTS behavior with parallelism
- You need simple, understandable code
- You have 2-4 cores (limited scalability)
- Lock contention is acceptable

Consider WU-UCT instead when:
- You need high scalability (8+ workers)
- You want state-of-the-art parallel MCTS
- Lock contention is a concern

## Future Improvements

Possible enhancements:
1. Lock-free traversal techniques
2. Lazy tree expansion
3. Progressive widening
4. RAVE (Rapid Action Value Estimation)
5. Parallel simulation with leaf parallelism

## References

- Original MCTS: Kocsis & Szepesvári (2006)
- UCT algorithm: Kocsis & Szepesvári (2006)
- Parallel MCTS survey: Chaslot et al. (2008)

For WU-UCT implementation, see `Simple_WU/` directory.
