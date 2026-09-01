import numpy as np
import pandas as pd

def extract_statistical_features(signal: np.ndarray) -> dict:
    """
    Extracts 4 statistical features from a 1D vibration signal array:
    1. RMS (Root Mean Square)
    2. Peak-to-Peak Amplitude
    3. Kurtosis (4th standardized moment)
    4. Standard Deviation
    """
    if len(signal) == 0:
        return {"rms": 0.0, "peak_to_peak": 0.0, "kurtosis": 3.0, "std": 0.0}

    signal = np.asarray(signal, dtype=np.float64)
    rms = np.sqrt(np.mean(signal ** 2))
    peak_to_peak = np.max(signal) - np.min(signal)
    std = np.std(signal)
    
    # Kurtosis: E[(X - mu)^4] / sigma^4
    if std > 1e-8:
        kurtosis = np.mean(((signal - np.mean(signal)) / std) ** 4)
    else:
        kurtosis = 3.0  # Normal distribution baseline

    return {
        "rms": float(rms),
        "peak_to_peak": float(peak_to_peak),
        "kurtosis": float(kurtosis),
        "std": float(std)
    }

def process_nasa_ims_file(filepath: str) -> dict:
    """Reads tab-separated NASA IMS bearing vibration file and extracts features per channel"""
    df = pd.read_csv(filepath, sep='\t', header=None)
    features_per_channel = {}
    
    # NASA IMS files usually have 4 columns (Bearing 1 Ch 1, Bearing 1 Ch 2, Bearing 2 Ch 1, Bearing 2 Ch 2)
    for col_idx in range(df.shape[1]):
        channel_name = f"channel_{col_idx + 1}"
        features_per_channel[channel_name] = extract_statistical_features(df.iloc[:, col_idx].values)
        
    return features_per_channel
