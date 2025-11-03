# UCT Implementation Analysis

## Overview
The UCT (Upper Confidence bounds applied to Trees) implementation consists of two main classes:
1. **UCTNode** - Represents a state in the search tree
2. **UCTSingleThread** - Implements the single-threaded UCT algorithm

This document examines each class and how they interact with the OrienteeringState.

---

## Class 1: UCTNode

### Purpose
Represents a single node in the MCTS search tree. Each node encapsulates:
- A specific state in the orienteering problem
- Visit statistics (visits and total reward)
- Parent-child relationships
- Untried actions for expansion

### Key Attributes

```python
self.state: OrienteeringState          # The orienteering state this node represents
self.parent: Optional['UCTNode']       # Parent node in the tree
self.children: List['UCTNode']         # Child nodes (expanded actions)
self.visits: int                       # Number of times this node has been visited
self.total_reward: float               # Cumulative reward from all simulations through this node
self.untried_actions: List[int]        # Actions (node IDs) not yet expanded
```

### Interaction with OrienteeringState

#### 1. **Initialization** (`__init__`)
```python
def __init__(self, state: OrienteeringState, parent: Optional['UCTNode'] = None):
    self.state = state
    # ...
    self.untried_actions = list(state.get_available_actions() or [])
    if self.untried_actions:
        random.shuffle(self.untried_actions)
```

**State Interaction:**
- Receives an `OrienteeringState` instance
- Calls `state.get_available_actions()` to get all possible next nodes
- Shuffles actions for randomness (breaks symmetry in exploration)

**OrienteeringState Method Used:**
- `get_available_actions()` - Returns list of valid node IDs that can be visited next

#### 2. **Terminal Check** (`is_terminal`)
```python
def is_terminal(self) -> bool:
    return self.state.is_terminal()
```

**State Interaction:**
- Delegates to `OrienteeringState.is_terminal()`
- In traditional variant: checks if `path[-1] == END_NODE`
- Terminal nodes stop expansion and selection

**OrienteeringState Method Used:**
- `is_terminal()` - Returns True if at END_NODE (traditional) or out of moves

#### 3. **UCT Selection** (`uct_select_child`)
```python
def uct_select_child(self, exploration_constant: float = math.sqrt(2)) -> 'UCTNode':
    # Prefer unvisited children first
    unvisited = [child for child in self.children if child.visits == 0]
    if unvisited:
        return random.choice(unvisited)
    
    # Calculate UCT values for all children
    exploitation = child.total_reward / child.visits
    exploration = exploration_constant * math.sqrt(ln_parent_visits / child.visits)
    uct_value = exploitation + exploration
```

**State Interaction:**
- Does NOT directly interact with OrienteeringState
- Uses statistics accumulated from simulations that used the state
- The UCT formula balances:
  - **Exploitation:** Average reward (child.total_reward / child.visits)
  - **Exploration:** Uncertainty bonus (proportional to sqrt(ln(parent)/child_visits))

**Formula:**
```
UCT = Q/N + c * sqrt(ln(N_parent) / N_child)

Where:
- Q = total_reward (sum of all simulation rewards through this node)
- N = visits (number of simulations through this node)
- c = exploration_constant (typically sqrt(2))
```

#### 4. **String Representation** (`__repr__`)
```python
def __repr__(self):
    last_node = self.state.path[-1] if self.state.path else None
    avg_reward = self.total_reward / self.visits if self.visits > 0 else 0.0
    return f"<UCTNode node={last_node} visits={visits} avg_reward={avg_reward:.2f} children={len(children)}>"
```

**State Interaction:**
- Reads `state.path` to display current node location
- Shows node's position in the orienteering path

### Key Methods Summary

| Method | Interacts with State? | Purpose |
|--------|----------------------|---------|
| `is_fully_expanded()` | No | Check if all actions tried |
| `is_terminal()` | Yes (`state.is_terminal()`) | Check if state is terminal |
| `add_child()` | No | Maintain tree structure |
| `find_child_by_action()` | Yes (`child.state.path`) | Find child by action taken |
| `uct_select_child()` | No | UCT selection formula |
| `get_average_reward()` | No | Calculate average reward |

---

## Class 2: UCTSingleThread

### Purpose
Implements the single-threaded UCT algorithm using the four standard MCTS phases:
1. **Selection** - Traverse tree using UCT formula
2. **Expansion** - Add a new child node
3. **Simulation** - Random rollout from new node
4. **Backpropagation** - Update statistics up the tree

### Key Attributes

