"""
Virtual Loss (VL) Parallel MCTS Implementation

This package implements standard Virtual Loss approach for parallel MCTS,
which differs from WU-UCT in how it coordinates parallel workers.

Key Differences from WU-UCT:
- VL: Applies a FIXED penalty value to nodes during selection
- WU-UCT: Tracks pending simulation COUNT that affects UCT calculation

Virtual Loss Mechanism:
1. Thread selects a path using standard UCT
2. Apply fixed virtual loss (negative value) to all nodes in path
3. Perform simulation
4. Remove virtual loss and add actual result

This discourages other threads from selecting the same nodes without
modifying the UCT formula itself.
"""

__version__ = "1.0.0"
__author__ = "VL-MCTS Implementation"
