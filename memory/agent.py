import os
import glob
import numpy as np
from memory.database import IncidentDatabase
from memory.embeddings import ResNetEmbeddingExtractor, cosine_similarity

class MemoryAgent:
    def __init__(self, data_dir: str = None, db_path: str = None, force_reseed: bool = False):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.data_dir = data_dir or os.path.join(base_dir, "data", "mvtec", "bottle")
        self.db = IncidentDatabase(db_path=db_path)
        self.extractor = ResNetEmbeddingExtractor()
        
        if force_reseed:
            self.db.clear_database()
            
        self._seed_demo_incidents_if_empty()

    def _seed_demo_incidents_if_empty(self):
        """Seeds 8-10 fake-but-realistic confirmed incidents using real MVTec AD images with seeded: True"""
        existing = self.db.get_all_incidents()
        
        # Check if DB needs re-seeding (e.g. if PyTorch loaded after initial fallback seeding)
        needs_reseed = False
        if existing:
            # Test recall on first entry image to verify embedding dimension & model consistency
            first_img = existing[0]["image_path"]
            if os.path.exists(first_img):
                test_emb = self.extractor.get_embedding(first_img)
                sim = cosine_similarity(test_emb, existing[0]["embedding"])
                if sim < 0.8:  # Mismatch indicates model changed (e.g. PyTorch installed after NumPy fallback)
                    print("Detected model embedding mismatch. Re-seeding incident memory database...")
                    self.db.clear_database()
                    existing = []
                    needs_reseed = True

        if len(existing) >= 8 and not needs_reseed:
            return

        print("Seeding Memory Agent database with historical senior-confirmed incidents...")
        
        good_imgs = sorted(glob.glob(os.path.join(self.data_dir, "train", "good", "*.png")) + \
                           glob.glob(os.path.join(self.data_dir, "test", "good", "*.png")))
        broken_imgs = sorted(glob.glob(os.path.join(self.data_dir, "test", "broken_large", "*.png")) + \
                             glob.glob(os.path.join(self.data_dir, "test", "broken_small", "*.png")))

        demo_seed_configs = [
            {
                "img": broken_imgs[0] if len(broken_imgs) > 0 else None,
                "diag": "Major Body Fracture - High Impact Line Collision",
                "steps": "1. Stop conveyor section 4\n2. Clear broken glass fragments\n3. Check side guide alignment before restarting.",
                "voice": "/audio/senior_note_fracture.mp3",
                "conf": 0.92
            },
            {
                "img": broken_imgs[1] if len(broken_imgs) > 1 else None,
                "diag": "Surface Hairline Scratch - Non-Structural Defect",
                "steps": "1. Inspect bottle neck gripping pads\n2. Clean rubber pads with isopropyl wipe\n3. Resume line at 80% speed.",
                "voice": "/audio/senior_note_scratch.mp3",
                "conf": 0.88
            },
            {
                "img": broken_imgs[2] if len(broken_imgs) > 2 else None,
                "diag": "Base Stress Crack - Thermal Shock Incident",
                "steps": "1. Verify washer water temperature manifold (Target 65C)\n2. Flush heat exchanger valve.",
                "voice": "/audio/senior_note_thermal.mp3",
                "conf": 0.85
            },
            {
                "img": broken_imgs[3] if len(broken_imgs) > 3 else None,
                "diag": "Sidewall Chipping - Starwheel Transfer Jam",
                "steps": "1. Check starwheel pocket clearance\n2. Replace worn nylon guide sleeve.",
                "voice": None,
                "conf": 0.87
            },
            {
                "img": good_imgs[0] if len(good_imgs) > 0 else None,
                "diag": "Normal Bottle Surface - No Anomaly Found",
                "steps": "1. No action required\n2. Baseline inspection verified.",
                "voice": None,
                "conf": 0.95
            },
            {
                "img": good_imgs[1] if len(good_imgs) > 1 else None,
                "diag": "Clean Surface Finish - Verification Pass",
                "steps": "1. Standard throughput pass.",
                "voice": None,
                "conf": 0.96
            },
            {
                "img": good_imgs[2] if len(good_imgs) > 2 else None,
                "diag": "Normal Neck & Rim - Baseline Pass",
                "steps": "1. Routine operation.",
                "voice": None,
                "conf": 0.94
            },
            {
                "img": broken_imgs[4] if len(broken_imgs) > 4 else (good_imgs[3] if len(good_imgs) > 3 else None),
                "diag": "Micro Cracking - Capping Head Overspec Pressure",
                "steps": "1. Reduce capper spindle torque to 2.4 Nm\n2. Inspect capping chuck wear.",
                "voice": "/audio/senior_note_capper.mp3",
                "conf": 0.89
            }
        ]

        count = 0
        for cfg in demo_seed_configs:
            img_path = cfg["img"]
            if not img_path or not os.path.exists(img_path):
                continue
            
            # Compute embedding ONCE at insert time
            emb = self.extractor.get_embedding(img_path)
            self.db.insert_incident(
                image_path=img_path,
                heatmap_path=None,
                embedding=emb,
                confirmed_diagnosis=cfg["diag"],
                fix_steps=cfg["steps"],
                voice_note_path=cfg["voice"],
                confidence_at_capture=cfg["conf"],
                seeded=True
            )
            count += 1
            
        print(f"Successfully seeded {count} demo incidents into SQLite.")

    def recall(self, image_path: str) -> dict:
        """
        Takes a new defect image, computes its embedding, and performs cosine similarity
        search against cached incident embeddings in SQLite.
        Returns single closest match. Returns match: null if similarity < 0.30.
        """
        if not os.path.exists(image_path):
            return {"match": None, "similarity_score": 0.0, "status": "image_not_found"}

        query_emb = self.extractor.get_embedding(image_path)
        incidents = self.db.get_all_incidents()

        if not incidents:
            return {"match": None, "similarity_score": 0.0, "status": "empty_database"}

        best_match = None
        best_sim = -1.0

        for inc in incidents:
            sim = cosine_similarity(query_emb, inc["embedding"])
            if sim >= best_sim:
                best_sim = sim
                best_match = inc

        best_sim = round(float(best_sim), 4)

        if best_sim < 0.30 or best_match is None:
            return {
                "match": None,
                "similarity_score": best_sim,
                "status": "no_match_below_threshold"
            }

        return {
            "match": {
                "id": best_match["id"],
                "image_path": best_match["image_path"],
                "heatmap_path": best_match["heatmap_path"],
                "confirmed_diagnosis": best_match["confirmed_diagnosis"],
                "fix_steps": best_match["fix_steps"],
                "voice_note_path": best_match["voice_note_path"],
                "confidence_at_capture": best_match["confidence_at_capture"],
                "timestamp": best_match["timestamp"],
                "seeded": best_match["seeded"]
            },
            "similarity_score": best_sim,
            "status": "match_found"
        }

    def remember(
        self,
        image_path: str,
        confirmed_diagnosis: str,
        fix_steps: str,
        heatmap_path: str = None,
        voice_note_path: str = None,
        confidence_at_capture: float = 0.85
    ) -> dict:
        """
        Inserts new senior-confirmed incident into SQLite with seeded: False.
        Computes embedding once at insert time.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")

        # Compute embedding ONCE at insert time
        emb = self.extractor.get_embedding(image_path)
        
        row_id = self.db.insert_incident(
            image_path=image_path,
            heatmap_path=heatmap_path,
            embedding=emb,
            confirmed_diagnosis=confirmed_diagnosis,
            fix_steps=fix_steps,
            voice_note_path=voice_note_path,
            confidence_at_capture=confidence_at_capture,
            seeded=False
        )

        return {
            "id": row_id,
            "image_path": image_path,
            "confirmed_diagnosis": confirmed_diagnosis,
            "fix_steps": fix_steps,
            "seeded": False,
            "status": "incident_remembered"
        }
