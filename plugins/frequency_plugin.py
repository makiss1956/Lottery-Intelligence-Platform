"""
Lottery Intelligence Platform
Frequency Analysis Plugin
"""

from collections import Counter

class FrequencyPlugin:

    def __init__(self, name="Frequency Analysis"):
        self.name = name

    def analyze(self, draws):
        all_numbers = []

        for draw in draws:
            all_numbers.extend(draw)

        counts = Counter(all_numbers)

        return sorted(counts.items(), key=lambda x: x[1], reverse=True)
# Frequency Plugin
