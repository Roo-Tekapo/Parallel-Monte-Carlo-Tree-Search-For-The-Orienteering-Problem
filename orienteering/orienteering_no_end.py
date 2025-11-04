"""
No-End-Node Orienteering Problem Implementation

This variant removes the requirement for an end node. The goal is to find the best path possible.
A path is terminal when:
1. The budget is exhausted (no more affordable moves)
2. All neighboring nodes have been visited (dead-end)

MCTS should terminate and return the best path once all iterations have run.

Key differences from traditional orienteering:
- No END_NODE constraint (but END_NODE constant exists for API compatibility)
- Terminal when budget runs out OR all neighbors visited
- Start node is still fixed (node 0)
- Maximizes reward collection within budget
"""

import math
from collections import namedtuple
from typing import List, Optional, Dict


START_NODE = 0
# END_NODE defined for API compatibility with MCTS implementations that reference it
# However, it's treated as a regular node in this variant (not a required destination)
END_NODE = 1  
Node = namedtuple('Node', ['id', 'x', 'y', 'score'])


class OrienteeringProblemNoEnd:
    """Orienteering problem without an end node requirement."""
    
    def __init__(self, nodes: List[Node], budget: float, max_edge_distance: Optional[float] = 1.42, 
                 normalize_rewards: bool = False):
        """
        Initialize orienteering problem without end node.
        
        Args:
            nodes: List of Node namedtuples with id, x, y, and score
            budget: Maximum distance/cost budget
            max_edge_distance: Maximum allowed edge distance (None for fully connected)
            normalize_rewards: Whether to normalize rewards for better UCT performance
        """
        self.nodes = nodes
        self.budget = budget
        self.start_id = START_NODE
        self.max_edge_distance: Optional[float] = max_edge_distance
        self._neighbors: Optional[Dict[int, List[int]]] = None
        
        # Mark as no-end variant for OR-Tools compatibility
        self.is_no_end_variant = True
        
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
            # Scale so the highest-value node has normalized score of 1.0
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


