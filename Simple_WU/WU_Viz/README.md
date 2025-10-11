# WU-UCT Visualization Tools

This directory contains visualization tools specifically designed for the Simple WU-UCT implementation, showing how the parallel algorithm develops the shared search tree.

## Files

### `wu_uct_tree_viz.py`
Basic tree visualization adapted from the MCTS visualization tools. Shows:
- **Shared tree structure** as it develops across parallel workers
- **Node states** with WU-UCT specific information (visits + pending simulations)
- **Visual indicators** for different node types (root, expanded, leaf, pending)
- **Interactive controls** for exploring the tree at different depths

**Key Features:**
- Node colors indicate state (red=root, orange=pending simulations, blue=expanded, green=leaf)
- Node sizes reflect total activity (visits + pending simulations)
- Real-time statistics showing best path and algorithm progress

### `wu_uct_parallel_viz.py`
Enhanced visualization showing detailed parallel worker activity. Features:
- **Multi-panel layout** with tree view, worker statistics, and algorithm info
- **Worker activity tracking** showing current worker states and positions
- **Path visualization** with colored lines showing each worker's current exploration
- **Real-time worker statistics** panel showing status of each parallel thread
- **Algorithm information** panel explaining WU-UCT concepts

**Key Features:**
- Each worker has a unique color for path tracking
- Dashed colored lines show current worker exploration paths
- Worker statistics panel shows real-time status (selecting, expanding, simulating, etc.)
- Enhanced legend and information displays

### `wu_uct_grid_viz.py`
Comprehensive grid-based visualization showing the orienteering problem and WU-UCT algorithm in action. Features:
- **Problem Grid Display** with all nodes, connections, and scoring information
- **Real-time Best Path** highlighting with golden path and directional arrows
- **Multi-panel Layout** with grid, statistics, worker status, and algorithm info
- **Node Activity Indicators** showing which nodes are being actively explored
- **Live Algorithm Statistics** including iterations/sec, tree size, and progress metrics
- **Worker Status Monitoring** showing each parallel worker's current state and progress

**Key Features:**
- Interactive grid showing the spatial orienteering problem layout
- Real-time visualization of the best path found so far
- **Parallel worker path tracking** - See each worker's active exploration path in real-time with unique colors
- Color-coded nodes based on score values using viridis colormap
- Live statistics panels showing algorithm performance metrics
- Visual distinction between start nodes (green squares) and end nodes (red squares)
- Golden path highlighting with directional arrows for the best solution
- Dashed colored lines showing current worker exploration paths (toggle with 'P' key)

### `example_usage.py`
Example script showing how to use both visualization tools with different problem instances and configurations.

## Usage

### Basic Tree Visualization
```bash
cd Simple_WU/WU_Viz
python3 wu_uct_tree_viz.py
```

### Parallel Worker Visualization
```bash
cd Simple_WU/WU_Viz
python3 wu_uct_parallel_viz.py
```

### Grid Visualization (NEW!)
```bash
cd Simple_WU/WU_Viz
python3 wu_uct_grid_viz.py
```

### Interactive Example Menu
```bash
cd Simple_WU/WU_Viz
python3 example_usage.py
```

## Controls

All visualizations support interactive controls:

### Grid Visualization (`wu_uct_grid_viz.py`)
- **P** - Toggle worker path display on/off

### Tree Visualizations
- **SPACE** - Pause/Resume the algorithm simulation
- **UP/DOWN** - Increase/Decrease tree depth display
- **N** - Toggle node labels on/off
- **P** - Toggle worker path display (parallel visualization only)

## WU-UCT Specific Features

These visualizations are specifically designed to show WU-UCT algorithm concepts:

### Watch the Unobservable Mechanism
- **Orange nodes** indicate nodes with pending simulations (unobserved samples)
- **Node sizes** reflect both completed visits (N) and pending simulations (O)
- Shows how the algorithm prevents over-exploration of promising nodes

### Parallel Worker Coordination
- **Colored paths** show how different workers explore different parts of the tree
- **Worker statistics** show current activity of each parallel thread
- **Shared tree** visualization shows how all workers contribute to the same structure

### UCT Formula Enhancement
The visualization helps understand the modified UCT formula used in WU-UCT:
```
a_n = arg max { V_c + β * sqrt(2*log(N_n + O_n) / (N_c + O_c)) }
```
Where:
- N = actual completed visits
- O = pending simulations (unobserved samples)
- Both numerator and denominator include pending work

## Configuration

Both visualizers can be configured with:
- **Problem file path** - Any orienteering problem instance
- **Number of workers** - Parallel worker count (affects visualization complexity)
- **Iterations** - Total algorithm iterations to simulate
- **Max depth** - Initial tree depth limit for display
- **Max nodes** - Maximum nodes to show (prevents overcrowding)

## Dependencies

- `matplotlib` - For plotting and animation
- `numpy` - For numerical operations
- `threading` - For worker activity simulation
- Parent Simple_WU modules - For WU-UCT implementation access

## Notes

- The current implementation includes simulated worker activity for demonstration purposes
- In a production version, the visualizer would interface directly with actual running worker threads
- The visualization is optimized for educational purposes to understand parallel MCTS algorithms
- Performance may vary with very large trees or high worker counts