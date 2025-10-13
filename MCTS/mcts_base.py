import random
import math

from orienteering.orienteering import OrienteeringProblem, OrienteeringState, END_NODE
from .mcts_node import MCTSNode


class MCTSSingleThread:
    def __init__(self, problem: OrienteeringProblem, iterations, exploration_constant = math.sqrt(2), epsilon: float = 0.00, traditional_mcts: bool = False, soft_end_bias: bool = False, bias_decay_factor: float = 10.0):
        self.problem = problem
        self.iterations = iterations
        self.const = exploration_constant
        self.epsilon = epsilon
        self.traditional_mcts = traditional_mcts  # Use traditional MCTS approach
        self.soft_end_bias = soft_end_bias  # Use soft bias toward end node
        self.bias_decay_factor = bias_decay_factor  # Controls how aggressively bias increases

        self.root = None  # Will be set to MCTSNode with initial state
        self.iteration = 0 # Track current iteration

    # Step 1: Selection
    def tree_policy(self, node: MCTSNode) -> MCTSNode:
        # traverse the tree until a leaf node is reached
        current = node
        while not current.state.is_terminal():
            # Check if this is a dead-end node (no actions available, not terminal)
            if current.is_dead_end:
                # Dead-end node: cannot expand, return for simulation
                return current
            
            if not current.is_fully_expanded():
                # Has untried actions, expand one
                return self.expand(current)
            elif current.children:
                # Fully expanded with children, select best child using UCT
                current = current.uct_best_child(self.const, self.epsilon)
            else:
                # Fully expanded but no children - shouldn't happen after dead-end check
                # but return it anyway for simulation
                return current
        return current
    
    # Step 2: Expansion
    def expand(self, node: MCTSNode) -> MCTSNode:
        action = node.untried_actions.pop()
        new_state = node.state.apply_action(action, traditional_mcts=self.traditional_mcts)
        child_node = MCTSNode(new_state, parent=node, traditional_mcts=self.traditional_mcts)
        node.children.append(child_node)
        return child_node

    def _calculate_end_bias_probability(self, current_state: OrienteeringState) -> float:
        """Calculate probability of biasing toward end node based on remaining budget"""
        if not self.soft_end_bias:
            return 0.0
        
        current_node = current_state.path[-1]
        if current_node == END_NODE:
            return 0.0  # Already at end
        
        # Calculate cost to reach end from current position
        cost_to_end = current_state.problem.get_distance(current_node, END_NODE)
        
        # Calculate remaining budget after reaching end
        remaining_budget = current_state.problem.budget - current_state.cost_so_far - cost_to_end
        
        # If we can't reach end, return maximum bias
        if remaining_budget < 0:
            return 0.9
        
        # Budget pressure: how much of total budget we've used
        budget_used_ratio = current_state.cost_so_far / current_state.problem.budget
        
        # Combine remaining budget and budget pressure for smarter bias
        # Start biasing earlier when we've used significant portion of budget
        if budget_used_ratio > 0.6:  # Start biasing after using 60% of budget
            # Stronger bias as we approach budget limit
            pressure_bias = (budget_used_ratio - 0.6) / 0.4  # Scale 0.6-1.0 to 0.0-1.0
            remaining_bias = math.exp(-remaining_budget / self.bias_decay_factor)
            
            # Take the maximum of pressure-based and remaining-budget-based bias
            bias_probability = max(pressure_bias * 0.6, remaining_bias)
            return min(bias_probability, 0.9)
        else:
            # Light bias in early stages
            bias_probability = math.exp(-remaining_budget / (self.bias_decay_factor * 2))
            return min(bias_probability, 0.3)  # Cap early bias at 30%
    
    def _choose_biased_action(self, state, actions):
        """Choose action with bias toward END_NODE and budget reservation"""
        if END_NODE not in actions:
            # Filter actions that would leave enough budget to reach END_NODE
            if self.soft_end_bias:
                safe_actions = []
                current_node = state.path[-1]
                
                for action in actions:
                    # Calculate total cost if we take this action then go to END_NODE
                    cost_to_action = state.problem.get_distance(current_node, action)
                    cost_action_to_end = state.problem.get_distance(action, END_NODE)
                    total_future_cost = state.cost_so_far + cost_to_action + cost_action_to_end
                    
                    if total_future_cost <= state.problem.budget:
                        safe_actions.append(action)
                
                # Use safe actions if available, otherwise fall back to all actions
                if safe_actions:
                    actions = safe_actions
            
            return random.choice(actions)
        
        budget_used_ratio = state.cost_so_far / state.problem.budget
        
        # Very strong bias when budget > 80% - almost always go to END_NODE
        if budget_used_ratio > 0.8:
            if random.random() < 0.95:  # 95% chance
                return END_NODE
        
        # Strong bias when budget > 70%
        elif budget_used_ratio > 0.7:
            if random.random() < 0.7:  # 70% chance
                return END_NODE
        
        # Check if we should reserve budget for END_NODE
        current_node = state.path[-1]
        cost_to_end = state.problem.get_distance(current_node, END_NODE)
        
        # If we're close to budget limit, strongly prefer END_NODE
        if state.cost_so_far + cost_to_end > state.problem.budget * 0.9:
            if random.random() < 0.9:  # 90% chance to go to end
                return END_NODE
        
        # Calculate bias probability for moderate budget usage
        bias_prob = self._calculate_end_bias_probability(state)
        
        if bias_prob > 0:
            # Weighted selection: give END_NODE higher probability
            choices = []
            weights = []
            
            # Add END_NODE with bias weight
            choices.append(END_NODE)
            weights.append(bias_prob * 5.0)  # Strong bias weight
            
            # Add other actions with normal weight, but filter unsafe ones
            other_actions = [a for a in actions if a != END_NODE]
            
            if self.soft_end_bias:
                # Only consider actions that leave budget for END_NODE
                safe_other_actions = []
                for action in other_actions:
                    cost_to_action = state.problem.get_distance(current_node, action)
                    cost_action_to_end = state.problem.get_distance(action, END_NODE)
                    total_future_cost = state.cost_so_far + cost_to_action + cost_action_to_end
                    
                    if total_future_cost <= state.problem.budget:
                        safe_other_actions.append(action)
                
                other_actions = safe_other_actions if safe_other_actions else other_actions
            
            for action in other_actions:
                choices.append(action)
                weights.append(1.0)
            
            # Weighted random selection
            if not weights:
                return END_NODE  # Safety fallback
                
            total_weight = sum(weights)
            r = random.random() * total_weight
            cumulative = 0
            for i, weight in enumerate(weights):
                cumulative += weight
                if r <= cumulative:
                    return choices[i]
        
        return random.choice(actions)

    def simulate(self, state: OrienteeringState) -> float:
        current = state.copy()
        max_simulation_steps = 1000  # Prevent infinite loops
        steps = 0
        
        while not current.is_terminal() and steps < max_simulation_steps:
            steps += 1
            actions = current.get_available_actions(traditional_mcts=self.traditional_mcts)
            if not actions:
                if self.traditional_mcts:
                    # Traditional MCTS: No forcing, just return current reward
                    break
                else:
                    # Conservative approach: try to force completion to END_NODE if possible
                    current_node = current.path[-1]
                    if current_node != END_NODE:
                        # Check if we can reach END_NODE directly within budget
                        cost_to_end = current.problem.get_distance(current_node, END_NODE)
                        if current.cost_so_far + cost_to_end <= current.problem.budget:
                            # Force move to END_NODE to complete the path
                            try:
                                current = current.apply_action(END_NODE, traditional_mcts=self.traditional_mcts)
                                break
                            except ValueError:
                                # Can't apply action, return penalized reward
                                pass
                    # Severe penalty for incomplete path - make it much worse than any complete path
                    return current.get_reward() * 0.1  # 90% penalty for not reaching end
            else:
                # Use biased action selection if soft_end_bias is enabled
                if self.soft_end_bias:
                    action = self._choose_biased_action(current, actions)
                else:
                    action = random.choice(actions)
                current = current.apply_action(action, traditional_mcts=self.traditional_mcts)
        
        # Add completion bonus if we reached the END_NODE
        reward = current.get_reward()
        if current.is_terminal():
            reward += 100  # Bonus for completing the path
        return reward

    # Step 4: Backpropagation
    def backpropagate(self, node: MCTSNode, reward: float):
        while node is not None:
            node.visits += 1
            node.total_reward += reward
            node = node.parent
        
    def best_descendant(self, node: MCTSNode) -> MCTSNode:
        current = node
        while current.children:
            current = max(
                current.children, 
                key=lambda c: c.total_reward / c.visits if c.visits > 0 else float("-inf")
            )
        return current

    # For the visualization step-by-step execution
    def initialize_root(self):
        if self.root is None:
            self.root_state = OrienteeringState(self.problem)
            self.root = MCTSNode(self.root_state, traditional_mcts=self.traditional_mcts)
            self.iteration = 0
        return self.root

    def reset(self):
        self.root = None
        self.iteration = 0

    def step(self):
            # Perform exactly one MCTS iteration (selection→expansion→simulation→backprop)
            # and return a small event dict useful for visualization.
            root = self.initialize_root()

            # Selection / Expansion
            leaf = self.tree_policy(root)

            # produce selection path (root -> leaf)
            selection_path = []
            n = leaf
            while n is not None:
                selection_path.append(n)
                n = n.parent
            selection_path = list(reversed(selection_path))

            # Simulation
            reward = self.simulate(leaf.state)

            # Backpropagation
            self.backpropagate(leaf, reward)

            self.iteration += 1

            # TODO: unpdate based on fixed best_descendant lo
            # best child of root (for final result / highlighting)
            best_child = None
            if root.children:
                # guard division by zero
                def score(c): return c.total_reward / c.visits if c.visits > 0 else float("-inf")
                best_child = max(root.children, key=score)

            event = {
                "iteration": self.iteration,
                "selection_path": selection_path,  # list of MCTSNode objects
                "leaf": leaf,
                "reward": reward,
                "updated_nodes": selection_path,   # shorthand; nodes that changed
                "best_child": best_child
            }
            return event

    # Main MCTS run method
    def run(self):
        root_state = OrienteeringState(self.problem)
        root = MCTSNode(root_state, traditional_mcts=self.traditional_mcts)

        for _ in range(self.iterations):
            # Selection and Expansion
            leaf = self.tree_policy(root)
            # Simulation
            reward = self.simulate(leaf.state)
            # Backpropagation
            self.backpropagate(leaf, reward)

        # Print visit stats for all nodes in the tree (DFS)
        # print("\nNode stats (visits and average reward):")
        # def print_tree(node, depth=0, visited=None):
        #     if visited is None:
        #         visited = set()
        #     if node in visited:
        #         return
        #     visited.add(node)
        #     indent = "  " * depth
        #     try:
        #         node_id = node.state.path[-1]
        #     except Exception:
        #         node_id = None
        #     avg = (node.total_reward / node.visits) if node.visits else 0.0
        #     print(f"{indent}Node {node_id}: visits={node.visits}, avg_reward={avg:.3f}")
        #     for child in node.children:
        #         print_tree(child, depth+1, visited)
        # print_tree(root)

        best_leaf = self.best_descendant(root)
        return best_leaf.state

