from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import math


def read_op_file(filename):
    with open(filename, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    Tmax, P = map(float, lines[0].split())
    Tmax = float(Tmax)
    P = int(P)

    coords = []
    scores = []
    for line in lines[1:]:
        x, y, s = map(float, line.split())
        coords.append((x, y))
        scores.append(s)

    return Tmax, P, coords, scores


def euclidean_distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def create_data_model(filename):
    Tmax, P, coords, scores = read_op_file(filename)

    n = len(coords)
    dist_matrix = [[euclidean_distance(coords[i], coords[j]) for j in range(n)] for i in range(n)]

    data = {
        'distance_matrix': dist_matrix,
        'rewards': scores,
        'num_nodes': n,
        'num_vehicles': P,
        'starts': [0],
        'ends': [1],
        'Tmax': Tmax,
    }
    return data


def main(filename):
    data = create_data_model(filename)

    manager = pywrapcp.RoutingIndexManager(
        data['num_nodes'],
        data['num_vehicles'],
        data['starts'],
        data['ends']
    )

    routing = pywrapcp.RoutingModel(manager)

    # --- Distance callback ---
    # Use scaling factor to preserve precision while using integers
    SCALE_FACTOR = 10000
    
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(data['distance_matrix'][from_node][to_node] * SCALE_FACTOR)

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # --- Add travel distance constraint (budget) ---
    routing.AddDimension(
        transit_callback_index,
        0,  # slack
        int(data['Tmax'] * SCALE_FACTOR),  # max travel (scaled)
        True,  # start cumul to zero
        'Distance'
    )

    # --- Make intermediate nodes optional with reward-based penalties ---
    # OR-Tools MINIMIZES cost, so:
    # - HIGH penalty for skipping = HIGH reward node (expensive to skip)
    # - LOW penalty for skipping = LOW reward node (cheap to skip)
    PENALTY_MULTIPLIER = 1000000  # Large multiplier to prioritize rewards
    
    for node in range(2, data['num_nodes']):  # skip start (0) and end (1)
        reward = data['rewards'][node]
        # Penalty for NOT visiting this node = reward * multiplier
        # This makes high-reward nodes expensive to skip
        penalty = int(reward * PENALTY_MULTIPLIER)
        routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

    # --- Search parameters ---
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING
    search_parameters.time_limit.seconds = 60  # Increase time for better solutions
    search_parameters.log_search = False

    # --- Solve ---
    solution = routing.SolveWithParameters(search_parameters)

    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print("No solution found.")


def print_solution(data, manager, routing, solution):
    print("\n" + "="*80)
    print("OR-TOOLS SOLUTION")
    print("="*80)
    print(f"\nObjective Value: {solution.ObjectiveValue()}")

    route_distance = 0
    route_score = 0
    path = []
    index = routing.Start(0)
    
    # Build the route
    while not routing.IsEnd(index):
        node_index = manager.IndexToNode(index)
        path.append(node_index)
        route_score += data['rewards'][node_index]
        
        previous_index = index
        index = solution.Value(routing.NextVar(index))
        
        # Add distance to next node
        from_node = manager.IndexToNode(previous_index)
        to_node = manager.IndexToNode(index)
        route_distance += data['distance_matrix'][from_node][to_node]
    
    # Add final node (end depot)
    final_node = manager.IndexToNode(index)
    path.append(final_node)
    route_score += data['rewards'][final_node]
    
    # Print results
    print(f"\nPath: {' -> '.join(map(str, path))}")
    print(f"Total Reward: {route_score:.2f}")
    print(f"Total Distance: {route_distance:.4f} / {data['Tmax']:.4f}")
    print(f"Budget Usage: {(route_distance/data['Tmax']*100):.1f}%")
    print(f"Nodes Visited: {len(path)}")
    
    # Validation
    print("\n" + "-"*80)
    print("VALIDATION")
    print("-"*80)
    
    is_valid = True
    if route_distance > data['Tmax'] + 1e-6:
        print(f"❌ Budget violated: {route_distance:.4f} > {data['Tmax']:.4f}")
        is_valid = False
    else:
        print(f"✓ Budget satisfied: {route_distance:.4f} <= {data['Tmax']:.4f}")
    
    if path[0] != 0:
        print(f"❌ Path doesn't start at node 0")
        is_valid = False
    else:
        print(f"✓ Path starts at node 0 (start depot)")
    
    if path[-1] != 1:
        print(f"❌ Path doesn't end at node 1")
        is_valid = False
    else:
        print(f"✓ Path ends at node 1 (end depot)")
    
    if len(path) != len(set(path[:-1])) + 1:
        print(f"❌ Path contains duplicate nodes")
        is_valid = False
    else:
        print(f"✓ No duplicate nodes in path")
    
    if is_valid:
        print("\n✅ Solution is VALID")
    else:
        print("\n❌ Solution is INVALID")
    
    print("="*80)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt'
        print(f"No file specified, using default: {filename}\n")
    
    main(filename)
