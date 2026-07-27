import random
from plugins.base_plugin import BasePlugin

class RandomPlugin(BasePlugin):
    def __init__(self):
        super().__init__(
            name="Random Choice Baseline",
            description="Παράγει τυχαίους αριθμούς για χρήση ως σημείο αναφοράς (baseline)."
        )

    def predict(self, history_data: list) -> list:
        # Παράδειγμα: Επιλογή 5 τυχαίων αριθμών από το 1 έως το 50
        return sorted(random.sample(range(1, 51), 5))
