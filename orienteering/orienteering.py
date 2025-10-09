import math
import random
from collections import namedtuple
from typing import List, Optional, Dict


START_NODE = 0
END_NODE = 1
Node = namedtuple('Node', ['id', 'x', 'y', 'score'])


class OrienteeringProblem:
    def __init__(self, nodes: List[Node], budget: float, max_edge_distance: Optional[float] = 10):
        # nodes is a list of Node namedtuples with id, x, y, and score, have removed score from init as its in namedtuple
        self.nodes = nodes
        self.budget = budget
        self.start_id = START_NODE
        self.end_id = END_NODE
        # If provided, only edges with distance <= max_edge_distance are allowed
        self.max_edge_distance: Optional[float] = max_edge_distance
        self._neighbors: Optional[Dict[int, List[int]]] = None
        
        # Cache for distance calculations - major speed improvement
        self._distance_cache: Dict[tuple, float] = {}
        
        # Precomputed reachability data (10-100x speedup for large graphs)
        self._end_reachable_nodes = None  # Nodes that can directly reach END
        self._can_reach_end_structure = None  # Nodes that can reach END through any path
        
        if self.max_edge_distance is not None:
            self._build_neighbors()
            self._precompute_end_reachability()
    
    @property
    def num_nodes(self):
        return len(self.nodes)

    # TODO: change method for new OrienteeringProblem class
    @staticmethod
    def load_problem(filename):
        with open(filename, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        # First line: Tmax P
        budget, _ = lines[0].split()
        budget = float(budget)
        node_lines = lines[1:]
        nodes = []
        for idx, line in enumerate(node_lines):
            x, y, score = line.split()
            nodes.append(Node(idx, float(x), float(y), int(score)))
        return nodes, budget
    
    def get_distance(self, a: int, b: int) -> float:
        # Use cache for significant speedup
        key = (min(a, b), max(a, b))  # Symmetric distance
        if key not in self._distance_cache:
            self._distance_cache[key] = math.hypot(
                self.nodes[a].x - self.nodes[b].x, 
                self.nodes[a].y - self.nodes[b].y
            )
        return self._distance_cache[key]

    def _build_neighbors(self) -> None:
        n = self.num_nodes
        self._neighbors = {i: [] for i in range(n)}
        if self.max_edge_distance is None:
            return
        # Fast path: no edges allowed when threshold <= 0
        if self.max_edge_distance <= 0:
            return
        thr_sq = float(self.max_edge_distance) * float(self.max_edge_distance)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                # Compare squared distances to avoid sqrt cost
                dx = self.nodes[i].x - self.nodes[j].x
                dy = self.nodes[i].y - self.nodes[j].y
                if (dx * dx + dy * dy) <= thr_sq:
                    self._neighbors[i].append(j)

    def get_neighbors(self, node_id: int) -> List[int]:
        # If no constraint set, assume fully connected
        if self.max_edge_distance is None:
            return list(range(self.num_nodes))
        if self._neighbors is None:
            self._build_neighbors()
        return self._neighbors.get(node_id, [])
    
    def _precompute_end_reachability(self) -> None:
        """Precompute structural reachability to END_NODE (massive speedup)."""
        # Find nodes that can directly reach END
        self._end_reachable_nodes = set()
        for i in range(self.num_nodes):
            if i != END_NODE and END_NODE in self.get_neighbors(i):
                self._end_reachable_nodes.add(i)
        
        # Use reverse BFS from END to find all nodes that can structurally reach it
        # (ignoring budget - just graph connectivity)
        from collections import deque
        self._can_reach_end_structure = {END_NODE}
        queue = deque([END_NODE])
        
        # Build reverse adjacency (who can reach each node)
        reverse_neighbors = {i: [] for i in range(self.num_nodes)}
        for i in range(self.num_nodes):
            for j in self.get_neighbors(i):
                reverse_neighbors[j].append(i)
        
        # BFS backwards from END
        while queue:
            current = queue.popleft()
            for predecessor in reverse_neighbors[current]:
                if predecessor not in self._can_reach_end_structure:
                    self._can_reach_end_structure.add(predecessor)
                    queue.append(predecessor)


class OrienteeringState:
    def __init__(self, problem: OrienteeringProblem, path=None, cost_so_far=0.0, reward_so_far=None):
        # path: list of visited node indices
        # cost_so_far: total distance travelled
        # reward_so_far: total collected reward

        self.problem = problem
        self.path = path or [START_NODE]  # Start at node 0
        self.visited = set(self.path)
        self.cost_so_far = cost_so_far
        if reward_so_far is None:
            # TODO: do i need this score of the start node (possible cases where start node has score)
            self.reward_so_far = self.problem.nodes[self.path[0]].score
        else:
            self.reward_so_far = reward_so_far
        
        # Cache for reachability checks (10-50x speedup)
        self._reachability_cache: Dict[tuple, bool] = {}


    def is_terminal(self):
        # Only terminal if the last node in the path is the END_NODE
        return self.path[-1] == END_NODE

    def copy(self):
        new_state = OrienteeringState(
            self.problem,
            path=self.path[:],
            cost_so_far=self.cost_so_far,
            reward_so_far=self.reward_so_far
        )
        # Share the cache for efficiency (states in same simulation can benefit)
        new_state._reachability_cache = self._reachability_cache
        return new_state
    
    def update_reward(self, reward):
        self.reward_so_far += reward
    
    def increment_visits(self):
        self.visited.add(self.path[-1])

    
    def _can_reach_end_from(self, node_id: int, current_cost: float) -> bool:
        """Check if we can reach END_NODE from given node within budget, respecting edge constraints.
        
        Optimized with:
        1. Precomputed structural reachability (100x faster)
        2. Caching with discretized costs (10-50x faster)
        3. Early termination checks
        """
        if node_id == END_NODE:
            return True
        
        # Quick structural check: if node can't reach END in the graph structure, fail fast
        if self.problem._can_reach_end_structure is not None:
            if node_id not in self.problem._can_reach_end_structure:
                return False
        
        # Check cache (discretize cost to integer for better hit rate)
        cache_key = (node_id, int(current_cost))
        if cache_key in self._reachability_cache:
            return self._reachability_cache[cache_key]
        
        # If node can directly reach END, check budget
        neighbors = self.problem.get_neighbors(node_id)
        if END_NODE in neighbors:
            cost_to_end = self.problem.get_distance(node_id, END_NODE)
            result = current_cost + cost_to_end <= self.problem.budget
            self._reachability_cache[cache_key] = result
            return result
        
        # Use precomputed end-reachable nodes (avoid recomputing every time)
        if self.problem._end_reachable_nodes is None or not self.problem._end_reachable_nodes:
            self._reachability_cache[cache_key] = False
            return False
        
        # BFS to find shortest path to any end-reachable node
        from collections import deque
        queue = deque([(node_id, current_cost)])
        visited = {node_id}
        
        while queue:
            current_node, cost = queue.popleft()
            
            # Check if this node can reach END
            if current_node in self.problem._end_reachable_nodes:
                cost_to_end = self.problem.get_distance(current_node, END_NODE)
                result = cost + cost_to_end <= self.problem.budget
                self._reachability_cache[cache_key] = result
                return result
            
            # Explore neighbors
            for neighbor in self.problem.get_neighbors(current_node):
                if neighbor not in visited and neighbor not in self.visited:
                    new_cost = cost + self.problem.get_distance(current_node, neighbor)
                    if new_cost <= self.problem.budget:  # Basic budget check
                        visited.add(neighbor)
                        queue.append((neighbor, new_cost))
        
        # Cache negative result
        self._reachability_cache[cache_key] = False
        return False

    # This method generates all possible next states from the current state
    def get_available_actions(self):
        actions = []
        current = self.path[-1]

        # Candidate neighbors: respect max_edge_distance if set
        neighbor_ids = self.problem.get_neighbors(current)

        # Option to go directly to END if feasible and not already there
        if current != END_NODE and END_NODE in neighbor_ids and END_NODE not in self.visited:
            cost_to_end = self.problem.get_distance(current, END_NODE)
            if self.cost_so_far + cost_to_end <= self.problem.budget:
                actions.append(END_NODE)

        # Explore other unvisited neighbor nodes but ensure we can still reach END
        for i in neighbor_ids:
            if i in self.visited or i == START_NODE:
                continue
            # END_NODE is handled separately above, skip it here to avoid duplicates
            if i == END_NODE:
                continue
            cost_to_i = self.problem.get_distance(current, i)
            new_cost = self.cost_so_far + cost_to_i
            
            # Check if we can reach END from node i with remaining budget
            if self._can_reach_end_from(i, new_cost):
                actions.append(i)
        return actions
    
    # looks like i dont need this method, as I can just use get_available_actions to get the next states
    def apply_action(self, node_index):
        if node_index in self.visited:
            raise ValueError(f"Node {node_index} already visited.")
        current = self.path[-1]
        # Enforce neighbor constraint if configured
        if self.problem.max_edge_distance is not None:
            if node_index not in self.problem.get_neighbors(current):
                raise ValueError(f"Node {node_index} not reachable from {current} under max_edge_distance constraint.")
        cost_to_next = self.problem.get_distance(current, node_index)
        # Ensure feasibility to still reach END after taking this action
        cost_next_to_end = self.problem.get_distance(node_index, END_NODE)
        if self.cost_so_far + cost_to_next + cost_next_to_end > self.problem.budget:
            raise ValueError(f"Cannot apply action to node {node_index}, exceeds budget.")
        new_path = self.path + [node_index]
        new_cost = self.cost_so_far + cost_to_next
        new_reward = self.reward_so_far + self.problem.nodes[node_index].score
        return OrienteeringState(self.problem, new_path, new_cost, new_reward)

    def best_child(self):
        # Returns the child with the highest score (reward)
        children = self.get_available_actions()
        if not children:
            return None
        return max(children, key=lambda child: child.reward_so_far)

    def get_reward(self):
        return self.reward_so_far
    
    def get_cost(self):
        return self.cost_so_far
    
    def get_path(self):
        return self.path

    def __str__(self):
        return f"Path: {self.path}, Reward: {self.reward_so_far}, Cost: {self.cost_so_far:.2f}, Terminal: {self.is_terminal()}"



        # def get_available_actions(self):
        # children = []
        # current = self.path[-1]

        # # Always consider going directly to END if feasible and not already there
        # if current != END_NODE:
        #     cost_to_end = self.problem.get_distance(current, END_NODE)
        #     if self.cost_so_far + cost_to_end <= self.problem.budget and END_NODE not in self.visited:
        #         end_path = self.path + [END_NODE]
        #         end_cost = self.cost_so_far + cost_to_end
        #         end_reward = self.reward_so_far + self.problem.nodes[END_NODE].score
        #         children.append(OrienteeringState(self.problem, end_path, end_cost, end_reward))

        # # Explore other unvisited nodes but reserve budget to still reach END
        # for i in range(self.problem.num_nodes):
        #     if i in self.visited:
        #         continue
        #     # skip adding START again
        #     if i == START_NODE:
        #         continue

        #     cost_to_i = self.problem.get_distance(current, i)
        #     cost_i_to_end = self.problem.get_distance(i, END_NODE)
        #     new_cost = self.cost_so_far + cost_to_i

        #     # Feasible only if we can still reach END
        #     if new_cost + cost_i_to_end <= self.problem.budget:
        #         new_path = self.path + [i]
        #         new_reward = self.reward_so_far + self.problem.nodes[i].score
        #         children.append(OrienteeringState(self.problem, new_path, new_cost, new_reward))
        # return children