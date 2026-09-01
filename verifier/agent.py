import os
from typing import Dict, Any, Optional
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
        percept_res = self.perception.perceive(image_path)
        mean_confidence = float(percept_res["mean_confidence"])
        variance = float(percept_res["variance"])

        correl_res = self.correlation.correlate(
            telemetry_mode=telemetry_mode,
            perception_score=mean_confidence,
            file_path=image_path
        )
        
        agrees_with_perception = bool(correl_res["agrees_with_perception"])
        sensor_anomaly = bool(correl_res["sensor_anomaly"])

        memory_res = self.memory.recall(image_path)
        
        match_info = memory_res.get("match")
        similarity_score = float(memory_res.get("similarity_score", 0.0))
        has_match = match_info is not None and similarity_score >= 0.30

        tier, reasoning = evaluate_stage_a_rules(
            mean_confidence=mean_confidence,
            variance=variance,
            agrees_with_perception=agrees_with_perception,
            sensor_anomaly=sensor_anomaly,
            similarity_score=similarity_score,
            has_match=has_match
        )

        stage_b = evaluate_stage_b_negotiation(
            agrees_with_perception=agrees_with_perception,
            mean_confidence=mean_confidence,
            match_info=match_info,
            similarity_score=similarity_score
        )

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

    def verify_junior_ask(
        self,
        llm_draft_answer: str,
        retrieved_records: list,
        hallucination_check: dict,
        perception_res: Optional[dict] = None
    ) -> dict:
        """
        Cross-examines LLM draft answer for Junior Ask flow.
        Enforces Hallucination Verification Gate & Memory match thresholds:
        - If false record citation or ungrounded claim -> Tier 3.
        - If highest similarity < 0.35 -> Tier 3 General Knowledge Estimate.
        """
        has_hallucination = hallucination_check.get("has_hallucination", False)
        failed_claims = hallucination_check.get("failed_claims", [])
        passed_claims = hallucination_check.get("passed_claims", [])
        
        highest_similarity = 0.0
        if retrieved_records:
            highest_similarity = float(retrieved_records[0].get("similarity_score", 0.0))

        if has_hallucination:
            tier = 3
            reasoning = (
                f"Tier 3 (Hallucination Gate Flagged): The draft response contained ungrounded claim(s) or false record citation(s) "
                f"({len(failed_claims)} failed check). Downgraded to Tier 3 general estimate."
            )
        elif highest_similarity < 0.35:
            tier = 3
            reasoning = (
                f"Tier 3 (General Knowledge Estimate): No strong historical record match in DB (top match similarity {highest_similarity*100:.0f}% < 35%). "
                f"Providing general domain knowledge technical estimate."
            )
        elif highest_similarity >= 0.50:
            tier = 1
            reasoning = f"Tier 1 (High-Confidence Grounded Match): Answer grounded in record #{retrieved_records[0]['id']} (similarity {highest_similarity*100:.0f}%)."
        else:
            tier = 2
            reasoning = f"Tier 2 (Tentative Grounded Match): Partial evidence match (similarity {highest_similarity*100:.0f}%)."

        tier_labels = {
            1: "Tier 1: High-Confidence Grounded Match",
            2: "Tier 2: Tentative Match - Further Senior Verification Suggested",
            3: "Tier 3: General Knowledge Estimate - Senior Confirmation Required"
        }

        return {
            "tier": tier,
            "tier_label": tier_labels[tier],
            "reasoning": reasoning,
            "has_hallucination": has_hallucination,
            "hallucination_check": {
                "passed_claims": passed_claims,
                "failed_claims": failed_claims,
                "has_hallucination": has_hallucination
            },
            "highest_similarity": highest_similarity
        }
