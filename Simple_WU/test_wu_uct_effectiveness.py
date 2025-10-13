#!/usr/bin/env python3
"""
Test to measure WU-UCT effectiveness at preventing worker convergence.

This test specifically examines:
1. How the pending_simulations (virtual loss) mechanism affects selection
2. Whether workers are actually selecting different paths simultaneously
3. The impact of the WU-UCT formula: a_n = arg max { V_c + β * sqrt(2*log(N_n + O_n) / (N_c + O_c)) }
"""

import sys
import os
import math
import threading
import time
from collections import defaultdict, Counter

# Add parent directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.extend([project_root, current_dir])

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from UCT.wu_uct_node import WUUCTNode
from simple_wu_worker import SimpleWUWorker


class DiagnosticWUWorker(SimpleWUWorker):
    """Enhanced worker that tracks selection patterns for diagnostic purposes."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selection_log = []  # Log of (timestamp, node_path, pending_sims)
        self.collision_count = 0  # Times we selected a node that had pending_simulations > 0
        
    def _select_best_child(self, node):
        """Override to track selection decisions."""
        # Call parent implementation
        best_child = super()._select_best_child(node)
        
        # Log selection metrics
        if best_child:
            collision = best_child.pending_simulations > 0
            if collision:
                self.collision_count += 1
                
        return best_child
    
    def _perform_iteration(self):
        """Override to log selection patterns."""
        start_time = time.time()
        
        # Perform normal iteration
        super()._perform_iteration()
        
        # Log the selection path and virtual loss state
        if self.last_selection_path:
            self.selection_log.append({
                'timestamp': start_time,
                'path': self.last_selection_path[:],
                'worker_id': self.worker_id,
                'iteration': self.iterations_completed
            })


def test_worker_convergence():
    """Test how well WU-UCT prevents workers from converging on same paths."""
    
    print("🔬 WU-UCT Worker Convergence Test")
    print("=" * 70)
    print("Testing the effectiveness of the WU-UCT virtual loss mechanism")
    print("at preventing workers from selecting the same paths simultaneously.")
    print("=" * 70)
    
    # Load problem
    problem_path = "../OP_Benchmark_Set/grid_sample/grid_10x10_long_50.txt"
    nodes, budget = OrienteeringProblem.load_problem(problem_path)
    problem = OrienteeringProblem(nodes, budget, max_edge_distance=1.42)
    
    print(f"\nProblem: {len(nodes)} nodes, budget={budget}")
    
    # Initialize shared tree
    initial_state = OrienteeringState(problem)
    root = WUUCTNode(initial_state)
    
    # Test parameters
    num_workers = 4
    iterations_per_worker = 100  # Short test to analyze early behavior
    
    print(f"Workers: {num_workers}")
    print(f"Iterations per worker: {iterations_per_worker}")
    print(f"Total iterations: {num_workers * iterations_per_worker}")
    print()
    
    # Create diagnostic workers
    workers = []
    for i in range(num_workers):
        worker = DiagnosticWUWorker(
            problem=problem,
            root=root,
            worker_id=i,
            iterations_per_worker=iterations_per_worker,
            exploration_constant=math.sqrt(2),
            max_distance=1.42
        )
        workers.append(worker)
    
    # Start all workers
    print("🚀 Starting workers...")
    start_time = time.time()
    for worker in workers:
        worker.start()
    
    # Wait for completion
    for worker in workers:
        worker.join()
    
    elapsed = time.time() - start_time
    print(f"✓ Completed in {elapsed:.2f}s\n")
    
    # Analyze results
    print("=" * 70)
    print("📊 CONVERGENCE ANALYSIS")
    print("=" * 70)
    
    # 1. Collision Analysis
    print("\n1️⃣ VIRTUAL LOSS COLLISIONS")
    print("-" * 70)
    print("When a worker selects a node with pending_simulations > 0,")
    print("it means another worker is already exploring that node.")
    print()
    
    total_collisions = sum(w.collision_count for w in workers)
    total_selections = sum(w.iterations_completed for w in workers)
    collision_rate = total_collisions / total_selections if total_selections > 0 else 0
    
    for worker in workers:
        print(f"Worker {worker.worker_id}: {worker.collision_count} collisions "
              f"in {worker.iterations_completed} selections "
              f"({100*worker.collision_count/worker.iterations_completed:.1f}%)")
    
    print(f"\nTotal collision rate: {100*collision_rate:.1f}%")
    print(f"Expected with perfect diversity: ~0%")
    print(f"Expected without WU-UCT: ~75% (3 of 4 workers collide)")
    
    # 2. Path Diversity Analysis
    print("\n2️⃣ PATH DIVERSITY")
    print("-" * 70)
    print("Measuring how diverse the paths selected by workers are.")
    print()
    
    # Collect all selection paths
    all_paths = []
    for worker in workers:
        all_paths.extend(worker.selection_log)
    
    # Sort by timestamp to see concurrent selections
    all_paths.sort(key=lambda x: x['timestamp'])
    
    # Group paths by time windows (10ms windows to catch concurrent selections)
    time_window = 0.01  # 10ms
    concurrent_selections = []
    current_window = []
    current_time = all_paths[0]['timestamp'] if all_paths else 0
    
    for selection in all_paths:
        if selection['timestamp'] - current_time < time_window:
            current_window.append(selection)
        else:
            if len(current_window) > 1:
                concurrent_selections.append(current_window)
            current_window = [selection]
            current_time = selection['timestamp']
    
    if len(current_window) > 1:
        concurrent_selections.append(current_window)
    
    print(f"Found {len(concurrent_selections)} time windows with concurrent selections")
    
    # Analyze diversity in concurrent selections
    if concurrent_selections:
        diverse_selections = 0
        identical_selections = 0
        
        for window in concurrent_selections[:20]:  # Check first 20 windows
            paths = [tuple(s['path']) for s in window]
            unique_paths = len(set(paths))
            
            if unique_paths == len(paths):
                diverse_selections += 1
            elif unique_paths == 1:
                identical_selections += 1
        
        windows_checked = min(20, len(concurrent_selections))
        print(f"\nAnalyzed {windows_checked} concurrent selection windows:")
        print(f"  - Fully diverse (all different paths): {diverse_selections}")
        print(f"  - Identical (all same path): {identical_selections}")
        print(f"  - Partially diverse: {windows_checked - diverse_selections - identical_selections}")
    
    # 3. Tree Structure Analysis
    print("\n3️⃣ TREE STRUCTURE")
    print("-" * 70)
    
    def count_nodes(node):
        count = 1
        for child in node.children:
            count += count_nodes(child)
        return count
    
    def get_root_branching():
        """Get branching factor at root level."""
        return len(root.children)
    
    total_nodes = count_nodes(root)
    root_children = get_root_branching()
    
    print(f"Total nodes in tree: {total_nodes}")
    print(f"Root branching factor: {root_children}")
    print(f"Root visits: {root.visits}")
    print(f"Root pending_simulations: {root.pending_simulations}")
    
    if root.children:
        print(f"\nRoot children visit distribution:")
        child_visits = sorted([c.visits for c in root.children], reverse=True)
        for i, visits in enumerate(child_visits[:10]):  # Top 10
            print(f"  Child {i+1}: {visits} visits")
    
    # 4. WU-UCT Formula Effectiveness
    print("\n4️⃣ WU-UCT FORMULA EFFECTIVENESS")
    print("-" * 70)
    print("The WU-UCT formula should make nodes with pending_simulations")
    print("less attractive, preventing multiple workers from selecting them.")
    print()
    
    # Check if virtual loss is actually being applied and removed
    print(f"Root final pending_simulations: {root.pending_simulations}")
    if root.pending_simulations == 0:
        print("✓ Virtual loss properly removed (pending_simulations = 0)")
    else:
        print(f"⚠ Virtual loss not fully removed (pending_simulations = {root.pending_simulations})")
    
    # 5. Overall Assessment
    print("\n5️⃣ OVERALL ASSESSMENT")
    print("-" * 70)
    
    score = 0
    max_score = 4
    
    if collision_rate < 0.3:
        print("✓ Good: Low collision rate (<30%)")
        score += 1
    else:
        print(f"⚠ High collision rate ({100*collision_rate:.1f}%)")
    
    if root_children >= 3:
        print(f"✓ Good: Multiple root children explored ({root_children})")
        score += 1
    else:
        print(f"⚠ Few root children explored ({root_children})")
    
    if total_nodes > num_workers * iterations_per_worker * 0.5:
        print(f"✓ Good: Healthy tree growth ({total_nodes} nodes)")
        score += 1
    else:
        print(f"⚠ Limited tree growth ({total_nodes} nodes)")
    
    if root.pending_simulations == 0:
        print("✓ Good: Virtual loss mechanism working correctly")
        score += 1
    else:
        print("⚠ Virtual loss not fully cleared")
    
    print(f"\nOverall WU-UCT Effectiveness: {score}/{max_score} ({100*score/max_score:.0f}%)")
    
    if score >= 3:
        print("✅ WU-UCT is effectively preventing worker convergence!")
    else:
        print("⚠️  WU-UCT may need tuning to better prevent convergence")


if __name__ == "__main__":
    try:
        test_worker_convergence()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
