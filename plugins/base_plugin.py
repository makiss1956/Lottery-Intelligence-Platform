from abc import ABC, abstractmethod

class BasePlugin(ABC):
    """
    Abstract Base Class για όλα τα Plugins/Αλγόριθμους.
    Κάθε νέος αλγόριθμος πρέπει να κληρονομεί από αυτή την κλάση.
    """
   
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def predict(self, history_data: list) -> list:
        """
        Επιστρέφει μια λίστα με τους προτεινόμενους αριθμούς.
        Must be implemented by each plugin.
        """
        pass
