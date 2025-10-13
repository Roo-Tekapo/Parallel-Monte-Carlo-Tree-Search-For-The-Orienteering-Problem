import math
import random

from orienteering.orienteering import OrienteeringState, OrienteeringProblem

class single_thread_mcts:
    def __init__(self, problem):
        self.problem = problem
        self.root = OrienteeringState(problem)
        self.visited_nodes = set()
        self.children = {} # Maps node to its children
        # TODO: implement visit counts and rewards
        self.visit_counts = {} # Maps node to number of visits (not used)

    def run(self, iterations):
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
            if node in self.children and self.children[node]:
                # If node has children, select one using UCT
                node = self._uct_select(node)
            else:
                return path

    def _expand(self, node):
        if node in self.visited_nodes:
            return
        self.visited_nodes.add(node)
        children = node.get_available_actions()
        self.children[node] = children


    def _simulate(self, node):
        current = node.copy()
        while not current.is_terminal():
            actions = current.get_available_actions()
            if not actions:
                break
            current = random.choice(actions)
        return current.get_reward()

    def _backpropagate(self, path, reward):
        for node in reversed(path):
            OrienteeringState.update_reward(node, reward)
            OrienteeringState.increment_visits(node)
            reward = OrienteeringState.get_reward(node)

    # TODO: uct never reach :(

    "Select a child of node, balancing exploration & exploitation"
    def _uct_select(self, node):
        # All children of node should already be expanded:
        assert all(n in self.children for n in self.children[node])

        log_N_vertex = math.log(self.N[node])

        def uct(n):
            # Upper confidence bound for trees
            return self.Q[n] / self.N[n] + self.exploration_weight * math.sqrt(
                log_N_vertex / self.N[n]
            )

        return max(self.children[node], key=uct)


    def print_results(self):
        path = OrienteeringState.get_path(self.root)
        normalized_reward = OrienteeringState.get_reward(self.root)
        # Calculate raw reward by summing actual node scores
        raw_reward = sum(self.problem.nodes[node_id].score for node_id in path)
        
        print("Best path:", path)
        print("Normalized reward:", normalized_reward)
        print("Raw reward:", raw_reward)
        print("Total cost:", OrienteeringState.get_cost(self.root))



if __name__ == "__main__":
    # Example usage
    nodes, budget = OrienteeringProblem.load_problem(
        'OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_10.txt'
    )
    problem = OrienteeringProblem(nodes, budget)
    mcts_solver = single_thread_mcts(problem)
    mcts_solver.run(iterations=10)
    mcts_solver.print_results()