```python
self.problem: OrienteeringProblem       # Problem definition (nodes, budget, distances)
self.iterations: int                    # Number of MCTS iterations to run
self.exploration_constant: float        # UCT exploration parameter (default sqrt(2))
self.max_distance: Optional[float]      # Max edge distance constraint
self.root: Optional[UCTNode]            # Root of the search tree
self.current_iteration: int             # Iteration counter
```

### Interaction with OrienteeringState

#### Phase 1: **Selection** (`selection`)
```python
def selection(self, node: UCTNode) -> UCTNode:
    current = node
    
    while not current.is_terminal():
        if not current.is_fully_expanded():
            return current
        elif current.children:
            current = current.uct_select_child(self.exploration_constant)
        else:
            return current
    
    return current
```

**State Interaction:**
- Indirectly checks `state.is_terminal()` via `UCTNode.is_terminal()`
- Traverses tree until finding a node to expand
- Does NOT modify state - only navigates tree structure

**Flow:**
1. Start at given node (usually root)
2. While not terminal:
   - If node has untried actions → return for expansion
   - If fully expanded → select best child via UCT
   - If dead end → return node
3. Return leaf node

#### Phase 2: **Expansion** (`expansion`)
```python
def expansion(self, node: UCTNode) -> UCTNode:
    if not node.untried_actions:
        return node
    
    # Select a random untried action
    action = node.untried_actions.pop()
    new_state = node.state.apply_action(action)
    child_node = UCTNode(new_state, parent=node)
    node.add_child(child_node)
    
    return child_node
```

**State Interaction:**
- **Critical:** Calls `state.apply_action(action)` to create new state
- Creates a new OrienteeringState with the action applied
- Wraps new state in a UCTNode and adds to tree

**OrienteeringState Method Used:**
- `apply_action(node_index)` - Returns new state with node added to path

**What `apply_action` Does:**
```python
# In OrienteeringState:
def apply_action(self, node_index):
    # 1. Check if node already visited
    if node_index in self.visited:
        raise ValueError("Already visited")
    
    # 2. Check neighbor constraint (if max_edge_distance set)
    if node_index not in problem.get_neighbors(current):
        raise ValueError("Not reachable")
    
    # 3. Calculate new cost
    cost_to_next = problem.get_distance(current, node_index)
    new_cost = self.cost_so_far + cost_to_next
    
    # 4. Check budget
    if new_cost > problem.budget:
        raise ValueError("Exceeds budget")
    
    # 5. Create new state
    new_path = self.path + [node_index]
    new_reward = self.reward_so_far + problem.get_normalized_score(node_index)
    return OrienteeringState(problem, new_path, new_cost, new_reward)
```

#### Phase 3: **Simulation** (`simulation`)
```python
def simulation(self, state: OrienteeringState) -> float:
    current = state.copy()
    
    while not current.is_terminal():
        actions = current.get_available_actions()
        if not actions:
            break
        
        action = random.choice(actions)
        current = current.apply_action(action)
    
    # Calculate final reward
    reward = current.get_reward()
    
    if current.is_terminal():
        reward += 0.05  # Completion bonus
    else:
        if len(current.path) > 2:
            reward *= 0.8  # 20% penalty for incomplete
    
    return reward
```

**State Interaction:**
- **Heavy interaction** - this is where most state operations happen
- Calls `state.copy()` to create independent simulation
- Repeatedly calls `get_available_actions()` and `apply_action()`
- Uses `state.is_terminal()` to check completion
- Uses `state.get_reward()` to get final score

**OrienteeringState Methods Used:**
- `copy()` - Create independent copy for simulation
- `is_terminal()` - Check if at END_NODE
- `get_available_actions()` - Get valid next moves
- `apply_action(action)` - Apply random move
- `get_reward()` - Get accumulated reward

**Reward Shaping:**
- **Completion bonus:** +0.05 if reached END_NODE
- **Incompletion penalty:** ×0.8 (20% penalty) for non-trivial incomplete paths

#### Phase 4: **Backpropagation** (`backpropagation`)
```python
def backpropagation(self, node: UCTNode, reward: float):
    current = node
    while current is not None:
        current.visits += 1
        current.total_reward += reward
        current = current.parent
```

**State Interaction:**
- Does NOT interact with OrienteeringState
- Only updates UCTNode statistics
- Propagates simulation reward up the tree

#### **Best Path Extraction** (`get_best_path`)
```python
def get_best_path(self) -> OrienteeringState:
    if self.root is None:
        raise ValueError("No search has been performed yet")
    
    current = self.root
    while current.children:
        current = self.get_best_child(current)
    
    return current.state
```

