# 4.3 Implementation Details

This section provides comprehensive details on the implementation of parallel MCTS algorithms for the Orienteering Problem, covering programming environment, architecture, data structures, and algorithm-specific optimizations.

---

## 4.3.1 Programming Environment and Dependencies

### Language and Version
- **Programming Language**: Python 3.x (3.8+)
- **Reason for Choice**: Rich scientific computing ecosystem, excellent threading support, rapid prototyping capabilities

### Key Dependencies
```python
# Core Libraries
import math           # Mathematical operations (sqrt, log, hypot)
import random         # Stochastic simulation and action selection
import threading      # Parallel worker management
import multiprocessing # Process-based parallelism (where needed)
from queue import Queue  # Thread-safe work queues for WU-UCT
from collections import namedtuple, deque  # Efficient data structures

# Optional (for benchmarking and visualization)
import pandas         # Results export to Excel
import matplotlib     # Search tree visualization
```

### Development Environment
- **IDE**: Visual Studio Code with Python extensions
- **Version Control**: Git (GitHub repository)
- **Operating Systems Tested**: Windows, Linux, macOS

---

## 4.3.2 Project Structure Overview

The codebase is organized into modular components, each handling specific aspects of the algorithms:

```
Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem/
│
├── orienteering/                    # Problem domain representation
│   ├── orienteering.py             # Core problem classes
│   ├── orienteering_optimized.py   # Performance optimizations
│   └── orienteering_traditional.py # Traditional OP variant
│
├── MCTS/                            # Base MCTS implementation
│   ├── mcts_base.py                # Single-threaded MCTS
│   ├── mcts_node.py                # Node data structure
│   └── mcts_backtrack.py           # Backpropagation logic
│
├── Tree/                            # Tree Parallelization
│   ├── tree_parallel_coordinator.py # Coordinator (shared tree)
│   ├── tree_parallel_worker.py      # Worker threads
│   ├── tree_parallel_node.py        # Thread-safe node
│   └── orienteering_adapter.py      # Problem adapter
│
├── VL/                              # Virtual Loss Parallelization
│   ├── vl_coordinator.py           # VL coordinator
│   ├── vl_worker.py                # VL worker threads
│   ├── vl_node.py                  # VL node with virtual loss
│   └── orienteering_adapter.py     # Problem adapter
│
├── WU_UCT/                          # WU-UCT Parallelization
│   ├── wu_uct_coordinator.py       # WU-UCT coordinator
│   ├── expansion_worker.py         # Expansion workers
│   ├── simulation_worker.py        # Simulation workers
│   ├── wu_uct_node.py              # WU-UCT node
│   └── orienteering_adapter.py     # Problem adapter
│
├── OP_Benchmark_Set/                # Test problem instances
│   ├── set_64_1/                   # 64-node problems
│   ├── set_100_1/                  # 100-node problems
│   ├── grid_sample/                # Grid-based problems
│   └── parallel_friendly_v2/       # Large-scale problems
│
├── results_gen/                     # Benchmarking framework
│   ├── run_benchmark.py            # Main benchmark runner
│   ├── analyze_results.py          # Statistical analysis
│   └── outputs/                    # Results storage
│
└── testing_solution/                # Validation tools
    ├── validate_solution.py        # Path validator
    └── solve_optimal.py            # Optimal solver (small instances)
```

---

## 4.3.3 Core Components

### 4.3.3.1 Orienteering Problem (OP) Module

The `orienteering/` module defines the problem domain and state representation.

#### Problem Definition
```python
class OrienteeringProblem:
    """
    Represents an Orienteering Problem instance.
    
    Attributes:
        nodes: List of Node(id, x, y, score)
        budget: Maximum travel distance allowed
        max_edge_distance: Optional constraint on edge connectivity
        normalize_rewards: Whether to normalize scores for UCT
    """
    def __init__(self, nodes, budget, max_edge_distance=None, normalize_rewards=False):
        self.nodes = nodes
        self.budget = budget
        self.max_edge_distance = max_edge_distance
        
        # Performance optimization: cache distances
        self._distance_cache = {}
        
        # Precompute neighbor graph if distance constraint exists
        if max_edge_distance is not None:
            self._build_neighbors()
            self._precompute_end_reachability()
```

