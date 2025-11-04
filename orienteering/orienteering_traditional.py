import math
from collections import namedtuple
from typing import List, Optional, Dict


START_NODE = 0
END_NODE = 1
Node = namedtuple('Node', ['id', 'x', 'y', 'score'])


class OrienteeringProblemTraditional:
    
    def __init__(self, nodes: List[Node], budget: float, max_edge_distance: Optional[float] = 1.42, 
                 normalize_rewards: bool = False):
        self.nodes = nodes
        self.budget = budget
        self.start_id = START_NODE
        self.end_id = END_NODE
        self.max_edge_distance: Optional[float] = max_edge_distance
        self._neighbors: Optional[Dict[int, List[int]]] = None
        
        # Mark as traditional variant (requires end node)
        self.is_no_end_variant = False
        
        # Reward normalization
        self.normalize_rewards = normalize_rewards
        if normalize_rewards:
            self._setup_reward_normalization()
        else:
            self.reward_scale = 1.0
            self.reward_offset = 0.0
        
        # Cache for distance calculations
        self._distance_cache: Dict[tuple, float] = {}
        
        # Build neighbor structure if needed
        if self.max_edge_distance is not None:
            self._build_neighbors()
    
    @property
    def num_nodes(self):
        return len(self.nodes)
    
    def _setup_reward_normalization(self):
        """Setup reward normalization to scale rewards to a reasonable range for UCT."""
        max_node_score = max(node.score for node in self.nodes) if self.nodes else 1.0
        
        if max_node_score > 0:
            self.reward_scale = 1.0 / max_node_score
        else:
            self.reward_scale = 1.0
        
        self.reward_offset = 0.0
    
    def get_normalized_score(self, node_id: int) -> float:
        """Get the (possibly normalized) score for a node."""
        raw_score = self.nodes[node_id].score
        return (raw_score + self.reward_offset) * self.reward_scale

    @staticmethod
    def load_problem(filename):
        """Load problem from file."""
        with open(filename, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        budget, _ = lines[0].split()
        budget = float(budget)
        node_lines = lines[1:]
        nodes = []
        for idx, line in enumerate(node_lines):
            x, y, score = line.split()
            nodes.append(Node(idx, float(x), float(y), int(score)))
        return nodes, budget
    
    def get_distance(self, a: int, b: int) -> float:
        """Get cached Euclidean distance between nodes."""
        key = (min(a, b), max(a, b))
        if key not in self._distance_cache:
            self._distance_cache[key] = math.hypot(
                self.nodes[a].x - self.nodes[b].x, 
                self.nodes[a].y - self.nodes[b].y
            )
        return self._distance_cache[key]

    def _build_neighbors(self) -> None:
        """Build neighbor adjacency lists based on max_edge_distance."""
        n = self.num_nodes
        self._neighbors = {i: [] for i in range(n)}
        if self.max_edge_distance is None:
            return
        if self.max_edge_distance <= 0:
            return
        thr_sq = float(self.max_edge_distance) * float(self.max_edge_distance)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                dx = self.nodes[i].x - self.nodes[j].x
                dy = self.nodes[i].y - self.nodes[j].y
                if (dx * dx + dy * dy) <= thr_sq:
                    self._neighbors[i].append(j)

    def get_neighbors(self, node_id: int) -> List[int]:
        """Get neighbor nodes within max_edge_distance constraint."""
        if self.max_edge_distance is None:
            return list(range(self.num_nodes))
        if self._neighbors is None:
            self._build_neighbors()
        return self._neighbors.get(node_id, [])


class OrienteeringStateTraditional:
    """Simplified OrienteeringState for traditional MCTS (no BFS reachability checks)."""
    
    def __init__(self, problem: OrienteeringProblemTraditional, path=None, cost_so_far=0.0, reward_so_far=None):
        self.problem = problem
        self.path = path or [START_NODE]
        self.visited = set(self.path)
        self.cost_so_far = cost_so_far
        if reward_so_far is None:
            self.reward_so_far = self.problem.get_normalized_score(self.path[0])
        else:
            self.reward_so_far = reward_so_far

    def is_terminal(self):
        """Check if we've reached the END node."""
        return self.path[-1] == END_NODE

    def copy(self):
        """Create a copy of this state."""
        return OrienteeringStateTraditional(
            self.problem,
            path=self.path[:],
            cost_so_far=self.cost_so_far,
            reward_so_far=self.reward_so_far
        )
    
    def get_available_actions(self, traditional_mcts=True):
        actions = []
        current = self.path[-1]
        neighbor_ids = self.problem.get_neighbors(current)

        # Option to go directly to END if feasible
        if current != END_NODE and END_NODE in neighbor_ids and END_NODE not in self.visited:
            cost_to_end = self.problem.get_distance(current, END_NODE)
            if self.cost_so_far + cost_to_end <= self.problem.budget:
                actions.append(END_NODE)

        # Explore other unvisited neighbor nodes
        for i in neighbor_ids:
            if i in self.visited or i == START_NODE or i == END_NODE:
                continue
            
            cost_to_i = self.problem.get_distance(current, i)
            new_cost = self.cost_so_far + cost_to_i
            
            # Check if we can afford this move AND still reach END from there
            if new_cost <= self.problem.budget:
                # Additional check: can we reach END from node i?
                cost_from_i_to_end = self.problem.get_distance(i, END_NODE)
                total_cost_with_end = new_cost + cost_from_i_to_end
                
                # Only include this action if we can still reach END afterwards
                if total_cost_with_end <= self.problem.budget:
                    actions.append(i)
        
        return actions
    
    def apply_action(self, node_index, traditional_mcts=True):
        """
        Apply an action to create a new state.
        
        Traditional MCTS: Only validates budget for the single move.
        
        Args:
            node_index: Node to move to
            traditional_mcts (bool): Kept for API compatibility, always uses traditional approach
        """
        if node_index in self.visited:
            raise ValueError(f"Node {node_index} already visited.")
        
        current = self.path[-1]
        
        # Enforce neighbor constraint if configured
        if self.problem.max_edge_distance is not None:
            if node_index not in self.problem.get_neighbors(current):
                raise ValueError(f"Node {node_index} not reachable from {current}.")
        
        cost_to_next = self.problem.get_distance(current, node_index)
        new_cost = self.cost_so_far + cost_to_next
        
        # Traditional MCTS: Only check if we can afford this single move
        if new_cost > self.problem.budget:
            raise ValueError(f"Cannot apply action to node {node_index}, exceeds budget.")
        
        new_path = self.path + [node_index]
        new_reward = self.reward_so_far + self.problem.get_normalized_score(node_index)
        return OrienteeringStateTraditional(self.problem, new_path, new_cost, new_reward)

    def get_reward(self):
        return self.reward_so_far
    
    def get_cost(self):
        return self.cost_so_far
    
    def get_path(self):
        return self.path

    def __str__(self):
        return f"Path: {self.path}, Reward: {self.reward_so_far}, Cost: {self.cost_so_far:.2f}, Terminal: {self.is_terminal()}"


# Convenience aliases for drop-in replacement
OrienteeringProblem = OrienteeringProblemTraditional
OrienteeringState = OrienteeringStateTraditional


if __name__ == "__main__":
    import time
    
    print("="*70)
    print("TRADITIONAL MCTS ORIENTEERING - Simplified Implementation")
    print("="*70)
    print("\nThis version removes all BFS reachability checking for maximum speed.")
    print("Best for traditional MCTS that only checks single-move budget feasibility.\n")
    
    # Load a test problem
    nodes, budget = OrienteeringProblemTraditional.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    
    # Time the initialization (should be fast - no BFS precomputation)
    start = time.perf_counter()
    problem = OrienteeringProblemTraditional(
        nodes, budget, 
        max_edge_distance=1.42, 
        normalize_rewards=True
    )
    init_time = time.perf_counter() - start
    
    print(f"Initialization time: {init_time:.4f}s (no BFS precomputation!)")
    
    # Test state creation and action generation
    state = OrienteeringStateTraditional(problem)
    
    print(f"\nInitial state: {state.path}")
    print(f"Available actions: {len(state.get_available_actions())} nodes")
    
    # Test action speed
    start = time.perf_counter()
    test_iterations = 10000
    for _ in range(test_iterations):
        actions = state.get_available_actions()
    elapsed = time.perf_counter() - start
    
    print(f"\nPerformance test:")
    print(f"  {test_iterations} get_available_actions() calls: {elapsed:.3f}s")
    print(f"  Average: {(elapsed / test_iterations) * 1000:.4f}ms per call")