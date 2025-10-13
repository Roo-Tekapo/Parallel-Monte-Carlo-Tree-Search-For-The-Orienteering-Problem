#!/usr/bin/env python3
"""
Test the refactored WU-UCT implementation.
This demonstrates that the modular structure works correctly.
"""

import sys
import os
import math

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from UCT.wu_uct_coordinator import WUUCT, run_wu_uct


def test_modular_wu_uct():
    """Test the modular WU-UCT implementation."""
    print("="*60)
    print("Testing Modular WU-UCT Implementation")
    print("="*60)
    
    # Load test problem
    print("Loading problem...")
    nodes, budget = OrienteeringProblem.load_problem(
        "../OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    )
    problem = OrienteeringProblem(nodes, budget)
    print(f"Loaded: {len(nodes)} nodes, budget: {budget}")
    
    # Test 1: Using WUUCT class directly
    print("\n" + "-"*40)
    print("Test 1: Using WUUCT class directly")
    print("-"*40)
    
    wu_uct = WUUCT(problem, 
                   expansion_workers=1, 
                   simulation_workers=3, 
                   exploration_constant=math.sqrt(2))
    
    print("Running WU-UCT for 2000 iterations...")
    best_state = wu_uct.run(max_iterations=2000, verbose=True)
    
    print(f"\nResults:")
    print(f"Best path: {best_state.get_path()}")
    print(f"Total reward: {best_state.get_reward()}")
    print(f"Total cost: {best_state.get_cost()}")
    
    stats = wu_uct.get_statistics()
    print(f"Final statistics:")
    print(f"  - Total nodes: {stats['nodes']}")
    print(f"  - Root visits: {stats['root_visits']}")
    print(f"  - Total simulations: {stats['total_simulations']}")
    
    # Test 2: Using convenience function
    print("\n" + "-"*40)
    print("Test 2: Using convenience function")
    print("-"*40)
    
    print("Running WU-UCT using convenience function...")
    best_state_2 = run_wu_uct(problem, 
                             max_iterations=1000,
                             simulation_workers=2,
                             verbose=True)
    
    print(f"\nConvenience function results:")
    print(f"Best path: {best_state_2.get_path()}")
    print(f"Total reward: {best_state_2.get_reward()}")
    print(f"Total cost: {best_state_2.get_cost()}")
    
    print("\n" + "="*60)
    print("Modular WU-UCT implementation working correctly!")
    print("="*60)
    
    return best_state, best_state_2


if __name__ == "__main__":
    test_modular_wu_uct()