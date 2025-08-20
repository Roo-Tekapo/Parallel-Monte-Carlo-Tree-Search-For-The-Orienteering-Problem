import unittest
from MCTS.mcts_single_thread import single_thread_mcts
from orienteering.orienteering import Node, OrienteeringProblem, OrienteeringState

class TestSingleThreadMCTS(unittest.TestCase):
    def setUp(self):
        # Create a small orienteering problem
        self.nodes = [
            Node(0, 0.0, 0.0, 5),
            Node(1, 2.0, 0.0, 10),
            Node(2, 2.0, 2.0, 15),
            Node(3, 0.0, 2.0, 20),
            Node(4, 1.0, 1.0, 25)
        ]
        self.budget = 5.0
        self.problem = OrienteeringProblem(self.nodes, self.budget)
        self.mcts = single_thread_mcts(self.problem)

    def test_init(self):
        self.assertIsInstance(self.mcts.root, OrienteeringState)

    def test_select(self):
        path = self.mcts._select(self.mcts.root)
        self.assertIsInstance(path, list)
        self.assertTrue(all(isinstance(n, OrienteeringState) for n in path))

    def test_expand(self):
        # Should not raise
        self.mcts._expand(self.mcts.root)

    def test_simulate(self):
        reward = self.mcts._simulate(self.mcts.root)
        self.assertIsInstance(reward, (int, float))

    def test_backpropagate(self):
        path = [self.mcts.root, self.mcts.root.copy()]
        # Should not raise
        self.mcts._backpropagate(path, 1)

    def test_print_results(self):
        # Should not raise
        self.mcts.print_results()

if __name__ == "__main__":
    unittest.main()


# python3 -m unittest Test/test_mcts_single_thread.py
