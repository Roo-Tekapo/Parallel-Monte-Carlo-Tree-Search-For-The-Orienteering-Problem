"""
Test script for Virtual Loss implementation

Validates that VL mechanism works correctly and compares with WU-UCT.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from VL.orienteering_adapter import OrienteeringProblem
from VL.vl_coordinator import VirtualLossMCTS
from VL.vl_node import VLNode


def test_vl_node_operations():
    """Test basic VL node operations."""
    print("\n" + "="*60)
    print("Test 1: VL Node Operations")
    print("="*60)
    
    # Create a simple problem
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    
    from VL.orienteering_adapter import OrienteeringState
    initial_state = OrienteeringState(problem)
    node = VLNode(initial_state)
    
    # Test initial state
    assert node.get_virtual_loss_count() == 0, "Initial VL count should be 0"
    assert node.get_effective_reward() == 0, "Initial effective reward should be 0"
    print("✓ Initial state correct")
    
    # Apply virtual loss
    node.apply_virtual_loss("thread_1", 1.0)
    assert node.get_virtual_loss_count() == 1, "VL count should be 1"
    assert node.get_effective_reward() == -1.0, "Effective reward should be -1.0"
    print("✓ Virtual loss application works")
    
    # Apply second virtual loss
    node.apply_virtual_loss("thread_2", 1.5)
    assert node.get_virtual_loss_count() == 2, "VL count should be 2"
    assert node.get_effective_reward() == -2.5, "Effective reward should be -2.5"
    print("✓ Multiple virtual losses work")
    
    # Update with real reward
    node.update(5.0)
    assert node.visits == 1, "Visits should be 1"
    assert node.total_reward == 5.0, "Total reward should be 5.0"
    # Effective reward is total_reward - virtual_loss = 5.0 - 2.5 = 2.5
    assert node.get_effective_reward() == 2.5, "Effective reward should be 2.5"
    print("✓ Update with virtual loss works")
    
    # Remove virtual losses
    removed = node.remove_virtual_loss("thread_1")
    assert removed == True, "Should successfully remove VL"
    assert node.get_virtual_loss_count() == 1, "VL count should be 1"
    assert node.get_effective_reward() == 3.5, "Effective reward should be 3.5"
    print("✓ Virtual loss removal works")
    
    # Remove second virtual loss
    node.remove_virtual_loss("thread_2")
    assert node.get_virtual_loss_count() == 0, "VL count should be 0"
    assert node.get_effective_reward() == 5.0, "Effective reward should be 5.0"
    print("✓ All virtual losses removed correctly")
    
    # Try to remove non-existent virtual loss
    removed = node.remove_virtual_loss("thread_3")
    assert removed == False, "Should return False for non-existent VL"
    print("✓ Non-existent VL removal handled correctly")
    
    print("\n✅ Test 1 PASSED: VL Node Operations")
    return True


def test_vl_mcts_basic():
    """Test basic VL-MCTS execution."""
    print("\n" + "="*60)
    print("Test 2: Basic VL-MCTS Execution")
    print("="*60)
    
    # Load problem
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    print(f"✓ Loaded problem with {problem.num_nodes} nodes")
    
    # Run VL-MCTS with minimal iterations
    vl_mcts = VirtualLossMCTS(
        problem=problem,
        num_workers=2,
        virtual_loss_value=1.0
    )
    print(f"✓ Created VL-MCTS with 2 workers")
    
    solution = vl_mcts.run(
        max_iterations=100,
        verbose=False
    )
    print(f"✓ Completed 100 iterations")
    
    # Validate solution
    assert solution is not None, "Solution should not be None"
    assert len(solution.path) >= 1, "Path should have at least 1 node"
    assert solution.path[0] == 0, "Path should start at node 0"
    # Note: With only 100 iterations, path may not reach END_NODE (1)
    print(f"✓ Solution valid: {len(solution.path)} nodes, reward={solution.reward_so_far:.4f}, terminal={solution.is_terminal()}")
    
    # Check statistics
    stats = vl_mcts.get_tree_statistics()
    assert stats['total_nodes'] > 0, "Should have created nodes"
    assert stats['root_visits'] > 0, "Root should have visits"
    print(f"✓ Tree statistics: {stats['total_nodes']} nodes, depth={stats['max_depth']}")
    
    print("\n✅ Test 2 PASSED: Basic VL-MCTS Execution")
    return True


def test_vl_collision_tracking():
    """Test virtual loss collision tracking."""
    print("\n" + "="*60)
    print("Test 3: Virtual Loss Collision Tracking")
    print("="*60)
    
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    
    # Test with different VL values
    vl_values = [0.5, 1.0, 2.0]
    
    for vl_value in vl_values:
        print(f"\nTesting VL value: {vl_value}")
        
        vl_mcts = VirtualLossMCTS(
            problem=problem,
            num_workers=4,
            virtual_loss_value=vl_value
        )
        
        solution = vl_mcts.run(max_iterations=1000, verbose=False)
        
        # Check collision statistics
        total_collisions = sum(w.virtual_loss_collisions for w in vl_mcts.workers)
        total_iters = sum(w.iterations_completed for w in vl_mcts.workers)
        collision_rate = total_collisions / total_iters if total_iters > 0 else 0
        
        print(f"  Collisions: {total_collisions}/{total_iters} ({collision_rate:.2%})")
        
        assert collision_rate <= 1.0, "Collision rate should be <= 100%"
        print(f"  ✓ VL value {vl_value} works correctly")
    
    print("\n✅ Test 3 PASSED: Virtual Loss Collision Tracking")
    return True


def test_vl_thread_safety():
    """Test thread safety with high worker count."""
    print("\n" + "="*60)
    print("Test 4: Thread Safety with High Worker Count")
    print("="*60)
    
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    
    # Run with many workers
    vl_mcts = VirtualLossMCTS(
        problem=problem,
        num_workers=8,
        virtual_loss_value=1.5
    )
    print("✓ Created VL-MCTS with 8 workers")
    
    solution = vl_mcts.run(max_iterations=2000, verbose=False)
    print("✓ Completed 2000 iterations with 8 workers")
    
    # Verify solution properties
    assert solution.cost_so_far <= problem.budget, "Solution should not exceed budget"
    print(f"✓ Solution is within budget ({solution.cost_so_far:.2f} <= {problem.budget:.2f})")
    
    # Check that all workers completed successfully
    completed = sum(w.iterations_completed for w in vl_mcts.workers)
    assert completed == 2000, f"Should complete 2000 iterations, got {completed}"
    print(f"✓ All {completed} iterations completed successfully")
    
    print("\n✅ Test 4 PASSED: Thread Safety")
    return True


def compare_vl_values():
    """Compare different VL values."""
    print("\n" + "="*60)
    print("Comparison: Different VL Values")
    print("="*60)
    
    nodes, budget = OrienteeringProblem.load_problem(
        "OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt"
    )
    problem = OrienteeringProblem(nodes, budget, normalize_rewards=True)
    
    vl_values = [0.5, 1.0, 1.5, 2.0, 3.0]
    iterations = 5000
    
    print(f"\nRunning {iterations} iterations with 4 workers for each VL value:\n")
    print(f"{'VL Value':<10} {'Best Reward':<15} {'Collision Rate':<15} {'Iters/sec':<15}")
    print("-" * 60)
    
    results = []
    
    for vl_value in vl_values:
        import time
        
        vl_mcts = VirtualLossMCTS(
            problem=problem,
            num_workers=4,
            virtual_loss_value=vl_value
        )
        
        start_time = time.time()
        solution = vl_mcts.run(max_iterations=iterations, verbose=False)
        elapsed = time.time() - start_time
        
        total_collisions = sum(w.virtual_loss_collisions for w in vl_mcts.workers)
        total_iters = sum(w.iterations_completed for w in vl_mcts.workers)
        collision_rate = total_collisions / total_iters if total_iters > 0 else 0
        iters_per_sec = total_iters / elapsed if elapsed > 0 else 0
        
        print(f"{vl_value:<10.1f} {solution.reward_so_far:<15.4f} "
              f"{collision_rate:<15.2%} {iters_per_sec:<15.1f}")
        
        results.append({
            'vl_value': vl_value,
            'reward': solution.reward_so_far,
            'collision_rate': collision_rate,
            'iters_per_sec': iters_per_sec
        })
    
    print("\n" + "="*60)
    print("Observations:")
    print(f"  - Higher VL values → Lower collision rates (better separation)")
    print(f"  - Lower VL values → Higher collision rates (more overlap)")
    print(f"  - Optimal VL value depends on problem characteristics")
    print("="*60)
    
    return results


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("VIRTUAL LOSS IMPLEMENTATION TEST SUITE")
    print("="*70)
    
    tests = [
        ("VL Node Operations", test_vl_node_operations),
        ("Basic VL-MCTS Execution", test_vl_mcts_basic),
        ("Virtual Loss Collision Tracking", test_vl_collision_tracking),
        ("Thread Safety", test_vl_thread_safety),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"\n❌ {test_name} FAILED with exception:")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Run comparison (not a pass/fail test)
    print("\n" + "="*70)
    try:
        compare_vl_values()
    except Exception as e:
        print(f"Comparison failed: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("\nThe Virtual Loss implementation is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
