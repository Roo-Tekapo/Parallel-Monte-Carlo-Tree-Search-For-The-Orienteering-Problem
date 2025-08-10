import math
import random
from collections import namedtuple
from typing import List


START_NODE = 0
END_NODE = 1
Node = namedtuple('Node', ['id', 'x', 'y', 'score'])


class OrienteeringProblem:
    def __init__(self, nodes: List[Node], budget: float):
        # nodes is a list of Node namedtuples with id, x, y, and score, have removed score from init as its in namedtuple
        self.nodes = nodes
        self.budget = budget
        self.start_id = START_NODE
        self.end_id = END_NODE
    
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
        return math.hypot(self.nodes[a].x - self.nodes[b].x, self.nodes[a].y - self.nodes[b].y)


# # TODO: test
# # Load nodes and budget from file - could change so a run method in mcts selects the file
# nodes, BUDGET = OrienteeringProblem.load_problem(
#     # r'OP_Benchmark_Set\Tsiligirides_1\tsiligirides_problem_1_budget_85.txt'
#     # r'OP_Benchmark_Set\test_OP_budget_30.txt'
#     r"OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_10.txt"
# )


class OrienteeringState:
    def __init__(self, problem: OrienteeringProblem, path=None, cost_so_far=0.0, reward_so_far=0.0):
        """
        path: list of visited node indices
        cost_so_far: total distance travelled
        reward_so_far: total collected reward
        """
        self.problem = problem
        self.path = path or [START_NODE]  # Start at node 0
        self.visited = set(self.path)
        self.cost_so_far = cost_so_far
        self.reward_so_far = reward_so_far

    def is_terminal(self):
        # Can't add any more nodes without exceeding budget
        for i in range(self.problem.num_nodes):
            if i not in self.visited:
                cost_to_next = self.problem.get_distance(self.path[-1], i)
                if self.cost_so_far + cost_to_next <= self.problem.budget:
                    return False
        return True
    
    def copy(self):
        return OrienteeringState(
            self.problem,
            path=self.path[:],
            cost_so_far=self.cost_so_far,
            reward_so_far=self.reward_so_far
        )

    def get_available_actions(self):
        children = []
        for i in range(self.problem.num_nodes):
            if i not in self.visited:
                cost_to_i = self.problem.get_distance(self.path[-1], i)
                new_cost = self.cost_so_far + cost_to_i
                if new_cost <= self.problem.budget:
                    new_path = self.path + [i]
                    new_reward = self.reward_so_far + self.problem.nodes[i].score # double check if score is correct
                    children.append(OrienteeringState(
                        self.problem, new_path, new_cost, new_reward))
        return children
    
    def apply_action(self, action):
        if action not in self.get_available_actions():
            raise ValueError(f"Action {action} is not available from state {self}")
        return OrienteeringState(
            self.problem,
            path=self.path + [action],
            cost_so_far=self.cost_so_far + self.problem.get_distance(self.path[-1], action),
            reward_so_far=self.reward_so_far + self.problem.nodes[action].score
        )
    
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


if __name__ == "__main__":
    nodes, budget = OrienteeringProblem.load_problem(
        'OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_10.txt'
    )
    problem = OrienteeringProblem(nodes, budget)
    # print(f"Loaded problem with {len(nodes)} nodes and budget {budget}")
    # for node in problem.nodes:
    #     print(f"Node {node.id}: ({node.x}, {node.y}), Score: {node.score}")

    state = OrienteeringState(problem)
    # print("path:", state.get_path())
    # print("cost:", state.get_cost())
    # print("reward:", state.get_reward())
    # print("Initial state:", state)
    # print("Is terminal:", state.is_terminal())
    print("Available actions:")
    actions = state.get_available_actions()
    for action in actions:
        print(action)


# class OrienteeringProblem:
#     def __init__(self, path=None, cost=0, score=0):
#         self.path = path or [START_NODE]
#         self.cost = cost
#         self.score = score

#     def copy(self):
#         return OrienteeringProblem(self.path[:], self.cost, self.score)

#     def is_terminal(self):
#         return self.path[-1] == END_NODE and len(self.path) > 1



    # def available_actions(self):
    #     visited = set(self.path)
    #     actions = []
    #     # print("Current path:", self.path, "with cost:", self.cost, "and score:", self.score)
    #     for i in range(len(nodes)):
    #         if i not in visited and i != START_NODE and i != END_NODE:
    #             # Check if we can visit this node and then reach END_NODE within budget
    #             next_cost = self.cost + getDistance(self.path[-1], i) + getDistance(i, END_NODE)
    #             if next_cost <= BUDGET:
    #                 actions.append(i)
    #     # Option to go directly to END_NODE if not already there
    #     if self.path[-1] != END_NODE:
    #         if self.cost + getDistance(self.path[-1], END_NODE) <= BUDGET:
    #             actions.append(END_NODE)
    #     return actions


# class OrienteeringProblem:
#     def __init__(self, nodes: List[Node], start_id: int, end_id: int, budget: float):
#         self.nodes = nodes
#         self.start_id = start_id
#         self.end_id = end_id
#         self.budget = budget
#         self.distance_matrix = self._compute_distances()