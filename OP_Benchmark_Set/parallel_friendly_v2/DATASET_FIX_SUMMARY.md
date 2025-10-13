# Parallel Friendly V2 Dataset Fix - Summary

## Issue Identified

The `parallel_friendly_v2` benchmark dataset had an issue with the node structure:

- **Node 0 (START)**: Correctly positioned at (0, 0) with reward 0
- **Node 1 (END)**: **PROBLEM** - Was positioned close to START and sometimes had a non-zero reward
  - Should be positioned far from START (opposite side of the problem space)
  - Should have reward 0

### Example Before Fix
File: `sparse_25x25_d60_47.txt`
```
47	375
0.000	0.000	0           # Node 0: START (correct)
11.000	23.000	16          # Node 1: Was intermediate node with reward
...
```

### Example After Fix
File: `sparse_25x25_d60_47.txt`
```
47	375
0.000	0.000	0           # Node 0: START (correct)
24.000	24.000	0          # Node 1: END at far corner with reward 0
11.000	23.000	16          # Intermediate node
...
```

## What Was Fixed

### 1. Fixed All Existing Dataset Files (270 files)

Created and ran `fix_parallel_friendly_datasets.py` which:
- Read each problem file
- Found the node farthest from START (0, 0)
- Set that node as END (node 1) with reward 0
- Reordered nodes so START is node 0, END is node 1, and all others follow

**Results:**
- ✅ **270 files fixed successfully**
- ✅ **0 errors**
- All END nodes now properly positioned with distances ranging from 9.90 to 69.30 units from START

### 2. Updated Generation Script

Modified `generate_constrained_parallel_datasets.py` to ensure future datasets are created correctly from the start:

- **`generate_dense_grid()`**: Now creates END at opposite corner (grid_width-1, grid_height-1)
- **`generate_sparse_grid()`**: END node at opposite corner with reward 0
- **`generate_clustered_grid()`**: END node at farthest cluster node
- **`generate_corridors()`**: END node at farthest corridor endpoint
- **`generate_islands()`**: END node at farthest island node

All functions now ensure:
```python
nodes[0] = (0.0, 0.0, 0)      # START at origin
nodes[1] = (end_x, end_y, 0)  # END at far position with reward 0
# Remaining nodes are intermediate nodes with rewards
```

## Verification

All 270 files pass verification with:
- Node 0 has reward 0 (START)
- Node 1 has reward 0 (END)
- START-END distances are appropriate for each problem size

### Distance Ranges by Problem Type
- **Dense 15x15**: ~19.80 units
- **Dense 20x20**: ~26.87 units
- **Dense 25x25**: ~33.94 units
- **Dense 30x30**: ~41.01 units
- **Dense 35x35**: ~48.08 units
- **Extra Large 40x40**: ~55.15 units
- **Extra Large 45x45**: ~62.23 units
- **Extra Large 50x50**: ~69.30 units
- **Corridors**: 15.03 to 25.08 units
- **Clustered**: 9.90 to 31.11 units
- **Islands**: 13.43 to 16.76 units
- **Sparse grids**: Varies by density and size

## Impact

This fix ensures:
1. **Correct OP format**: All files now follow the standard Orienteering Problem convention
2. **Meaningful problems**: Solutions must traverse from one side to the other
3. **Better testing**: Algorithms must find paths across the entire problem space
4. **Consistency**: All benchmark files follow the same structure

## Files Modified

1. **`fix_parallel_friendly_datasets.py`** (new) - Script to fix existing datasets
2. **`generate_constrained_parallel_datasets.py`** (updated) - Updated generation logic
3. **All 270 .txt files** in `OP_Benchmark_Set/parallel_friendly_v2/` - Fixed node ordering

## Date
October 7, 2025
