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
        
        Fix 3 Note: Uses mean_confidence (the MC-Dropout-averaged score across 20 passes)
        as the single canonical Perception confidence metric across both Correlation and Verifier logic.
        """
        # 1. Perception Analysis
        percept_res = self.perception.perceive(image_path)
        
        # Canonical Perception confidence score: mean_confidence (MC-Dropout-averaged score over 20 passes)
        mean_confidence = float(percept_res["mean_confidence"])
        variance = float(percept_res["variance"])

        # 2. Correlation Analysis using canonical mean_confidence score
        correl_res = self.correlation.correlate(
            telemetry_mode=telemetry_mode,
            perception_score=mean_confidence
        )
        
        agrees_with_perception = bool(correl_res["agrees_with_perception"])
        sensor_anomaly = bool(correl_res["sensor_anomaly"])

        # 3. Memory Recall Analysis
        memory_res = self.memory.recall(image_path)
        
        match_info = memory_res.get("match")
        similarity_score = float(memory_res.get("similarity_score", 0.0))
        has_match = match_info is not None and similarity_score >= 0.30

        # 4. Stage A: Deterministic Rule Engine
        tier, reasoning = evaluate_stage_a_rules(
            mean_confidence=mean_confidence,
            variance=variance,
            agrees_with_perception=agrees_with_perception,
            sensor_anomaly=sensor_anomaly,
            similarity_score=similarity_score,
            has_match=has_match
        )

        # 5. Stage B: Tiebreaker Negotiation Engine
        stage_b = evaluate_stage_b_negotiation(
            agrees_with_perception=agrees_with_perception,
            mean_confidence=mean_confidence,
            match_info=match_info,
            similarity_score=similarity_score
        )

        # Fix 2: Stage B Negotiation Tier Upgrade Logic
        # When Stage A lands Tier 2 due to Perception/Correlation disagreement (agrees_with_perception is False),
        # AND Stage B's tiebreaker yields sides_with == "perception" with a strong memory match (similarity_score >= 0.70),
        # upgrade the verdict from Tier 2 back to Tier 1!
        if tier == 2 and not agrees_with_perception and similarity_score >= 0.70 and stage_b.get("sides_with") == "perception":
            tier = 1
            reasoning = (
                f"Tier 1 (Conflict Resolved via Memory Negotiation): Perception and Correlation initially disagreed, "
                f"but strong Memory match (ID #{match_info.get('id')}, sim: {similarity_score:.2f}) "
                f"confirmed historical defect diagnosis ('{match_info.get('confirmed_diagnosis')}'), "
                f"resolving the tie in favor of Perception."
            )
            stage_b["applied_to_verdict"] = True
            stage_b["upgrade_applied"] = True
        else:
            stage_b["applied_to_verdict"] = False
            stage_b["upgrade_applied"] = False

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
