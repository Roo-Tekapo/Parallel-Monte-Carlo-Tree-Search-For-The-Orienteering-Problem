from abc import ABC, abstractmethod
from collections import defaultdict
import math

"""
Monte Carlo Tree Search Algorithm
"""
class MCTS:

    "Initialise the tree"
    def __init__(self, domain, exploration_weight=1):
        self.Q = defaultdict(int)  # total reward of each node
        self.N = defaultdict(int)  # total visit count for each node
        self.children = dict()  # children of each node
        self.exploration_weight = exploration_weight # exploration exploitation constant
        self.domain = domain # custom domain

    "Choose the best successor of node. (Choose a move in the domain)"
    def choose(self, node):
        
        if node.is_terminal():
            raise RuntimeError(f"choose called on terminal node {node}")

        if node not in self.children:
            return node.find_random_child()

        def score(n):
            if self.N[n] == 0:
                return float("-inf")  # avoid unseen moves
            return self.Q[n] / self.N[n]  # average reward

        return max(self.children[node], key=score)

    "Make the tree one layer better. (Train for one iteration.)"
    def do_rollout(self, node):
        path = self._select(node)
        leaf = path[-1]
        self._expand(leaf)
        reward = self._simulate(leaf)
        self._backpropagate(path, reward)

    "Find an unexplored descendent of 'node'"
    def _select(self, node):
        
        path = []
        while True:
            path.append(node)
            if node not in self.children or not self.children[node]:
                # node is either unexplored or terminal
                return path
            unexplored = self.children[node] - self.children.keys()
            if unexplored:
                n = unexplored.pop()
                path.append(n)
                return path
            node = self._uct_select(node)  # descend a layer deeper

    "Update the 'children' dictionary with the children of 'node'"
    def _expand(self, node):
        if node in self.children:
            return  # already expanded
        self.children[node] = node.find_children()

    "Returns the reward for a random simulation (to completion) of 'node'"
    def _simulate(self, node):
        origin = node
        while True:
            if node.is_terminal():
                reward = node.get_reward(origin)
                return reward
            node = node.find_random_child()

    "Send the reward back up to the ancestors of the leaf"
    def _backpropagate(self, path, reward):
        for node in reversed(path):
            self.N[node] += 1
            self.Q[node] += reward
            reward = node.set_reward(reward)

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
    
    """
    Export current tree and information for each nested node in the format of:
    "tree": {
        "attributes": {
            "board": {
                "data": [
                ],
                "type":
            },
            "reward":
            "visits":
        },
        "children":
        "name":
    }
    """
    def export_to_format(self, mcts, node):
        exported_data = {'name': node.__str__(), 'attributes': {'reward': mcts.Q[node], 'visits': mcts.N[node], 'board':{'type': self.domain.__class__.__name__, 'data': node.display()}}}
        for key in mcts.children.keys():
            if node.__str__() == key.__str__():
                exported_data['children'] = []
                for child in mcts.children[key]:
                    if (self.N[child] > 0):
                        exported_data['children'].append(self.export_to_format(mcts, child))
                break  # Stop searching once we've found the node
        return exported_data
    
    "Define the amount of iterations to complete"
    def iterate(self, iterations):
        for _ in range(iterations):
            self.do_rollout(self.domain)

    "Set the exploration exploitation constant"
    def setConstant(self, constant):
        self.exploration_weight = constant

    """
    Append metadata to the exported tree in the format:

    "metadata": {
        "rewardMAX":
        "rewardMIN":
        "visitsMAX":
        "visitsMIN":
    }
    """
    def export(self):
        data = {}
        data["tree"] = self.export_to_format(self, next(iter(self.children.keys())))
        data["metadata"] = {'rewardMIN': min(self.Q.values()), 'rewardMAX': max(self.Q.values()), 'visitsMIN': min(self.N.values()), 'visitsMAX': max(self.N.values())}
        return data


"""
Abstract Node class that all domains but inherit from
"""
class Node(ABC):

    # A set of all possible child states
    @abstractmethod
    def find_children(self):
        return set()

    # Returns a random child state (for simulation)
    @abstractmethod
    def find_random_child(self):
        return None

    # Return true if no possible further children
    @abstractmethod
    def is_terminal(self):
        return True

    # Returns the reward for the terminal state (e.g. 1 for win, 0 for loss)
    # Origin is the node that the simulation is running from, used to determine
    # if win or loss from that node's perspective
    # Value should be normalised between 0-1 to get consistancy across domains
    @abstractmethod
    def get_reward(self, origin):
        return 0
    
    # For inversing when backpropogating if necessary (e.g. 1 - reward for 2 player games)
    @abstractmethod
    def set_reward(self, reward):
        return reward
    
    # Optional display function (e.g. ["X", "O", "O", "X", "O", " ", "X", "O", " "])
    @abstractmethod
    def display(self):
        return None

    # Nodes must be hashable
    @abstractmethod
    def __hash__(self):
        return 123456789

    # Nodes must be comparable
    @abstractmethod
    def __eq__(node1, node2):
        return True