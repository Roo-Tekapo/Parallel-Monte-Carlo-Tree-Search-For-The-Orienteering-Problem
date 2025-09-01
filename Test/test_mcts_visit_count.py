import unittest
import math
from orienteering.orienteering import OrienteeringProblem, OrienteeringState, Node
from MCTS.mcts_base import MCTSSingleThread
from MCTS.mcts_node import MCTSNode


class TestMCTSVisitCount(unittest.TestCase):
    def setUp(self):
        # Create a simple orienteering problem with 3 nodes (start, 1, end)
        nodes = [Node(0, 0.0, 0.0, 0), Node(1, 10.0, 0.0, 5), Node(2, 20.0, 0.0, 0)]
        budget = 30.0
        self.problem = OrienteeringProblem(nodes, budget)
        self.solver = MCTSSingleThread(self.problem, iterations=1)

    def test_visit_count_increases(self):
        root_state = OrienteeringState(self.problem)
        root_node = MCTSNode(root_state)
        # Simulate visiting the root node multiple times
        for _ in range(5):
            self.solver.backpropagate(root_node, reward=1.0)
        self.assertEqual(root_node.visits, 5)

    def test_visit_count_increases_with_tree(self):
        root = self.solver.initialize_root()
        # Run several steps, which should increase visit count on root
        for _ in range(10):
            self.solver.step()
        self.assertEqual(root.visits, 10)

if __name__ == "__main__":
    unittest.main()
