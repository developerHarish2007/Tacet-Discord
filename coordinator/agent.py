import os
from verifier.agent import VerifierAgent
from investigation.engine import InvestigationEngine
from onboarding.factory_state import FactoryStateManager

class CoordinatorAgent:
    def __init__(self, verifier_agent: VerifierAgent = None):
        self.verifier = verifier_agent or VerifierAgent()
        self.investigation_engine = InvestigationEngine(verifier_agent=self.verifier)
        self.factory_state_manager = FactoryStateManager(memory_agent=self.verifier.memory)

    def ask(self, image_path: str, telemetry_mode: str = "normal") -> dict:
        """
        Coordinator Agent Entrypoint:
        Calls /verify (Perception -> Correlation -> Memory -> Verifier),
        attaches Active Evidence Gathering analysis & Factory Onboarding state,
        and returns ONE final JSON response shaped strictly by confidence tier.
        """
        verify_res = self.verifier.verify(image_path=image_path, telemetry_mode=telemetry_mode)
        
        tier = verify_res["tier"]
        reasoning = verify_res["reasoning"]
        agent_outputs = verify_res.get("agent_outputs", {})
        
        percept = agent_outputs.get("perception", {})
        correl = agent_outputs.get("correlation", {})
        memory = agent_outputs.get("memory", {})
        match = memory.get("match")

        # Active Evidence Gathering & Factory Onboarding State
        investigation_res = self.investigation_engine.evaluate_case(verify_res)
        factory_state = self.factory_state_manager.get_factory_state()

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
                "summary": f"Cosine similarity {memory.get('similarity_score', 0.0)*100:.1f}% against incident DB" if match else "No match in incident memory (<30% similarity)"
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
                "investigation": investigation_res,
                "factory_state": factory_state,
                "status": "success"
            }
        elif tier == 2:
            if match:
                tentative = f"TENTATIVE (Historical Similarity {memory.get('similarity_score', 0.0)*100:.0f}%): {match.get('confirmed_diagnosis')}"
            else:
                tentative = "TENTATIVE: New/Unseen Visual Anomaly Pattern (No Prior Incident Match)"
                
            return {
                "tier": 2,
                "tier_label": "Tier 2: Unconfirmed / Tentative Diagnosis",
                "image_path": image_path,
                "tentative_diagnosis": tentative,
                "unconfirmed": True,
                "who_to_ask": "Senior Tech on shift (Lead Specialist)",
                "heatmap_path": percept.get("heatmap_path"),
                "verifier_reasoning": reasoning,
                "reasoning_trace": reasoning_trace,
                "investigation": investigation_res,
                "factory_state": factory_state,
                "status": "success"
            }
        else:
            return {
                "tier": 3,
                "tier_label": "Tier 3: No Match - Safe Redirection Required",
                "image_path": image_path,
                "redirect_message": "Not confident enough — escalate to a senior technician",
                "verifier_reasoning": reasoning,
                "reasoning_trace": reasoning_trace,
                "investigation": investigation_res,
                "factory_state": factory_state,
                "status": "success"
            }
