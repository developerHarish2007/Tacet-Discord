import os
from typing import Optional, Dict, Any
from verifier.agent import VerifierAgent
from investigation.engine import InvestigationEngine
from onboarding.factory_state import FactoryStateManager
from coordinator.llm_grounding import GroundedLLMReasoningEngine

class CoordinatorAgent:
    def __init__(self, verifier_agent: VerifierAgent = None):
        self.verifier = verifier_agent or VerifierAgent()
        self.investigation_engine = InvestigationEngine(verifier_agent=self.verifier)
        self.factory_state_manager = FactoryStateManager(memory_agent=self.verifier.memory)
        self.llm_engine = GroundedLLMReasoningEngine()

    def ask(self, image_path: str, telemetry_mode: str = "normal") -> dict:
        """Existing image-only ask entrypoint"""
        verify_res = self.verifier.verify(image_path=image_path, telemetry_mode=telemetry_mode)
        
        tier = verify_res["tier"]
        reasoning = verify_res["reasoning"]
        agent_outputs = verify_res.get("agent_outputs", {})
        
        percept = agent_outputs.get("perception", {})
        correl = agent_outputs.get("correlation", {})
        memory = agent_outputs.get("memory", {})
        match = memory.get("match")

        investigation_res = self.investigation_engine.evaluate_case(verify_res)
        factory_state = self.factory_state_manager.get_factory_state()

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
            tentative = f"TENTATIVE (Similarity {memory.get('similarity_score', 0.0)*100:.0f}%): {match.get('confirmed_diagnosis')}" if match else "TENTATIVE: New/Unseen Visual Anomaly Pattern"
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

    def ask_junior(
        self,
        question: str,
        image_path: Optional[str] = None,
        telemetry_mode: str = "normal"
    ) -> dict:
        """
        Junior Ask Entrypoint (Photo + Text Question):
        1. Runs perception analysis if image is provided.
        2. Retrieves top 1-3 grounded records via MemoryAgent hybrid matcher.
        3. Calls Grounded LLM Reasoning Engine.
        4. Runs explicit Hallucination-Check Gate.
        5. Verifies output through VerifierAgent.
        """
        percept_res = None
        query_text = question
        if image_path and os.path.exists(image_path):
            percept_res = self.verifier.perception.perceive(image_path)
            if percept_res and percept_res.get("extracted_text"):
                query_text = f"{question} [Image Label/OCR: '{percept_res['extracted_text']}']"

        # 2. Hybrid Memory Recall (TF-IDF Text + ResNet Visual)
        memory_hybrid_res = self.verifier.memory.recall_hybrid(
            image_path=image_path,
            text_query=query_text,
            top_k=3
        )
        retrieved_records = memory_hybrid_res.get("top_matches", [])

        # 3. Grounded LLM Generation & Hallucination Check Gate
        llm_grounding_res = self.llm_engine.generate_and_verify_answer(
            question=question,
            retrieved_records=retrieved_records,
            perception_output=percept_res
        )

        # 4. Verifier Cross-Examination & Confidence Tiering
        verify_junior_res = self.verifier.verify_junior_ask(
            llm_draft_answer=llm_grounding_res["draft_answer"],
            retrieved_records=retrieved_records,
            hallucination_check=llm_grounding_res,
            perception_res=percept_res
        )

        tier = verify_junior_res["tier"]
        has_hallucination = verify_junior_res["has_hallucination"]

        cross_modal_note = None
        if percept_res and retrieved_records and verify_junior_res["highest_similarity"] >= 0.35:
            rec_id = retrieved_records[0]["id"]
            sim_pct = int(verify_junior_res["highest_similarity"] * 100)
            cross_modal_note = f"💡 Multi-Modal Alignment: Grounded primarily via text query match against Record #{rec_id} ({sim_pct}% similarity). Image scan generated spatial heatmap."

        # Build reasoning trace including raw LLM output for Pipeline Trace tab
        reasoning_trace = {
            "perception": {
                "score": percept_res.get("anomaly_score", 0.0) if percept_res else None,
                "confidence": percept_res.get("mean_confidence", 0.0) if percept_res else None,
                "variance": percept_res.get("variance", 0.0) if percept_res else None,
                "dropout_pass_scores": percept_res.get("dropout_pass_scores", []) if percept_res else [],
                "extracted_ocr": percept_res.get("extracted_text", "") if percept_res else "",
                "summary": f"Perception: Score {percept_res['mean_confidence']:.2f}" if percept_res else "No image provided for visual scan"
            },
            "cross_modal_note": cross_modal_note,
            "memory": {
                "retrieved_count": len(retrieved_records),
                "top_similarity": retrieved_records[0]["similarity_score"] if retrieved_records else 0.0,
                "summary": f"Retrieved {len(retrieved_records)} records from memory (Top match sim: {retrieved_records[0]['similarity_score']*100:.0f}%)" if retrieved_records else "No matching records found in incident DB"
            },
            "llm_generation": {
                "raw_llm_output": llm_grounding_res.get("raw_llm_output", ""),
                "has_strong_match": llm_grounding_res.get("has_strong_match", False),
                "evidence_text": llm_grounding_res.get("evidence_text", "")
            },
            "hallucination_check": {
                "has_hallucination": has_hallucination,
                "passed_claims": llm_grounding_res["passed_claims"],
                "failed_claims": llm_grounding_res["failed_claims"]
            },
            "verifier": {
                "tier": tier,
                "tier_label": verify_junior_res["tier_label"],
                "reasoning": verify_junior_res["reasoning"]
            }
        }

        # Warning banner for Tier 3
        warning_banner = None
        if tier == 3:
            warning_banner = "⚠️ General knowledge estimate — not grounded in historical records, may be inaccurate, confirm with a senior technician."

        factory_state = self.factory_state_manager.get_factory_state()

        return {
            "tier": tier,
            "tier_label": verify_junior_res["tier_label"],
            "question": question,
            "image_path": image_path,
            "heatmap_path": percept_res.get("heatmap_path") if percept_res else None,
            "answer": llm_grounding_res["draft_answer"],
            "raw_llm_output": llm_grounding_res.get("raw_llm_output", ""),
            "grounded_sources": llm_grounding_res["grounded_sources"],
            "retrieved_records": retrieved_records,
            "warning_banner": warning_banner,
            "verifier_reasoning": verify_junior_res["reasoning"],
            "reasoning_trace": reasoning_trace,
            "factory_state": factory_state,
            "status": "success"
        }
