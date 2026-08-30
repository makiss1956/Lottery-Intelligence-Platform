"""Monte Carlo Simulation Engine for Eurojackpot."""
import random
from typing import Dict, List, Tuple
from collections import Counter
from src.core.logger import get_logger

logger = get_logger("MonteCarlo")

class MonteCarloSimulator:
    """
    Runs thousands of simulated draws based on historical frequencies
    to find the most probable combinations.
    """
    
    def __init__(self, frequency_analyzer, simulations: int = 10000):
        self.freq = frequency_analyzer
        self.simulations = simulations
        self.rng = random.Random()
    
    def run_simulation(self, primary_count: int = 5, euro_count: int = 2) -> Dict:
        """Run Monte Carlo and return top candidates."""
        primary_freqs = self.freq.get_primary_frequencies()
        euro_freqs = self.freq.get_euro_frequencies()
        
        # Normalize frequencies to probabilities
        primary_total = sum(primary_freqs.values())
        euro_total = sum(euro_freqs.values())
        
        primary_probs = {k: v / primary_total for k, v in primary_freqs.items()}
        euro_probs = {k: v / euro_total for k, v in euro_freqs.items()}
        
        primary_counter = Counter()
        euro_counter = Counter()
        combination_counter = Counter()
        
        logger.info("Running %d Monte Carlo simulations...", self.simulations)
        
        for _ in range(self.simulations):
            # Weighted random draw
            primary = self._weighted_sample(
                list(range(1, 51)), 
                [primary_probs.get(i, 0.001) for i in range(1, 51)], 
                primary_count
            )
            euro = self._weighted_sample(
                list(range(1, 13)), 
                [euro_probs.get(i, 0.001) for i in range(1, 13)], 
                euro_count
            )
            
            for n in primary:
                primary_counter[n] += 1
            for n in euro:
                euro_counter[n] += 1
            
            combo_key = tuple(sorted(primary))
            combination_counter[combo_key] += 1
        
        # Get top candidates
        top_primary = [n for n, _ in primary_counter.most_common(20)]
        top_euro = [n for n, _ in euro_counter.most_common(8)]
        top_combinations = combination_counter.most_common(10)
        
        return {
            "primary_candidates": top_primary,
            "euro_candidates": top_euro,
            "top_combinations": top_combinations,
            "primary_probabilities": {
                n: round(c / self.simulations, 4) 
                for n, c in primary_counter.most_common(20)
            },
            "euro_probabilities": {
                n: round(c / self.simulations, 4)
                for n, c in euro_counter.most_common(8)
            },
            "simulations_run": self.simulations
        }
    
    def _weighted_sample(self, population: List[int], weights: List[float], k: int) -> List[int]:
        """Sample without replacement using weights."""
        selected = []
        temp_pop = list(population)
        temp_weights = list(weights)
        
        for _ in range(k):
            if not temp_pop:
                break
            total = sum(temp_weights)
            if total == 0:
                break
            probs = [w / total for w in temp_weights]
            choice = self.rng.choices(temp_pop, weights=probs, k=1)[0]
            idx = temp_pop.index(choice)
            selected.append(choice)
            temp_pop.pop(idx)
            temp_weights.pop(idx)
        
        return selected
