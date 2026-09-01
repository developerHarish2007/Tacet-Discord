import os
from verifier.agent import VerifierAgent

class CoordinatorAgent:
    def __init__(self, verifier_agent: VerifierAgent = None):
        self.verifier = verifier_agent or VerifierAgent()

    def ask(self, image_path: str, telemetry_mode: str = "normal") -> dict:
        """
        Coordinator Agent Entrypoint:
        Calls /verify (which executes Perception -> Correlation -> Memory in sequence).
        Returns ONE final JSON response shaped strictly by the tier from /verify.
        """
        verify_res = self.verifier.verify(image_path=image_path, telemetry_mode=telemetry_mode)
        
        tier = verify_res["tier"]
        reasoning = verify_res["reasoning"]
        agent_outputs = verify_res.get("agent_outputs", {})
        
        percept = agent_outputs.get("perception", {})
        correl = agent_outputs.get("correlation", {})
        memory = agent_outputs.get("memory", {})
        match = memory.get("match")

        # Build clean reasoning trace for live UI dashboard display
        reasoning_trace = {
            "perception": {
                "score": percept.get("anomaly_score", 0.0),
                "confidence": percept.get("mean_confidence", 0.0),
                "variance": percept.get("variance", 0.0),
                "summary": f"Visual anomaly score {percept.get('anomaly_score', 0.0):.4f} (MC Dropout ±{percept.get('variance', 0.0):.6f})"
            },
            "correlation": {
                "predicted_rul": correl.get("predicted_rul_hours", 0.0),
                "sensor_anomaly": correl.get("sensor_anomaly", False),
                "agrees": correl.get("agrees_with_perception", True),
                "summary": f"Predicted RUL {correl.get('predicted_rul_hours', 0.0)}h ({correl.get('top_contributing_feature', 'Baseline')}). Agrees: {correl.get('agrees_with_perception', True)}"
            },
            "memory": {
                "similarity": memory.get("similarity_score", 0.0),
                "has_match": match is not None,
                "matched_diagnosis": match.get("confirmed_diagnosis") if match else None,
                "summary": f"Cosine similarity {memory.get('similarity_score', 0.0)*100:.1f}% against incident DB"
            },
            "verifier": {
                "tier": tier,
                "reasoning": reasoning,
                "stage_b_tiebreaker": verify_res.get("stage_b_tiebreaker")
            }
        }

        # Shape final response strictly by confidence tier
        if tier == 1:
            return {
                "tier": 1,
                "tier_label": "Tier 1: Confirmed Match (High Confidence)",
                "image_path": image_path,
                "heatmap_path": percept.get("heatmap_path"),
                "confirmed_diagnosis": match.get("confirmed_diagnosis") if match else "Confirmed Defect",
                "fix_steps": match.get("fix_steps") if match else "Follow standard maintenance procedure.",
                "voice_note_path": match.get("voice_note_path") if match else None,
                "verifier_reasoning": reasoning,
                "reasoning_trace": reasoning_trace,
                "status": "success"
            }
        elif tier == 2:
            # Tier 2 response: tentative diagnosis + UNCONFIRMED flag + who_to_ask + reasoning
            tentative = match.get("confirmed_diagnosis") if match else "Tentative Visual Anomaly Detected (Unconfirmed)"
            return {
                "tier": 2,
                "tier_label": "Tier 2: Unconfirmed / Tentative Diagnosis",
                "tentative_diagnosis": f"TENTATIVE: {tentative}",
                "unconfirmed": True,
                "who_to_ask": "Senior Tech on shift (Lead Specialist)",
                "heatmap_path": percept.get("heatmap_path"),
                "verifier_reasoning": reasoning,
                "reasoning_trace": reasoning_trace,
                "status": "success"
            }
        else:
            # Tier 3 response: redirect message ONLY, NO diagnosis guess
            return {
                "tier": 3,
                "tier_label": "Tier 3: No Match - Safe Redirection Required",
                "redirect_message": "Not confident enough — escalate to a senior technician",
                "verifier_reasoning": reasoning,
                "reasoning_trace": reasoning_trace,
                "status": "success"
            }