class OrienteeringStateNoEnd:
    """State for orienteering problem without end node requirement."""
    
    def __init__(self, problem: OrienteeringProblemNoEnd, path=None, cost_so_far=0.0, reward_so_far=None):
        """
        Initialize state.
        
        Args:
            problem: The orienteering problem instance
            path: List of visited node indices
            cost_so_far: Total distance travelled
            reward_so_far: Total collected reward
        """
        self.problem = problem
        self.path = path or [START_NODE]
        self.visited = set(self.path)
        self.cost_so_far = cost_so_far
        if reward_so_far is None:
            self.reward_so_far = self.problem.get_normalized_score(self.path[0])
        else:
            self.reward_so_far = reward_so_far

    def is_terminal(self):
        """
        Check if state is terminal.
        
        A state is terminal when:
        1. No available actions (budget exhausted or all neighbors visited)
        """
        return len(self.get_available_actions()) == 0

    def copy(self):
        """Create a copy of this state."""
        return OrienteeringStateNoEnd(
            self.problem,
            path=self.path[:],
            cost_so_far=self.cost_so_far,
            reward_so_far=self.reward_so_far
        )
    
    def get_available_actions(self, traditional_mcts=True):
        """
        Get available actions from current state.
        
        Args:
            traditional_mcts: Kept for API compatibility, not used (always True for no-end variant)
        
        Returns:
            List of node indices that can be visited next
        """
        actions = []
        current = self.path[-1]
        neighbor_ids = self.problem.get_neighbors(current)

        # Explore unvisited neighbor nodes within budget
        for i in neighbor_ids:
            if i in self.visited or i == START_NODE:
                continue
            
            cost_to_i = self.problem.get_distance(current, i)
            new_cost = self.cost_so_far + cost_to_i
            
            # Check if we can afford this move
            if new_cost <= self.problem.budget:
                actions.append(i)
        
        return actions
    
    def apply_action(self, node_index, traditional_mcts=True):
        """
        Apply an action to create a new state.
        
        Args:
            node_index: Node to move to
            traditional_mcts: Kept for API compatibility, not used (always True for no-end variant)
            
        Returns:
            New OrienteeringStateNoEnd after applying action
            
        Raises:
            ValueError: If action is invalid
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
        
        # Check if we can afford this move
        if new_cost > self.problem.budget:
            raise ValueError(f"Cannot apply action to node {node_index}, exceeds budget.")
        
        new_path = self.path + [node_index]
        new_reward = self.reward_so_far + self.problem.get_normalized_score(node_index)
        return OrienteeringStateNoEnd(self.problem, new_path, new_cost, new_reward)

    def get_reward(self):
        """Get total reward collected."""
        return self.reward_so_far
    
    def get_cost(self):
        """Get total cost (distance) used."""
        return self.cost_so_far
    
    def get_path(self):
        """Get the path taken."""
        return self.path

    def __str__(self):
        return f"Path: {self.path}, Reward: {self.reward_so_far:.4f}, Cost: {self.cost_so_far:.2f}, Terminal: {self.is_terminal()}"


# Convenience aliases for drop-in replacement
OrienteeringProblem = OrienteeringProblemNoEnd
OrienteeringState = OrienteeringStateNoEnd


if __name__ == "__main__":
    import time
    
    print("="*70)
    print("NO-END-NODE ORIENTEERING - Maximize Reward Within Budget")
    print("="*70)
    print("\nThis version removes the end node requirement.")
    print("Goal: Find the best path possible within budget constraints.")
    print("Terminal when: budget exhausted OR all neighbors visited.\n")
    
    # Load a test problem
    nodes, budget = OrienteeringProblemNoEnd.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    
    print(f"Problem: {len(nodes)} nodes, budget={budget}")
    
    # Time the initialization
    start = time.perf_counter()
    problem = OrienteeringProblemNoEnd(
        nodes, budget, 
        max_edge_distance=1.42, 
        normalize_rewards=True
    )
    init_time = time.perf_counter() - start
    
    print(f"Initialization time: {init_time:.4f}s")
    
    # Test state creation and action generation
    state = OrienteeringStateNoEnd(problem)
    
    print(f"\nInitial state: {state.path}")
    print(f"  Cost: {state.cost_so_far:.2f}/{problem.budget}")
    print(f"  Reward: {state.reward_so_far:.4f}")
    print(f"  Available actions: {len(state.get_available_actions())} nodes")
    print(f"  Terminal: {state.is_terminal()}")
    
    # Simulate a simple greedy path to demonstrate terminal conditions
    print("\n" + "="*70)
    print("Demonstrating terminal conditions with greedy simulation:")
    print("="*70)
    
    simulation_state = state.copy()
    steps = 0
    max_steps = 20
    
    while not simulation_state.is_terminal() and steps < max_steps:
        actions = simulation_state.get_available_actions()
        if not actions:
            break
        
        # Greedy: choose highest reward neighbor
        best_action = max(actions, key=lambda a: problem.nodes[a].score)
        simulation_state = simulation_state.apply_action(best_action)
        steps += 1
        
        print(f"Step {steps}: Moved to node {best_action}, "
              f"Cost: {simulation_state.cost_so_far:.2f}/{problem.budget}, "
              f"Reward: {simulation_state.reward_so_far:.4f}")
    
    print(f"\nFinal state: {simulation_state}")
    print(f"Stopped because: ", end="")
    if simulation_state.is_terminal():
        actions = simulation_state.get_available_actions()
        if len(actions) == 0:
            remaining_budget = problem.budget - simulation_state.cost_so_far
            if remaining_budget > 0:
                print(f"All reachable neighbors visited (dead-end)")
            else:
                print(f"Budget exhausted")
    else:
        print(f"Max steps reached (demo limit)")
    
    print(f"\nPath length: {len(simulation_state.path)} nodes")
    print(f"Budget used: {simulation_state.cost_so_far:.2f}/{problem.budget} ({100*simulation_state.cost_so_far/problem.budget:.1f}%)")
    print(f"Total reward: {simulation_state.reward_so_far:.4f}")
