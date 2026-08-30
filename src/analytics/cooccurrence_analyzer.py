"""Pair and Triple number co-occurrence analysis."""
from itertools import combinations
from collections import Counter
from typing import Dict, List, Tuple
from src.core.logger import get_logger

logger = get_logger("CooccurrenceAnalyzer")

class CooccurrenceAnalyzer:
    """
    Analyzes which numbers appear together frequently.
    Useful for building 'companion' number sets.
    """
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def analyze_pairs(self, min_occurrences: int = 3) -> Dict[Tuple[int, int], int]:
        """Find pairs that appear together most often."""
        draws = self.db.get_all_draws()
        pair_counter = Counter()
        
        for draw in draws:
            nums = sorted(draw.get("primary_numbers", []))
            for pair in combinations(nums, 2):
                pair_counter[pair] += 1
        
        # Filter by minimum occurrences
        significant = {
            pair: count 
            for pair, count in pair_counter.items() 
            if count >= min_occurrences
        }
        
        logger.info("Found %d significant pairs (>= %d occurrences)", 
                    len(significant), min_occurrences)
        return dict(sorted(significant.items(), key=lambda x: -x[1]))
    
    def analyze_triples(self, min_occurrences: int = 2) -> Dict[Tuple[int, int, int], int]:
        """Find triples that appear together."""
        draws = self.db.get_all_draws()
        triple_counter = Counter()
        
        for draw in draws:
            nums = sorted(draw.get("primary_numbers", []))
            for triple in combinations(nums, 3):
                triple_counter[triple] += 1
        
        significant = {
            triple: count 
            for triple, count in triple_counter.items() 
            if count >= min_occurrences
        }
        
        logger.info("Found %d significant triples (>= %d occurrences)", 
                    len(significant), min_occurrences)
        return dict(sorted(significant.items(), key=lambda x: -x[1]))
    
    def get_companion_numbers(self, number: int, top_n: int = 5) -> List[Tuple[int, int]]:
        """Get numbers that most frequently appear with a given number."""
        pairs = self.analyze_pairs(min_occurrences=1)
        companions = []
        
        for (a, b), count in pairs.items():
            if a == number:
                companions.append((b, count))
            elif b == number:
                companions.append((a, count))
        
        return sorted(companions, key=lambda x: -x[1])[:top_n]
    
    def build_cooccurrence_matrix(self) -> Dict[int, Dict[int, int]]:
        """Build full co-occurrence matrix for all numbers."""
        draws = self.db.get_all_draws()
        matrix = {i: {j: 0 for j in range(1, 51)} for i in range(1, 51)}
        
        for draw in draws:
            nums = draw.get("primary_numbers", [])
            for a in nums:
                for b in nums:
                    if a != b:
                        matrix[a][b] += 1
        
        return matrix
    
    def suggest_combinations(self, seed_numbers: List[int], 
                            pool_size: int = 7) -> List[int]:
        """
        Given 1-2 seed numbers, suggest companions to build a set.
        """
        if not seed_numbers:
            return []
        
        matrix = self.build_cooccurrence_matrix()
        scores = {i: 0 for i in range(1, 51)}
        
        for seed in seed_numbers:
            if 1 <= seed <= 50:
                for other, count in matrix[seed].items():
                    scores[other] += count
        
        # Exclude seed numbers from scoring (they're already chosen)
        for seed in seed_numbers:
            scores[seed] = -1
        
        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        companions = [n for n, _ in ranked[:pool_size - len(seed_numbers)]]
        
        return sorted(seed_numbers + companions)
