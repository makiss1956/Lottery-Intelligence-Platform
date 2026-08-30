"""Hot-Cold-Warm number classification."""
from typing import Dict, List
from src.core.logger import get_logger

logger = get_logger("TemperatureAnalyzer")

class TemperatureAnalyzer:
    """
    Classifies numbers into Hot (frequent + recent), 
    Cold (rare + absent), Warm (medium).
    """
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def classify_numbers(self) -> Dict[str, Dict[str, List[int]]]:
        """Classify primary and euro numbers by temperature."""
        draws = self.db.get_all_draws()
        total_draws = len(draws)
        
        if total_draws < 10:
            logger.warning("Not enough data for temperature analysis (need >= 10)")
            return {}
        
        # Calculate frequencies
        primary_freq = {i: 0 for i in range(1, 51)}
        euro_freq = {i: 0 for i in range(1, 13)}
        
        for draw in draws:
            for n in draw.get("primary_numbers", []):
                primary_freq[n] += 1
            for n in draw.get("euro_numbers", []):
                euro_freq[n] += 1
        
        # Calculate recency (draws since last appearance)
        primary_recency = {i: total_draws + 1 for i in range(1, 51)}
        euro_recency = {i: total_draws + 1 for i in range(1, 13)}
        
        for idx, draw in enumerate(draws):
            for n in draw.get("primary_numbers", []):
                if primary_recency[n] == total_draws + 1:
                    primary_recency[n] = idx
            for n in draw.get("euro_numbers", []):
                if euro_recency[n] == total_draws + 1:
                    euro_recency[n] = idx
        
        # Classify
        primary_result = self._classify_pool(primary_freq, primary_recency, total_draws)
        euro_result = self._classify_pool(euro_freq, euro_recency, total_draws)
        
        return {
            "primary": primary_result,
            "euro": euro_result
        }
    
    def _classify_pool(self, freq: Dict[int, int], recency: Dict[int, int], 
                       total: int) -> Dict[str, List[int]]:
        """Classify a pool of numbers."""
        avg_freq = sum(freq.values()) / len(freq)
        
        hot = []
        warm = []
        cold = []
        
        for num in freq:
            f = freq[num]
            r = recency[num]
            
            # Hot: above average frequency AND appeared in last 5 draws
            if f > avg_freq * 1.2 and r <= 5:
                hot.append(num)
            # Cold: below average AND absent for > 10 draws
            elif f < avg_freq * 0.8 and r > 10:
                cold.append(num)
            else:
                warm.append(num)
        
        return {
            "hot": sorted(hot),
            "warm": sorted(warm),
            "cold": sorted(cold),
            "stats": {
                "avg_frequency": round(avg_freq, 2),
                "total_draws": total
            }
        }
    
    def get_mixed_candidates(self, hot_ratio: float = 0.4, 
                            warm_ratio: float = 0.4, 
                            cold_ratio: float = 0.2,
                            total: int = 7) -> Dict[str, List[int]]:
        """
        Generate candidates by mixing temperatures.
        Default: 40% hot, 40% warm, 20% cold
        """
        classification = self.classify_numbers()
        if not classification:
            return {}
        
        primary = classification["primary"]
        p_hot = primary["hot"]
        p_warm = primary["warm"]
        p_cold = primary["cold"]
        
        n_hot = int(total * hot_ratio)
        n_warm = int(total * warm_ratio)
        n_cold = total - n_hot - n_warm
        
        candidates = []
        candidates.extend(p_hot[:n_hot])
        candidates.extend(p_warm[:n_warm])
        candidates.extend(p_cold[:n_cold])
        
        # For euro numbers: mostly hot
        euro = classification["euro"]
        euro_candidates = euro["hot"][:2] + euro["warm"][:1]
        
        return {
            "primary_candidates": sorted(candidates[:total]),
            "euro_candidates": sorted(euro_candidates[:3]),
            "temperature_breakdown": {
                "hot_used": n_hot,
                "warm_used": n_warm,
                "cold_used": n_cold
            }
        }
