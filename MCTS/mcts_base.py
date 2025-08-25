import random
import math

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from .mcts_node import MCTSNode


class MCTSSingleThread:
    def __init__(self, problem: OrienteeringProblem, iterations = 1000, exploration_constant = math.sqrt(4)):
        self.problem = problem
        self.iterations = iterations
        self.const = exploration_constant

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
                current = current.uct_best_child(self.const)
            else:
                break # if no children, return current node
        return current
    
    # Step 2: Expansion
    def expand(self, node: MCTSNode) -> MCTSNode:
        new_state = node.untried_actions.pop()
        child_node = MCTSNode(new_state, parent=node)
        node.children.append(child_node)
        return child_node
    
    # Step 3: Simulation (I ensure state is an OrienteeringState)
    def simulate(self, state: OrienteeringState) -> float:
        current = state.copy()
        while not current.is_terminal():
            actions = current.get_available_actions()
            if not actions:
                break
            current = random.choice(actions)
        return current.get_reward()
    
    # Step 4: Backpropagation
    def backpropagate(self, node: MCTSNode, reward: float):
        while node is not None:
            node.visits += 1
            node.total_reward += reward
            node = node.parent
    
    def intialize_root(self):
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
        
        best = max(root.children, key=lambda c: c.total_reward / c.visits)
        return best.state
    

if __name__ == "__main__":
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_10.txt"
    )

    problem = OrienteeringProblem(nodes, budget)

    solver = MCTSSingleThread(problem, iterations=1000)
    best_state = solver.run()

    print("Best path:", best_state.get_path())
    print("Total reward:", best_state.get_reward())
    print("Total cost:", best_state.get_cost())




# python3 -m MCTS.mcts_base