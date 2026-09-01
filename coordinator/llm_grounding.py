import os
import re
import json
import urllib.request
from typing import List, Dict, Any, Tuple, Optional

class GroundedLLMReasoningEngine:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "auto").lower()
        self.local_model = os.getenv("LOCAL_MODEL")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.nvidia_key = os.getenv("NVIDIA_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self._auto_detect_local_model()

    def _auto_detect_local_model(self):
        """Auto-detects installed Ollama model from local server tags if LOCAL_MODEL is not set"""
        if self.local_model:
            return
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                if models:
                    self.local_model = models[0]
                    print(f"Auto-detected local Ollama model: '{self.local_model}'")
        except Exception:
            pass

        if not self.local_model:
            self.local_model = "gemma4:latest"

    def generate_and_verify_answer(
        self,
        question: str,
        retrieved_records: List[Dict[str, Any]],
        perception_output: Optional[Dict[str, Any]] = None,
        correlation_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generates grounded or general-knowledge LLM answer using provided evidence records or domain knowledge,
        then executes an explicit Hallucination-Check Gate.
        """
        # 1. Prepare grounding evidence summary
        evidence_summary_lines = []
        grounded_sources = []

        if perception_output:
            score = perception_output.get("mean_confidence", perception_output.get("anomaly_score", 0.0))
            var = perception_output.get("variance", 0.0)
            evidence_summary_lines.append(f"[Visual Perception] Anomaly score: {score:.2f}, Variance: {var:.4f}")
            grounded_sources.append("Perception Agent visual anomaly scan")

        if correlation_output:
            rul = correlation_output.get("predicted_rul_hours")
            feature = correlation_output.get("top_contributing_feature")
            evidence_summary_lines.append(f"[Telemetry Correlation] Predicted RUL: {rul} hours ({feature})")

        has_strong_match = len(retrieved_records) > 0 and retrieved_records[0].get("similarity_score", 0.0) >= 0.35

        for idx, rec in enumerate(retrieved_records, 1):
            diag = rec.get("confirmed_diagnosis", "")
            fix = rec.get("fix_steps", "")
            prov = rec.get("provenance", "seeded_dataset")
            sim = rec.get("similarity_score", 0.0)
            evidence_summary_lines.append(
                f"[Record #{rec['id']} - {prov} (Similarity {sim*100:.0f}%)] Diagnosis: '{diag}' | Fix Steps: '{fix}'"
            )
            if has_strong_match:
                grounded_sources.append(f"Historical Incident #{rec['id']} ({prov})")

        evidence_text = "\n".join(evidence_summary_lines) if evidence_summary_lines else "No matching historical records found."

        # 2. Call LLM to generate raw draft answer
        raw_llm_output = self._call_llm_backend(question, evidence_text, has_strong_match)

        # 3. Format draft answer with label if no strong record match
        if not has_strong_match:
            draft_answer = (
                "General knowledge estimate — not grounded in historical records, may be inaccurate, confirm with a senior technician.\n\n"
                f"{raw_llm_output}"
            )
            grounded_sources = ["General Domain Knowledge (Unanchored to DB)"]
        else:
            draft_answer = raw_llm_output

        # 4. Hallucination Check Gate - Extract factual claims and check against evidence & false record citations
        passed_claims, failed_claims, has_hallucination = self._hallucination_check_gate(
            raw_llm_output=raw_llm_output,
            draft_answer=draft_answer,
            retrieved_records=retrieved_records if has_strong_match else [],
            perception_output=perception_output,
            correlation_output=correlation_output,
            has_strong_match=has_strong_match
        )

        return {
            "draft_answer": draft_answer,
            "raw_llm_output": raw_llm_output,
            "grounded_sources": grounded_sources,
            "passed_claims": passed_claims,
            "failed_claims": failed_claims,
            "has_hallucination": has_hallucination,
            "has_strong_match": has_strong_match,
            "evidence_text": evidence_text
        }

    def _call_llm_backend(
        self,
        question: str,
        evidence_text: str,
        has_strong_match: bool
    ) -> str:
        """
        Calls LLM backend (Hosted API -> Local Gemma -> General Knowledge Synthesizer).
        Always queries LLM with junior's specific question for best-effort reasoning.
        """
        if has_strong_match:
            system_prompt = (
                "You are TACET DISCORD's Senior Technician Grounded Assistant. "
                "Answer the junior technician's question using ONLY the provided evidence records as grounding. "
                "Explicitly cite the record diagnosis and fix steps."
            )
            user_prompt = f"Question: {question}\n\nGrounding Evidence:\n{evidence_text}"
        else:
            system_prompt = (
                "You are TACET DISCORD's Senior Technician Assistant. "
                "No matching historical incident records were found in the database for this specific query. "
                "Provide a real, specific, best-effort technical troubleshooting answer for the junior technician's question based on general knowledge. "
                "Do NOT invent fake record numbers or cite fake database IDs."
            )
            user_prompt = f"Question: {question}\n\nNote: No matching database records available."

        # 1. Gemini API Override
        if self.gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
                payload = {"contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}]}
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as e:
                print(f"Gemini API call failed ({e}); checking next provider.")

        # 2. Groq API Override
        if self.groq_key:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    "temperature": 0.2
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.groq_key}"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"Groq API call failed ({e}); checking next provider.")

        # 3. NVIDIA Nim API Override
        if self.nvidia_key:
            try:
                url = "https://integrate.api.nvidia.com/v1/chat/completions"
                payload = {
                    "model": "google/gemma-2-9b-it",
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    "temperature": 0.2
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.nvidia_key}"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"NVIDIA API call failed ({e}); checking next provider.")

        # 4. OpenAI API Override
        if self.openai_key:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    "temperature": 0.2
                }
                req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.openai_key}"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    return data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"OpenAI API call failed ({e}); checking local Gemma.")

        # 5. Local Gemma Support (via Ollama http://localhost:11434/api/generate)
        try:
            self._auto_detect_local_model()
            url = "http://localhost:11434/api/generate"
            payload = {
                "model": self.local_model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                ans = data.get("response", "").strip()
                if ans:
                    return ans
        except Exception as e:
            print(f"Local Ollama ({self.local_model}) query failed: {e}")

        # 6. Technical Synthesizer (Question-specific fallback if all LLMs fail)
        words = [w for w in re.findall(r'\b[a-z0-9]+\b', question.lower()) if len(w) > 3]
        topic = ", ".join(words[:4]) if words else "the reported component"
        return (
            f"Regarding '{question}', immediate technical assessment for {topic} recommends isolating the area, "
            f"cleaning any spilled liquid or physical debris, drying exposed electrical housings, inspecting sensor ports, "
            f"and performing a dry test run before resuming automated machine cycle."
        )

    def _hallucination_check_gate(
        self,
        raw_llm_output: str,
        draft_answer: str,
        retrieved_records: List[Dict[str, Any]],
        perception_output: Optional[Dict[str, Any]],
        correlation_output: Optional[Dict[str, Any]],
        has_strong_match: bool
    ) -> Tuple[List[str], List[str], bool]:
        """
        Hallucination Gate logic:
        - When strong records exist: verifies claim grounding against retrieved evidence.
        - When NO strong record match exists: flags any FAKE record citations as hallucinations, but accepts valid general estimates.
        """
        passed_claims = []
        failed_claims = []

        # Check for false record citations when no strong records match
        if not has_strong_match:
            fake_citations = re.findall(r'(?:record|incident|case)[\s#]*(\d+)', raw_llm_output, re.IGNORECASE)
            valid_ids = {str(r["id"]) for r in retrieved_records}
            for cite in fake_citations:
                if cite not in valid_ids:
                    failed_claims.append(f"FAILED (Ungrounded Citation): Falsely cited record #{cite} without DB evidence.")

            passed_claims.append("PASSED: Labeled as general domain knowledge estimate (unanchored to DB).")
            has_hallucination = len(failed_claims) > 0
            return passed_claims, failed_claims, has_hallucination

        # Standard Grounded Gate when records exist
        evidence_corpus_text = ""
        for rec in retrieved_records:
            evidence_corpus_text += f" {rec.get('confirmed_diagnosis', '')} {rec.get('fix_steps', '')} {json.dumps(rec.get('sensor_data', {}))}"
        if perception_output:
            evidence_corpus_text += f" {perception_output.get('anomaly_score', '')} {perception_output.get('variance', '')}"
        if correlation_output:
            evidence_corpus_text += f" {correlation_output.get('predicted_rul_hours', '')} {correlation_output.get('top_contributing_feature', '')}"

        corpus_tokens = set(re.findall(r'\b[a-z0-9]+\b', evidence_corpus_text.lower()))

        claims = []
        diag_matches = re.findall(r'(?:diagnosis|defect|failure|issue|mode)[\s:]*([A-Za-z0-9\s\-]+)', raw_llm_output, re.IGNORECASE)
        for d in diag_matches:
            clean_d = d.strip()[:40]
            if clean_d and len(clean_d) > 3:
                claims.append(f"Diagnosis claim: '{clean_d}'")

        num_matches = re.findall(r'\b\d+(?:\.\d+)?\s*(?:min|rpm|nm|k|c|h|hours|%)\b', raw_llm_output, re.IGNORECASE)
        for n in num_matches:
            claims.append(f"Operational parameter: '{n}'")

        action_matches = re.findall(r'(?:replace|clean|inspect|reduce|check|adjust|recalibrate)\s+[a-z0-9\s]{3,25}', raw_llm_output, re.IGNORECASE)
        for act in action_matches[:3]:
            claims.append(f"Fix action step: '{act.strip()}'")

        if not claims:
            claims = [f"Grounded statement: '{raw_llm_output[:50]}...'"]

        for claim in claims:
            claim_tokens = [t for t in re.findall(r'\b[a-z0-9]+\b', claim.lower()) if len(t) > 2 and t not in ['claim', 'operational', 'parameter', 'action', 'step', 'diagnosis', 'based', 'record']]
            if not claim_tokens:
                passed_claims.append(f"PASSED: {claim}")
                continue

            matches = [t for t in claim_tokens if t in corpus_tokens]
            match_ratio = len(matches) / len(claim_tokens) if claim_tokens else 1.0

            if match_ratio >= 0.4:
                passed_claims.append(f"PASSED: {claim}")
            else:
                failed_claims.append(f"FAILED (Ungrounded): {claim}")

        has_hallucination = len(failed_claims) > 0
        return passed_claims, failed_claims, has_hallucination
