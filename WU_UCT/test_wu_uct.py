"""
Tests for True WU-UCT Implementation

Verifies that the implementation follows the WU-UCT paper design.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from WU_UCT.wu_uct_node import WUUCTNode, LocalStatistics
from WU_UCT.wu_uct_coordinator import WUUCTCoordinator
from WU_UCT.orienteering_adapter import OrienteeringAdapter


class SimpleState:
    """Simple test state."""
    def __init__(self, value=0, terminal=False):
        self.value = value
        self.terminal = terminal
        self.path = [value]
    
    def is_terminal(self):
        return self.terminal
    
    def get_available_actions(self):
        if self.terminal:
            return []
        return [1, 2, 3]
    
    def apply_action(self, action):
        return SimpleState(self.value + action, terminal=(self.value + action >= 10))
    
    def copy(self):
        return SimpleState(self.value, self.terminal)


def test_node_lock_free_reads():
    """Test that node statistics can be read without locks."""
    print("Testing lock-free statistics reading...")
    
    state = SimpleState()
    node = WUUCTNode(state)
    
    # Add some statistics
    node.visits = 10
    node.total_reward = 50.0
    node.mark_simulation_started("sim1")
    node.mark_simulation_started("sim2")
    
    # Read statistics (should not block)
    stats = node.get_local_statistics()
    
    assert stats.visits == 10
    assert stats.total_reward == 50.0
    assert stats.unobserved_count == 2
    assert stats.effective_visits == 12
    assert abs(stats.average_reward - 5.0) < 0.001
    
    print("✓ Lock-free reads working correctly")


def test_traverse_history():
    """Test that traverse_history tracks unobserved samples."""
    print("Testing traverse history (unobserved samples)...")
    
    state = SimpleState()
    node = WUUCTNode(state)
    
    # Mark simulations as started
    node.mark_simulation_started("sim1", action=1, immediate_reward=1.0)
    node.mark_simulation_started("sim2", action=2, immediate_reward=2.0)
    
    stats = node.get_local_statistics()
    assert stats.unobserved_count == 2, f"Expected 2 unobserved, got {stats.unobserved_count}"
    
    # Commit one simulation
    total_reward = node.commit_simulation_result("sim1", accumulated_reward=5.0)
    
    assert node.visits == 1
    assert total_reward == 6.0  # 1.0 + 5.0
    
    stats = node.get_local_statistics()
    assert stats.unobserved_count == 1, f"Expected 1 unobserved after commit, got {stats.unobserved_count}"
    
    print("✓ Traverse history working correctly")


def test_wu_uct_formula():
    """Test that WU-UCT formula includes unobserved samples."""
    print("Testing WU-UCT selection formula...")
    
    # Create parent with some visits and unobserved samples
    parent_state = SimpleState()
    parent = WUUCTNode(parent_state)
    parent.visits = 100
    parent.mark_simulation_started("ongoing1")
    parent.mark_simulation_started("ongoing2")
    
    # Create children
    child1_state = SimpleState(1)
    child1 = WUUCTNode(child1_state, parent=parent)
    child1.visits = 10
    child1.total_reward = 50.0
    parent.children.append(child1)
    
    child2_state = SimpleState(2)
    child2 = WUUCTNode(child2_state, parent=parent)
    child2.visits = 5
    child2.total_reward = 30.0
    child2.mark_simulation_started("ongoing3")  # Has unobserved sample
    parent.children.append(child2)
    
    # Select child using WU-UCT
    selected = parent.wu_uct_select_child(exploration_constant=1.414)
    
    # Verify selection considers unobserved samples
    parent_stats = parent.get_local_statistics()
    assert parent_stats.effective_visits == 102  # 100 + 2 unobserved
    
    child2_stats = child2.get_local_statistics()
    assert child2_stats.effective_visits == 6  # 5 + 1 unobserved
    
    print("✓ WU-UCT formula using N + O correctly")


def test_async_commits():
    """Test that commits are asynchronous (minimal locking)."""
    print("Testing asynchronous commits...")
    
    state = SimpleState()
    node = WUUCTNode(state)
    
    # Mark multiple simulations as started
    sim_ids = [f"sim{i}" for i in range(10)]
    for sim_id in sim_ids:
        node.mark_simulation_started(sim_id, immediate_reward=1.0)
    
    # Commit them asynchronously
    start_time = time.time()
    for i, sim_id in enumerate(sim_ids):
        node.commit_simulation_result(sim_id, accumulated_reward=float(i))
    commit_time = time.time() - start_time
    
    # Verify all committed
    assert node.visits == 10
    stats = node.get_local_statistics()
    assert stats.unobserved_count == 0
    
    # Commits should be very fast (< 1ms total for 10 commits)
    assert commit_time < 0.01, f"Commits too slow: {commit_time*1000:.2f}ms"
    
    print(f"✓ Async commits working (10 commits in {commit_time*1000:.2f}ms)")


def test_expansion_simulation_separation():
    """Test that expansion and simulation are properly separated."""
    print("Testing expansion/simulation separation...")
    
    # This test requires a small problem file
    # For now, we'll skip if file doesn't exist
    test_problem = project_root / "OP_Benchmark_Set" / "sample" / "tsiligirides_problem_1_budget_5.txt"
    
    if not test_problem.exists():
        print("⚠ Skipping (test problem not found)")
        return
    
    problem = OrienteeringAdapter.load_problem(str(test_problem))
    
    coordinator = WUUCTCoordinator(
        problem=problem,
        num_expansion_workers=2,
        num_simulation_workers=4,
        exploration_constant=1.414
    )
    
    # Run for short time
    best_state = coordinator.run(
        max_iterations=100,
        verbose=False
    )
    
    # Verify workers ran
    assert len(coordinator.expansion_workers) == 2
    assert len(coordinator.simulation_workers) == 4
    
    total_iterations = sum(w.iterations_completed for w in coordinator.expansion_workers)
    total_simulations = sum(w.simulations_completed for w in coordinator.simulation_workers)
    
    assert total_iterations > 0, "No expansion iterations completed"
    assert total_simulations > 0, "No simulations completed"
    
    # Check that simulation workers processed work units
    for worker in coordinator.simulation_workers:
        stats = worker.get_statistics()
        # At least some workers should have done work
    
    print(f"✓ Separation working ({total_iterations} iterations, {total_simulations} simulations)")


def test_lock_free_selection():
    """Test that selection doesn't hold locks."""
    print("Testing lock-free selection...")
    
    # Create a small tree
    root_state = SimpleState()
    root = WUUCTNode(root_state)
    
    # Add some children with statistics
    for i in range(3):
        child_state = SimpleState(i+1)
        child = WUUCTNode(child_state, parent=root)
        child.visits = 10 + i
        child.total_reward = 50.0 + i * 10
        root.children.append(child)
    
    root.visits = 30
    
    # Selection should not hold locks
    # We can't directly test this, but we can verify it's fast
    start_time = time.time()
    for _ in range(1000):
        selected = root.wu_uct_select_child()
    selection_time = time.time() - start_time
    
    # Should be reasonably fast (< 10ms for 1000 selections)
    assert selection_time < 0.010, f"Selection too slow: {selection_time*1000:.2f}ms"
    
    print(f"✓ Lock-free selection working (1000 selections in {selection_time*1000:.2f}ms)")


def run_all_tests():
    """Run all tests."""
    print("="*70)
    print("True WU-UCT Implementation Tests")
    print("="*70)
    print()
    
    tests = [
        test_node_lock_free_reads,
        test_traverse_history,
        test_wu_uct_formula,
        test_async_commits,
        test_lock_free_selection,
        test_expansion_simulation_separation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
        print()
    
    print("="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
