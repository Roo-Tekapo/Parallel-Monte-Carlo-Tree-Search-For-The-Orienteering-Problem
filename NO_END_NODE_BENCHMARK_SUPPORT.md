# No-End-Node Benchmark Support

**Date:** November 4, 2025  
**Feature:** Added parameter to benchmark runner for testing algorithms without end node requirement

## Overview

Added `--no-end-node` flag to the benchmark runner that allows testing all algorithms (including OR-Tools) with the "no-end" orienteering variant where paths are not required to return to the END node.

## Changes Made

### 1. Benchmark Runner (`results_gen/run_benchmark.py`)

#### New Command-Line Parameter
```bash
--no-end-node    # Allow paths to end at any node (not required to return to END node)
```

#### Updated Method Signatures
All algorithm runner methods now accept `require_end_node: bool = True` parameter:
- `run_uct_single()`
- `run_simple_wu()`
- `run_vl()`
- `run_tree()`
- `run_ortools()`
- `run_benchmark()`

#### Environment Variable Control
Each MCTS algorithm sets its environment variable based on `require_end_node`:
```python
# Traditional mode (require_end_node=True)
os.environ['UCT_USE_NO_END'] = 'false'

# No-end mode (require_end_node=False)
os.environ['UCT_USE_NO_END'] = 'true'
```

Applies to:
- `UCT_USE_NO_END`
- `SIMPLE_WU_USE_NO_END`
- `VL_USE_NO_END`
- `TREE_USE_NO_END`

#### OR-Tools Integration
OR-Tools now dynamically loads the correct orienteering problem class:
```python
if require_end_node:
    from orienteering.orienteering import OrienteeringProblem
else:
    from orienteering.orienteering_no_end import OrienteeringProblemNoEnd as OrienteeringProblem
```

### 2. OR-Tools Solver (`OR_Tool/or_tools_solver.py`)

#### No-End Variant Detection
OR-Tools solver now detects whether the problem is a no-end variant:
```python
is_no_end = hasattr(self.problem, 'is_no_end_variant') and self.problem.is_no_end_variant
```

#### Routing Manager Configuration
- **Traditional mode:** Start at node 0, end at node 1
- **No-end mode:** Start at node 0, end at node 0 (open tour)

```python
if is_no_end:
    # No-end variant: can end anywhere, use node 0 as dummy end
    self.manager = pywrapcp.RoutingIndexManager(
        self.num_nodes, 1, [0], [0]  # Start and end at same node
    )
else:
    # Traditional: must end at node 1
    self.manager = pywrapcp.RoutingIndexManager(
        self.num_nodes, 1, [0], [1]  # Start at 0, end at 1
    )
```

#### Validation Updates
Solution validation now adapts based on the variant:
- **Traditional:** Checks path ends at node 1
- **No-end:** Accepts any ending node

### 3. Problem Classes

#### Added `is_no_end_variant` Attribute

**`orienteering/orienteering_traditional.py`:**
```python
self.is_no_end_variant = False  # Requires end node
```

**`orienteering/orienteering_no_end.py`:**
```python
self.is_no_end_variant = True   # No end node required
```

This attribute allows solvers (especially OR-Tools) to detect which variant they're working with.

## Usage Examples

### Traditional Mode (Default - Requires END Node)
```bash
# Default behavior - paths must return to END node
python .\results_gen\run_benchmark.py -d grid_patterns -w 8 --runs 5
```

### No-End Mode (New Feature)
```bash
# Allow paths to end anywhere
python .\results_gen\run_benchmark.py -d grid_patterns -w 8 --runs 5 --no-end-node
```

### Comparing Both Modes
```bash
# Test traditional mode
python .\results_gen\run_benchmark.py -d grid_sample --algorithms all --output traditional.xlsx

# Test no-end mode
python .\results_gen\run_benchmark.py -d grid_sample --algorithms all --output no_end.xlsx --no-end-node
```

## Technical Details

### MCTS Algorithms
All MCTS algorithms (UCT, Simple_WU, VL, Tree) already supported no-end mode through their orienteering adapters. The environment variables control which variant is loaded:

```python
# In adapter files (e.g., VL/orienteering_adapter.py)
_USE_NO_END = os.environ.get('VL_USE_NO_END', 'false').lower() in ('true', '1', 'yes')

if _USE_NO_END:
    from orienteering.orienteering_no_end import (
        OrienteeringProblemNoEnd as OrienteeringProblem,
        OrienteeringStateNoEnd as OrienteeringState,
        # ...
    )
else:
    from orienteering.orienteering_traditional import (
        OrienteeringProblemTraditional as OrienteeringProblem,
        # ...
    )
```

### OR-Tools Adaptation
OR-Tools needed new logic to support no-end mode:

1. **Open Tour Formulation:** Use the same node as start/end depot to create an "open" tour
2. **Dynamic Validation:** Check path ending based on variant
3. **Node Penalty Adjustment:** Skip appropriate nodes when setting up disjunctions

### Result Validation
The benchmark runner now validates results based on the mode:

**Traditional Mode:**
```python
ends_at_end_node = (len(path) > 0 and path[-1] == 1)
```

**No-End Mode:**
```python
ends_at_end_node = (len(path) > 0)  # Valid if path exists
```

## Benefits

### 1. Comprehensive Testing
Can now benchmark all algorithms on both problem variants:
- Traditional orienteering (return to depot)
- Prize-collecting TSP variant (no return requirement)

### 2. Fair Comparison with OR-Tools
OR-Tools can now be tested on the same no-end variant as MCTS algorithms, enabling fair comparisons.

### 3. Research Flexibility
Researchers can easily switch between problem variants to study:
- Impact of end-node constraint on solution quality
- Algorithm behavior with vs. without forced completion
- Computational efficiency differences

### 4. Single Command
One benchmark runner handles both variants - no need for separate scripts.

## Output Differences

### Success Criteria
- **Traditional:** `success = (path ends at node 1)`
- **No-end:** `success = (path exists and is valid)`

### Metrics
Both modes track:
- Raw reward collected
- Path length
- Budget usage
- Completion status (interpreted differently per mode)

## Limitations

### WU-UCT
Note: WU-UCT was not updated with `require_end_node` parameter in this change. It can be added if needed following the same pattern as other algorithms.

### OR-Tools Open Tour
The OR-Tools implementation uses a workaround (same start/end depot) to simulate an open tour. This works but may not be the most efficient formulation for very large problems.

## Future Enhancements

1. **Add WU-UCT support** for require_end_node parameter
2. **Optimize OR-Tools** formulation for open tours
3. **Add result comparison tools** to analyze traditional vs. no-end performance
4. **Support mixed benchmarks** (some problems with end node, some without)

## Testing

To verify the feature works correctly:

```bash
# Test with a small dataset
python .\results_gen\run_benchmark.py -d grid_sample --algorithms uct vl tree --no-end-node --runs 3

# Compare with traditional mode
python .\results_gen\run_benchmark.py -d grid_sample --algorithms uct vl tree --runs 3
```

Expected: No-end mode should generally achieve higher rewards (no forced return to END node).
