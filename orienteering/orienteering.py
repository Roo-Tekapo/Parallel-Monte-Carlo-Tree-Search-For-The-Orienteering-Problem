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


    def is_terminal(self):
        # Only terminal if the last node in the path is the END_NODE
        return self.path[-1] == END_NODE
    
    def copy(self):
        return OrienteeringState(
            self.problem,
            path=self.path[:],
            cost_so_far=self.cost_so_far,
            reward_so_far=self.reward_so_far
        )
    
    def update_reward(self, reward):
        self.reward_so_far += reward
    
    def increment_visits(self):
        self.visited.add(self.path[-1])

    
    # This method generates all possible next states from the current state
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
    
    # looks like i dont need this method, as I can just use get_available_actions to get the next states
    def apply_action(self, node_index):
        if node_index in self.visited:
            raise ValueError(f"Node {node_index} already visited.")
        cost_to_next = self.problem.get_distance(self.path[-1], node_index)
        if self.cost_so_far + cost_to_next > self.problem.budget:
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


# if __name__ == "__main__":
#     nodes, budget = OrienteeringProblem.load_problem(
#         'OP_Benchmark_Set/tsiligirides_1/tsiligirides_problem_1_budget_10.txt'
#     )
#     problem = OrienteeringProblem(nodes, budget)
    
#     state = OrienteeringState(problem)
#     terminalNodes = [node for node in nodes if node.id == END_NODE]
#     print("Initial state:", state)
#     print("Terminal nodes:", terminalNodes)
    
    # print("Available actions:")
    # actions = state.get_available_actions()
    # for action in actions:
    #     print(action)




    # TODO: error in apply_action
    # if actions:
    #     print("\nApplying first action:")
    #     new_state = state.apply_action(actions[0])
    #     print("New state after applying action:")
    #     print(new_state)
    # else:
    #     print("No available actions from the initial state.")

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
