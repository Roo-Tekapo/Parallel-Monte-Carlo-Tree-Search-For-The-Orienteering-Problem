import unittest
from unittest.mock import MagicMock, patch
from MCTS.mcts_single_thread import single_thread_mcts

class DummyProblem:
    def __init__(self):
        self.nodes = []
        self.budget = 10

class DummyState:
    def __init__(self):
        self.path = [0]
        self.reward_so_far = 0
        self.cost_so_far = 0

    def is_terminal(self):
        return False

    def get_available_actions(self):
        return []

    def best_child(self):
        return self

    def copy(self):
        return DummyState()

    def get_reward(self):
        return 0

    def get_cost(self):
        return 0

    def get_path(self):
        return [0]

class TestSingleThreadMCTS(unittest.TestCase):
    @patch('MCTS.mcts_single_thread.OrienteeringState', new=DummyState)
    def setUp(self):
        self.problem = DummyProblem()
        self.mcts = single_thread_mcts(self.problem)

    @patch('MCTS.mcts_single_thread.OrienteeringState', new=DummyState)
    def test_init(self):
        self.assertIsInstance(self.mcts.root, DummyState)

#     @patch('MCTS.mcts_single_thread.OrienteeringState', new=DummyState)
#     def test_select(self):
#         path = self.mcts._select(self.mcts.root)
#         self.assertIsInstance(path, list)
#         self.assertTrue(all(isinstance(n, DummyState) for n in path))

#     @patch('MCTS.mcts_single_thread.OrienteeringState', new=DummyState)
#     def test_expand(self):
#         # Should not raise
#         self.mcts._expand(self.mcts.root)

#     @patch('MCTS.mcts_single_thread.OrienteeringState', new=DummyState)
#     def test_simulate(self):
#         reward = self.mcts._simulate(self.mcts.root)
#         self.assertEqual(reward, 0)

#     @patch('MCTS.mcts_single_thread.OrienteeringState', new=DummyState)
#     def test_backpropagate(self):
#         path = [self.mcts.root, self.mcts.root]
#         # Should not raise
#         self.mcts._backpropagate(path, 1)

#     @patch('MCTS.mcts_single_thread.OrienteeringState', new=DummyState)
#     def test_print_results(self):
#         # Should not raise
#         self.mcts.print_results()

if __name__ == "__main__":
    unittest.main()


# python3 -m unittest Test/test_mcts_single_thread.py
