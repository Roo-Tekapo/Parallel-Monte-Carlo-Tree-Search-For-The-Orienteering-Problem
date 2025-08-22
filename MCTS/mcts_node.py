import math

from orienteering.orienteering import OrienteeringState

class MCTSNode:
    def __init__(self, state: OrienteeringState, parent=None):
        self.state: OrienteeringState = state
        self.parent: "MCTSNode" = parent
        self.children: list[MCTSNode] = []
        self.visits: int = 0
        self.total_reward: float= 0.0
        self.untried_actions: list[OrienteeringState] = state.get_available_actions()

    def is_fully_expanded(self):
        return len(self.untried_actions) == 0

    def uct_best_child(self, c_param=math.sqrt(2)):
        """Select best child with UCT."""
        choices = []
        for child in self.children:
            exploit = child.total_reward / child.visits
            explore = c_param * math.sqrt(math.log(self.visits) / child.visits)
            choices.append(exploit + explore)
        return self.children[choices.index(max(choices))]
