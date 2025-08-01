import math

from orienteering.orienteering import OrienteeringState

class single_thread_mcts:
    def __init__(self, problem):
        self.problem = problem
        self.root = OrienteeringState(problem)
        self.visited_nodes = set()

    def run(self, iterations=1000):
        for _ in range(iterations):
            path = self._select(self.root)
            leaf = path[-1]
            self._expand(leaf)
            reward = self._simulate(leaf)
            self._backpropagate(path, reward)

    def _select(self, node):
        path = []
        while True:
            path.append(node)
            if OrienteeringState.is_terminal(node) or not OrienteeringState.get_available_actions(node):
                return path
            node = OrienteeringState.best_child(node)

    def print_results(self):
        print("Best path:", OrienteeringState.get_path(self.root))
        print("Total reward:", OrienteeringState.get_reward(self.root))
        print("Total cost:", OrienteeringState.get_cost(self.root))

# if __name__ == "__main__":
#     # Example usage
#     nodes, budget = OrienteeringProblem.load_problem(
#         'OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_10.txt'
#     )
#     problem = OrienteeringProblem(nodes, budget)
#     mcts_solver = single_thread_mcts(problem)
#     mcts_solver.run(iterations=1000)
#     mcts_solver.print_results()