**Key Optimizations**:
1. **Distance Caching**: Euclidean distances computed once and stored
2. **Neighbor Precomputation**: Graph connectivity computed upfront
3. **End Reachability**: BFS-based reachability analysis for pruning

#### State Representation
```python
class OrienteeringState:
    """
    Represents a state in the OP search space.
    
    Attributes:
        path: Sequence of visited node IDs [START, ..., END]
        visited: Set of visited nodes (O(1) lookup)
        cost_so_far: Total distance traveled
        reward_so_far: Total score collected
    """
    def __init__(self, problem, path=[START_NODE], cost_so_far=0.0, reward_so_far=None):
        self.problem = problem
        self.path = path
        self.visited = set(path)
        self.cost_so_far = cost_so_far
        self.reward_so_far = reward_so_far or problem.get_normalized_score(START_NODE)
        
        # Reachability cache for pruning (major speedup)
        self._reachability_cache = {}
```

**Pseudocode for Action Generation**:
```
FUNCTION get_available_actions(state):
    actions ← empty list
    current ← last node in state.path
    neighbors ← get_neighbors(current)  // Respects max_edge_distance
    
    // Always consider END node if reachable
    IF END_NODE in neighbors AND END_NODE not visited:
        cost_to_end ← distance(current, END_NODE)
        IF state.cost_so_far + cost_to_end ≤ budget:
            actions.append(END_NODE)
    
    // Consider other unvisited neighbors
    FOR each neighbor in neighbors:
        IF neighbor visited OR neighbor = START_NODE:
            CONTINUE
        
        cost_to_neighbor ← distance(current, neighbor)
        new_cost ← state.cost_so_far + cost_to_neighbor
        
        // Conservative: ensure END is still reachable
        IF can_reach_end_from(neighbor, new_cost):
            actions.append(neighbor)
    
    RETURN actions
```

#### Data File Format
Problem instances follow the Tsiligirides format:
```
Tmax P
x1 y1 score1
x2 y2 score2
...
xn yn scoren
```
- Line 1: `Tmax` (budget), `P` (number of paths, always 1)
- Line 2+: Node coordinates and scores
- Node 0: START, Node 1: END
- Distance metric: Euclidean

**Loading Example**:
```python
@staticmethod
def load_problem(filename):
    with open(filename, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # Parse header
    budget, _ = lines[0].split()
    budget = float(budget)
    
    # Parse nodes
    nodes = []
    for idx, line in enumerate(lines[1:]):
        x, y, score = line.split()
        nodes.append(Node(idx, float(x), float(y), int(score)))
    
    return nodes, budget
```

---

### 4.3.3.2 MCTS Base Module

The `MCTS/` module implements single-threaded MCTS serving as the foundation for parallel variants.

#### Node Structure
```python
class MCTSNode:
    """
    Node in MCTS search tree.
    
    Attributes:
        state: OrienteeringState at this node
        parent: Parent node (None for root)
        children: List of child nodes
        visits: Number of times node visited (N)
        total_reward: Cumulative reward from simulations (Q)
        untried_actions: Actions not yet expanded
    """
    def __init__(self, state, parent=None):
        self.state = state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.total_reward = 0.0
        
        # Shuffle untried actions for randomization
        self.untried_actions = list(state.get_available_actions())
        random.shuffle(self.untried_actions)
```

#### UCT Selection Formula
```python
def uct_best_child(self, c_param=math.sqrt(2)):
    """
    Select child with highest UCT value.
    
    UCT = Q_i/N_i + c * sqrt(ln(N_parent) / N_i)
          ^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
          Exploitation    Exploration
    """
    # Prefer unvisited children first
    unvisited = [c for c in self.children if c.visits == 0]
    if unvisited:
        return random.choice(unvisited)
    
    # Compute UCT scores
    ln_parent = math.log(max(1, self.visits))
    best_score = float("-inf")
    best_child = None
    
    for child in self.children:
        exploit = child.total_reward / child.visits
        explore = c_param * math.sqrt(ln_parent / child.visits)
        uct_score = exploit + explore
        
        if uct_score > best_score:
            best_score = uct_score
            best_child = child
    
    return best_child
```