if __name__ == "__main__":
    nodes, budget = OrienteeringProblem.load_problem(
        # "OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_85.txt"
        "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
        # "OP_Benchmark_Set/set_1000_1/set_1000_1_30.txt"
        # "OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt"
        # "OP_Benchmark_Set\grid_patterns\grid_corners_b40.txt"
        # "OP_Benchmark_Set/parallel_friendly_v2/xlarge/xlarge_50x50_r0_104.txt"
        # "OP_Benchmark_Set/grid_patterns/grid_corners_b40.txt"
        # "OP_Benchmark_Set\parallel_friendly_v2\clustered\clustered_c4_s4_sp6_19.txt"
    )

    # Remove max_edge_distance constraint for traditional MCTS testing
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)

    # Enable traditional MCTS approach
    solver = MCTSSingleThread(problem, iterations=100000, traditional_mcts=False)
    best_state = solver.run()

    # Calculate raw reward by summing actual node scores
    raw_reward = sum(problem.nodes[node_id].score for node_id in best_state.get_path())
    
    print("Traditional MCTS Results:")
    print("Best path:", best_state.get_path())
    print("Normalized reward:", best_state.get_reward())
    print("Raw reward:", raw_reward)
    print("Total cost:", best_state.get_cost())
    print("Valid solution:", best_state.is_terminal())




# python3 -m MCTS.mcts_base