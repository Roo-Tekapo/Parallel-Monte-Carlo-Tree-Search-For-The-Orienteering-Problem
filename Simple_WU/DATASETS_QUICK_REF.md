# Quick Reference: Batch Runner Datasets

## Available Datasets

### 1. Parallel Friendly (default)
**Command:** `python run_parallel_friendly_batch.py` or `--dataset parallel_friendly`

**Test Files (6):**
- `clustered_c4_s5_sp8_32.txt` - Clustered reward patterns
- `corridors_n4_l20_w3_24.txt` - Corridor structures
- `dense_20x20_r10_28.txt` - Dense grids
- `islands_n6_s5_b30_28.txt` - Island structures
- `sparse_30x30_d50_44.txt` - Sparse grids
- `xlarge_40x40_r0_84.txt` - Extra large instances

### 2. Grid Patterns
**Command:** `python run_parallel_friendly_batch.py --dataset grid_patterns`

**Test Files (10):**
- `grid_corners_b30.txt` - High rewards at corners
- `grid_center_b30.txt` - High rewards in center
- `grid_edges_b30.txt` - High rewards on edges
- `grid_diagonal_b30.txt` - High rewards along diagonals
- `grid_grad_horiz_b30.txt` - Horizontal gradient
- `grid_quadrants_b30.txt` - Different rewards per quadrant
- `grid_checkerboard_b30.txt` - Checkerboard pattern
- `grid_ring_b30.txt` - Ring pattern around center
- `grid_clustered_b30.txt` - Clustered rewards
- `grid_random_b30.txt` - Random baseline

## Quick Commands

```bash
# Test parallel_friendly with defaults
python run_parallel_friendly_batch.py

# Test grid_patterns with defaults
python run_parallel_friendly_batch.py --dataset grid_patterns

# Quick test with 5000 iterations
python run_parallel_friendly_batch.py --dataset grid_patterns --max-iterations 5000

# Full test with 8 workers
python run_parallel_friendly_batch.py --dataset grid_patterns --num-workers 8 --verbose
```

## Output Location

All results are saved to the `Simple_WU/results/` directory:
- Batch runs: `results/batch_results_TIMESTAMP.txt`
- Individual runs: `results/simple-wu-uct_PROBLEM_ITERATIONS.txt`