#### MCTS Algorithm (Single-Threaded)
```
ALGORITHM: MCTS_SingleThread(problem, iterations)
INPUT: problem (OrienteeringProblem), iterations (int)
OUTPUT: best_state (OrienteeringState)

1. root ← MCTSNode(initial_state)

2. FOR i = 1 TO iterations:
   
   a) SELECTION:
      node ← root
      WHILE node is not terminal AND node.is_fully_expanded():
          node ← node.uct_best_child()
   
   b) EXPANSION:
      IF node.untried_actions is not empty:
          action ← pop random untried action
          new_state ← node.state.apply_action(action)
          node ← new child node with new_state
   
   c) SIMULATION:
      current ← node.state.copy()
      WHILE current is not terminal:
          actions ← current.get_available_actions()
          IF actions is empty: BREAK
          action ← random choice from actions
          current ← current.apply_action(action)
      reward ← current.get_reward()
   
   d) BACKPROPAGATION:
      WHILE node is not None:
          node.visits ← node.visits + 1
          node.total_reward ← node.total_reward + reward
          node ← node.parent

3. RETURN state from best descendant of root
```

**Key Implementation Features**:
- **Dead-end Detection**: Nodes with no available actions marked to avoid wasteful exploration
- **Soft End Bias**: Optional biasing toward END node as budget depletes
- **Reward Normalization**: Scales rewards to [0, 1] range for stable UCT

---

### 4.3.3.3 Tree Parallel Module

The `Tree/` module implements shared-tree parallelization with standard UCT.

#### Architecture
```
┌─────────────────────────────────────────┐
│      Tree Parallel Coordinator          │
│  - Shared search tree (root)            │
│  - Global tree lock                     │
│  - Worker management                    │
└──────┬──────┬──────┬──────┬─────────────┘
       │      │      │      │
   ┌───▼──┐ ┌─▼───┐ ┌▼────┐ ┌▼────┐
   │Worker│ │Worker│ │Worker│ │Worker│
   │  0   │ │  1   │ │  2  │ │  3  │
   └──────┘ └──────┘ └─────┘ └─────┘
   All workers share same tree structure
```

#### Thread-Safe Node
```python
class TreeParallelNode:
    """Node with thread-safe operations."""
    
    def __init__(self, state, parent=None):
        self.state = state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.total_reward = 0.0
        self.untried_actions = list(state.get_available_actions())
        
        # Thread safety
        self._node_lock = threading.Lock()
    
    def uct_select_child(self, exploration_constant):
        """Thread-safe child selection."""
        with self._node_lock:
            # Read visits/rewards safely
            parent_visits = self.visits
        
        # Compute UCT for each child
        best_child = None
        best_score = float("-inf")
        
        for child in self.children:
            with child._node_lock:
                if child.visits == 0:
                    return child  # Prefer unvisited
                
                exploit = child.total_reward / child.visits
                explore = exploration_constant * math.sqrt(
                    math.log(parent_visits) / child.visits
                )
                uct_score = exploit + explore
            
            if uct_score > best_score:
                best_score = uct_score
                best_child = child
        
        return best_child
    
    def update_statistics(self, reward):
        """Thread-safe backpropagation."""
        with self._node_lock:
            self.visits += 1
            self.total_reward += reward
```

#### Worker Implementation
```
ALGORITHM: TreeParallelWorker(root, iterations_per_worker)
INPUT: root (shared TreeParallelNode), iterations_per_worker (int)

FOR i = 1 TO iterations_per_worker:
    
    1) SELECTION (shared tree):
       node ← root
       WHILE node not terminal AND node.is_fully_expanded():
           node ← node.uct_select_child()  // Thread-safe
    
    2) EXPANSION (with lock):
       ACQUIRE tree_lock:
           IF node.untried_actions not empty:
               action ← pop untried action
               child ← create new child
               node.children.append(child)
               node ← child
       RELEASE tree_lock
    
    3) SIMULATION (local, no locks):
       reward ← simulate_from(node.state)
    
    4) BACKPROPAGATION (thread-safe):
       WHILE node is not None:
           node.update_statistics(reward)  // Uses node lock
           node ← node.parent
```

