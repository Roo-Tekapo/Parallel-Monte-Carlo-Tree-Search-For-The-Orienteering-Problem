import random
import math

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from .mcts_node import MCTSNode


class MCTSSingleThread:
    def __init__(self, problem: OrienteeringProblem, iterations, exploration_constant = math.sqrt(2), epsilon: float = 0.05):
        self.problem = problem
        self.iterations = iterations
        self.const = exploration_constant
        self.epsilon = epsilon

        self.root = None  # Will be set to MCTSNode with initial state
        self.iteration = 0 # Track current iteration

    # Step 1: Selection
    def tree_policy(self, node: MCTSNode) -> MCTSNode:
        # traverse the tree until a leaf node is reached
        current = node
        while not current.state.is_terminal():
            if not current.is_fully_expanded():
                return self.expand(current)
            elif current.children: # if node has children, select one using UCT
                current = current.uct_best_child(self.const, self.epsilon)
            else:
                break # if no children, return current node
        return current
    
    # Step 2: Expansion
    def expand(self, node: MCTSNode) -> MCTSNode:
        action = node.untried_actions.pop()
        new_state = node.state.apply_action(action)
        child_node = MCTSNode(new_state, parent=node)
        node.children.append(child_node)
        return child_node
    
    # Step 3: Simulation (I ensure state is an OrienteeringState)
    # def simulate(self, state: OrienteeringState) -> float:
    #     current = state.copy()
    #     while not current.is_terminal():
    #         actions = current.get_available_actions()
    #         if not actions:
    #             break
    #         # Bias rollout: pick node with best score/distance ratio
    #         action = max(actions, key=lambda a: current.problem.nodes[a].score / 
    #                                     (1 + current.problem.get_distance(current.path[-1], a)))
    #         current = current.apply_action(action)
    #     return current.get_reward()

    def simulate(self, state: OrienteeringState) -> float:
        current = state.copy()
        while not current.is_terminal():
            # print("Current state:", current.path)
            actions = current.get_available_actions()
            # print("Available actions:", actions)
            if not actions:
                break
            action = random.choice(actions)
            current = current.apply_action(action)
        # print("Final state:", current.path)
        return current.get_reward()

    # def simulate(self, state: OrienteeringState) -> float:
        # current = state.copy()
        # while not current.is_terminal():
        #     actions = current.get_available_actions()
        #     # Print the next node index for each action
        #     next_nodes = [a.path[-1] for a in actions]
        #     print("Available actions from", current.path, ":", next_nodes)
        #     if not actions:
        #         # try force moving to END if possible from current
        #         if current.path[-1] != self.problem.end_id:
        #             cost_to_end = current.problem.get_distance(current.path[-1], self.problem.end_id)
        #             if current.cost_so_far + cost_to_end <= self.problem.budget:
        #                 # apply move to END
        #                 current = OrienteeringState(
        #                     current.problem,
        #                     path=current.path + [self.problem.end_id],
        #                     cost_so_far=current.cost_so_far + cost_to_end,
        #                     reward_so_far=current.reward_so_far + current.problem.nodes[self.problem.end_id].score,
        #                 )
        #                 break
        #         break
        #     current = random.choice(actions)
        # return current.get_reward()


        # #  If not at END_NODE, force add it (if feasible) --- TODO not sure if this is the best idea will double check
        # if current.path[-1] != self.problem.end_id:
        #     cost_to_end = current.problem.get_distance(current.path[-1], self.problem.end_id)
        #     if current.cost_so_far + cost_to_end <= self.problem.budget:
        #         current.path.append(self.problem.end_id)
        #         current.cost_so_far += cost_to_end
        #         current.reward_so_far += self.problem.nodes[self.problem.end_id].score
        # return current.reward_so_far # current.get_reward()

        # if current.path[-1] != self.problem.end_id:
        #     cost_to_end = self.problem.get_distance(current.path[-1], self.problem.end_id)
        #     if current.cost_so_far + cost_to_end <= problem.budget:
        #         current.path.apply_action(self.problem.end_id)
        # return current.get_reward()

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
            self.root = MCTSNode(self.root_state)
            self.iteration = 0
        return self.root

    def reset(self):
        self.root = None
        self.iteration = 0

    def step(self):
            """
            Perform exactly one MCTS iteration (selection→expansion→simulation→backprop)
            and return a small event dict useful for visualization.
            """
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
        root = MCTSNode(root_state)

        for _ in range(self.iterations):
            # Selection and Expansion
            leaf = self.tree_policy(root)
            # Simulation
            reward = self.simulate(leaf.state)
            # Backpropagation
            self.backpropagate(leaf, reward)

        # Print visit stats for all nodes in the tree (DFS)
        print("\nNode stats (visits and average reward):")
        def print_tree(node, depth=0, visited=None):
            if visited is None:
                visited = set()
            if node in visited:
                return
            visited.add(node)
            indent = "  " * depth
            try:
                node_id = node.state.path[-1]
            except Exception:
                node_id = None
            avg = (node.total_reward / node.visits) if node.visits else 0.0
            print(f"{indent}Node {node_id}: visits={node.visits}, avg_reward={avg:.3f}")
            for child in node.children:
                print_tree(child, depth+1, visited)
        print_tree(root)

        best_leaf = self.best_descendant(root)
        return best_leaf.state

if __name__ == "__main__":
    nodes, budget = OrienteeringProblem.load_problem(
        # "OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_85.txt"
        "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    )

    problem = OrienteeringProblem(nodes, budget)

    solver = MCTSSingleThread(problem, iterations=10000)
    best_state = solver.run()

    print("Best path:", best_state.get_path())
    print("Total reward:", best_state.get_reward())
    print("Total cost:", best_state.get_cost())




# python3 -m MCTS.mcts_base