**State Interaction:**
- Follows children with highest visit counts
- Returns the `OrienteeringState` from the leaf node
- **Important:** Uses visit count, NOT average reward (standard MCTS approach)

### Key Methods Summary

| Method | Phase | State Interaction | Purpose |
|--------|-------|------------------|---------|
| `selection()` | 1 | Reads (via `is_terminal()`) | Traverse to leaf |
| `expansion()` | 2 | Creates (via `apply_action()`) | Add new child |
| `simulation()` | 3 | Heavy (copy, actions, apply) | Random rollout |
| `backpropagation()` | 4 | None | Update statistics |
| `get_best_path()` | Post-search | Reads (returns state) | Extract solution |
| `run_iteration()` | Orchestrator | Indirect (calls phases) | Single MCTS iteration |
| `run()` | Main | Indirect (calls iterations) | Complete search |

---

## OrienteeringState Methods Called by UCT

### Summary Table

| State Method | Called By | Frequency | Purpose |
|-------------|-----------|-----------|---------|
| `get_available_actions()` | UCTNode.__init__, simulation | High | Get valid next nodes |
| `apply_action(action)` | expansion, simulation | Very High | Create new state |
| `is_terminal()` | selection, simulation | Very High | Check if done |
| `copy()` | simulation | High | Independent simulation |
| `get_reward()` | simulation | High | Get accumulated reward |
| `get_path()` | (utility) | Low | Get node sequence |
| `get_cost()` | (utility) | Low | Get budget used |

### Method Details

#### 1. `get_available_actions()`
**Called:** During node initialization and simulation
**Purpose:** Returns list of valid node IDs that can be visited next
**Implementation in OrienteeringState:**
```python
def get_available_actions(self):
    actions = []
    current = self.path[-1]
    neighbor_ids = self.problem.get_neighbors(current)
    
    # Check if can go to END
    if END_NODE in neighbor_ids and END_NODE not in self.visited:
        cost_to_end = self.problem.get_distance(current, END_NODE)
        if self.cost_so_far + cost_to_end <= self.problem.budget:
            actions.append(END_NODE)
    
    # Check other neighbors
    for i in neighbor_ids:
        if i in self.visited or i == START_NODE or i == END_NODE:
            continue
        
        cost_to_i = self.problem.get_distance(current, i)
        new_cost = self.cost_so_far + cost_to_i
        
        if new_cost <= self.problem.budget:
            # Traditional: Check if can reach END from i
            cost_from_i_to_end = self.problem.get_distance(i, END_NODE)
            if new_cost + cost_from_i_to_end <= self.problem.budget:
                actions.append(i)
    
    return actions
```