**Threading Details**:
- **Locks**: Fine-grained per-node locks minimize contention
- **Expansion Lock**: Optional global lock during node creation
- **Lock-Free Simulation**: Rollouts performed on local state copies

---

### 4.3.3.4 Virtual Loss (VL) Module

The `VL/` module implements Virtual Loss coordination mechanism.

#### VL-Enhanced Node
```python
class VLNode:
    """Node with Virtual Loss mechanism."""
    
    def __init__(self, state, parent=None):
        self.state = state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.total_reward = 0.0
        self.untried_actions = list(state.get_available_actions())
        
        # Virtual Loss tracking
        self.virtual_losses = 0  // Number of active VLs
        
        self._node_lock = threading.Lock()
    
    def apply_virtual_loss(self):
        """Apply temporary penalty when worker enters node."""
        with self._node_lock:
            self.virtual_losses += 1
    
    def revert_virtual_loss(self):
        """Remove penalty when worker completes."""
        with self._node_lock:
            self.virtual_losses -= 1
```

#### Modified UCT with Virtual Loss
```python
def vl_uct_select_child(self, exploration_constant, virtual_loss_value):
    """
    UCT selection with Virtual Loss penalty.
    
    VL-UCT = (Q_i - VL * λ) / N_i + c * sqrt(ln(N_parent) / N_i)
             ^^^^^^^^^^^^^^^^^^
             Reward with penalty
    
    Where:
    - VL = number of active virtual losses on child
    - λ = virtual loss penalty value (auto-scaled)
    """
    with self._node_lock:
        parent_visits = self.visits
    
    best_child = None
    best_score = float("-inf")
    
    for child in self.children:
        with child._node_lock:
            if child.visits == 0:
                return child
            
            # Apply virtual loss penalty to reward
            penalized_reward = (child.total_reward - 
                              child.virtual_losses * virtual_loss_value)
            
            exploit = penalized_reward / child.visits
            explore = exploration_constant * math.sqrt(
                math.log(parent_visits) / child.visits
            )
            vl_uct_score = exploit + explore
        
        if vl_uct_score > best_score:
            best_score = vl_uct_score
            best_child = child
    
    return best_child
```

#### VL Worker Algorithm
```
ALGORITHM: VL_Worker(root, iterations, vl_value)

FOR i = 1 TO iterations:
    
    1) SELECTION with Virtual Loss:
       path ← []  // Track path for VL application
       node ← root
       
       WHILE node not terminal AND node.is_fully_expanded():
           node.apply_virtual_loss()  // Discourage others
           path.append(node)
           node ← node.vl_uct_select_child(c, vl_value)
       
       node.apply_virtual_loss()
       path.append(node)
    
    2) EXPANSION:
       IF node.untried_actions not empty:
           // Expansion with lock as in Tree parallel
    
    3) SIMULATION:
       reward ← simulate_from(node.state)
    
    4) BACKPROPAGATION + VL Reversion:
       FOR each node in path (reverse order):
           node.update_statistics(reward)
           node.revert_virtual_loss()  // Remove penalty
```

**Virtual Loss Configuration**:
```python
# Auto-scaling virtual loss value
avg_node_reward = mean([node.score for node in problem.nodes])
virtual_loss_value = avg_node_reward * 0.2  # 20% of average

# Larger VL → more aggressive worker separation
# Smaller VL → more exploitation of good paths
```

---

### 4.3.3.5 WU-UCT Module

The `WU_UCT/` module implements the full WU-UCT algorithm with specialized worker types.

#### Architecture
```
┌────────────────────────────────────────────┐
│       WU-UCT Coordinator                   │
│  - Shared search tree                      │
│  - Work queue (expansion → simulation)     │
│  - Worker management                       │
└─────┬──────────────────┬───────────────────┘
      │                  │
┌─────▼──────┐      ┌────▼─────────────────┐
│ Expansion  │      │   Simulation         │
│  Workers   │      │    Workers           │
│ (1-4)      │      │   (4-12)             │
│            │      │                      │
│ - Selection│      │ - Dequeue (node, c)  │
│ - Expansion│─────►│ - Simulate           │
│ - Enqueue  │ Queue│ - Backpropagate      │
└────────────┘      └──────────────────────┘
```

