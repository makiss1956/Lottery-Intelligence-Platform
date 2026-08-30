"""Seeded Random Number Generator for Eurojackpot."""
import random
import hashlib
from datetime import datetime
from typing import List, Dict
from src.core.logger import get_logger

logger = get_logger("SeededRNG")

class SeededRNGGenerator:
    """
    Deterministic RNG with configurable seed.
    Seed can be based on: draw date, historical stats hash, or custom string.
    """
    
    def __init__(self, seed_source: str = "auto"):
        """
        seed_source: "auto" (draw date), "stats" (hash of frequencies), 
                     or any custom string
        """
        self.seed_source = seed_source
        self.rng = random.Random()
    
    def set_seed_from_draw_date(self, draw_date: str = None):
        """Seed based on upcoming draw date."""
        if draw_date is None:
            draw_date = datetime.now().strftime("%Y-%m-%d")
        seed = int(hashlib.md5(draw_date.encode()).hexdigest(), 16)
        self.rng.seed(seed)
        logger.info("RNG seeded with draw date: %s (seed=%d)", draw_date, seed)
        return self
    
    def set_seed_from_stats(self, frequencies: Dict[int, int]):
        """Seed based on hash of current frequency distribution."""
        freq_str = ",".join(f"{k}:{v}" for k, v in sorted(frequencies.items()))
        seed = int(hashlib.md5(freq_str.encode()).hexdigest(), 16)
        self.rng.seed(seed)
        logger.info("RNG seeded from frequency hash (seed=%d)", seed)
        return self
    
    def set_custom_seed(self, seed: int):
        self.rng.seed(seed)
        logger.info("RNG seeded with custom seed: %d", seed)
        return self
    
    def generate_primary(self, pool: List[int] = None, count: int = 5) -> List[int]:
        """Generate primary numbers using weighted random selection."""
        if pool is None:
            pool = list(range(1, 51))
        
        selected = self.rng.sample(pool, count)
        return sorted(selected)
    
    def generate_euro(self, pool: List[int] = None, count: int = 2) -> List[int]:
        """Generate euro numbers."""
        if pool is None:
            pool = list(range(1, 13))
        selected = self.rng.sample(pool, count)
        return sorted(selected)
    
    def generate_weighted(self, weights: Dict[int, float], 
                          count: int = 5, 
                          total_pool: int = 50) -> List[int]:
        """
        Weighted random selection. Numbers with higher weights 
        have higher probability of selection.
        """
        numbers = list(range(1, total_pool + 1))
        probs = [weights.get(n, 0.01) for n in numbers]
        total_prob = sum(probs)
        normalized = [p / total_prob for p in probs]
        
        selected = self.rng.choices(numbers, weights=normalized, k=count * 3)
        # Remove duplicates and take top count
        unique = []
        for n in selected:
            if n not in unique:
                unique.append(n)
            if len(unique) == count:
                break
        
        return sorted(unique[:count])
