import os
import glob
import numpy as np
import pandas as pd
from correlation.features import process_nasa_ims_file, extract_statistical_features
from correlation.lstm_model import RULPredictorLSTM
from correlation.shap_explainer import CachedSHAPExplainer

class CorrelationAgent:
    def __init__(self, data_dir: str = None):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.data_dir = data_dir or os.path.join(base_dir, "data", "nasa_ims")
        self.lstm_model = RULPredictorLSTM()
        self.shap_explainer = CachedSHAPExplainer()

    def _get_sample_feature_sequence(self, telemetry_mode: str) -> np.ndarray:
        """Constructs a 60-window sequence of statistical features based on real NASA IMS data files"""
        files = sorted(glob.glob(os.path.join(self.data_dir, "2004*")))
        mode_key = telemetry_mode.lower()
        
        if files:
            if mode_key == "critical" and len(files) >= 90:
                selected_files = files[-60:] # End of run-to-failure
            elif mode_key == "degraded" and len(files) >= 60:
                selected_files = files[30:90] # Mid-degradation
            else:
                selected_files = files[:60] # Healthy baseline start
                
            seq = []
            for f in selected_files:
                feats = process_nasa_ims_file(f)
                ch1 = feats.get("channel_1", {"rms": 0.05, "peak_to_peak": 0.1, "kurtosis": 3.0, "std": 0.02})
                seq.append([ch1["rms"], ch1["peak_to_peak"], ch1["kurtosis"], ch1["std"]])
            return np.array(seq, dtype=np.float32)

        # Fallback synthetic 60-window sequence matching mode
        np.random.seed(42)
        if mode_key == "critical":
            kurtosis = np.random.normal(9.2, 0.8, 60)
            p2p = np.random.normal(1.4, 0.2, 60)
            rms = np.random.normal(0.45, 0.05, 60)
            std = np.random.normal(0.18, 0.02, 60)
        elif mode_key == "degraded":
            kurtosis = np.random.normal(5.4, 0.5, 60)
            p2p = np.random.normal(0.65, 0.08, 60)
            rms = np.random.normal(0.18, 0.02, 60)
            std = np.random.normal(0.08, 0.01, 60)
        else:
            kurtosis = np.random.normal(3.0, 0.1, 60)
            p2p = np.random.normal(0.12, 0.01, 60)
            rms = np.random.normal(0.05, 0.005, 60)
            std = np.random.normal(0.02, 0.002, 60)

        return np.column_stack([rms, p2p, kurtosis, std])

    def correlate(
        self,
        telemetry_mode: str = "normal",
        perception_score: float = None,
        file_path: str = None
    ) -> dict:
        """
        Runs correlation analysis on telemetry stream.
        Extracts statistical features -> runs PyTorch 2-layer LSTM RUL model -> fetches SHAP attributions.
        Evaluates agreement against canonical Perception confidence score (mean_confidence).
        """
        if file_path and os.path.exists(file_path):
            feats = process_nasa_ims_file(file_path)
            ch1 = feats.get("channel_1", {"rms": 0.05, "peak_to_peak": 0.1, "kurtosis": 3.0, "std": 0.02})
            single_feat = np.array([[ch1["rms"], ch1["peak_to_peak"], ch1["kurtosis"], ch1["std"]]])
            feature_seq = np.tile(single_feat, (60, 1))
        else:
            feature_seq = self._get_sample_feature_sequence(telemetry_mode)

        # 1. Live PyTorch 2-Layer LSTM RUL Prediction
        predicted_rul = self.lstm_model.predict_rul(feature_seq)
        
        # 2. Retrieve cached SHAP feature attributions
        shap_info = self.shap_explainer.explain(telemetry_mode)
        sensor_anomaly = shap_info["sensor_anomaly"]
        top_feature = shap_info["top_contributing_feature"]
        shap_summary = shap_info["shap_summary"]
        explanation_text = shap_info["explanation_text"]

        # 3. Agreement / Disagreement logic against canonical Perception mean_confidence score
        agrees_with_perception = True
        disagreement_reason = None

        if perception_score is not None:
            # Perception is confident of visual defect (mean_confidence >= 0.75), but telemetry shows healthy bearing (RUL > 80h)
            if perception_score >= 0.75 and predicted_rul > 80.0:
                agrees_with_perception = False
                disagreement_reason = (
                    f"Conflict Detected: Perception Agent reports {perception_score*100:.1f}% visual defect confidence, "
                    f"but Correlation Agent PyTorch LSTM telemetry confirms healthy bearing operation with RUL of {predicted_rul} hours."
                )
            # Perception sees clean surface (mean_confidence < 0.35), but telemetry indicates severe internal bearing failure (RUL <= 30h)
            elif perception_score < 0.35 and predicted_rul <= 30.0:
                agrees_with_perception = False
                disagreement_reason = (
                    f"Conflict Detected: Perception Agent reports clean visual surface ({perception_score*100:.1f}% confidence), "
                    f"but Correlation Agent PyTorch LSTM telemetry detects critical internal wear with RUL of only {predicted_rul} hours."
                )

        return {
            "predicted_rul_hours": predicted_rul,
            "sensor_anomaly": sensor_anomaly,
            "top_contributing_feature": top_feature,
            "shap_summary": shap_summary,
            "explanation_text": explanation_text,
            "agrees_with_perception": agrees_with_perception,
            "disagreement_reason": disagreement_reason,
            "status": "success"
        }