**Key Constraints Enforced:**
- Node not already visited
- Within neighbor distance (if max_edge_distance set)
- Budget allows move + eventual return to END
- Not START_NODE (can't revisit)

#### 2. `apply_action(action)`
**Called:** During expansion (once) and simulation (many times)
**Purpose:** Creates a new state with the action applied
**Returns:** New OrienteeringState instance
**Validation:**
- Checks if node already visited
- Enforces neighbor constraint
- Validates budget feasibility
- Raises ValueError if invalid

#### 3. `is_terminal()`
**Called:** Throughout selection and simulation
**Purpose:** Determines if state is complete
**Returns:** Boolean
**Implementation:**
```python
def is_terminal(self):
    return self.path[-1] == END_NODE
```

#### 4. `copy()`
**Called:** At start of each simulation
**Purpose:** Creates independent copy for rollout
**Returns:** New OrienteeringState with copied path
**Important:** Ensures simulation doesn't affect tree nodes

#### 5. `get_reward()`
**Called:** After simulation completes
**Purpose:** Returns accumulated normalized reward
**Returns:** Float (sum of normalized node scores)

---

## Key Interactions Flow

### Single MCTS Iteration Flow

```
1. SELECTION (navigate tree)
   UCTSingleThread.selection(root)
   ├─> UCTNode.is_terminal() 
   │   └─> OrienteeringState.is_terminal()
   └─> UCTNode.uct_select_child()
       └─> (uses statistics, no state interaction)

2. EXPANSION (add new node)
   UCTSingleThread.expansion(leaf)
   ├─> pop untried_action
   ├─> OrienteeringState.apply_action(action)  ← STATE CREATION
   │   ├─> validate move
   │   ├─> calculate new cost
   │   └─> return new state
   └─> UCTNode(new_state)
       └─> OrienteeringState.get_available_actions()  ← GET ACTIONS

3. SIMULATION (random rollout)
   UCTSingleThread.simulation(leaf.state)
   ├─> OrienteeringState.copy()  ← COPY STATE
   └─> while not terminal:
       ├─> OrienteeringState.get_available_actions()  ← GET MOVES
       ├─> random.choice(actions)
       └─> OrienteeringState.apply_action(action)  ← APPLY MOVE
   └─> OrienteeringState.get_reward()  ← GET SCORE

4. BACKPROPAGATION (update stats)
   UCTSingleThread.backpropagation(leaf, reward)
   └─> update visits and total_reward
       (no state interaction)
```

### Data Flow Diagram

```
OrienteeringProblem (nodes, budget, distances)
        │
        ├──> OrienteeringState (path, cost, reward)
        │           │
        │           ├──> get_available_actions() → [actions]
        │           ├──> apply_action(a) → new_state
        │           ├──> is_terminal() → bool
        │           └──> get_reward() → float
        │
        └──> UCTSingleThread (iterations, exploration)
                    │
                    ├──> root: UCTNode(initial_state)
                    │           │
                    │           ├─> state: OrienteeringState
                    │           ├─> visits: int
                    │           ├─> total_reward: float
                    │           └─> children: [UCTNode]
                    │
                    └──> run_iteration()
                            ├─> selection() → leaf
                            ├─> expansion() → new_child
                            ├─> simulation() → reward
                            └─> backpropagation()
```

---

## Critical Design Points

### 1. **State Immutability**
- `apply_action()` creates NEW state (doesn't modify existing)
- Allows tree to maintain different states at different nodes
- Simulation uses `copy()` to avoid affecting tree

### 2. **Lazy Expansion**
- Actions stored in `untried_actions` when node created
- Expanded one at a time as needed
- Reduces memory usage for large action spaces

### 3. **Separation of Concerns**
- **OrienteeringState:** Problem-specific logic (validity, costs, rewards)
- **UCTNode:** Tree structure and statistics
- **UCTSingleThread:** MCTS algorithm orchestration

### 4. **UCT vs. State Logic**
- **UCT decides:** Which node to expand (using UCT formula)
- **State decides:** Which actions are valid (using constraints)
- Clear separation enables different search strategies with same state

### 5. **Reward Normalization**
- Handled in `OrienteeringProblem.get_normalized_score()`
- Makes rewards comparable across different problem instances
- Typical range: 0 to 1 instead of 0 to 100+

### 6. **Visit Count Selection**
- Best path uses visit count, NOT average reward
- Represents most robust action (most explored)
- Standard MCTS approach for final decision

---

## Performance Considerations

### Bottlenecks in State Interaction

1. **`get_available_actions()` - Called Most Frequently**
   - Must check: visited, neighbors, budget, reachability
   - Traditional variant adds END reachability check
   - **Optimization:** Cache neighbor lists in problem

2. **`apply_action()` - Creates New States**
   - Memory allocation for new state instance
   - Copying path list
   - **Optimization:** Path could use persistent data structure

3. **`simulation()` - Deepest Interaction**
   - Many `get_available_actions()` calls per iteration
   - Many `apply_action()` calls per iteration
   - **Optimization:** Faster simulation strategies (see optimized/)

### Traditional vs. Optimized OrienteeringState

**Traditional (current):**
```python
def get_available_actions(self):
    # Check if can reach END from each neighbor
    cost_from_i_to_end = self.problem.get_distance(i, END_NODE)
    if new_cost + cost_from_i_to_end <= self.problem.budget:
        actions.append(i)
```
- Ensures all paths can reach END
- Safer but slower
- Extra distance calculation per neighbor

**Optimized (alternative):**
```python
def get_available_actions(self):
    # Only check if move fits budget
    if new_cost <= self.problem.budget:
        actions.append(i)
```
- Faster action generation
- May generate dead-end paths
- Relies on simulation to filter naturally

---

## Conclusion

The UCT implementation cleanly separates:
1. **Search strategy** (UCT formula, tree navigation) - in UCTNode and UCTSingleThread
2. **Problem domain** (orienteering constraints, rewards) - in OrienteeringState

**Key Takeaways:**
- UCTNode wraps OrienteeringState with tree structure and statistics
- UCTSingleThread orchestrates MCTS phases using node operations
- OrienteeringState encapsulates all problem-specific logic
- Heavy interaction happens during simulation (random rollouts)
- State immutability enables independent exploration paths

This design makes it straightforward to:
- Swap orienteering variants (traditional vs. no-end)
- Parallelize the algorithm (WU-UCT)
- Optimize individual components independently
