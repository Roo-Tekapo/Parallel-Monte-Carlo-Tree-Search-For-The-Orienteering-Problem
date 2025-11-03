# Parallel MCTS Implementation Comparison

## Overall Approach: Shared Tree Parallelization

All three parallel MCTS implementations (Tree-Parallel, Virtual Loss, and WU-UCT) follow the same fundamental **shared tree parallelization** strategy. Multiple worker threads operate concurrently on a single unified search tree, rather than each maintaining separate trees or splitting the search space. This approach allows workers to benefit from each other's explorations, building collective knowledge in one central tree structure. Each implementation performs the four classic MCTS phases: **Selection** (traversing the tree using UCT), **Expansion** (adding new nodes), **Simulation** (random rollouts), and **Backpropagation** (updating statistics). The key difference between implementations lies in how they handle **coordination** between workers to prevent redundant exploration and race conditions when multiple threads attempt to explore the same promising paths simultaneously.

---

## Core Differences Summary

### **Tree-Parallel (Standard UCT)**
- **Selection Formula:** Standard UCT with no modifications
- **Coordination Mechanism:** Coarse-grained locks (global tree lock during expansion)
- **Virtual Loss:** None - workers compete directly for promising nodes
- **Best For:** Simple parallelization with 1-4 workers

### **Virtual Loss (VL-UCT)**
- **Selection Formula:** Standard UCT, but rewards are temporarily penalized
- **Coordination Mechanism:** Fixed penalty values applied to nodes being explored
- **Virtual Loss:** Fixed value (e.g., 0.2) subtracted from node rewards temporarily
- **Best For:** Moderate parallelization with 4-12 workers, intuitive tuning

### **WU-UCT (Weighted Update UCT)**
- **Selection Formula:** Modified UCT using pending simulation counts
- **Coordination Mechanism:** Lock-free selection with asynchronous updates
- **Virtual Loss:** Dynamic counter-based system tracking unobserved simulations
- **Best For:** High parallelization with 8+ workers, maximum scalability

---

## Component-by-Component Analysis

### **1. NODE IMPLEMENTATION**

#### **Tree-Parallel Node** (`TreeParallelNode`)
```python
class TreeParallelNode(UCTNode):
    def __init__(self, state, parent):
        super().__init__(state, parent)
        self._node_lock = threading.Lock()  # Basic thread safety
```

**Key Features:**
- Extends `UCTNode` with minimal changes
- Single lock (`_node_lock`) protects all node statistics
- Standard statistics: `visits`, `total_reward`
- No virtual loss or prediction mechanisms

**Selection Formula:**
```
UCT = Q/N + c * sqrt(ln(N_parent) / N_child)
```
Standard UCT with no modifications.

---

#### **Virtual Loss Node** (`VLNode`)
```python
class VLNode(UCTNode):
    def __init__(self, state, parent):
        super().__init__(state, parent)
        self._vl_lock = threading.Lock()
        self._virtual_losses = {}  # Maps thread_id -> loss_value
        self._total_virtual_loss = 0.0
        self._virtual_visits = 0  # Number of threads exploring
```

**Key Features:**
- Tracks **per-thread virtual losses** in a dictionary
- Maintains `_total_virtual_loss` (sum of all applied penalties)
- Tracks `_virtual_visits` (number of active explorations)
- Virtual loss directly reduces effective reward

**Selection Formula:**
```
UCT = (Q - L) / (N + V) + c * sqrt(ln(N_parent) / (N + V))
```
Where:
- `L` = total virtual loss (penalty)
- `V` = virtual visits (number of threads)

**Mechanism:**
1. When worker selects a path: Apply fixed penalty to all nodes
2. Penalty temporarily reduces exploitation term
3. After simulation: Remove penalty and update with real result

---

#### **WU-UCT Node** (`WUUCTNode`)
```python
class WUUCTNode(UCTNode):
    def __init__(self, state, parent):
        super().__init__(state, parent)
        self.traverse_history = {}  # Maps sim_id -> (action, reward, time)
        self._history_lock = threading.Lock()
        self._write_lock = threading.Lock()  # Only for commits
```

**Key Features:**
- **Traverse History:** Tracks pending simulations by ID
- **Lock-free reading:** Workers read statistics without blocking
- **Asynchronous updates:** Results committed independently
- Separates "completed visits" from "unobserved simulations"

**Selection Formula:**
```
UCT = Q/N + c * sqrt(ln(N_parent + O_parent) / (N_child + O_child))
```
Where:
- `O` = unobserved count (number of pending simulations)
- Only completed visits (`N`) used in exploitation
- Both parent and child use `N + O` in exploration term

**Mechanism:**
1. Mark simulation started: Add entry to `traverse_history`
2. Selection reads `O` (unobserved count) without locking
3. Simulation completes independently
4. Commit result: Brief atomic write to update `N` and `Q`

