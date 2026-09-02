"""Seeded Random Number Generator for Eurojackpot."""
import random
import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Path setup
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from src.core.logger import get_logger

logger = get_logger("SeededRNG")

class SeededRNGGenerator:
    """
    Deterministic RNG with configurable seed.
    Seed can be based on: draw date, historical stats hash, or custom string.
    """
    
    def __init__(self, seed_source: str = "auto"):
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
        ✅ ΔΙΟΡΘΩΣΗ: Weighted random selection με εγγύηση count αριθμών.
        """
        numbers = list(range(1, total_pool + 1))
        probs = [weights.get(n, 0.01) for n in numbers]
        total_prob = sum(probs)
        if total_prob == 0:
            # Αν όλα τα weights είναι 0, χρησιμοποίησε uniform
            normalized = [1.0 / len(numbers)] * len(numbers)
        else:
            normalized = [p / total_prob for p in probs]
        
        # Χρησιμοποίησε sample αντί για choices για να αποφύγεις duplicates
        # Αν τα weights είναι πολύ skewed, το choices μπορεί να δώσει πολλά duplicates
        # Χρησιμοποιούμε weighted sample without replacement
        selected = []
        temp_numbers = list(numbers)
        temp_weights = list(normalized)
        
        for _ in range(count):
            if not temp_numbers:
                break
            total_w = sum(temp_weights)
            if total_w == 0:
                break
            # Επίλεξε έναν αριθμό
            choice = self.rng.choices(temp_numbers, weights=temp_weights, k=1)[0]
            idx = temp_numbers.index(choice)
            selected.append(choice)
            temp_numbers.pop(idx)
            temp_weights.pop(idx)
        
        # ✅ Fallback: αν δεν βρήκαμε αρκετούς, συμπλήρωσε με random από τα υπόλοιπα
        if len(selected) < count:
            remaining = [n for n in numbers if n not in selected]
            needed = count - len(selected)
            selected.extend(self.rng.sample(remaining, min(needed, len(remaining))))
            logger.warning("RNG weighted fallback used: added %d random numbers", needed)
        
        return sorted(selected[:count])
