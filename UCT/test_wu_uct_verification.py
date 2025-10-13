"""
Test suite to verify WU-UCT implementation correctness and diagnose performance issues.

Tests:
1. Virtual loss/visits calculation (Watch the Unobservable)
2. Thread safety and race conditions
3. Performance profiling and bottleneck identification
4. Queue management and worker synchronization
"""

import time
import math
import sys
import os
from typing import List, Dict, Any
import threading
import queue

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orienteering.orienteering import OrienteeringProblem, OrienteeringState
from UCT.wu_uct_coordinator import WUUCT
from UCT.expansion_worker import WUUCTExpansionWorker
from UCT.simulation_worker import SimulationWorkerPool
from UCT.uct_single_thread import UCTNode, UCTSingleThread
from UCT.wu_uct_node import WUUCTNode


class WUUCTVerifier:
    """Comprehensive testing and verification for WU-UCT implementation."""
    
    def __init__(self, problem: OrienteeringProblem):
        self.problem = problem
        self.test_results = {}
    
    def test_virtual_loss_presence(self):
        """
        Test 1: Check if virtual loss mechanism is implemented.
        
        Virtual loss (Watch the Unobservable) means:
        - When a node is selected for simulation, it should get a temporary penalty
        - This prevents other workers from selecting the same node
        - The penalty is removed when the simulation completes
        
        EXPECTED: Nodes should track pending simulations
        ACTUAL: Need to verify if this is implemented
        """
        print("\n" + "="*70)
        print("TEST 1: Watch the Unobservable Mechanism")
        print("="*70)
        
        # Check if WUUCTNode has pending_simulations tracking
        wu_test_node = WUUCTNode(OrienteeringState(self.problem))
        uct_test_node = UCTNode(OrienteeringState(self.problem))
        
        wu_has_pending = hasattr(wu_test_node, 'pending_simulations')
        uct_has_pending = hasattr(uct_test_node, 'pending_simulations')
        wu_has_method = hasattr(wu_test_node, 'wu_uct_select_child')
        
        print(f"[PASS] Checking node attributes:")
        print(f"  - WUUCTNode has 'pending_simulations': {wu_has_pending}")
        print(f"  - WUUCTNode has 'wu_uct_select_child': {wu_has_method}")
        print(f"  - UCTNode has 'pending_simulations': {uct_has_pending}")
        
        if not wu_has_pending or not wu_has_method:
            print(f"\n[FAIL] CRITICAL: Watch the Unobservable NOT implemented!")
            print(f"   WUUCTNode needs pending_simulations and wu_uct_select_child")
            self.test_results['watch_unobservable'] = 'MISSING'
        elif uct_has_pending:
            print(f"\n[WARN] UCTNode should NOT have pending_simulations")
            print(f"   Only WUUCTNode (parallel) needs this, not UCTNode (single-threaded)")
            self.test_results['watch_unobservable'] = 'MIXED'
        else:
            print(f"\n[PASS] Watch the Unobservable correctly implemented")
            print(f"   WUUCTNode has mechanism, UCTNode is clean")
            self.test_results['watch_unobservable'] = 'CORRECT'
        
        return self.test_results['watch_unobservable'] == 'CORRECT'
    
    def test_uct_selection_with_pending(self):
        """
        Test 2: Verify UCT selection considers pending simulations.
        
        When multiple nodes are being simulated, the UCT formula should account for this:
        UCT = Q/N + C * sqrt(ln(N_parent) / (N + virtual_visits))
        
        Without this, the same promising node gets selected repeatedly.
        """
        print("\n" + "="*70)
        print("TEST 2: UCT Selection with Pending Simulations")
        print("="*70)
        
        # Create a simple tree
        root = UCTNode(OrienteeringState(self.problem))
        
        # Add some children and give them different values
        actions = root.state.get_available_actions()[:3]
        children = []
        for action in actions:
            new_state = root.state.apply_action(action)
            child = UCTNode(new_state, parent=root)
            root.add_child(child)
            children.append(child)
        
        # Simulate some visits
        children[0].visits = 10
        children[0].total_reward = 80  # Average: 8.0
        children[1].visits = 5
        children[1].total_reward = 45  # Average: 9.0 (better!)
        children[2].visits = 3
        children[2].total_reward = 24  # Average: 8.0
        
        root.visits = 18
        
        # Test selection multiple times
        selections = []
        for i in range(10):
            selected = root.uct_select_child(math.sqrt(2))
            selections.append(children.index(selected))
        
        print(f"[OK] Selection distribution over 10 trials:")
        for i, child in enumerate(children):
            count = selections.count(i)
            avg_reward = child.get_average_reward()
            print(f"  Child {i}: Selected {count} times, Avg Reward: {avg_reward:.2f}")
        
        # Check if the same node is selected too often (sign of missing virtual loss)
        max_selection = max([selections.count(i) for i in range(len(children))])
        if max_selection >= 8:  # If one node is selected 80%+ of the time
            print(f"\n[WARN]  WARNING: Same node selected {max_selection}/10 times")
            print(f"   This suggests missing virtual loss mechanism")
            print(f"   In parallel execution, this causes worker redundancy")
            self.test_results['uct_selection'] = 'POTENTIALLY_REDUNDANT'
        else:
            print(f"\n[OK] Selection appears reasonably distributed")
            self.test_results['uct_selection'] = 'GOOD'
        
        return self.test_results['uct_selection'] == 'GOOD'
    
    def test_pending_work_tracking(self):
        """
        Test 3: Verify expansion worker properly tracks pending work.
        
        The expansion worker should:
        1. Track which nodes have pending simulations
        2. Know which work_ids correspond to which nodes
        3. Not lose track of pending work
        """
        print("\n" + "="*70)
        print("TEST 3: Pending Work Tracking")
        print("="*70)
        
        # Create expansion worker
        work_queue = queue.Queue()
        result_queue = queue.Queue()
        
        worker = WUUCTExpansionWorker(
            self.problem,
            worker_id=0,
            work_queue=work_queue,
            result_queue=result_queue,
            max_iterations=10
        )
        
        worker.initialize_root()
        
        # Generate some work units
        print(f"[OK] Generating work units...")
        work_units = []
        for i in range(5):
            work_unit = worker.selection_and_expansion()
            if work_unit:
                work_units.append(work_unit)
        
        print(f"  Generated {len(work_units)} work units")
        print(f"  Pending work: {len(worker.pending_work)} items")
        
        if len(work_units) != len(worker.pending_work):
            print(f"\n[FAIL] ERROR: Work unit count mismatch!")
            print(f"   Generated: {len(work_units)}, Tracked: {len(worker.pending_work)}")
            self.test_results['pending_tracking'] = 'MISMATCH'
        else:
            print(f"\n[OK] Pending work tracking appears correct")
            self.test_results['pending_tracking'] = 'GOOD'
        
        # Check work_id encoding
        if work_units:
            first_id = work_units[0].work_id
            worker_id = first_id >> 16
            counter = first_id & 0xFFFF
            print(f"\n[OK] Work ID encoding:")
            print(f"  Full ID: {first_id}")
            print(f"  Worker ID: {worker_id} (expected: 0)")
            print(f"  Counter: {counter}")
        
        return self.test_results['pending_tracking'] == 'GOOD'
    
    def test_performance_bottlenecks(self):
        """
        Test 4: Identify performance bottlenecks in WU-UCT.
        
        Common issues:
        1. Lock contention - too much time waiting for locks
        2. Queue synchronization overhead
        3. Slow simulation worker throughput
        4. Memory allocation overhead
        """
        print("\n" + "="*70)
        print("TEST 4: Performance Bottleneck Analysis")
        print("="*70)
        
        # Run short benchmark
        iterations = 1000
        wu_uct = WUUCT(self.problem, 
                      expansion_workers=1,
                      simulation_workers=3,
                      exploration_constant=math.sqrt(2))
        
        print(f"[OK] Running {iterations} iterations with 1 expansion + 3 simulation workers...")
        start_time = time.time()
        wu_uct.run(max_iterations=iterations, verbose=False)
        elapsed = time.time() - start_time
        
        stats = wu_uct.get_statistics()
        
        print(f"\n[OK] Performance Metrics:")
        print(f"  Total time: {elapsed:.3f}s")
        print(f"  Iterations/second: {iterations/elapsed:.1f}")
        print(f"  Average time per iteration: {elapsed/iterations*1000:.2f}ms")
        
        # Get detailed worker stats
        for worker in wu_uct.expansion_workers:
            worker_stats = worker.get_thread_statistics()
            print(f"\n  Expansion Worker {worker_stats['worker_id']}:")
            print(f"    - Iterations: {worker_stats['iterations']}")
            print(f"    - Nodes expanded: {worker_stats['nodes_expanded']}")
            print(f"    - Simulations requested: {worker_stats['simulations_requested']}")
            print(f"    - Simulations processed: {worker_stats['simulations_processed']}")
            print(f"    - Pending: {worker_stats['pending_simulations']}")
            
            # Check for backlog
            if worker_stats['pending_simulations'] > 100:
                print(f"    [WARN]  HIGH BACKLOG: {worker_stats['pending_simulations']} pending")
                self.test_results['performance'] = 'HIGH_BACKLOG'
            
            # Check simulation completion rate
            if worker_stats['simulations_requested'] > 0:
                completion_rate = worker_stats['simulations_processed'] / worker_stats['simulations_requested']
                print(f"    - Completion rate: {completion_rate*100:.1f}%")
                if completion_rate < 0.9:
                    print(f"    [WARN]  LOW COMPLETION RATE: Only {completion_rate*100:.1f}%")
        
        # Compare with single-threaded
        print(f"\n[OK] Running single-threaded UCT for comparison...")
        uct_single = UCTSingleThread(self.problem, iterations=iterations)
        start_time = time.time()
        uct_single.run()
        single_elapsed = time.time() - start_time
        
        print(f"  Single-threaded time: {single_elapsed:.3f}s")
        print(f"  Single-threaded rate: {iterations/single_elapsed:.1f} it/s")
        
        speedup = single_elapsed / elapsed
        print(f"\n[OK] Speedup Analysis:")
        print(f"  Speedup: {speedup:.2f}x")
        print(f"  Efficiency: {speedup/3*100:.1f}% (for 3 simulation workers)")
        
        if speedup < 1.5:
            print(f"  [WARN]  LOW SPEEDUP: Expected ~2-3x with 3 workers")
            print(f"     Possible causes:")
            print(f"     - Lock contention")
            print(f"     - Queue synchronization overhead")
            print(f"     - Imbalanced work distribution")
            self.test_results['performance'] = 'SLOW_SPEEDUP'
        elif speedup < 2.0:
            print(f"  [WARN]  MODERATE SPEEDUP: Could be better")
            self.test_results['performance'] = 'MODERATE'
        else:
            print(f"  [OK] GOOD SPEEDUP")
            self.test_results['performance'] = 'GOOD'
        
        return self.test_results['performance'] in ['GOOD', 'MODERATE']
    
    def test_thread_safety(self):
        """
        Test 5: Check for thread safety issues.
        
        Issues to look for:
        1. Race conditions in tree updates
        2. Lost updates due to missing locks
        3. Deadlocks
        """
        print("\n" + "="*70)
        print("TEST 5: Thread Safety")
        print("="*70)
        
        # Run multiple quick runs and check consistency
        results = []
        for run in range(3):
            wu_uct = WUUCT(self.problem, 
                          expansion_workers=1,
                          simulation_workers=4)
            best_state = wu_uct.run(max_iterations=500, verbose=False)
            stats = wu_uct.get_statistics()
            results.append(stats)
            print(f"  Run {run+1}: {stats['total_iterations']} iterations, "
                  f"{stats['total_nodes']} nodes")
        
        # Check if results are consistent
        iterations_match = all(r['total_iterations'] == results[0]['total_iterations'] 
                              for r in results)
        
        if not iterations_match:
            print(f"\n[WARN]  WARNING: Inconsistent iteration counts across runs")
            print(f"   This could indicate race conditions or lost updates")
            self.test_results['thread_safety'] = 'INCONSISTENT'
        else:
            print(f"\n[OK] Iteration counts consistent across runs")
            self.test_results['thread_safety'] = 'GOOD'
        
        return self.test_results['thread_safety'] == 'GOOD'
    
    def run_all_tests(self):
        """Run all verification tests."""
        print("\n" + "="*70)
        print("WU-UCT COMPREHENSIVE VERIFICATION TEST SUITE")
        print("="*70)
        
        tests = [
            ("Virtual Loss", self.test_virtual_loss_presence),
            ("UCT Selection", self.test_uct_selection_with_pending),
            ("Pending Work Tracking", self.test_pending_work_tracking),
            ("Performance Bottlenecks", self.test_performance_bottlenecks),
            ("Thread Safety", self.test_thread_safety),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                passed = test_func()
                results.append((test_name, passed))
            except Exception as e:
                print(f"\n[FAIL] ERROR in {test_name}: {e}")
                import traceback
                traceback.print_exc()
                results.append((test_name, False))
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        for test_name, passed in results:
            status = "[OK] PASS" if passed else "[FAIL] FAIL"
            print(f"{status:10} {test_name}")
        
        print("\n" + "="*70)
        print("DETAILED FINDINGS")
        print("="*70)
        for key, value in self.test_results.items():
            print(f"  {key}: {value}")
        
        return all(passed for _, passed in results)


def main():
    """Main test execution."""
    print("Loading test problem...")
    
    # Use a small problem for testing
    problem_file = "../OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    if not os.path.exists(problem_file):
        problem_file = "OP_Benchmark_Set/set_64_1/set_64_1_80.txt"
    
    nodes, budget = OrienteeringProblem.load_problem(problem_file)
    problem = OrienteeringProblem(nodes, budget)
    
    print(f"Problem loaded: {len(nodes)} nodes, budget: {budget}")
    
    # Run verification
    verifier = WUUCTVerifier(problem)
    all_passed = verifier.run_all_tests()
    
    if not all_passed:
        print("\n" + "="*70)
        print("RECOMMENDED FIXES")
        print("="*70)
        
        if verifier.test_results.get('virtual_loss') == 'MISSING':
            print("\n1. ADD VIRTUAL LOSS MECHANISM:")
            print("   - Add 'pending_simulations' counter to UCTNode")
            print("   - Modify UCT selection to account for pending simulations")
            print("   - Update formula: UCT = Q/N + C * sqrt(ln(N_parent) / (N + pending))")
            
        if verifier.test_results.get('performance') in ['SLOW_SPEEDUP', 'HIGH_BACKLOG']:
            print("\n2. OPTIMIZE PERFORMANCE:")
            print("   - Reduce lock scope in expansion worker")
            print("   - Use lock-free queues if possible")
            print("   - Batch backpropagation updates")
            print("   - Profile with cProfile to identify hotspots")
        
        if verifier.test_results.get('thread_safety') == 'INCONSISTENT':
            print("\n3. FIX THREAD SAFETY ISSUES:")
            print("   - Ensure all tree modifications are locked")
            print("   - Use atomic operations where possible")
            print("   - Add assertions to verify lock ownership")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
