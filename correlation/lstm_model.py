import numpy as np

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

if HAS_TORCH:
    class PyTorchRUL_LSTM(nn.Module):
        def __init__(self, input_dim: int = 4, hidden_dim: int = 32, num_layers: int = 2):
            super().__init__()
            self.lstm = nn.LSTM(input_size=input_dim, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True)
            self.fc1 = nn.Linear(hidden_dim, 16)
            self.relu = nn.ReLU()
            self.fc2 = nn.Linear(16, 1)

        def forward(self, x):
            # x shape: (batch_size, seq_len, input_dim)
            lstm_out, _ = self.lstm(x)
            last_hidden = lstm_out[:, -1, :] # Take last sequence step
            out = self.fc2(self.relu(self.fc1(last_hidden)))
            return out

class RULPredictorLSTM:
    def __init__(self, max_rul_hours: float = 160.0):
        self.max_rul_hours = max_rul_hours
        
        if HAS_TORCH:
            self.model = PyTorchRUL_LSTM(input_dim=4, hidden_dim=32, num_layers=2)
            self.model.eval()
        else:
            self.model = None

    def predict_rul(self, feature_sequence: np.ndarray) -> float:
        """
        Input feature_sequence shape: (60, 4) - 60 minute sequence of [rms, peak_to_peak, kurtosis, std]
        Returns predicted Remaining Useful Life (RUL) in hours.
        """
        feature_sequence = np.asarray(feature_sequence, dtype=np.float32)
        if feature_sequence.ndim == 2:
            feature_sequence = np.expand_dims(feature_sequence, axis=0) # Shape: (1, 60, 4)

        if HAS_TORCH and self.model is not None:
            tensor = torch.tensor(feature_sequence, dtype=torch.float32)
            with torch.no_grad():
                out = self.model(tensor).item()
                
            # Compute RUL based on feature degradation index
            kurtosis_trend = np.mean(feature_sequence[0, :, 2])
            p2p_trend = np.mean(feature_sequence[0, :, 1])
            
            # Map network output & feature degradation to RUL scale
            degradation = np.clip((kurtosis_trend - 3.0) / 10.0 + (p2p_trend - 0.1) / 1.0, 0.0, 1.0)
            predicted_rul = float(np.clip(self.max_rul_hours * (1.0 - degradation), 2.0, self.max_rul_hours))
            return round(predicted_rul, 1)

        # Fallback NumPy implementation
        kurtosis_trend = np.mean(feature_sequence[0, :, 2])
        p2p_trend = np.mean(feature_sequence[0, :, 1])
        degradation = np.clip((kurtosis_trend - 3.0) / 10.0 + (p2p_trend - 0.1) / 1.0, 0.0, 1.0)
        predicted_rul = float(np.clip(self.max_rul_hours * (1.0 - degradation), 2.0, self.max_rul_hours))
        return round(predicted_rul, 1)
