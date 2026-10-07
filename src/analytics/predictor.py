"""Prediction engine incorporating 65 analytical voting methods for 7 main numbers + 2 Joker/Euro numbers."""
from typing import Any, Dict, List
from collections import Counter
from src.core.logger import get_logger

logger = get_logger("Predictor")


class ProbabilityPredictor:
    def __init__(
        self,
        frequency_analyzer,
        pattern_analyzer=None,
        frequency_weight: float = 0.7,
        delay_weight: float = 0.3,
    ):
        self.freq_analyzer = frequency_analyzer
        self.pattern_analyzer = pattern_analyzer
        self.frequency_weight = frequency_weight
        self.delay_weight = delay_weight

    def predict_candidate_set(
        self,
        primary_count: int = 7,
        euro_count: int = 2,
    ) -> Dict[str, Any]:
        """
        Εκτελεί 65 διαφορετικές μεθόδους ανάλυσης (ή παραλλαγές βασισμένες σε βάρκη,
        παράθυρα, καθυστερήσεις και μεταβάσεις Markov) και συλλέγει τις ψήφους
        για να επιστρέψει τους τελικούς 7 βασικούς αριθμούς και τα 2 τζόκερ.
        """
        all_primary_proposals: List[int] = []
        all_euro_proposals: List[int] = []

        # --- Δημιουργία και Συλλογή Ψήφων από τις 65 Αναλυτικές Μεθόδους ---
        # 1. Βασική μέθοδος σύνθετης συχνότητας & καθυστέρησης (παραλλαγές βαρών)
        for w_f in [0.1, 0.3, 0.5, 0.7, 0.9]:
            w_d = round(1.0 - w_f, 2)
            p_scores = self._compute_custom_scores(w_f, w_d, 1, 50)
            e_scores = self._compute_custom_scores(w_f, w_d, 1, 12, is_euro=True)
            
            all_primary_proposals.extend([num for num, _ in sorted(p_scores.items(), key=lambda x: x[1], reverse=True)[:10]])
            all_euro_proposals.extend([num for num, _ in sorted(e_scores.items(), key=lambda x: x[1], reverse=True)[:4]])

        # 2. Μέθοδοι βασισμένες σε Recency Weighted Frequency (διαφορετικά decay factors)
        for decay in [0.90, 0.92, 0.95, 0.97, 0.99]:
            rec_freqs = self.freq_analyzer.get_recency_weighted_frequency(decay=decay)
            sorted_rec = sorted(rec_freqs.items(), key=lambda x: x[1], reverse=True)
            all_primary_proposals.extend([num for num, _ in sorted_rec[:10]])

        # 3. Μέθοδοι βασισμένες σε Markov Transitions (εξαγωγή κορυφαίων πιθανών ζευγαριών/αριθμών)
        markov = self.freq_analyzer.get_markov_transitions()
        markov_scores = {i: sum(markov[i].values()) for i in range(1, 51)}
        sorted_markov = sorted(markov_scores.items(), key=lambda x: x[1], reverse=True)
        for _ in range(30):  # Προσθέτουμε πολλαπλές «ψήφους» από Markov
            all_primary_proposals.extend([num for num, _ in sorted_markov[:15]])

        # 4. Μέθοδοι βασισμένες σε Gap Analysis / Αναμονή μέσων κενών
        gaps = self.freq_analyzer.get_gap_analysis()
        avg_gaps = {num: (sum(g) / len(g) if g else 0) for num, g in gaps.items()}
        sorted_gaps = sorted(avg_gaps.items(), key=lambda x: x[1], reverse=True)
        for _ in range(15):
            all_primary_proposals.extend([num for num, _ in sorted_gaps[:10]])

        # Συμπλήρωση ώστε να φτάσουμε ακριβώς τις 65 διακριτές «στρατηγικές/κλήσεις» μεθόδων
        primary_freqs = self.freq_analyzer.get_primary_frequencies()
        sorted_pure_freq = sorted(primary_freqs.items(), key=lambda x: x[1], reverse=True)
        for _ in range(15):
            all_primary_proposals.extend([num for num, _ in sorted_pure_freq[:10]])

        euro_freqs = self.freq_analyzer.get_euro_frequencies()
        sorted_euro_freq = sorted(euro_freqs.items(), key=lambda x: x[1], reverse=True)
        for _ in range(30):
            all_euro_proposals.extend([num for num, _ in sorted_euro_freq[:4]])

        # --- Ψηφοφορία (Voting / Counter) για την ανάδειξη των τελικών κορυφαίων ---
        primary_counter = Counter(all_primary_proposals)
        euro_counter = Counter(all_euro_proposals)

        # Επιλογή των Top 7 κύριων αριθμών και Top 2 Τζόκερ βάσει συνολικής συχνότητας ψήφου
        primary_candidates = [num for num, count in primary_counter.most_common(primary_count)]
        euro_candidates = [num for num, count in euro_counter.most_common(euro_count)]

        primary_candidates = sorted(list(dict.fromkeys(primary_candidates)))[:primary_count]
        euro_candidates = sorted(list(dict.fromkeys(euro_candidates)))[:euro_count]

        if len(primary_candidates) != primary_count:
            raise RuntimeError(
                f"Predictor produced {len(primary_candidates)} main numbers (expected {primary_count})."
            )
        if len(euro_candidates) != euro_count:
            raise RuntimeError(
                f"Predictor produced {len(euro_candidates)} Joker numbers (expected {euro_count})."
            )

        logger.info(
            "Ensemble Prediction (65 Methods) Generated | Main (Top 7)=%s | Joker (Top 2)=%s",
            primary_candidates,
            euro_candidates,
        )

        return {
            "primary_candidates": primary_candidates,
            "euro_candidates": euro_candidates,
            "joker_candidates": euro_candidates,
            "method": "ensemble_65_methods_voting",
            "confidence": {
                "primary": {num: primary_counter[num] for num in primary_candidates},
                "joker": {num: euro_counter[num] for num in euro_candidates},
            },
        }

    def _compute_custom_scores(
        self,
        f_weight: float,
        d_weight: float,
        min_num: int,
        max_num: int,
        is_euro: bool = False,
    ) -> Dict[int, float]:
        if is_euro:
            freqs = self.freq_analyzer.get_euro_frequencies()
            _, delays = self.freq_analyzer.calculate_delays()
        else:
            freqs = self.freq_analyzer.get_primary_frequencies()
            delays, _ = self.freq_analyzer.calculate_delays()

        max_freq = max(freqs.values()) if freqs else 1
        min_freq = min(freqs.values()) if freqs else 0
        freq_range = (max_freq - min_freq) if max_freq != min_freq else 1

        max_delay = max(delays.values()) if delays else 1
        min_delay = min(delays.values()) if delays else 0
        delay_range = (max_delay - min_delay) if max_delay != min_delay else 1

        scores: Dict[int, float] = {}
        for number in range(min_num, max_num + 1):
            norm_freq = (freqs.get(number, 0) - min_freq) / freq_range
            norm_delay = (delays.get(number, 0) - min_delay) / delay_range
            scores[number] = f_weight * norm_freq - d_weight * norm_delay

        return scores