#### WU-UCT Node
```python
class WUUCTNode:
    """Node with WU-UCT pending simulations counter."""
    
    def __init__(self, state, parent=None):
        self.state = state
        self.parent = parent
        self.children = []
        self.visits = 0
        self.total_reward = 0.0
        self.untried_actions = list(state.get_available_actions())
        
        # WU-UCT specific: pending simulations
        self.pending_simulations = 0
        
        self._node_lock = threading.Lock()
    
    def increment_pending(self):
        """Increment pending count when simulation queued."""
        with self._node_lock:
            self.pending_simulations += 1
    
    def decrement_pending(self):
        """Decrement pending count after backpropagation."""
        with self._node_lock:
            self.pending_simulations -= 1
```

#### WU-UCT Formula
```python
def wu_uct_select_child(self, exploration_constant):
    """
    WU-UCT selection formula (Chen et al., 2018).
    
    WU-UCT = Q_i / (N_i + P_i) + c * sqrt(ln(N_parent) / (N_i + P_i))
                    ^^^^^^^^^^            ^^^^^^^^^^
                    Adjusted visit count for pending simulations
    
    Where:
    - Q_i = total reward
    - N_i = completed simulations
    - P_i = pending simulations (in queue or being processed)
    - c = exploration constant
    """
    with self._node_lock:
        parent_visits = self.visits
    
    best_child = None
    best_score = float("-inf")
    
    for child in self.children:
        with child._node_lock:
            # Effective visit count includes pending
            effective_visits = child.visits + child.pending_simulations
            
            if effective_visits == 0:
                return child  # Unvisited
            
            # WU-UCT formula
            exploit = child.total_reward / effective_visits
            explore = exploration_constant * math.sqrt(
                math.log(max(1, parent_visits)) / effective_visits
            )
            wu_uct_score = exploit + explore
        
        if wu_uct_score > best_score:
            best_score = wu_uct_score
            best_child = child
    
    return best_child
```

#### Expansion Worker
```
ALGORITHM: ExpansionWorker(root, work_queue, iterations)

FOR i = 1 TO iterations:
    
    1) SELECTION with WU-UCT:
       node ← root
       WHILE node not terminal AND node.is_fully_expanded():
           node ← node.wu_uct_select_child(c)
    
    2) EXPANSION:
       ACQUIRE expansion_lock:
           IF node.untried_actions not empty:
               action ← pop untried action
               child ← create new child
               node.children.append(child)
               node ← child
       RELEASE expansion_lock
    
    3) ENQUEUE FOR SIMULATION:
       node.increment_pending()
       work_item ← (node, exploration_constant)
       work_queue.put(work_item)
       
       // Expansion worker does NOT simulate
       // Simulation workers handle the rest
```

#### Simulation Worker
```
ALGORITHM: SimulationWorker(work_queue, stop_event)

WHILE not stop_event.is_set():
    
    1) DEQUEUE WORK:
       TRY:
           (node, c_param) ← work_queue.get(timeout=0.1)
       EXCEPT Empty:
           CONTINUE  // Check stop_event again
    
    2) SIMULATION:
       reward ← simulate_from(node.state)
    
    3) BACKPROPAGATION:
       current ← node
       WHILE current is not None:
           current.update_statistics(reward)
           current.decrement_pending()  // Release pending count
           current ← current.parent
    
    4) MARK WORK DONE:
       work_queue.task_done()
```

**Work Queue Design**:
- **Type**: `queue.Queue` (thread-safe, blocking)
- **Size**: Configurable (default: 1000 items)
- **Overflow Handling**: Expansion workers block when queue full
- **Graceful Shutdown**: `stop_event` signals workers to terminate

---

## 4.3.4 Data Handling and Results Management

