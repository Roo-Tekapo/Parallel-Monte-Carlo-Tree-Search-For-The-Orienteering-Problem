import math
import random
from collections import namedtuple
from typing import List


START_NODE = 0
END_NODE = 1

Node = namedtuple('Node', ['id', 'x', 'y', 'score'])

# class Node:
#     def __init__(self, node_id: int, x: float, y: float, score: int):
#         self.id = node_id
#         self.x = x
#         self.y = y
#         self.score = score


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

# Load nodes and budget from file
nodes, BUDGET = load_problem(
    # r'OP_Benchmark_Set\Tsiligirides_1\tsiligirides_problem_1_budget_85.txt'
    # r'OP_Benchmark_Set\test_OP_budget_30.txt'
    r"OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_10.txt"
)

def getDistance(a, b):
    return math.hypot(nodes[a][0] - nodes[b][0], nodes[a][1] - nodes[b][1])

class State:
    def __init__(self, path=None, cost=0, score=0):
        self.path = path or [START_NODE]
        self.cost = cost
        self.score = score

    def copy(self):
        return State(self.path[:], self.cost, self.score)

    def is_terminal(self):
        return self.path[-1] == END_NODE and len(self.path) > 1


# class OrienteeringProblem:
#     def __init__(self, nodes: List[Node], start_id: int, end_id: int, budget: float):
#         self.nodes = nodes
#         self.start_id = start_id
#         self.end_id = end_id
#         self.budget = budget
#         self.distance_matrix = self._compute_distances()