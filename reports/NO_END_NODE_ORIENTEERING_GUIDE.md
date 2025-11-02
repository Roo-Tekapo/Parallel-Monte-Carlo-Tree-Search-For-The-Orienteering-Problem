# No-End-Node Orienteering Problem Variant

## Overview

The `orienteering_no_end.py` module provides an orienteering problem variant that **removes the requirement for an end node**. Instead of finding a path from START to END, the goal is to **maximize reward collection within the budget constraint**.

## Key Differences from Traditional Orienteering

| Feature | Traditional Orienteering | No-End-Node Variant |
|---------|------------------------|---------------------|
| **Goal** | Path from START to END | Maximize reward within budget |
| **End Node** | Required (node 1) | Not required (removed) |
| **Start Node** | Fixed (node 0) | Fixed (node 0) |
| **Terminal Condition** | Reaches END node | Budget exhausted OR all neighbors visited |
| **Path Length** | Variable, ends at END | Variable, ends when no moves available |

## When to Use This Variant

Use the no-end variant when:
- You want to maximize reward/score collection without a fixed destination
- The problem is about resource gathering or coverage within a budget
- You don't have a specific endpoint constraint
- You want simpler terminal conditions (no path planning to END required)

## Installation

No additional installation needed. The module is already part of the `orienteering` package:

```python
from orienteering.orienteering_no_end import (
    OrienteeringProblemNoEnd,
    OrienteeringStateNoEnd
)
```

## Basic Usage

### 1. Load and Create Problem

```python
from orienteering.orienteering_no_end import OrienteeringProblemNoEnd

# Load from file
nodes, budget = OrienteeringProblemNoEnd.load_problem("path/to/problem.txt")

# Create problem instance
problem = OrienteeringProblemNoEnd(
    nodes=nodes,
    budget=budget,
    max_edge_distance=1.42,      # Optional: limit edge distances
    normalize_rewards=True        # Optional: normalize rewards for UCT
)
```

### 2. Create Initial State

```python
from orienteering.orienteering_no_end import OrienteeringStateNoEnd

# Create initial state (starts at START_NODE = 0)
state = OrienteeringStateNoEnd(problem)

print(f"Path: {state.path}")                    # [0]
print(f"Reward: {state.reward_so_far}")         # Initial reward
print(f"Cost: {state.cost_so_far}")             # 0.0
print(f"Terminal: {state.is_terminal()}")       # False
```

### 3. Explore Actions

```python
# Get available actions (neighboring nodes within budget)
actions = state.get_available_actions()
print(f"Available nodes to visit: {actions}")

# Apply an action to create a new state
if actions:
    new_state = state.apply_action(actions[0])
    print(f"New path: {new_state.path}")
    print(f"New reward: {new_state.reward_so_far}")
    print(f"New cost: {new_state.cost_so_far}")
```

### 4. Terminal Conditions

A state is terminal when `get_available_actions()` returns an empty list, which occurs when:

1. **Budget exhausted**: No neighboring nodes can be reached within remaining budget
2. **Dead-end reached**: All reachable neighbors have already been visited

```python
# Check if terminal
if state.is_terminal():
    print("State is terminal - no more moves available")
```

## Using with MCTS Implementations

The no-end variant is compatible with all MCTS implementations in this repository.

### MCTS Base (Single-threaded Traditional MCTS)

```python
from MCTS.mcts_base import MCTSSingleThread
from MCTS.mcts_node import MCTSNode
from orienteering.orienteering_no_end import OrienteeringProblemNoEnd, OrienteeringStateNoEnd

# Load problem
problem = OrienteeringProblemNoEnd(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
initial_state = OrienteeringStateNoEnd(problem)

# Create and run MCTS
mcts = MCTSSingleThread(
    problem, 
    iterations=1000,
    soft_end_bias=False  # Disable end bias (no END_NODE)
)
mcts.root = MCTSNode(initial_state)
mcts.search()

# Get best solution
best_node = mcts.best_child(mcts.root)
solution = best_node.state
print(f"Best path: {solution.path}")
print(f"Reward: {solution.reward_so_far}")
```

### UCT Single Thread

```python
from UCT.uct_single_thread import UCTSingleThread
from orienteering.orienteering_no_end import OrienteeringProblemNoEnd, OrienteeringStateNoEnd

# Load problem
problem = OrienteeringProblemNoEnd(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)
initial_state = OrienteeringStateNoEnd(problem)

# Create and run UCT
uct = UCTSingleThread(
    problem,
    exploration_constant=1.414,
    iterations=1000
)

solution = uct.search(initial_state, verbose=True)
print(f"Best path: {solution.path}")
print(f"Reward: {solution.reward_so_far}")
```

### Virtual Loss (VL) - Parallel MCTS

```python
from VL.vl_coordinator import VirtualLossMCTS
from orienteering.orienteering_no_end import OrienteeringProblemNoEnd

# Load problem
problem = OrienteeringProblemNoEnd(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)

# Create and run VL coordinator
coordinator = VirtualLossMCTS(
    problem=problem,
    num_workers=4,
    exploration_constant=1.414
)

solution = coordinator.search(iterations=1000, verbose=True)
print(f"Best path: {solution.path}")
print(f"Reward: {solution.reward_so_far}")
```

### Simple WU-UCT - Parallel MCTS

