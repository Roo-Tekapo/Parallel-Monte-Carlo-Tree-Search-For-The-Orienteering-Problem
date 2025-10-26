# Grid Problem File Format Template

This document explains the structure of orienteering problem files used in this benchmark set.

## File Format Overview

All problem files follow a consistent tab-separated or space-separated text format with the following structure:

```
<budget>	<num_problems>
<start_x>	<start_y>	<start_reward>
<end_x>	<end_y>	<end_reward>
<node1_x>	<node1_y>	<node1_reward>
<node2_x>	<node2_y>	<node2_reward>
...
<nodeN_x>	<nodeN_y>	<nodeN_reward>
```

## Line-by-Line Breakdown

### Line 1: Header
```
<budget>	<num_problems>
```
- **budget**: Maximum travel distance allowed (integer or float)
- **num_problems**: Number of problem instances in the file (typically 1)
- **Example**: `20	1` means budget of 20 units, 1 problem instance

### Line 2: Start Node
```
<start_x>	<start_y>	<start_reward>
```
- **start_x**: X-coordinate of starting position (float)
- **start_y**: Y-coordinate of starting position (float)
- **start_reward**: Reward at start node (typically 0)
- **Example**: `4.000	0.000	0` - start at position (4, 0) with 0 reward

### Line 3: End Node
```
<end_x>	<end_y>	<end_reward>
```
- **end_x**: X-coordinate of ending position (float)
- **end_y**: Y-coordinate of ending position (float)
- **end_reward**: Reward at end node (typically 0)
- **Example**: `5.000	9.000	0` - end at position (5, 9) with 0 reward

### Lines 4+: Intermediate Nodes
```
<node_x>	<node_y>	<node_reward>
```
- **node_x**: X-coordinate of node (float)
- **node_y**: Y-coordinate of node (float)
- **node_reward**: Reward value at this node (integer or float, typically > 0)
- **Example**: `3.000	4.000	15` - node at (3, 4) with reward 15

## Complete Example

```
20	1
4.000	0.000	0
5.000	9.000	0
0.000	0.000	20
0.000	1.000	17
0.000	2.000	14
1.000	0.000	17
1.000	1.000	15
2.000	0.000	14
```

**Interpretation:**
- Budget: 20 distance units
- Start: Position (4, 0) with 0 reward
- End: Position (5, 9) with 0 reward
- 6 intermediate nodes with varying rewards (14-20)

## Distance Calculation

The distance between any two nodes is calculated using **Euclidean distance**:

$$d = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$

## Problem Objective

Find a path from the start node to the end node that:
1. Stays within the budget constraint (total distance ≤ budget)
2. Maximizes the total reward collected from visited nodes
3. Visits each intermediate node at most once

## File Naming Conventions

### Grid Pattern Files
Format: `grid_<pattern>_b<budget>.txt`

Examples:
- `grid_center_b20.txt` - Center pattern with budget 20
- `grid_corners_b30.txt` - Corners pattern with budget 30
- `grid_diagonal_b40.txt` - Diagonal pattern with budget 40

**Common Patterns:**
- `center` - High rewards concentrated in center
- `corners` - High rewards at grid corners
- `edges` - High rewards along grid edges
- `diagonal` - High rewards along diagonals
- `ring` - Ring-shaped reward distribution
- `clustered` - Rewards clustered at specific locations
- `checkerboard` - Alternating high/low pattern
- `gradient` - Gradual reward increase (horizontal/vertical)
- `quadrants` - Different rewards per grid quadrant
- `random` - Random reward distribution

### Standard Benchmark Files
Format: `set_<nodes>_<instance>_<budget>.txt`

Examples:
- `set_64_1_20.txt` - 64 nodes, instance 1, budget 20
- `set_100_1_30.txt` - 100 nodes, instance 1, budget 30

## Important Notes

1. **Coordinates**: Can be any real numbers (positive, negative, or zero)
2. **Rewards**: Typically non-negative integers, but can be floats
3. **Start/End Rewards**: Usually 0, as they are mandatory nodes
4. **Whitespace**: Fields separated by tabs or spaces
5. **Node Order**: Order of intermediate nodes doesn't matter algorithmically
6. **Grid Patterns**: For grid problems, coordinates typically form a regular grid (e.g., 10×10)

## Creating Your Own Problem Files

To create a custom problem file:

1. Determine your grid size and layout
2. Set an appropriate budget based on grid dimensions
3. Define start and end positions
4. Assign reward values to create desired patterns
5. Follow the format template exactly
6. Save as `.txt` file with descriptive name

## Validation Checklist

✓ First line contains budget and number of problems  
✓ Second line defines start node (typically 0 reward)  
✓ Third line defines end node (typically 0 reward)  
✓ All subsequent lines define intermediate nodes  
✓ Each line has exactly 3 values: x, y, reward  
✓ Coordinates are consistent with intended grid structure  
✓ Budget is feasible (allows reaching end from start)  

## Example Problem Types

### Small Grid (10×10)
- Budgets: 20-40
- Nodes: ~90-100 (excluding start/end)
- Typical reward range: 1-20

### Medium Grid (20×20)  
- Budgets: 40-80
- Nodes: ~400 (excluding start/end)
- Typical reward range: 5-50

### Large Benchmark Sets
- Budgets: 15-80
- Nodes: 64, 100, 1000+
- Reward patterns: Problem-dependent
