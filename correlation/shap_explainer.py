import os
import json

class CachedSHAPExplainer:
    def __init__(self, cache_file: str = None):
        if cache_file is None:
            cache_file = os.path.join(os.path.dirname(__file__), "shap_cache.json")
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading SHAP cache {self.cache_file}: {e}")
        return {}

    def explain(self, telemetry_mode: str = "normal") -> dict:
        """Returns precomputed SHAP attribution dictionary for given telemetry state"""
        mode_key = telemetry_mode.lower()
        if mode_key in self.cache:
            return self.cache[mode_key]
        
        # Fallback default if unknown mode requested
        return self.cache.get("normal", {
            "predicted_rul_hours": 140.0,
            "sensor_anomaly": False,
            "top_contributing_feature": "RMS Baseline",
            "shap_summary": {"rms": 0.5, "peak_to_peak": 0.2, "kurtosis": 0.2, "std": 0.1},
            "explanation_text": "Baseline telemetry operating normally."
        })
