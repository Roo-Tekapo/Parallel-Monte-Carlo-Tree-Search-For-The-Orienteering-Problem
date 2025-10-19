# Orienteering Problem Variant Guide

This guide explains how to switch between Traditional and No-End orienteering variants in the UCT, Simple_WU, and VL implementations.

## Two Orienteering Variants

### Traditional Orienteering (`orienteering_traditional.py`)
- **Objective**: Find best path from START_NODE to END_NODE within budget
- **Terminal Condition**: Path reaches END_NODE OR no more moves possible
- **Use Case**: Classic orienteering problem with fixed start and end points

### No-End Orienteering (`orienteering_no_end.py`)
- **Objective**: Maximize reward collection within budget (no required end node)
- **Terminal Condition**: Budget exhausted OR all neighbors visited (dead-end)
- **Use Case**: Pure reward optimization without destination constraint

## How to Switch Variants

All three implementations (UCT, Simple_WU, VL) support the `--use-no-end` flag:

### UCT (Single-threaded and WU-UCT)

**Traditional Orienteering (default):**
```bash
python UCT/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --algorithm uct --max-iterations 10000
```

**No-End Orienteering:**
```bash
python UCT/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --algorithm uct --max-iterations 10000 --use-no-end
```

**WU-UCT with No-End:**
```bash
python UCT/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --algorithm wu-uct --max-iterations 10000 --use-no-end --simulation-workers 4 --expansion-workers 2
```

### Simple_WU

**Traditional Orienteering (default):**
```bash
python Simple_WU/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --num-workers 4 --max-iterations 10000
```

**No-End Orienteering:**
```bash
python Simple_WU/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --num-workers 4 --max-iterations 10000 --use-no-end
```

### VL (Virtual Loss)

**Traditional Orienteering (default):**
```bash
python VL/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --workers 4 --iterations 10000
```

**No-End Orienteering:**
```bash
python VL/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --workers 4 --iterations 10000 --use-no-end
```

## Implementation Details

### Adapter Pattern with Environment Variables

The implementation uses an **adapter pattern** with environment variables to switch between variants:

1. **Adapter Modules**: Each folder has an `orienteering_adapter.py` that reads an environment variable and imports the correct variant
   - `UCT/orienteering_adapter.py` - reads `UCT_USE_NO_END`
   - `Simple_WU/orienteering_adapter.py` - reads `SIMPLE_WU_USE_NO_END`
   - `VL/orienteering_adapter.py` - reads `VL_USE_NO_END`

2. **main.py Sets Environment Variable**: When you use `--use-no-end`, main.py sets the environment variable BEFORE importing other modules

3. **All Other Files Import from Adapter**: Worker files, coordinators, and nodes all import from their folder's adapter:
   ```python
   # Instead of:
   from orienteering.orienteering_traditional import OrienteeringProblem
   
   # They use:
   from UCT.orienteering_adapter import OrienteeringProblem
   ```

This approach:
- ✅ Works across all files in the folder
- ✅ No code duplication
- ✅ Clean API - same `OrienteeringProblem` interface
- ✅ Easy to switch via command-line flag
- ✅ Both variants use identical MCTS/UCT logic
- ✅ Environment variable controls all imports consistently

### API Compatibility

Both `orienteering_traditional.py` and `orienteering_no_end.py` provide:
- `OrienteeringProblem` class
- `OrienteeringState` class
- `START_NODE` and `END_NODE` constants
- Compatible methods: `load_problem()`, `get_distance()`, `get_neighbors()`, etc.

The MCTS/UCT implementations work with **either variant** without modification!

## Comparison Example

Run both variants on the same problem to compare:

```bash
# Traditional - requires reaching end node
python UCT/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --algorithm uct --max-iterations 10000 --verbose

# No-End - maximize reward without end constraint
python UCT/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --algorithm uct --max-iterations 10000 --use-no-end --verbose
```

## When to Use Each Variant

### Use Traditional Orienteering When:
- Problem has fixed start and end locations
- Must reach specific destination
- Comparing with benchmark datasets that require end nodes

### Use No-End Orienteering When:
- Goal is pure reward maximization
- No required destination
- Exploring "open-ended" path finding
- Testing budget utilization without destination constraint

## Technical Notes

1. **Reward Normalization**: Both variants support `normalize_rewards=True` for better UCT performance

2. **Max Edge Distance**: Grid-based problems use `max_edge_distance=1.42` (sqrt(2)) to create graph connectivity

3. **Terminal States**: 
   - Traditional: `is_terminal()` checks if END_NODE reached or no moves
   - No-End: `is_terminal()` checks if budget exhausted or dead-end

4. **Budget Usage**:
   - Traditional: Often uses less budget (stops at end node)
   - No-End: Typically uses more budget (explores until exhausted)

5. **Import Updates**: A helper script `update_imports.py` was used to convert all files to use the adapter pattern. If you add new files to UCT, Simple_WU, or VL, make sure to:
   ```python
   # Use the adapter import:
   from UCT.orienteering_adapter import OrienteeringProblem, OrienteeringState, END_NODE
   # NOT the direct import:
   # from orienteering.orienteering_traditional import OrienteeringProblem
   ```

## Quick Reference

| Feature | Traditional | No-End |
|---------|------------|---------|
| Flag | (none) | `--use-no-end` |
| End Node Required | Yes | No |
| Terminal Condition | Reach END_NODE | Budget exhausted |
| Typical Budget Usage | Partial | Full |
| Import Module | `orienteering_traditional` | `orienteering_no_end` |

---

**Need Help?** See:
- `orienteering/orienteering_traditional.py` - Traditional implementation
- `orienteering/orienteering_no_end.py` - No-End implementation  
- `NO_END_NODE_ORIENTEERING_GUIDE.md` - Detailed no-end guide
- `ORIENTEERING_USAGE_GUIDE.md` - General usage guide
