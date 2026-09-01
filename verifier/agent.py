import os
from perception.agent import PerceptionAgent
from correlation.agent import CorrelationAgent
from memory.agent import MemoryAgent
from verifier.rules import evaluate_stage_a_rules
from verifier.negotiation import evaluate_stage_b_negotiation

class VerifierAgent:
    def __init__(
        self,
        perception_agent: PerceptionAgent = None,
        correlation_agent: CorrelationAgent = None,
        memory_agent: MemoryAgent = None
    ):
        self.perception = perception_agent or PerceptionAgent()
        self.correlation = correlation_agent or CorrelationAgent()
        self.memory = memory_agent or MemoryAgent()

    def verify(self, image_path: str, telemetry_mode: str = "normal") -> dict:
        """
        Cross-examines Perception, Correlation, and Memory outputs.
        Executes Stage A deterministic rule-based evaluation and Stage B tiebreaker negotiation.
        """
        # 1. Gather outputs from earlier phase agents
        percept_res = self.perception.perceive(image_path)
        
        mean_confidence = float(percept_res["mean_confidence"])
        variance = float(percept_res["variance"])
        anomaly_score = float(percept_res["anomaly_score"])

        correl_res = self.correlation.correlate(
            telemetry_mode=telemetry_mode,
            perception_score=anomaly_score
        )
        
        agrees_with_perception = bool(correl_res["agrees_with_perception"])
        sensor_anomaly = bool(correl_res["sensor_anomaly"])

        memory_res = self.memory.recall(image_path)
        
        match_info = memory_res.get("match")
        similarity_score = float(memory_res.get("similarity_score", 0.0))
        has_match = match_info is not None and similarity_score >= 0.30

        # 2. Stage A: Enforce exact rule-based tier evaluation
        tier, reasoning = evaluate_stage_a_rules(
            mean_confidence=mean_confidence,
            variance=variance,
            agrees_with_perception=agrees_with_perception,
            sensor_anomaly=sensor_anomaly,
            similarity_score=similarity_score,
            has_match=has_match
        )

        # 3. Stage B: Execute tiebreaker negotiation
        stage_b = evaluate_stage_b_negotiation(
            agrees_with_perception=agrees_with_perception,
            mean_confidence=mean_confidence,
            match_info=match_info,
            similarity_score=similarity_score
        )

        tier_labels = {
            1: "Tier 1: High-Confidence Confirmed Match",
            2: "Tier 2: Unconfirmed / Tentative Answer",
            3: "Tier 3: No Confident Match - Redirection to Senior Required"
        }

        return {
            "tier": tier,
            "tier_label": tier_labels.get(tier, "Tier 3: No Match"),
            "reasoning": reasoning,
            "auditable_values": {
                "mean_confidence": round(mean_confidence, 4),
                "variance": round(variance, 6),
                "agrees_with_perception": agrees_with_perception,
                "sensor_anomaly": sensor_anomaly,
                "similarity_score": round(similarity_score, 4),
                "has_match": has_match
            },
            "stage_b_tiebreaker": stage_b,
            "agent_outputs": {
                "perception": percept_res,
                "correlation": correl_res,
                "memory": memory_res
            },
            "status": "success"
        }