---

### **2. WORKER IMPLEMENTATION**

#### **Tree-Parallel Worker** (`TreeParallelWorker`)
```python
def _perform_iteration(self):
    path, leaf_node, leaf_state = self._select_leaf()
    expanded_node, expanded_state = self._expand_leaf(leaf_node, leaf_state)
    reward = self._simulate(expanded_state)
    self._backpropagate(path, reward)
```

**Characteristics:**
- **Single thread type:** All workers do complete MCTS iterations
- **Expansion locking:** Global tree lock during expansion
- **Lock contention tracking:** Measures competition for expansion rights
- **Synchronous:** Selection → Expansion → Simulation → Backprop in sequence

**Coordination:**
```python
lock_available = self.tree_lock.acquire(blocking=False)
if not lock_available:
    self.lock_contentions += 1  # Count collision
    self.tree_lock.acquire(blocking=True)  # Wait
```

---

#### **Virtual Loss Worker** (`VLWorker`)
```python
def _perform_iteration(self):
    path, leaf_node, leaf_state = self._select_leaf()
    self._apply_virtual_loss(path)  # Apply fixed penalties
    
    try:
        expanded_node, expanded_state = self._expand_leaf(leaf_node, leaf_state)
        reward = self._simulate(expanded_state)
        self._remove_virtual_loss_and_backpropagate(path, reward)
    except:
        self._remove_virtual_loss(path)  # Ensure cleanup
```

**Characteristics:**
- **Single thread type:** All workers do complete MCTS iterations
- **Virtual loss protocol:**
  1. Apply fixed penalty to entire selected path
  2. Expand and simulate
  3. Remove penalty and backpropagate real result
- **Collision detection:** Tracks when selecting paths with existing VL
- **Synchronous:** But paths are discouraged via temporary penalties

**Coordination:**
```python
def apply_virtual_loss(self, thread_id, loss_value):
    with self._vl_lock:
        self._virtual_losses[thread_id] = loss_value
        self._total_virtual_loss += loss_value
        self._virtual_visits += 1
```

---

#### **WU-UCT Workers** (`ExpansionWorker` + `SimulationWorker`)

**ExpansionWorker:**
```python
def _perform_iteration(self):
    path, leaf_node, leaf_state = self._select_leaf()  # Lock-free!
    node, state = self._expand_if_possible(leaf_node, leaf_state)
    
    simulation_id = self._generate_simulation_id()
    self._mark_path_as_started(path, simulation_id)  # Update-Incomplete
    
    work_unit = WorkUnit(simulation_id, path, state, time.time())
    self.work_queue.put(work_unit)
```

**SimulationWorker:**
```python
def _process_work_unit(self, work_unit):
    reward = self._simulate(work_unit.state_to_simulate)  # Independent
    self._backpropagate(work_unit.path, reward, work_unit.simulation_id)
    
def _backpropagate(self, path, reward, sim_id):
    for node in reversed(path):
        node.commit_simulation_result(sim_id, reward)  # Update-Complete
```

**Characteristics:**
- **Two thread types:** Separation of concerns
  - Expansion workers: Tree traversal and expansion
  - Simulation workers: Independent rollouts
- **Asynchronous pipeline:** Work queue connects expansion to simulation
- **Lock-free selection:** Reading statistics doesn't block other workers
- **Update-Incomplete/Update-Complete:** Two-phase commit protocol

**Coordination:**
```python
# Algorithm 2: Update-Incomplete (mark started)
def mark_simulation_started(self, simulation_id):
    with self._history_lock:
        self.traverse_history[simulation_id] = (action, reward, time)

# Algorithm 3: Update-Complete (commit result)
def commit_simulation_result(self, simulation_id, reward):
    with self._history_lock:
        action, imm_reward, start = self.traverse_history.pop(simulation_id)
    
    with self._write_lock:  # Brief atomic write
        self.visits += 1
        self.total_reward += reward
```

**Two-Phase Commit Protocol Explained:**

WU-UCT uses a two-phase protocol to handle the asynchronous nature of separating tree expansion from simulation execution:

**Phase 1: Update-Incomplete (Expansion Worker)**
- **When:** Immediately after selecting a path and BEFORE simulation starts
- **Purpose:** Notify other workers that this path is being explored
- **Action:** Add simulation ID to `traverse_history` dictionary
- **Effect on UCT:** Increases `O` (unobserved count) which makes the node less attractive
- **Why it matters:** Prevents other expansion workers from immediately selecting the same path

```python
# Expansion worker execution flow:
path = select_leaf()                    # Select using UCT with current N and O
expand_if_possible(leaf_node)           # Add new node to tree
simulation_id = generate_id()           
for node in path:
    # Phase 1: Mark as started
    node.traverse_history[sim_id] = (action, reward, start_time)
    # Now O = len(traverse_history) has increased by 1
queue_work(WorkUnit(sim_id, path, ...))  # Hand off to simulation worker
# Expansion worker continues immediately - doesn't wait!
```

