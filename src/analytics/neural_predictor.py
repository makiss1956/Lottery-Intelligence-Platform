"""Simple Neural Network predictor for Eurojackpot."""
import numpy as np
from typing import Dict, List, Tuple
from src.core.logger import get_logger

logger = get_logger("NeuralPredictor")

class NeuralPredictor:
    """
    Simple feedforward neural network that learns patterns
    from historical draws. Uses one-hot encoding.
    """
    
    def __init__(self, db_manager, hidden_size: int = 64, 
                 learning_rate: float = 0.01):
        self.db = db_manager
        self.hidden_size = hidden_size
        self.lr = learning_rate
        self.weights_input = None
        self.weights_hidden = None
        self.bias_hidden = None
        self.bias_output = None
        self.is_trained = False
    
    def _draw_to_vector(self, numbers: List[int], size: int = 50) -> np.ndarray:
        """Convert number list to one-hot vector."""
        vec = np.zeros(size)
        for n in numbers:
            if 1 <= n <= size:
                vec[n - 1] = 1.0
        return vec
    
    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))
    
    def _sigmoid_derivative(self, x: np.ndarray) -> np.ndarray:
        return x * (1 - x)
    
    def train(self, epochs: int = 1000) -> None:
        """Train on historical data to predict next draw."""
        draws = self.db.get_all_draws()
        if len(draws) < 20:
            logger.warning("Need at least 20 draws for neural training")
            return
        
        # Prepare training data: input = draw N, target = draw N+1
        X = []
        y = []
        
        for i in range(len(draws) - 1):
            current = self._draw_to_vector(draws[i]["primary_numbers"])
            next_draw = self._draw_to_vector(draws[i + 1]["primary_numbers"])
            X.append(current)
            y.append(next_draw)
        
        X = np.array(X)
        y = np.array(y)
        
        # Initialize weights
        np.random.seed(42)
        self.weights_input = np.random.randn(50, self.hidden_size) * 0.1
        self.weights_hidden = np.random.randn(self.hidden_size, 50) * 0.1
        self.bias_hidden = np.zeros((1, self.hidden_size))
        self.bias_output = np.zeros((1, 50))
        
        # Training loop
        for epoch in range(epochs):
            # Forward pass
            hidden = self._sigmoid(np.dot(X, self.weights_input) + self.bias_hidden)
            output = self._sigmoid(np.dot(hidden, self.weights_hidden) + self.bias_output)
            
            # Backward pass
            output_error = y - output
            output_delta = output_error * self._sigmoid_derivative(output)
            
            hidden_error = output_delta.dot(self.weights_hidden.T)
            hidden_delta = hidden_error * self._sigmoid_derivative(hidden)
            
            # Update weights
            self.weights_hidden += hidden.T.dot(output_delta) * self.lr
            self.bias_output += np.sum(output_delta, axis=0, keepdims=True) * self.lr
            self.weights_input += X.T.dot(hidden_delta) * self.lr
            self.bias_hidden += np.sum(hidden_delta, axis=0, keepdims=True) * self.lr
            
            if epoch % 200 == 0:
                loss = np.mean(np.square(output_error))
                logger.info("Epoch %d, Loss: %.4f", epoch, loss)
        
        self.is_trained = True
        logger.info("Neural network training complete")
    
    def predict(self, last_draw: List[int] = None) -> Dict[str, any]:
        """Predict next draw probabilities."""
        if not self.is_trained:
            logger.warning("Model not trained. Training now...")
            self.train()
        
        if last_draw is None:
            draws = self.db.get_all_draws()
            last_draw = draws[0]["primary_numbers"] if draws else []
        
        input_vec = self._draw_to_vector(last_draw)
        hidden = self._sigmoid(np.dot(input_vec, self.weights_input) + self.bias_hidden)
        output = self._sigmoid(np.dot(hidden, self.weights_hidden) + self.bias_output)
        
        # Get top 7 candidates
        probabilities = output[0]
        ranked = sorted(enumerate(probabilities), key=lambda x: -x[1])
        candidates = [i + 1 for i, _ in ranked[:7]]
        conf = {i + 1: round(float(p), 4) for i, p in ranked[:7]}
        
        return {
            "primary_candidates": candidates,
            "confidence": conf,
            "method": "simple_mlp_neural"
        }