```python
from Simple_WU.simple_wu_coordinator import SimpleWUUCT
from orienteering.orienteering_no_end import OrienteeringProblemNoEnd

# Load problem
problem = OrienteeringProblemNoEnd(nodes, budget, max_edge_distance=1.42, normalize_rewards=True)

# Create and run Simple WU coordinator
coordinator = SimpleWUUCT(
    problem=problem,
    num_workers=4,
    exploration_constant=1.414
)

solution = coordinator.search(iterations=1000, verbose=True)
print(f"Best path: {solution.path}")
print(f"Reward: {solution.reward_so_far}")
```

## Complete Example

See `example_no_end_orienteering.py` for a complete demonstration that:
- Loads a problem instance
- Runs all four MCTS implementations
- Compares results
- Shows best solution

Run it with:
```bash
python example_no_end_orienteering.py
```

## API Reference

### OrienteeringProblemNoEnd

```python
OrienteeringProblemNoEnd(
    nodes: List[Node],
    budget: float,
    max_edge_distance: Optional[float] = 1.42,
    normalize_rewards: bool = False
)
```

**Parameters:**
- `nodes`: List of `Node` namedtuples with `(id, x, y, score)`
- `budget`: Maximum distance/cost budget
- `max_edge_distance`: Maximum allowed edge distance (None = fully connected graph)
- `normalize_rewards`: Whether to normalize rewards for better UCT performance

**Methods:**
- `load_problem(filename)`: Static method to load problem from file
- `get_distance(a, b)`: Get Euclidean distance between nodes
- `get_neighbors(node_id)`: Get list of neighboring nodes
- `get_normalized_score(node_id)`: Get (possibly normalized) score for node

### OrienteeringStateNoEnd

```python
OrienteeringStateNoEnd(
    problem: OrienteeringProblemNoEnd,
    path: Optional[List[int]] = None,
    cost_so_far: float = 0.0,
    reward_so_far: Optional[float] = None
)
```

**Attributes:**
- `problem`: Reference to the problem instance
- `path`: List of visited node indices
- `visited`: Set of visited nodes
- `cost_so_far`: Total distance travelled
- `reward_so_far`: Total reward collected

**Methods:**
- `is_terminal()`: Check if state is terminal (no available actions)
- `get_available_actions()`: Get list of available node indices to visit
- `apply_action(node_index)`: Create new state after visiting node
- `copy()`: Create a copy of this state
- `get_reward()`: Get total reward
- `get_cost()`: Get total cost
- `get_path()`: Get the path

## Problem File Format

The same format as traditional orienteering:

```
<budget> <num_nodes>
<x1> <y1> <score1>
<x2> <y2> <score2>
...
```

**Note:** Node 0 is automatically treated as the START node. Node 1 (traditionally END) is treated as a regular visitable node in this variant.

## Advantages

1. **Simpler terminal conditions**: No need to plan path to specific end node
2. **More flexible**: Can collect rewards anywhere in the graph
3. **Better for certain problems**: Resource gathering, coverage, exploration
4. **Compatible**: Works with all existing MCTS implementations
5. **Performance**: Slightly faster (no END node reachability checks)

## Limitations

1. **No guaranteed path structure**: Solutions don't have fixed start/end points
2. **Budget management**: May use less budget than available (terminates at dead-ends)
3. **Comparison**: Solutions less directly comparable to traditional orienteering

## Testing

Test the implementation:

```bash
# Run built-in demo
python orienteering/orienteering_no_end.py

# Run comprehensive example with all MCTS variants
python example_no_end_orienteering.py
```

## Migration from Traditional Orienteering

To switch from traditional orienteering to no-end variant:

```python
# Before (traditional)
from orienteering.orienteering_traditional import OrienteeringProblem, OrienteeringState

# After (no-end)
from orienteering.orienteering_no_end import OrienteeringProblemNoEnd, OrienteeringStateNoEnd

# Or use convenience aliases
from orienteering.orienteering_no_end import OrienteeringProblem, OrienteeringState
```

The API is identical, so most code will work without changes. Main differences:
1. No END_NODE in paths
2. `is_terminal()` returns True when no actions available (not when at END)
3. Solutions may have different path lengths

## Troubleshooting

### Issue: States terminate too early

**Solution:** Increase budget or decrease `max_edge_distance` to allow more connectivity

### Issue: Poor reward collection

**Solution:** 
- Enable reward normalization: `normalize_rewards=True`
- Tune exploration constant in MCTS
- Increase number of iterations

### Issue: All neighbors visited quickly

**Solution:** Check graph connectivity with `max_edge_distance`. Consider increasing it or setting to `None` for fully connected graph.

## Performance Tips

1. **Enable reward normalization** for better UCT performance
2. **Cache distances** (done automatically)
3. **Use appropriate `max_edge_distance`** to balance connectivity and realism
4. **Parallel implementations** (VL, Simple WU) scale well with more workers
5. **More iterations** generally lead to better solutions

## See Also

- `orienteering_traditional.py` - Traditional orienteering with END node
- `orienteering.py` - Original implementation with BFS reachability
- `example_no_end_orienteering.py` - Complete usage example
- `MCTS/` - MCTS implementations
- `UCT/` - UCT implementations
- `VL/` - Virtual Loss parallel MCTS
- `Simple_WU/` - Wu-UCT parallel MCTS