**Phase 2: Update-Complete (Simulation Worker)**
- **When:** After simulation finishes and reward is calculated
- **Purpose:** Commit the actual simulation result to the tree
- **Action:** Remove from `traverse_history`, update `N` (visits) and `Q` (total reward)
- **Effect on UCT:** Decreases `O`, increases `N` and `Q` with real results
- **Why it matters:** Transforms a pending simulation into actual statistical knowledge

```python
# Simulation worker execution flow (happens asynchronously):
work_unit = work_queue.get()            # Get work when available
reward = simulate(work_unit.state)      # Expensive rollout (could take 100ms+)
for node in reversed(work_unit.path):
    # Phase 2: Commit result
    with node._history_lock:
        # Remove from pending (decreases O)
        action, imm_reward, start = node.traverse_history.pop(sim_id)
    with node._write_lock:
        # Update actual statistics
        node.visits += 1                # N++ (completed visit)
        node.total_reward += reward     # Q += reward (actual result)
```

**Timeline Example:**

```
Time    Node State                Selection Impact                      Workers
────    ──────────                ────────────────                      ───────
t=0     N=10, O=0, Q=50          UCT = 50/10 + c*sqrt(ln(10)/(10+0))  All workers see
        traverse_history={}       exploitation = 5.0                    same state

t=1     N=10, O=1, Q=50          UCT = 50/10 + c*sqrt(ln(10)/(10+1))  Worker 1:
        traverse_history=        exploitation = 5.0 (unchanged)         Phase 1 done
        {123: (...)}             exploration penalty applied            queued work
                                  → Node less attractive!               continues...

t=2     N=10, O=2, Q=50          UCT = 50/10 + c*sqrt(ln(10)/(10+2))  Worker 2:
        traverse_history=        exploitation = 5.0                     Also selected
        {123:(...), 456:(...)}   exploration penalty increased          this path
                                  → Even less attractive!               (before seeing O=1)

t=50    N=11, O=1, Q=55.2        UCT = 55.2/11 + c*sqrt(ln(11)/(11+1)) Sim Worker:
        traverse_history=        exploitation = 5.02 (better!)          Committed
        {456: (...)}             exploration denominator = 12           sim 123
                                  → Reward improved, O decreased        

t=100   N=12, O=0, Q=60.4        UCT = 60.4/12 + c*sqrt(ln(12)/(12+0)) Sim Worker:
        traverse_history={}      exploitation = 5.03                    Committed
                                  exploration denominator = 12           sim 456
                                  → All simulations complete!
```

**Key Benefits of Two-Phase Protocol:**

1. **Non-blocking expansion**: Expansion workers don't wait for slow simulations
2. **Immediate coordination**: Phase 1 instantly signals "I'm exploring here"
3. **Accurate statistics**: Phase 2 ensures real results eventually update the tree
4. **Independent timing**: Phases can be separated by milliseconds or seconds
5. **Lock-free reads**: Selection can read N and O without waiting for commits

**Comparison to Single-Phase Updates:**

| Aspect | Single-Phase (Tree-Parallel/VL) | Two-Phase (WU-UCT) |
|--------|----------------------------------|-------------------|
| Update timing | Synchronous (after simulation) | Asynchronous (split) |
| Worker blocking | Worker blocked during simulation | Expansion worker freed immediately |
| Coordination signal | Virtual loss or lock | O count (pending simulations) |
| Statistics accuracy | Always reflects completed work | Predictive (includes pending) |
| Scalability | Limited by simulation time | Decoupled - high scalability |

---

### **3. COORDINATOR IMPLEMENTATION**

#### **Tree-Parallel Coordinator** (`TreeParallelMCTS`)
```python
class TreeParallelMCTS:
    def __init__(self, problem, num_workers, exploration_constant):
        self.root = TreeParallelNode(initial_state)
        self.tree_lock = threading.Lock()  # Global lock
        self.workers = []
    
    def run(self, max_iterations):
        # Create workers with equal iteration splits
        for i in range(self.num_workers):
            worker = TreeParallelWorker(
                root=self.root,
                tree_lock=self.tree_lock,  # Shared lock
                iterations_per_worker=iterations_per_worker
            )
            worker.start()
        
        # Wait for completion
        for worker in self.workers:
            worker.join()
```

**Characteristics:**
- **Simple architecture:** Just manages worker threads
- **Single tree lock:** Shared among all workers for expansion
- **Equal work distribution:** Iterations split evenly
- **Synchronous completion:** Wait for all workers to finish

**Statistics Tracked:**
- Lock contentions (competition for expansion)
- Iterations per worker
- Tree size and depth
- Average simulation time

