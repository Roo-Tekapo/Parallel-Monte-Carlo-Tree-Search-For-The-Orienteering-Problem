"""
Reward Normalizer for WU-UCT

This module provides thread-safe reward normalization for MCTS/UCT algorithms.
It tracks the min and max rewards observed during search and normalizes values
to the [0, 1] range to ensure consistent exploration-exploitation balance.
"""

import threading
from typing import Optional


class RewardNormalizer:
    """
    Thread-safe reward normalizer that tracks observed reward range
    and normalizes values to [0, 1].
    
    This ensures that the UCT formula's exploration-exploitation balance
    remains consistent regardless of the actual reward scale of the problem.
    
    Normalization formula:
        normalized = (reward - min_reward) / (max_reward - min_reward)
        
    If all rewards are the same (max == min), returns 0.5 as a neutral value.
    """
    
    def __init__(self, initial_min: Optional[float] = None, 
                 initial_max: Optional[float] = None,
                 epsilon: float = 1e-10):
        """
        Initialize the reward normalizer.
        
        Args:
            initial_min: Optional initial minimum reward (if known beforehand)
            initial_max: Optional initial maximum reward (if known beforehand)
            epsilon: Small value to avoid division by zero
        """
        self.min_reward = initial_min
        self.max_reward = initial_max
        self.epsilon = epsilon
        self._lock = threading.Lock()
        
        # Statistics
        self.num_updates = 0
        
    def update(self, reward: float):
        """
        Update the observed reward range with a new reward value.
        
        This method is thread-safe and should be called after each simulation
        to keep the normalization bounds up to date.
        
        Args:
            reward: New reward value observed
        """
        with self._lock:
            if self.min_reward is None or reward < self.min_reward:
                self.min_reward = reward
            if self.max_reward is None or reward > self.max_reward:
                self.max_reward = reward
            self.num_updates += 1
    
    def normalize(self, reward: float) -> float:
        """
        Normalize a reward value to the [0, 1] range based on observed bounds.
        
        Args:
            reward: Raw reward value to normalize
            
        Returns:
            Normalized reward in [0, 1] range
            Returns 0.5 if no range has been observed yet (min == max)
        """
        with self._lock:
            # If we haven't seen any rewards yet, return the raw value
            if self.min_reward is None or self.max_reward is None:
                return reward
            
            # If all rewards are the same, return neutral value
            reward_range = self.max_reward - self.min_reward
            if reward_range < self.epsilon:
                return 0.5
            
            # Normalize to [0, 1]
            normalized = (reward - self.min_reward) / reward_range
            
            # Clamp to [0, 1] in case reward is outside observed range
            return max(0.0, min(1.0, normalized))
    
    def get_bounds(self):
        """
        Get the current observed reward bounds.
        
        Returns:
            Tuple of (min_reward, max_reward)
        """
        with self._lock:
            return (self.min_reward, self.max_reward)
    
    def get_statistics(self):
        """
        Get normalizer statistics.
        
        Returns:
            Dictionary with normalizer statistics
        """
        with self._lock:
            return {
                'min_reward': self.min_reward,
                'max_reward': self.max_reward,
                'reward_range': (self.max_reward - self.min_reward) 
                               if self.min_reward is not None and self.max_reward is not None 
                               else None,
                'num_updates': self.num_updates
            }
    
    def __repr__(self):
        stats = self.get_statistics()
        return (f"RewardNormalizer(min={stats['min_reward']}, "
                f"max={stats['max_reward']}, "
                f"range={stats['reward_range']}, "
                f"updates={stats['num_updates']})")


class EstimatedRewardNormalizer(RewardNormalizer):
    """
    Reward normalizer that estimates bounds from problem structure.
    
    For orienteering problems, we can estimate:
    - Min reward: score of start node (often 0)
    - Max reward: sum of all node scores (theoretical upper bound)
    
    This can provide better initial bounds than discovering them during search.
    """
    
    def __init__(self, problem, epsilon: float = 1e-10):
        """
        Initialize with estimated bounds from the problem.
        
        Args:
            problem: OrienteeringProblem instance
            epsilon: Small value to avoid division by zero
        """
        # Estimate minimum reward (typically the start node score)
        min_reward = problem.nodes[problem.start_id].score
        
        # Estimate maximum reward (sum of all node scores)
        # This is an upper bound - actual paths will be constrained by distance
        max_reward = sum(node.score for node in problem.nodes)
        
        super().__init__(initial_min=min_reward, 
                        initial_max=max_reward, 
                        epsilon=epsilon)
        
        self.problem = problem
        self.use_estimated_bounds = True
    
    def update(self, reward: float):
        """
        Update bounds, but only allow tightening within estimated range.
        
        Args:
            reward: New reward value observed
        """
        # Still track observed rewards, but don't expand beyond estimates
        with self._lock:
            # We can tighten the min bound if we observe something higher
            if self.min_reward is None or (reward > self.min_reward and self.num_updates < 10):
                # Only update min in early iterations
                pass
            
            # Max bound should stay at the estimated upper bound
            # (we don't want to expand it based on observations)
            
            self.num_updates += 1
    
    def __repr__(self):
        stats = self.get_statistics()
        return (f"EstimatedRewardNormalizer(min={stats['min_reward']}, "
                f"max={stats['max_reward']}, "
                f"range={stats['reward_range']}, "
                f"updates={stats['num_updates']}, "
                f"estimated=True)")