### Benchmark Runner Architecture
```python
class BenchmarkRunner:
    """
    Orchestrates experiments across multiple:
    - Algorithms (UCT, Tree, VL, WU-UCT, OR-Tools)
    - Problem instances (datasets)
    - Parameter configurations
    """
    
    def run_experiment(self, algorithm, problem_file, config):
        """
        Run single experiment and collect metrics.
        
        Returns:
            {
                'algorithm': 'WU_UCT',
                'problem': 'grid_10x10_medium_30.txt',
                'dataset': 'grid_sample',
                'num_nodes': 102,
                'budget': 30.0,
                'iterations': 10000,
                'workers': 4,
                'elapsed_time': 5.23,
                'raw_reward': 450,
                'normalized_reward': 0.876,
                'path_length': 12,
                'total_cost': 29.8,
                'budget_used_pct': 99.3,
                'ends_at_end_node': True,
                'success': True
            }
        """
```

### Results Storage
**JSON Format** (detailed logs):
```json
{
  "metadata": {
    "timestamp": "2025-11-03T10:30:00",
    "python_version": "3.11.5",
    "hostname": "research-server-01"
  },
  "results": [
    {
      "algorithm": "WU_UCT",
      "problem": "grid_10x10_medium_30.txt",
      "iterations": 10000,
      "workers": {"expansion": 2, "simulation": 6},
      "reward": 450,
      "time": 5.23,
      "path": [0, 15, 28, 34, ..., 1]
    }
  ]
}
```

**Excel Format** (aggregate analysis):
- Sheet 1: Summary statistics (mean, std, best per dataset)
- Sheet 2: Raw results (one row per run)
- Sheet 3: Scaling analysis (speedup vs. workers)

### Validation Tools
```python
# Validate solution correctness
def validate_solution(problem_file, path):
    """
    Check if path is valid:
    1. Starts at START_NODE (0)
    2. Ends at END_NODE (1)
    3. No revisits (except START/END)
    4. Total distance ≤ budget
    5. All edges satisfy max_distance constraint
    """
    
# Compare against optimal (small instances)
def solve_optimal(problem_file):
    """
    Brute-force search for optimal path (tractable for n < 20).
    Used as ground truth for validation.
    """
```

---

## 4.3.5 Optimizations and Performance Tuning

### Algorithm-Level Optimizations

#### 1. Distance Caching
```python
class OrienteeringProblem:
    def get_distance(self, a, b):
        key = (min(a, b), max(a, b))  # Symmetric cache key
        if key not in self._distance_cache:
            self._distance_cache[key] = math.hypot(
                self.nodes[a].x - self.nodes[b].x,
                self.nodes[a].y - self.nodes[b].y
            )
        return self._distance_cache[key]
```
**Impact**: 10-20x speedup on distance lookups

#### 2. End Reachability Precomputation
```python
def _precompute_end_reachability(self):
    """
    BFS from END_NODE to find all nodes that can structurally reach it.
    Used to prune impossible actions during action generation.
    """
    # Reverse BFS from END
    reachable = {END_NODE}
    queue = deque([END_NODE])
    
    while queue:
        node = queue.popleft()
        for predecessor in reverse_neighbors[node]:
            if predecessor not in reachable:
                reachable.add(predecessor)
                queue.append(predecessor)
    
    self._can_reach_end_structure = reachable
```
**Impact**: 50-100x speedup on action generation for large, sparse graphs

#### 3. Reward Normalization
```python
# Normalize rewards to [0, 1] range for stable UCT
max_score = max(node.score for node in nodes)
reward_scale = 1.0 / max_score

def get_normalized_score(node_id):
    return nodes[node_id].score * reward_scale
```
**Impact**: Prevents reward scale from dominating exploration term

### Parameter Tuning

| Parameter | Default | Range | Impact |
|-----------|---------|-------|--------|
| `exploration_constant` | √2 ≈ 1.41 | [0.5, 3.0] | Balance exploration/exploitation |
| `virtual_loss_value` | 0.2 × avg_reward | [0.1, 0.5] | Worker diversity (VL only) |
| `expansion_workers` | 2 | [1, 4] | Tree growth rate (WU-UCT) |
| `simulation_workers` | 6 | [4, 16] | Rollout throughput (WU-UCT) |
| `max_edge_distance` | 1.42 | [1.0, 2.0] | Graph connectivity |

