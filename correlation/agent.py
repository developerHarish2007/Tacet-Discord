import os
import glob
import numpy as np
from correlation.features import process_nasa_ims_file
from correlation.lstm_model import RULPredictorLSTM
from correlation.shap_explainer import CachedSHAPExplainer

class CorrelationAgent:
    def __init__(self, data_dir: str = None):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.data_dir = data_dir or os.path.join(base_dir, "data", "nasa_ims")
        self.lstm_model = RULPredictorLSTM()
        self.shap_explainer = CachedSHAPExplainer()

    def correlate(self, telemetry_mode: str = "normal", perception_score: float = None) -> dict:
        """
        Runs correlation analysis on telemetry stream.
        Calculates predicted_rul_hours, top_contributing_feature, shap_summary,
        and checks whether telemetry agrees or disagrees with Perception score.
        """
        shap_info = self.shap_explainer.explain(telemetry_mode)
        
        predicted_rul = shap_info["predicted_rul_hours"]
        sensor_anomaly = shap_info["sensor_anomaly"]
        top_feature = shap_info["top_contributing_feature"]
        shap_summary = shap_info["shap_summary"]
        explanation_text = shap_info["explanation_text"]

        # Agreement / Disagreement logic against Perception Agent visual score
        agrees_with_perception = True
        disagreement_reason = None

        if perception_score is not None:
            # Case 1: Perception is confident of visual defect (score >= 0.65), but telemetry shows healthy bearing (RUL > 80h)
            if perception_score >= 0.65 and predicted_rul > 80.0:
                agrees_with_perception = False
                disagreement_reason = (
                    f"Conflict Detected: Perception Agent reports {perception_score*100:.1f}% visual defect confidence, "
                    f"but Correlation Agent vibration telemetry confirms healthy bearing operation with RUL of {predicted_rul} hours."
                )
            # Case 2: Perception sees clean surface (score <= 0.35), but telemetry indicates severe internal bearing failure (RUL <= 30h)
            elif perception_score <= 0.35 and predicted_rul <= 30.0:
                agrees_with_perception = False
                disagreement_reason = (
                    f"Conflict Detected: Perception Agent reports clean visual surface ({perception_score*100:.1f}% anomaly), "
                    f"but Correlation Agent vibration telemetry detects critical internal wear with RUL of only {predicted_rul} hours."
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
