import random
import math

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from .mcts_node import MCTSNode


class MCTSSingleThread:
    def __init__(self, problem: OrienteeringProblem, iterations = 1000, exploration_constant = math.sqrt(2)):
        self.problem = problem
        self.iterations = iterations
        self.const = exploration_constant

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
        "OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_15.txt"
    )

    problem = OrienteeringProblem(nodes, budget)

    solver = MCTSSingleThread(problem, iterations=1000)
    best_state = solver.run()

    print("Best path:", best_state.get_path())
    print("Total reward:", best_state.get_reward())
    print("Total cost:", best_state.get_cost())
