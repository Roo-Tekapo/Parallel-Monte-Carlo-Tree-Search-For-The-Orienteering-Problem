import random
from typing import Set, Iterable

from MCTS.mcts_simple import MCTS
from orienteering.orienteering import OrienteeringProblem, OrienteeringState, START_NODE, END_NODE


class OrienteeringNode:
    """Adapter that makes OrienteeringState compatible with the MCTS.Node interface

    It wraps an `OrienteeringState` and implements the minimal methods expected
    by `MCTS` in `MCTS/mcts_simple.py` (find_children, find_random_child,
    is_terminal, reward, __hash__, __eq__). Rewards are normalized by the
    total obtainable score in the problem so they fall in [0,1].
    """

    def __init__(self, state: OrienteeringState):
        self.state = state
        # cache the maximum possible score (sum of all node scores) for reward normalization
        self._max_score = sum(n.score for n in state.problem.nodes) or 1

    def find_children(self) -> Set["OrienteeringNode"]:
        actions = self.state.get_available_actions()
        children = set()
        for a in actions:
            # use apply_action to create the resulting state
            try:
                child_state = self.state.apply_action(a)
            except Exception:
                # If apply_action fails for any reason, skip that action
                continue
            children.add(OrienteeringNode(child_state))
        return children

    def find_random_child(self):
        actions = self.state.get_available_actions()
        if not actions:
            return None
        a = random.choice(actions)
        return OrienteeringNode(self.state.apply_action(a))

    def is_terminal(self) -> bool:
        return self.state.is_terminal()

    def reward(self) -> float:
        # Only called for terminal nodes by the MCTS implementation.
        raw = self.state.get_reward()
        return max(0.0, min(1.0, raw / self._max_score))

    def __hash__(self):
        # Use the path tuple to uniquely identify a node in the tree
        return hash(tuple(self.state.path))

    def __eq__(self, other):
        if not isinstance(other, OrienteeringNode):
            return False
        return tuple(self.state.path) == tuple(other.state.path)

    def __str__(self):
        return str(self.state)


def run_mcts_on_problem(problem: OrienteeringProblem, iterations: int = 1000, exploration_weight: float = 1.0):
    """Run MCTS on the provided OrienteeringProblem and return the best path found.

    Returns a tuple (best_path, best_score, best_cost).
    """
    root_state = OrienteeringState(problem)
    root = OrienteeringNode(root_state)
    mcts = MCTS(exploration_weight=exploration_weight)

    for _ in range(iterations):
        mcts.do_rollout(root)

    # Choose best child of root according to MCTS
    if root not in mcts.children:
        # No children expanded; fallback to greedy next action
        actions = root_state.get_available_actions()
        if not actions:
            return root_state.get_path(), root_state.get_reward(), root_state.get_cost()
        best = max(actions, key=lambda a: problem.nodes[a].score)
        best_state = root_state.apply_action(best)
        return best_state.get_path(), best_state.get_reward(), best_state.get_cost()

    best_child = mcts.choose(root)
    # best_child is an OrienteeringNode; return its wrapped state's info
    return best_child.state.get_path(), best_child.state.get_reward(), best_child.state.get_cost()
