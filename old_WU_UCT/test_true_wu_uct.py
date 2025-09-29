"""
Test True WU-UCT Implementation
"""
import sys
import os
import time

# Add the parent directory to path to import orienteering module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orienteering.orienteering import OrienteeringProblem

# Import WU-UCT components
from wu_orienteering_tree import WUOrienteeringTree
from wu_specialized_workers import WUCoordinatedSolver
from main import WUOrienteeringSolver


def create_test_problem():
    """Create a simple test problem"""
    from orienteering.orienteering import Node
    
    # Simple test problem: 5 nodes with rewards
    nodes = [
        Node(0, 0, 0, 0),      # Start node
        Node(1, 10, 10, 0),    # End node  
        Node(2, 5, 5, 10),     # High reward node
        Node(3, 3, 7, 5),      # Medium reward node
        Node(4, 7, 3, 8)       # Good reward node
    ]
    budget = 50  # More permissive budget
    return OrienteeringProblem(nodes, budget, max_edge_distance=None)  # Remove edge distance constraint


def test_wu_uct_basic():
    """Test basic WU-UCT functionality"""
    print("Testing basic True WU-UCT functionality...")
    
    problem = create_test_problem()
    tree = WUOrienteeringTree(
        problem=problem,
        max_steps=500,
        max_depth=10,
        expansion_worker_num=1,
        simulation_worker_num=2
    )
    
    # Test coordinated solver
    solver = WUCoordinatedSolver(
        tree=tree,
        num_expansion_workers=1,
        num_simulation_workers=2
    )
    
    start_time = time.time()
    best_path, best_reward, stats = solver.solve(
        max_iterations=1000,
        max_time=5.0,
        verbose=True
    )
    elapsed_time = time.time() - start_time
    
    print(f"\nBasic WU-UCT Test Results:")
    print(f"Best path: {best_path}")
    print(f"Best reward: {best_reward}")
    print(f"Time: {elapsed_time:.2f}s")
    print(f"Total simulations: {stats['total_simulations']}")
    
    # Verify we found a valid solution
    assert best_path is not None
    assert len(best_path) >= 2  # At least start and end
    assert best_path[0] == 0    # Starts at node 0
    assert best_path[-1] == 1   # Ends at node 1
    print("✓ Basic test passed!")


def test_wu_uct_vs_regular():
    """Compare True WU-UCT with regular parallel MCTS"""
    print("\nComparing True WU-UCT vs Regular Parallel MCTS...")
    
    problem = create_test_problem()
    
    # Test regular solver
    print("Testing regular solver...")
    regular_solver = WUOrienteeringSolver(
        problem=problem,
        num_workers=4,
        max_steps=500
    )
    
    start_time = time.time()
    regular_path, regular_reward, regular_stats = regular_solver.solve_parallel(
        max_iterations=2000,
        max_time=10.0,
        verbose=False
    )
    regular_time = time.time() - start_time
    
    # Test WU-UCT solver
    print("Testing True WU-UCT solver...")
    wu_solver = WUOrienteeringSolver(
        problem=problem,
        num_workers=4,
        expansion_workers=1,
        simulation_workers=3,
        max_steps=500
    )
    
    start_time = time.time()
    wu_path, wu_reward, wu_stats = wu_solver.solve_wu_uct(
        max_iterations=2000,
        max_time=10.0,
        verbose=False
    )
    wu_time = time.time() - start_time
    
    print(f"\nComparison Results:")
    print(f"Regular Parallel MCTS:")
    print(f"  Path: {regular_path}")
    print(f"  Reward: {regular_reward}")
    print(f"  Time: {regular_time:.2f}s")
    print(f"  Simulations: {regular_stats.get('total_simulations', 0)}")
    
    print(f"\nTrue WU-UCT:")
    print(f"  Path: {wu_path}")
    print(f"  Reward: {wu_reward}")
    print(f"  Time: {wu_time:.2f}s")
    print(f"  Simulations: {wu_stats.get('total_simulations', 0)}")
    print(f"  Expansions: {wu_stats.get('total_expansions', 0)}")
    
    # Both should find valid solutions
    assert regular_path is not None and wu_path is not None
    print("✓ Both methods found valid solutions!")


def test_scaling():
    """Test WU-UCT with different worker configurations"""
    print("\nTesting WU-UCT worker scaling...")
    
    problem = create_test_problem()
    configurations = [
        (1, 1),  # 1 expansion, 1 simulation
        (1, 2),  # 1 expansion, 2 simulation
        (1, 4),  # 1 expansion, 4 simulation
        (2, 2),  # 2 expansion, 2 simulation
    ]
    
    results = []
    
    for exp_workers, sim_workers in configurations:
        print(f"Testing {exp_workers} expansion + {sim_workers} simulation workers...")
        
        solver = WUOrienteeringSolver(
            problem=problem,
            num_workers=exp_workers + sim_workers,
            expansion_workers=exp_workers,
            simulation_workers=sim_workers,
            max_steps=300
        )
        
        start_time = time.time()
        path, reward, stats = solver.solve_wu_uct(
            max_iterations=1000,
            max_time=5.0,
            verbose=False
        )
        elapsed_time = time.time() - start_time
        
        results.append({
            'config': f"{exp_workers}+{sim_workers}",
            'path': path,
            'reward': reward,
            'time': elapsed_time,
            'simulations': stats.get('total_simulations', 0)
        })
    
    print(f"\nScaling Test Results:")
    print(f"{'Config':<8} {'Reward':<8} {'Time':<8} {'Simulations':<12} {'Path'}")
    print("-" * 60)
    for result in results:
        print(f"{result['config']:<8} {result['reward']:<8.1f} {result['time']:<8.2f} "
              f"{result['simulations']:<12} {result['path']}")
    
    print("✓ Scaling test completed!")


if __name__ == "__main__":
    print("Testing True WU-UCT Implementation")
    print("=" * 50)
    
    try:
        test_wu_uct_basic()
        test_wu_uct_vs_regular()
        test_scaling()
        
        print("\n" + "=" * 50)
        print("All tests passed! ✓")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)