---

#### **Virtual Loss Coordinator** (`VirtualLossMCTS`)
```python
class VirtualLossMCTS:
    def __init__(self, problem, num_workers, exploration_constant, 
                 virtual_loss_value=None):
        self.root = VLNode(initial_state)
        self.workers = []
        
        # Auto-scale virtual loss if not specified
        if virtual_loss_value is None:
            avg_normalized = average_node_reward()
            self.virtual_loss_value = avg_normalized * 0.2
    
    def run(self, max_iterations):
        for i in range(self.num_workers):
            worker = VLWorker(
                root=self.root,
                virtual_loss_value=self.virtual_loss_value,
                iterations_per_worker=iterations_per_worker
            )
            worker.start()
        
        for worker in self.workers:
            worker.join()
```

**Characteristics:**
- **Auto-scaling:** Virtual loss value calculated from problem
- **Simple architecture:** Like Tree-Parallel but with VL parameter
- **No global lock:** Each node manages its own virtual losses
- **Tunable coordination:** Can adjust penalty strength

**Statistics Tracked:**
- Virtual loss collisions (selecting nodes with existing VL)
- Collision rate (lower = better thread separation)
- Per-worker performance
- Virtual loss value used

---

#### **WU-UCT Coordinator** (`WUUCTCoordinator`)
```python
class WUUCTCoordinator:
    def __init__(self, problem, num_expansion_workers, 
                 num_simulation_workers, exploration_constant):
        self.root = WUUCTNode(initial_state)
        self.work_queue = Queue(maxsize=1000)
        self.expansion_workers = []
        self.simulation_workers = []
        self.stop_event = threading.Event()
    
    def run(self, max_iterations):
        # Start simulation workers first
        for i in range(self.num_simulation_workers):
            worker = SimulationWorker(
                work_queue=self.work_queue,
                stop_event=self.stop_event
            )
            worker.start()
        
        # Start expansion workers
        for i in range(self.num_expansion_workers):
            worker = ExpansionWorker(
                root=self.root,
                work_queue=self.work_queue,
                num_iterations=iterations_per_worker
            )
            worker.start()
        
        # Wait for expansion to complete
        for worker in self.expansion_workers:
            worker.join()
        
        # Wait for queue to drain
        self.work_queue.join()
        
        # Stop simulation workers
        self.stop_event.set()
```

**Characteristics:**
- **Two-tier architecture:** Separate expansion and simulation pools
- **Work queue:** Decouples tree operations from simulations
- **Flexible worker ratios:** Can tune expansion:simulation balance
- **Asynchronous completion:** Expansion finishes, queue drains, then stop

**Statistics Tracked:**
- Expansions vs simulations ratio
- Queue wait times
- Lock-free selection count
- Per-worker type breakdown
- Worker utilization

---

## Performance Characteristics

| **Aspect** | **Tree-Parallel** | **Virtual Loss** | **WU-UCT** |
|------------|-------------------|------------------|------------|
| **Scalability** | Poor (1-4 workers) | Good (4-12 workers) | Excellent (8+ workers) |
| **Lock Contention** | High (global lock) | Medium (per-node) | Low (lock-free selection) |
| **Implementation Complexity** | Low | Medium | High |
| **Tuning Required** | Minimal | Moderate (VL value) | Significant (worker ratios) |
| **Memory Overhead** | Minimal | Low (VL tracking) | Medium (traverse history) |
| **Best Use Case** | Simple problems | General purpose | Large-scale problems |

---

## Key Formula Comparison

### **Tree-Parallel (Standard UCT):**
```
UCT = Q/N + c * sqrt(ln(N_p) / N)
```

### **Virtual Loss (VL-UCT):**
```
UCT = (Q - L) / (N + V) + c * sqrt(ln(N_p) / (N + V))
```
- `L` = temporary penalty (e.g., 0.2)
- `V` = number of threads exploring this node

### **WU-UCT:**
```
UCT = Q/N + c * sqrt(ln(N_p + O_p) / (N + O))
```
- `O` = unobserved samples (pending simulations)
- Exploitation uses only completed visits
- Exploration uses predicted visit counts

---

## Summary

All three implementations share the same **tree structure and MCTS phases**, but differ fundamentally in **coordination strategy**:

1. **Tree-Parallel** uses **coarse-grained locking** - simple but creates bottlenecks
2. **Virtual Loss** uses **temporary penalties** - intuitive and effective for moderate parallelism
3. **WU-UCT** uses **lock-free predictions** - complex but scales to many workers

The choice depends on your needs:
- **Few workers (1-4):** Tree-Parallel is simplest
- **Moderate parallelism (4-12):** Virtual Loss offers best balance
- **High parallelism (8+):** WU-UCT provides maximum scalability
