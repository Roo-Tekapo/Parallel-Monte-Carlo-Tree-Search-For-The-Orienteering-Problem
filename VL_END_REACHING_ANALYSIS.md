# Virtual Loss (VL) End-Reaching Analysis

## Issue Discovered

The VL implementation was not properly reaching the END node, similar to the issue found in WU-UCT.

## Root Cause Analysis

### Bug #1: Tree Expansion Past END_NODE (FIXED)
**Location:** `orienteering/orienteering_traditional.py` - `get_available_actions()`

**Problem:** 
When a state was already at END_NODE (terminal state), the `get_available_actions()` method was still returning available neighbors. This allowed the MCTS tree to expand PAST the end node, creating invalid paths like: `...76 -> 1 -> 55` (where node 1 is END_NODE).

**Root Cause:**
The method checked `if current != END_NODE` before adding END_NODE to actions, but then continued to iterate through all neighbors, adding unvisited ones even when `current == END_NODE`.

**Fix Applied:**
```python
def get_available_actions(self, traditional_mcts=True):
    actions = []
    current = self.path[-1]
    
    # If we're already at END_NODE, the path is complete - no more actions
    if current == END_NODE:
        return actions  # Return empty list immediately
    
    # ... rest of the method
```

**Verification:**
- Before fix: END_NODE had 5 available actions [55, 56, 65, 75, 76]
- After fix: END_NODE has 0 available actions ✓

### Bug #2: Insufficient Terminal Node Exploration (ONGOING)
**Problem:**
Even after fixing Bug #1, VL still doesn't reach END_NODE in its best solution:
- **Terminal nodes explored: 0.0%** (0 out of 11 nodes in tree at depth ≤10)
- Best path ends at node 21, not node 1 (END_NODE)
- Path cost: 29.80 / 30.00 (very close to budget limit)

**Symptoms:**
```
Best solution:
  Path: 0 -> 46 -> 47 -> ... -> 21
  Reaches END: NO ✗
  Raw score: 197
  Normalized reward: 9.850000
  Potential with end bonus: 10.000000
  Missing improvement: +1.5%
```

**Analysis:**
1. The root avg reward is 6.896, which includes the 30% penalty (9.85 * 0.7 = 6.895)
2. Simulations ARE being penalized correctly
3. But simulations never actually reach END_NODE at all
4. The +0.15 bonus (1.5% improvement) may be too small to overcome the cost of traveling to END_NODE

**Potential Causes:**
1. **Budget constraints**: Getting to END_NODE requires backtracking or expensive paths
2. **Reward structure imbalance**: The 0.15 bonus might be too small
3. **Incomplete path penalty not strong enough**: 30% penalty vs 15% bonus (2:1 ratio)
4. **Exploration insufficient**: Standard exploration constant (√2) may not be enough

## Comparison with WU-UCT

This is the SAME issue that WU-UCT had, suggesting this is a problem with:
1. The shared orienteering problem definition (now fixed)
2. The reward structure (bonuses/penalties)
3. The simulation strategy

## Current Reward Structure

### For Normalized Rewards (reward_scale = 1/20):
- **Complete path (reaches END_NODE)**: `reward += 0.15` (15% bonus)
- **Incomplete path (>2 nodes)**: `reward *= 0.7` (30% penalty)

### For Unnormalized Rewards:
- **Complete path**: `reward += 100`
- **Incomplete path (>2 nodes)**: `reward *= 0.1` (90% penalty)

## Testing Summary

### Test 1: END_NODE Bug Confirmation
- Created state at END_NODE
- Checked available actions
- **Result**: FOUND BUG - 5 actions available when should be 0

### Test 2: After Fix Verification
- Re-ran same test
- **Result**: FIXED - 0 actions available ✓

### Test 3: VL MCTS Diagnostic (After Fix)
- 10,000 iterations with 4 workers
- **Result**: Still doesn't reach END_NODE
- **Terminal exploration**: 0.0%
- **Best path**: Stops at node 21

## Recommendations

### Option 1: Increase End Bonus
```python
# Current
if self.problem.normalize_rewards:
    reward += 0.15  # 15% bonus
    
# Proposed
if self.problem.normalize_rewards:
    reward += 0.50  # 50% bonus (or higher)
```

### Option 2: Strengthen Incomplete Penalty
```python
# Current
if self.problem.normalize_rewards:
    reward *= 0.7  # 30% penalty
    
# Proposed
if self.problem.normalize_rewards:
    reward *= 0.5  # 50% penalty (or stronger)
```

### Option 3: Hybrid Approach
- Increase end bonus to 0.30 (30%)
- Increase incomplete penalty to *0.5 (50% reduction)
- This creates a 3:1 ratio between bonus and penalty

### Option 4: Exploration Boost
- Increase exploration constant from √2 (1.414) to 2.0 or higher
- This encourages more diverse path exploration

## Next Steps

1. ✅ Fix get_available_actions() bug (DONE)
2. Test different bonus/penalty combinations
3. Compare with WU-UCT behavior after same fix
4. Potentially create a version with configurable bonuses for tuning
5. Run comprehensive benchmarks

## Files Modified

- `orienteering/orienteering_traditional.py` - Fixed get_available_actions()
- `test_end_simple.py` - Bug verification test
- `diagnostic_vl.py` - VL end-reaching diagnostic script

## Files Created

- `test_end_node_bug.py` - Initial bug detection test
- `VL_END_REACHING_ANALYSIS.md` - This document
