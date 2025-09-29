"""
Example usage of WU-UCT for Orienteering Problem
"""
import sys
import os
import time

# Add the parent directory to path to import orienteering module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orienteering.orienteering import OrienteeringProblem
from old_WU_UCT.wu_orienteering_tree import WUOrienteeringTree
from old_WU_UCT.main import WUOrienteeringSolver


def test_wu_uct_solver():
    """Test the WU-UCT solver on a sample problem"""
    
    # Load a sample problem
    problem_file = "OP_Benchmark_Set/sample/sample_6_small.txt"
    
    try:
        nodes, budget = OrienteeringProblem.load_problem(problem_file)
        problem = OrienteeringProblem(nodes, budget)
        
        print(f"Loaded problem: {len(nodes)} nodes, budget: {budget}")
        print("Nodes:")
        for i, node in enumerate(nodes):
            print(f"  Node {i}: pos=({node.x:.1f}, {node.y:.1f}), score={node.score}")
    
    except FileNotFoundError:
        print(f"Problem file not found: {problem_file}")
        print("Creating a simple test problem instead...")
        
        # Create a simple test problem
        from orienteering.orienteering import Node
        nodes = [
            Node(0, 0.0, 0.0, 0),    # Start node
            Node(1, 10.0, 0.0, 0),   # End node  
            Node(2, 2.0, 1.0, 15),   # High value node
            Node(3, 4.0, 2.0, 10),   # Medium value node
            Node(4, 6.0, 1.0, 8),    # Lower value node
            Node(5, 3.0, 3.0, 12),   # Another medium value node
        ]
        budget = 15.0
        problem = OrienteeringProblem(nodes, budget)
        
        print(f"Created test problem: {len(nodes)} nodes, budget: {budget}")
        print("Nodes:")
        for node in nodes:
            print(f"  Node {node.id}: pos=({node.x:.1f}, {node.y:.1f}), score={node.score}")
    
    print("\n" + "="*50)
    print("Testing WU-UCT Tree directly")
    print("="*50)
    
    # Test 1: Direct tree usage
    tree = WUOrienteeringTree(
        problem=problem,
        max_steps=500,
        max_depth=20,
        max_width=5,
        gamma=1.0
    )
    
    start_time = time.time()
    best_path, best_reward, stats = tree.solve_complete_problem(
        max_iterations=2000,
        verbose=True
    )
    elapsed_time = time.time() - start_time
    
    print(f"\nDirect Tree Results:")
    print(f"Best path: {best_path}")
    print(f"Best reward: {best_reward}")
    print(f"Time taken: {elapsed_time:.2f}s")
    print(f"Statistics: {stats}")
    
    print("\n" + "="*50)
    print("Testing WU-UCT Solver")
    print("="*50)
    
    # Test 2: Using the solver class
    solver = WUOrienteeringSolver(
        problem=problem,
        num_workers=2,
        max_steps=500,
        max_depth=20,
        max_width=5,
        gamma=1.0
    )
    
    start_time = time.time()
    best_path2, best_reward2, stats2 = solver.solve(
        max_iterations=2000,
        verbose=True
    )
    elapsed_time2 = time.time() - start_time
    
    print(f"\nSolver Results:")
    print(f"Best path: {best_path2}")
    print(f"Best reward: {best_reward2}")
    print(f"Time taken: {elapsed_time2:.2f}s")
    print(f"Statistics: {stats2}")
    
    print("\n" + "="*50)
    print("Comparison")
    print("="*50)
    
    print(f"Direct Tree - Reward: {best_reward:.2f}, Time: {elapsed_time:.2f}s")
    print(f"Solver      - Reward: {best_reward2:.2f}, Time: {elapsed_time2:.2f}s")
    
    # Validate solution
    print(f"\nSolution validation:")
    try:
        from orienteering.orienteering import OrienteeringState
        state = OrienteeringState(problem)
        total_cost = 0.0
        
        print(f"Starting at node {state.path[-1]}")
        
        for i in range(1, len(best_path2)):
            action = best_path2[i]
            prev_node = state.path[-1]
            cost = problem.get_distance(prev_node, action)
            total_cost += cost
            
            state = state.apply_action(action)
            print(f"Step {i}: Move to node {action}, cost: {cost:.2f}, total_cost: {total_cost:.2f}, reward: {state.get_reward()}")
        
        print(f"Final state: reward={state.get_reward()}, cost={state.get_cost():.2f}, terminal={state.is_terminal()}")
        print(f"Budget constraint: {state.get_cost():.2f} <= {problem.budget} ? {state.get_cost() <= problem.budget}")
        
    except Exception as e:
        print(f"Solution validation failed: {e}")


def test_with_benchmark_problems():
    """Test with actual benchmark problems"""
    
    benchmark_files = [
        "OP_Benchmark_Set/sample/sample_6_small.txt",
        "OP_Benchmark_Set/set_64_1/set_64_1_15.txt",
    ]
    
    for problem_file in benchmark_files:
        print(f"\n{'='*60}")
        print(f"Testing with {problem_file}")
        print(f"{'='*60}")
        
        try:
            nodes, budget = OrienteeringProblem.load_problem(problem_file)
            problem = OrienteeringProblem(nodes, budget)
            
            print(f"Problem: {len(nodes)} nodes, budget: {budget}")
            
            # Test with WU-UCT solver
            solver = WUOrienteeringSolver(
                problem=problem,
                num_workers=2,
                max_steps=1000,
                max_depth=30,
                max_width=8,
                gamma=1.0
            )
            
            start_time = time.time()
            best_path, best_reward, stats = solver.solve(
                max_iterations=5000,
                verbose=True
            )
            elapsed_time = time.time() - start_time
            
            print(f"\nResults for {os.path.basename(problem_file)}:")
            print(f"Best path: {best_path}")
            print(f"Best reward: {best_reward}")
            print(f"Path length: {len(best_path)}")
            print(f"Time taken: {elapsed_time:.2f}s")
            print(f"Simulations: {stats.get('total_simulations', 0)}")
            print(f"Simulations/second: {stats.get('total_simulations', 0) / max(elapsed_time, 0.001):.1f}")
            
        except FileNotFoundError:
            print(f"Benchmark file not found: {problem_file}")
        except Exception as e:
            print(f"Error testing {problem_file}: {e}")


if __name__ == "__main__":
    print("WU-UCT Orienteering Problem Solver - Example Usage")
    print("="*60)
    
    # Test basic functionality
    test_wu_uct_solver()
    
    # Test with benchmark problems
    test_with_benchmark_problems()
    
    print(f"\n{'='*60}")
    print("Example usage completed!")
    print("="*60)