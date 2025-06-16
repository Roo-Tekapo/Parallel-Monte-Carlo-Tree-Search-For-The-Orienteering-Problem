from collections import namedtuple
from Algorithm_Visualisation.monte_carlo_tree_search import Node
from random import choice
from math import sqrt

_TTTB = namedtuple("OrienteeringBoard", "tup locations terminal")

"""
Orienteering Board

Functionality: a number of 'cities' is set, a maximum distance is allowed
the goal is to get to the highest amount of cities within the maximum distance
"""

# Inheriting from a namedtuple is convenient because it makes the class
# immutable and predefines __init__, __repr__, __hash__, __eq__, and others
class OrienteeringBoard(_TTTB, Node):

    "Initialise the board"
    def __new__(cls, tup, locations, terminal):
        global id
        if id is None:
            id = 0
        self = super(OrienteeringBoard, cls).__new__(cls, tup, locations, terminal)
        self.id = id
        id += 1
        return self

    "Return all possible remaining moves (every non visited 'city')"
    def find_children(board):
        if board.terminal:  # If the non-visted list is finished then no moves can be made
            return set()
        # Otherwise, you can make a move in each of the empty spots
        return {
            board.make_move(i) for i in board.locations
        }

    "Select a random 'city' out of remaining 'cities''"
    def find_random_child(board):
        if board.terminal:
            return None  # If the game is finished then no more 'cities' can be visited
        return board.make_move(choice(list(board.locations)))

    "Return reward based on the total amount of cities that have been visited"
    def get_reward(board, origin):
        if not board.terminal:
            raise RuntimeError(f"reward called on nonterminal board {board}")
        else:
            actual_reward = sum(1 for item in board.tup if item is not None)
            global max_reward
            return actual_reward / max_reward # Normalise reward between 0-1 based on total possible 'cities'
    
    "Update the board state after a 'city' has been visited"
    def make_move(board, point):
        index = next(i for i, value in enumerate(board.tup) if value is None)
        point_index = board.locations.index(point)
        locations = board.locations[:point_index] + board.locations[point_index + 1 :]
        tup = board.tup[:index] + (point,) + board.tup[index + 1 :]
        total_distance = board.get_total_distance(tup) # Retrieve the total distance that has been taken visiting each 'city'
        global max
        is_terminal = not any(v is None for v in tup) or total_distance > max # Check if the total distance exceeds the maximum allowed
        newBoard = OrienteeringBoard(tup, locations, is_terminal)
        return newBoard
    
    "Return the total distance between provided cities in set order"
    def get_total_distance(board, tup):
        total_distance = 0
        previous_point = (50, 50)
        for current_point in tup:
            if current_point is None:
                total_distance += board.get_distance(previous_point, (50, 50))
                return total_distance
            total_distance += board.get_distance(previous_point, current_point)
            previous_point = current_point

        total_distance += board.get_distance(tup[-1], (50, 50))
        return total_distance
    
    "Return the distance between 2 points"
    def get_distance(board, pointA, pointB):
        x1, y1 = pointA
        x2, y2 = pointB
        return sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    "Return whether no further moves can be made"
    def is_terminal(board):
        return board.terminal
    
    "Return the id of the node as the name"
    def __str__(self):
        return self.id

"""
Orienteering Problem
"""
class Orienteering():
    
    "Initialise the board"
    def __init__(self, nodes=15, distance=200):
        global id
        id = 0

        # Set the maximum distance allowed
        global max
        max = distance

        # Set the maximum reward possible (for normalisation)
        global max_reward
        max_reward = nodes

        # Generate plane of unique points
        locations = set()
        while len(locations) < nodes:
            point = tuple(sorted((choice(range(100)) for _ in range(2))))
            locations.add(point)

        locations = tuple(locations)
        self.board = OrienteeringBoard(tup=(None,) * (nodes), locations=locations, terminal=False)

    "Return the root node"
    def get_root(self):
        return self.board