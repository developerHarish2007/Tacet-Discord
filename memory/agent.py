import os
import json
import glob
import numpy as np
from typing import List, Dict, Any, Optional
from memory.database import IncidentDatabase
from memory.embeddings import ResNetEmbeddingExtractor, cosine_similarity
from memory.text_matcher import SemanticTextMatcher
from scripts.download_ai4i_data import generate_ai4i_dataset

class MemoryAgent:
    def __init__(self, data_dir: str = None, db_path: str = None, force_reseed: bool = False):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.data_dir = data_dir or os.path.join(base_dir, "data", "mvtec", "bottle")
        self.ai4i_file = os.path.join(base_dir, "data", "ai4i2020_sampled.json")
        self.db = IncidentDatabase(db_path=db_path)
        self.extractor = ResNetEmbeddingExtractor()
        self.text_matcher = SemanticTextMatcher(model_name="all-MiniLM-L6-v2")
        
        if force_reseed:
            self.db.clear_database()
            
        self._seed_demo_incidents_if_empty()
        self._fit_text_matcher()

    def _fit_text_matcher(self):
        """Embeds all incident diagnosis & fix-step texts into the semantic vector store"""
        incidents = self.db.get_all_incidents()
        docs = []
        for inc in incidents:
            text = f"{inc['confirmed_diagnosis']} {inc['fix_steps']} {json.dumps(inc.get('sensor_data', {}))}"
            docs.append((inc["id"], text))
        self.text_matcher.fit_documents(docs)

    def _seed_demo_incidents_if_empty(self):
        """Seeds ~1,000 dataset records transformed from AI4I 2020 Predictive Maintenance Dataset"""
        existing = self.db.get_all_incidents()
        
        if len(existing) >= 900:
            return

        print("Seeding Memory Agent database with ~1,000 AI4I 2020 Predictive Maintenance records...")
        
        if os.path.exists(self.ai4i_file):
            try:
                with open(self.ai4i_file, "r", encoding="utf-8") as f:
                    ai4i_records = json.load(f)
            except Exception:
                ai4i_records = generate_ai4i_dataset(1000)
        else:
            ai4i_records = generate_ai4i_dataset(1000)

        # Clear old toy seed records
        self.db.clear_database()

        # Cache reference embedding for synthetic image paths
        dummy_emb = np.zeros(512, dtype=np.float32)
        sample_img = "data/mvtec/bottle/test/broken_large/000.png"
        if os.path.exists(sample_img):
            try:
                dummy_emb = self.extractor.get_embedding(sample_img)
            except Exception:
                pass

        count = 0
        for rec in ai4i_records:
            self.db.insert_incident(
                image_path=rec.get("image_path", sample_img),
                heatmap_path=rec.get("heatmap_path"),
                embedding=dummy_emb,
                confirmed_diagnosis=rec["confirmed_diagnosis"],
                fix_steps=rec["fix_steps"],
                voice_note_path=rec.get("voice_note_path"),
                confidence_at_capture=rec.get("confidence_at_capture", 0.90),
                seeded=True,
                provenance=rec.get("provenance", "seeded_dataset"),
                sensor_data=rec.get("sensor_data", {}),
                confirmed=rec.get("confirmed", True)
            )
            count += 1
            
        print(f"Successfully seeded {count} AI4I 2020 incidents into SQLite.")

    def recall(self, image_path: str) -> dict:
        """Single image recall backward compatibility"""
        res = self.recall_hybrid(image_path=image_path, text_query=None, top_k=1)
        if res["top_matches"]:
            top = res["top_matches"][0]
            return {
                "match": top,
                "similarity_score": top["similarity_score"],
                "status": "match_found"
            }
        return {"match": None, "similarity_score": 0.0, "status": "no_match_below_threshold"}

    def recall_hybrid(
        self,
        image_path: Optional[str] = None,
        text_query: Optional[str] = None,
        top_k: int = 3
    ) -> dict:
        """
        Hybrid recall method using ResNet image similarity and all-MiniLM-L6-v2 semantic text similarity.
        Returns top_k matching historical records with score breakdown.
        """
        incidents = self.db.get_all_incidents()
        if not incidents:
            return {"top_matches": [], "highest_similarity": 0.0, "status": "empty_database"}

        inc_map = {inc["id"]: inc for inc in incidents}

        # 1. Semantic Text Similarity Search (all-MiniLM-L6-v2)
        text_sims = {}
        if text_query and text_query.strip():
            matches = self.text_matcher.query(text_query, top_k=len(incidents))
            for m in matches:
                text_sims[m["id"]] = m["similarity_score"]

        # 2. ResNet Visual Image Similarity Search
        img_sims = {}
        if image_path and os.path.exists(image_path):
            query_emb = self.extractor.get_embedding(image_path)
            for inc in incidents:
                sim = cosine_similarity(query_emb, inc["embedding"])
                img_sims[inc["id"]] = float(sim)

        # 3. Combined Hybrid Score
        scored_records = []
        for inc_id, inc in inc_map.items():
            t_score = text_sims.get(inc_id, 0.0)
            v_score = img_sims.get(inc_id, 0.0)

            if image_path and text_query:
                combined_score = max(v_score, t_score, 0.6 * v_score + 0.4 * t_score)
            elif text_query:
                combined_score = t_score
            else:
                combined_score = v_score

            combined_score = round(float(combined_score), 4)

            if combined_score >= 0.15:
                scored_records.append({
                    "id": inc["id"],
                    "image_path": inc["image_path"],
                    "heatmap_path": inc["heatmap_path"],
                    "confirmed_diagnosis": inc["confirmed_diagnosis"],
                    "fix_steps": inc["fix_steps"],
                    "voice_note_path": inc["voice_note_path"],
                    "confidence_at_capture": inc["confidence_at_capture"],
                    "timestamp": inc["timestamp"],
                    "seeded": inc["seeded"],
                    "provenance": inc.get("provenance", "seeded_dataset"),
                    "sensor_data": inc.get("sensor_data", {}),
                    "confirmed": inc.get("confirmed", True),
                    "similarity_score": combined_score,
                    "text_similarity": round(t_score, 4),
                    "visual_similarity": round(v_score, 4)
                })

        scored_records.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_matches = scored_records[:top_k]

        highest_sim = top_matches[0]["similarity_score"] if top_matches else 0.0

        return {
            "top_matches": top_matches,
            "highest_similarity": highest_sim,
            "status": "match_found" if top_matches else "no_match"
        }

    def remember(
        self,
        image_path: Optional[str],
        confirmed_diagnosis: str,
        fix_steps: str,
        heatmap_path: str = None,
        voice_note_path: str = None,
        confidence_at_capture: float = 0.95,
        provenance: str = "senior_manual_entry",
        sensor_data: dict = None
    ) -> dict:
        """
        Inserts new senior-confirmed incident record into SQLite memory store.
        Embeds its text and adds it to the semantic vector store.
        """
        emb = np.zeros(512, dtype=np.float32)
        target_path = image_path or "data/mvtec/bottle/test/broken_large/000.png"

        if os.path.exists(target_path):
            emb = self.extractor.get_embedding(target_path)
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            alt_path = os.path.join(base_dir, target_path)
            if os.path.exists(alt_path):
                target_path = alt_path
                emb = self.extractor.get_embedding(target_path)

        row_id = self.db.insert_incident(
            image_path=target_path,
            heatmap_path=heatmap_path,
            embedding=emb,
            confirmed_diagnosis=confirmed_diagnosis,
            fix_steps=fix_steps,
            voice_note_path=voice_note_path,
            confidence_at_capture=confidence_at_capture,
            seeded=False,
            provenance=provenance,
            sensor_data=sensor_data or {},
            confirmed=True
        )

        # Add newly added senior record's text to the semantic vector store
        text_content = f"{confirmed_diagnosis} {fix_steps} {json.dumps(sensor_data or {})}"
        self.text_matcher.add_document(row_id, text_content)

        return {
            "id": row_id,
            "image_path": target_path,
            "confirmed_diagnosis": confirmed_diagnosis,
            "fix_steps": fix_steps,
            "provenance": provenance,
            "confirmed": True,
            "seeded": False,
            "status": "incident_remembered"
        }