**Tuning Strategy**:
1. **Grid Search**: Exhaustive search over parameter combinations
2. **Problem-Specific**: Different optima for sparse vs. dense graphs
3. **Scaling Laws**: More workers → lower optimal exploration constant

### Threading Best Practices

1. **Lock Granularity**: Per-node locks minimize contention
2. **Lock-Free Simulation**: Rollouts on copied states (no locks)
3. **Work Queue Size**: Balance memory vs. producer-consumer smoothness
4. **Worker Ratios**: WU-UCT performs best with 1:3 expansion:simulation ratio

---

## 4.3.6 Example Usage

### Single-Threaded MCTS
```bash
# Run basic UCT on a problem instance
python -m MCTS.mcts_base \
    --problem OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt \
    --iterations 10000 \
    --exploration 1.42
```

### Tree Parallel MCTS
```bash
# Run with 4 shared-tree workers
python Tree/main.py \
    --problem OP_Benchmark_Set/set_64_1/set_64_1_80.txt \
    --workers 4 \
    --iterations 100000
```

### Virtual Loss MCTS
```bash
# Run with 8 VL workers
python VL/main.py \
    --problem OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt \
    --workers 8 \
    --virtual-loss 0.15 \
    --iterations 100000
```

### WU-UCT
```bash
# Run with 2 expansion + 6 simulation workers
python WU_UCT/main.py \
    --problem OP_Benchmark_Set/parallel_friendly_v2/xlarge/xlarge_40x40_r0_84.txt \
    --expansion-workers 2 \
    --simulation-workers 6 \
    --iterations 100000
```

### Batch Benchmarking
```bash
# Run full benchmark suite
python results_gen/run_benchmark.py \
    --dataset parallel_friendly_v2/xlarge \
    --algorithms simple_wu vl wu_uct \
    --iterations 100000 \
    --workers 4 \
    --runs 3 \
    --limit 10 \
    --output benchmark_results.xlsx
```

---

## 4.3.7 Testing and Validation

### Unit Tests
- **Action Generation**: Verify all actions satisfy budget and connectivity constraints
- **UCT Formula**: Numerical validation against reference implementation
- **Thread Safety**: Race condition detection via stress testing

### Integration Tests
- **End-to-End**: Run full algorithm on known instances, verify solution validity
- **Scaling Tests**: Confirm speedup with increasing worker count

### Validation Against Baselines
- **Optimal Solver**: Compare on small instances (n < 20)
- **OR-Tools**: Industry-standard optimization library baseline
- **Literature Results**: Verify performance on Tsiligirides benchmark set

---

## 4.3.8 Visualization (Optional)

The `viz/` module provides interactive visualization of the search process:

```python
# Visualize step-by-step MCTS execution
python viz/mcts_viz.py \
    --problem OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt \
    --iterations 1000 \
    --animate
```

**Features**:
- **Node Coloring**: By visit count or average reward
- **Path Highlighting**: Best path found so far
- **Animation**: Step-through of selection/expansion/simulation phases

**Example Output**:
```
[Iteration 100]
Best path: [0, 15, 28, 34, 45, 67, 1]
Reward: 320
Cost: 28.5 / 30.0 (95%)
Tree size: 487 nodes, 8 levels deep
```

---

## 4.3.9 Summary

This implementation provides a comprehensive, modular framework for parallel MCTS research on the Orienteering Problem:

✅ **Correctness**: Validated against optimal solutions and OR-Tools  
✅ **Performance**: Optimized data structures achieve 10-100x speedups  
✅ **Scalability**: Tested on problems up to 1600 nodes with 12 workers  
✅ **Reproducibility**: Detailed configuration logging and random seed control  
✅ **Extensibility**: Modular design supports new algorithms and variants  

The codebase serves both as a research platform for investigating parallel MCTS coordination mechanisms and as a practical solver for orienteering problems in robotics and logistics applications.

---

**Next Section**: [4.4 Experimental Setup] - Details on benchmark datasets, hardware configuration, and evaluation metrics.
